#!/usr/bin/env python
"""
Setup script - Initialize environment and database
Run this once before first start
"""
import os
import sys
import subprocess

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set development environment
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

from backend.models.schedule import Schedule
from backend.models.history import History
from backend.models.user import User
from backend.config import Config

def setup_directories():
    """Create necessary directories"""
    dirs = [
        os.path.dirname(Config.DATABASE_PATH),
        os.path.join(os.path.dirname(Config.DATABASE_PATH), 'users'),
        os.path.dirname(Config.GMAIL_TOKEN_FILE),
        os.path.join(os.path.dirname(Config.GMAIL_TOKEN_FILE), 'users'),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"✓ Directory OK: {d}")

def setup_databases():
    """Initialize databases"""
    try:
        Schedule.init_db()
        print("✓ Schedule DB initialized")
        History.init_db()
        print("✓ History DB initialized")
        User.init_db()
        print("✓ User DB initialized")
    except Exception as e:
        print(f"⚠ DB initialization: {e}")

def setup_environment():
    """Check and report configuration"""
    print("\n📋 Configuration Status:")
    print(f"  Gmail Client ID: {'✓' if Config.GMAIL_CLIENT_ID else '✗ Not set'}")
    print(f"  Gmail Client Secret: {'✓' if Config.GMAIL_CLIENT_SECRET else '✗ Not set'}")
    print(f"  OpenAI Key: {'✓' if Config.OPENAI_API_KEY else '✗ Not set'}")
    print(f"  Mistral Key: {'✓' if Config.MISTRAL_API_KEY else '✗ Not set'}")
    print(f"  Claude Key: {'✓' if Config.CLAUDE_API_KEY else '✗ Not set'}")
    print(f"  Gemini Key: {'✓' if Config.GEMINI_API_KEY else '✗ Not set'}")
    print(f"\n  Database: {Config.DATABASE_PATH}")
    print(f"  Gmail Token: {Config.GMAIL_TOKEN_FILE}")

def main():
    print("🚀 TeacherBot Setup\n")
    
    setup_directories()
    setup_databases()
    setup_environment()
    
    print("\n✅ Setup complete!")
    print("You can now start the server with:")
    print("  python -m flask --app app run --debug")

if __name__ == '__main__':
    main()
