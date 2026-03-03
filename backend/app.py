from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Allow insecure OAuth transport for local development (HTTP)
# Must be set before importing google oauth flow modules
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

from config import Config
from models.schedule import Schedule
from models.history import History
from routes.chat import chat_bp
from routes.email import email_bp
from routes.schedule import schedule_bp

app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
# Allow CORS with credentials for the frontend origin(s) so session cookies are preserved
allowed_origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://192.168.0.102:5000"
]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# Register blueprints
app.register_blueprint(chat_bp)
app.register_blueprint(email_bp)
app.register_blueprint(schedule_bp)

# Ensure data directory exists
os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

# Initialize databases
Schedule.init_db()
History.init_db()

# Serve frontend
@app.route('/')
def serve_frontend():
    """Serve frontend index.html"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    if path.startswith('css/') or path.startswith('js/'):
        return send_from_directory('../frontend', path)
    return send_from_directory('../frontend', 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    gmail_from_env = bool(Config.GMAIL_CLIENT_ID and Config.GMAIL_CLIENT_SECRET)
    gmail_from_json = bool(Config.GMAIL_CREDENTIALS_JSON)
    gmail_from_file = os.path.exists(Config.GMAIL_CREDENTIALS_FILE)

    ai_map = {
        'openai': bool(Config.OPENAI_API_KEY),
        'mistral': bool(Config.MISTRAL_API_KEY),
        'claude': bool(Config.CLAUDE_API_KEY),
        'gemini': bool(Config.GEMINI_API_KEY)
    }
    missing_ai = [name for name, ok in ai_map.items() if not ok]

    return jsonify({
        'status': 'running',
        'openai_configured': ai_map['openai'],
        'mistral_configured': ai_map['mistral'],
        'claude_configured': ai_map['claude'],
        'gemini_configured': ai_map['gemini'],
        'ai_providers_configured': [name for name, ok in ai_map.items() if ok],
        'ai_missing_providers': missing_ai,
        'gmail_configured': gmail_from_env or gmail_from_json or gmail_from_file,
        'gmail_config_source': 'env' if gmail_from_env else ('env_json' if gmail_from_json else ('file' if gmail_from_file else 'missing')),
        'gmail_expected_env': [
            'GMAIL_CLIENT_ID / GOOGLE_CLIENT_ID / GOOGLE_OAUTH_CLIENT_ID / OAUTH_CLIENT_ID',
            'GMAIL_CLIENT_SECRET / GOOGLE_CLIENT_SECRET / GOOGLE_OAUTH_CLIENT_SECRET / OAUTH_CLIENT_SECRET',
            'GMAIL_CREDENTIALS_JSON / GOOGLE_OAUTH_CLIENT_JSON (optional alternative)'
        ]
    })

if __name__ == '__main__':
    app.run(host=Config.API_HOST, port=Config.API_PORT, debug=Config.DEBUG)
