import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import GoogleAuthError
from googleapiclient.discovery import build
from config import Config
import base64
import email
from datetime import datetime, timedelta

class GmailService:
    # require both read and send permissions for our features
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send'
    ]
    
    def __init__(self, token_file=None):
        self.service = None
        self.token_file = token_file or Config.GMAIL_TOKEN_FILE
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API (used only if token file missing).

        For the web‑based OAuth flow our routes create the token; this
        method remains as a fallback during development or testing.
        """
        try:
            creds = None
            
            # Load token if exists
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # fallback; not normally used in production
                    flow = InstalledAppFlow.from_client_secrets_file(
                        Config.GMAIL_CREDENTIALS_FILE, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            print(f"Gmail authentication error: {str(e)}")
            return False
    
    def get_emails(self, max_results=10, query='is:unread'):
        """Get emails from inbox"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                email_data = self.get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
        except Exception as e:
            print(f"Error getting emails: {str(e)}")
            return []

    def get_emails_by_date(self, date_str, max_results=20):
        """Get emails received on a specific date.

        Accepted formats: dd/mm/yyyy, d/m/yyyy, yyyy-mm-dd, yyyy/mm/dd
        """
        try:
            target_date = self._parse_date(date_str)
            if not target_date:
                raise ValueError("Invalid date format. Use dd/mm/yyyy")

            next_date = target_date + timedelta(days=1)
            after_str = target_date.strftime('%Y/%m/%d')
            before_str = next_date.strftime('%Y/%m/%d')

            query = f"after:{after_str} before:{before_str}"
            return self.get_emails(max_results=max_results, query=query)
        except Exception as e:
            print(f"Error getting emails by date: {str(e)}")
            return []

    @staticmethod
    def _parse_date(date_str):
        if not date_str:
            return None

        date_str = date_str.strip()
        formats = ['%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d']

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None
    
    def get_email_details(self, message_id):
        """Get email details"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            
            # Extract header information
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract body
            body = self._get_email_body(message['payload'])
            
            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body,
                'snippet': message['snippet']
            }
        except Exception as e:
            print(f"Error getting email details: {str(e)}")
            return None
    
    def _get_email_body(self, payload):
        """Extract email body from payload - handles multipart, HTML, and plain text"""
        try:
            body = ""
            
            # If payload has multiple parts (multipart email)
            if 'parts' in payload:
                # Priority: text/plain > text/html > first available part
                text_plain = None
                text_html = None
                
                for part in payload['parts']:
                    mime_type = part.get('mimeType', '')
                    data = part['body'].get('data', '')
                    
                    if mime_type == 'text/plain' and data:
                        text_plain = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    elif mime_type == 'text/html' and data:
                        text_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    
                    # Handle nested parts (e.g., alternative/related)
                    if 'parts' in part and not body:
                        nested_body = self._get_email_body(part)
                        if nested_body and nested_body != "Could not extract email body":
                            body = nested_body
                
                # Prefer plain text over HTML
                if text_plain:
                    body = text_plain[:5000]  # Limit to first 5000 chars
                elif text_html:
                    body = text_html[:5000]
                elif body:
                    body = body[:5000]
                else:
                    body = ""
            else:
                # Simple payload (not multipart)
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')[:5000]
            
            return body if body else "Email body unavailable"
        except Exception as e:
            print(f"Error extracting email body: {str(e)}")
            return f"Error reading email: {str(e)[:100]}"
    
    def send_email(self, to, subject, body):
        """Send email reply"""
        try:
            message = self._create_message(to, subject, body)
            self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def _create_message(to, subject, body):
        """Create message for Gmail API"""
        import base64
        from email.mime.text import MIMEText
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}
