from flask import Blueprint, request, jsonify, redirect, url_for, session
import os
import sys
import pickle
import json
import base64
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from services.gmail_service import GmailService
from services.mistral_service import MistralService
from services.ai_service import AIService
from models.history import History
from config import Config
from utils.user_context import get_current_user_id, get_user_db_path, get_user_token_file

"""Email-related endpoints including OAuth login and Gmail access"""
email_bp = Blueprint('email', __name__, url_prefix='/api/email')

# Initialize Mistral AI service
mistral_service = MistralService()
ai_service = AIService()


def _fetch_google_userinfo(creds):
    """Fetch Google account profile (email, name, picture) from UserInfo endpoint."""
    try:
        token_value = getattr(creds, 'token', None)
        if not token_value:
            return {}

        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {token_value}'},
            timeout=8
        )
        if response.status_code != 200:
            return {}

        data = response.json() or {}
        return {
            'email': data.get('email', ''),
            'name': data.get('name', ''),
            'picture': data.get('picture', '')
        }
    except Exception:
        return {}


def _load_gmail_service(user_id):
    """Return GmailService instance if credentials token exists."""
    if not user_id or user_id == 'default':
        return None
    token_file = get_user_token_file(user_id)
    if os.path.exists(token_file):
        try:
            return GmailService(token_file=token_file)
        except Exception as e:
            print(f"Error creating GmailService: {e}")
    return None


def _clear_oauth_state(user_id):
    """Clear OAuth token/session so another user can sign in."""
    token_file = get_user_token_file(user_id)

    if os.path.exists(token_file):
        try:
            os.remove(token_file)
        except Exception as e:
            print(f"Error deleting token file: {e}")

    # Clear oauth session keys
    session.pop('oauth_state', None)
    session.pop('oauth_code_verifier', None)
    session.pop('oauth_user_id', None)
    session.pop('gmail_user_email', None)
    session.pop('gmail_user_name', None)
    session.pop('gmail_user_picture', None)
    session.pop('user_id', None)


def _get_redirect_uri():
    """Return configured redirect URI or build from request."""
    configured = (getattr(Config, 'GMAIL_REDIRECT_URI', None) or '').strip()
    if configured:
        # Prevent localhost redirect leak when running on Vercel
        if not (os.getenv('VERCEL') and 'localhost' in configured.lower()):
            return configured

    # Prefer forwarded host/proto from reverse proxy (Vercel)
    forwarded_host = request.headers.get('x-forwarded-host', '').strip()
    forwarded_proto = request.headers.get('x-forwarded-proto', '').strip() or 'https'
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}/api/email/oauth2callback"

    # Fallback to Flask-generated URL
    return url_for('email.oauth2callback', _external=True)


def _build_oauth_flow(state=None):
    """Create OAuth flow from env vars (preferred) or credentials file."""
    redirect_uri = _get_redirect_uri()

    raw_credentials_json = (Config.GMAIL_CREDENTIALS_JSON or '').strip()
    if raw_credentials_json:
        candidates = [raw_credentials_json]

        # Remove wrapping quotes if env was pasted as a quoted JSON string
        if (raw_credentials_json.startswith('"') and raw_credentials_json.endswith('"')) or (
            raw_credentials_json.startswith("'") and raw_credentials_json.endswith("'")
        ):
            candidates.append(raw_credentials_json[1:-1])

        # Try base64-decoded variant as well
        try:
            decoded = base64.b64decode(raw_credentials_json).decode('utf-8')
            if decoded:
                candidates.append(decoded)
        except Exception:
            pass

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict) and 'installed' in parsed and 'web' not in parsed:
                    parsed = {'web': parsed.get('installed', {})}

                if isinstance(parsed, dict) and 'web' in parsed:
                    web_cfg = parsed.get('web') or {}
                    redirect_uris = web_cfg.get('redirect_uris') or []
                    if redirect_uri and redirect_uri not in redirect_uris:
                        web_cfg['redirect_uris'] = redirect_uris + [redirect_uri]
                    parsed['web'] = web_cfg

                return Flow.from_client_config(
                    parsed,
                    scopes=GmailService.SCOPES,
                    state=state,
                    redirect_uri=redirect_uri
                )
            except Exception:
                continue

    client_id = (Config.GMAIL_CLIENT_ID or '').strip()
    client_secret = (Config.GMAIL_CLIENT_SECRET or '').strip()
    if client_id and client_secret:
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [redirect_uri]
            }
        }
        return Flow.from_client_config(
            client_config,
            scopes=GmailService.SCOPES,
            state=state,
            redirect_uri=redirect_uri
        )

    if os.path.exists(Config.GMAIL_CREDENTIALS_FILE):
        return Flow.from_client_secrets_file(
            Config.GMAIL_CREDENTIALS_FILE,
            scopes=GmailService.SCOPES,
            state=state,
            redirect_uri=redirect_uri
        )

    raise RuntimeError(
        'Gmail OAuth chưa được cấu hình. Vui lòng set GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET '
        'hoặc GMAIL_CREDENTIALS_JSON trên Vercel.'
    )


