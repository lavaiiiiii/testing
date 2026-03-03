import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
IS_VERCEL = bool(os.getenv('VERCEL'))
DATA_DIR = os.path.join('/tmp', 'teacher-ai-assistant-data') if IS_VERCEL else os.path.join(PROJECT_ROOT, 'data')

class Config:
    # Flask config
    DEBUG = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    DATABASE_PATH = os.path.join(DATA_DIR, 'assistant.db')
    
    # OpenAI config
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # Mistral AI config
    MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
    MISTRAL_MODEL = os.getenv('MISTRAL_MODEL', 'mistral-small')

    # Claude (Anthropic) config
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-5-haiku-latest')

    # Gemini config
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

    # Multi-provider orchestration
    AI_PRIMARY_PROVIDER = os.getenv('AI_PRIMARY_PROVIDER', 'openai').lower()
    AI_PROVIDER_ORDER = os.getenv(
        'AI_PROVIDER_ORDER',
        'openai,mistral,claude,gemini'
    )
    AI_REQUEST_TIMEOUT = int(os.getenv('AI_REQUEST_TIMEOUT', 20))

    # Token optimization
    AI_MAX_CONTEXT_MESSAGES = int(os.getenv('AI_MAX_CONTEXT_MESSAGES', 6))
    AI_MAX_INPUT_CHARS = int(os.getenv('AI_MAX_INPUT_CHARS', 2800))
    AI_MAX_SYSTEM_PROMPT_CHARS = int(os.getenv('AI_MAX_SYSTEM_PROMPT_CHARS', 450))
    AI_DEFAULT_MAX_TOKENS = int(os.getenv('AI_DEFAULT_MAX_TOKENS', 220))
    AI_SUMMARY_MAX_TOKENS = int(os.getenv('AI_SUMMARY_MAX_TOKENS', 180))
    AI_REPLY_MAX_TOKENS = int(os.getenv('AI_REPLY_MAX_TOKENS', 220))
    AI_ANALYZE_MAX_TOKENS = int(os.getenv('AI_ANALYZE_MAX_TOKENS', 180))

    # Task-based provider routing (optional overrides)
    AI_TASK_PROVIDERS_CHAT = os.getenv('AI_TASK_PROVIDERS_CHAT', '')
    AI_TASK_PROVIDERS_SUMMARY = os.getenv('AI_TASK_PROVIDERS_SUMMARY', '')
    AI_TASK_PROVIDERS_REPLY = os.getenv('AI_TASK_PROVIDERS_REPLY', '')
    AI_TASK_PROVIDERS_ANALYZE = os.getenv('AI_TASK_PROVIDERS_ANALYZE', '')
    
    # Gmail config
    GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID')
    GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
    GMAIL_CREDENTIALS_FILE = os.path.join(DATA_DIR, 'gmail_credentials.json')
    GMAIL_TOKEN_FILE = os.path.join(DATA_DIR, 'gmail_token.pickle')
    # Optional: set this to the redirect URI registered in Google Cloud Console
    # e.g. 'http://localhost:5000/api/email/oauth2callback'
    GMAIL_REDIRECT_URI = os.getenv('GMAIL_REDIRECT_URI')
    
    # API config
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 5000))