@email_bp.route('/oauth-config-check', methods=['GET'])
def oauth_config_check():
    """Safe diagnostics for OAuth configuration (no secret values)."""
    return jsonify({
        'success': True,
        'has_client_id': bool((Config.GMAIL_CLIENT_ID or '').strip()),
        'has_client_secret': bool((Config.GMAIL_CLIENT_SECRET or '').strip()),
        'has_credentials_json': bool((Config.GMAIL_CREDENTIALS_JSON or '').strip()),
        'has_credentials_file': os.path.exists(Config.GMAIL_CREDENTIALS_FILE),
        'redirect_uri_preview': _get_redirect_uri()
    })


@email_bp.route('/get-unread', methods=['GET'])
def get_unread_emails():
    """Get unread emails filtered by selected category using AI classifier."""
    user_id = get_current_user_id(request, session=session)
    service = _load_gmail_service(user_id)
    if not service:
        return jsonify({'error': 'not_authenticated', 'auth_url': url_for('email.gmail_auth', _external=True)}), 401

    try:
        max_results = request.args.get('max_results', 10, type=int)
        filter_type = request.args.get('filter', 'education', type=str).strip().lower()

        # Pull extra rows when applying specific filters to keep enough results
        fetch_count = max_results if filter_type == 'all' else min(max_results * 4, 80)
        raw_emails = service.get_emails(max_results=fetch_count, query='is:unread')

        filtered_emails = mistral_service.batch_classify_emails(raw_emails, filter_type=filter_type)
        filtered_emails = filtered_emails[:max_results]
        
        return jsonify({
            'success': True,
            'filter': filter_type,
            'emails': filtered_emails,
            'total_filtered': len(raw_emails),
            'matched_count': len(filtered_emails)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@email_bp.route('/send-reply', methods=['POST'])
def send_email_reply():
    """Send email reply; requires authentication."""
    user_id = get_current_user_id(request, session=session)
    service = _load_gmail_service(user_id)
    db_path = get_user_db_path(user_id)
    if not service:
        return jsonify({'error': 'not_authenticated', 'auth_url': url_for('email.gmail_auth', _external=True)}), 401

    data = request.get_json()
    to_email = data.get('to', '').strip()
    subject = data.get('subject', '').strip()
    body = data.get('body', '').strip()

    if not all([to_email, subject, body]):
        return jsonify({'error': 'Missing email details'}), 400

    try:
        success = service.send_email(to_email, subject, body)
        if success:
            History.create(f"Gửi email tới {to_email}", body, action_type='email_sent', db_path=db_path)
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to send email'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@email_bp.route('/auth-status', methods=['GET'])
def gmail_auth_status():
    """Return whether Gmail is currently authenticated."""
    user_id = get_current_user_id(request, session=session)
    token_file = get_user_token_file(user_id)
    connected_at = None
    if os.path.exists(token_file):
        try:
            connected_at = os.path.getmtime(token_file)
        except Exception:
            connected_at = None

    return jsonify({
        'success': True,
        'user_id': user_id,
        'gmail_email': session.get('gmail_user_email'),
        'gmail_name': session.get('gmail_user_name'),
        'gmail_picture': session.get('gmail_user_picture'),
        'connected_at': connected_at,
        'authenticated': os.path.exists(token_file)
    })


@email_bp.route('/logout', methods=['POST'])
def gmail_logout():
    """Log out Gmail by revoking token (if possible) and clearing local credentials."""
    try:
        user_id = get_current_user_id(request, session=session)
        token_file = get_user_token_file(user_id)

        # Best-effort revoke
        if os.path.exists(token_file):
            try:
                with open(token_file, 'rb') as token_handle:
                    creds = pickle.load(token_handle)
                token_value = getattr(creds, 'token', None)
                if token_value:
                    requests.post(
                        'https://oauth2.googleapis.com/revoke',
                        params={'token': token_value},
                        headers={'content-type': 'application/x-www-form-urlencoded'},
                        timeout=8
                    )
            except Exception as revoke_err:
                print(f"Token revoke skipped: {revoke_err}")

        _clear_oauth_state(user_id)
        return jsonify({'success': True, 'message': 'Đã đăng xuất Gmail'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@email_bp.route('/summarize-by-date', methods=['POST'])
def summarize_emails_by_date():
    """Summarize emails received on a specific date and return tabular report."""
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    service = _load_gmail_service(user_id)
    if not service:
        return jsonify({'error': 'not_authenticated', 'auth_url': url_for('email.gmail_auth', _external=True)}), 401

    data = request.get_json() or {}
    date_str = (data.get('date') or '').strip()
    max_results = int(data.get('max_results', 20))

    if not date_str:
        return jsonify({'error': 'Missing date. Expected format dd/mm/yyyy'}), 400

    try:
        emails = service.get_emails_by_date(date_str, max_results=max_results)
        if not emails:
            return jsonify({
                'success': True,
                'date': date_str,
                'total_emails': 0,
                'rows': []
            })

        rows = ai_service.summarize_email_report(emails)

        History.create(
            f"Báo cáo tóm tắt email theo ngày {date_str}",
            f"Tổng {len(rows)} email đã được tóm tắt",
            action_type='email_daily_summary',
            db_path=db_path
        )

        return jsonify({
            'success': True,
            'date': date_str,
            'total_emails': len(emails),
            'rows': rows
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# OAuth flow endpoints


@email_bp.route('/auth', methods=['GET'])
def gmail_auth():
    """Initiate OAuth2 login flow."""
    try:
        flow = _build_oauth_flow()
    except Exception as e:
        return jsonify({'error': str(e)}), 503

    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account consent'
    )
    # store the state and PKCE code_verifier in session; do not pickle the flow object
    session['oauth_state'] = state
    # try to capture code_verifier used for PKCE (name may differ by implementation)
    try:
        code_verifier = getattr(flow, 'code_verifier', None)
        if not code_verifier and hasattr(flow, '_client'):
            code_verifier = getattr(flow._client, 'code_verifier', None)
        if code_verifier:
            session['oauth_code_verifier'] = code_verifier
    except Exception:
        pass
    return redirect(auth_url)


@email_bp.route('/oauth2callback', methods=['GET'])
def oauth2callback():
    """Handle redirect from Google and store credentials."""
    # Rebuild the Flow using the stored state and client secrets
    state = session.pop('oauth_state', None)
    if not state:
        return jsonify({'error': 'flow_not_initialized'}), 400

    try:
        flow = _build_oauth_flow(state=state)
    except Exception as e:
        return jsonify({'error': str(e)}), 503
    # restore PKCE code_verifier from session if present
    code_verifier = session.pop('oauth_code_verifier', None)
    try:
        if code_verifier:
            # primary attempt: set attribute on flow
            try:
                setattr(flow, 'code_verifier', code_verifier)
            except Exception:
                pass
            # fallback: set on internal client object if present
            if hasattr(flow, '_client'):
                try:
                    setattr(flow._client, 'code_verifier', code_verifier)
                except Exception:
                    pass
    except Exception:
        pass

    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    # Identify Gmail account email from profile
    gmail_service = build('gmail', 'v1', credentials=creds)
    profile = gmail_service.users().getProfile(userId='me').execute()
    gmail_email = profile.get('emailAddress', '')

    # Fetch richer account profile for UI
    userinfo = _fetch_google_userinfo(creds)
    gmail_name = userinfo.get('name', '')
    gmail_picture = userinfo.get('picture', '')
    if userinfo.get('email'):
        gmail_email = userinfo.get('email')

    user_id = gmail_email or 'default'

    token_file = get_user_token_file(user_id)
    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)

    session['gmail_user_email'] = gmail_email
    session['gmail_user_name'] = gmail_name
    session['gmail_user_picture'] = gmail_picture
    session['user_id'] = user_id
    
    # Redirect back to frontend UI with success indicator
    return redirect('/?gmail_auth=success')


@email_bp.route('/auth_url', methods=['GET'])
def gmail_auth_url():
    """Return the OAuth authorization URL (JSON) so frontend can redirect."""
    try:
        flow = _build_oauth_flow()
    except Exception as e:
        return jsonify({'error': str(e)}), 503

    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account consent'
    )
    session['oauth_state'] = state
    # store PKCE verifier as well so callback can exchange token
    try:
        code_verifier = getattr(flow, 'code_verifier', None)
        if not code_verifier and hasattr(flow, '_client'):
            code_verifier = getattr(flow._client, 'code_verifier', None)
        if code_verifier:
            session['oauth_code_verifier'] = code_verifier
    except Exception:
        pass
    return jsonify({'auth_url': auth_url})
 
