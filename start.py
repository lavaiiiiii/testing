#!/usr/bin/env python3
"""
TeacherBot - Unified Startup Script
Run with: python start.py

Features:
  - One-command startup
  - Auto setup & initialization
  - Clean logging
  - Error recovery
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add backend to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

# Set development environment
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('FLASK_DEBUG', '1')

COLORS = {
    'HEADER': '\033[95m',
    'BLUE': '\033[94m',
    'CYAN': '\033[96m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'END': '\033[0m',
    'BOLD': '\033[1m',
}

def print_header(text):
    print(f"\n{COLORS['CYAN']}{COLORS['BOLD']}{'='*60}{COLORS['END']}")
    print(f"{COLORS['CYAN']}{COLORS['BOLD']}  {text}{COLORS['END']}")
    print(f"{COLORS['CYAN']}{COLORS['BOLD']}{'='*60}{COLORS['END']}\n")

def print_success(text):
    print(f"{COLORS['GREEN']}✅ {text}{COLORS['END']}")

def print_info(text):
    print(f"{COLORS['BLUE']}ℹ️  {text}{COLORS['END']}")

def print_warning(text):
    print(f"{COLORS['YELLOW']}⚠️  {text}{COLORS['END']}")

def print_error(text):
    print(f"{COLORS['RED']}❌ {text}{COLORS['END']}")

def setup_dependencies():
    """Install/update dependencies"""
    print_info("Installing dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            check=True,
            cwd=PROJECT_ROOT
        )
        print_success("Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False

def setup_environment():
    """Initialize databases and directories"""
    print_info("Setting up environment...")
    try:
        from backend.models.schedule import Schedule
        from backend.models.history import History
        from backend.models.user import User
        from backend.config import Config
        
        # Create directories
        dirs = [
            os.path.dirname(Config.DATABASE_PATH),
            os.path.join(os.path.dirname(Config.DATABASE_PATH), 'users'),
            os.path.dirname(Config.GMAIL_TOKEN_FILE),
            os.path.join(os.path.dirname(Config.GMAIL_TOKEN_FILE), 'users'),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
        
        # Initialize databases
        Schedule.init_db()
        History.init_db()
        User.init_db()
        
        print_success("Databases initialized")
        
        # Show configuration status
        print("\n📋 Configuration Status:")
        config_items = [
            ('Gmail Client ID', Config.GMAIL_CLIENT_ID),
            ('Gmail Client Secret', Config.GMAIL_CLIENT_SECRET),
            ('OpenAI Key', Config.OPENAI_API_KEY),
            ('Mistral Key', Config.MISTRAL_API_KEY),
            ('Claude Key', Config.CLAUDE_API_KEY),
            ('Gemini Key', Config.GEMINI_API_KEY),
            ('OpenRouter Key', Config.OPENROUTER_API_KEY),
        ]
        
        for name, value in config_items:
            status = '✓' if value else '✗'
            status_color = COLORS['GREEN'] if value else COLORS['RED']
            print(f"  {status_color}{status}{COLORS['END']} {name}")
        
        return True
    except Exception as e:
        print_error(f"Setup failed: {e}")
        return False

def run_app():
    """Start the Flask application"""
    print_header("🚀 Starting TeacherBot")
    
    print_info("Starting Flask development server...")
    print(f"\n{COLORS['GREEN']}{COLORS['BOLD']}Access the app at: http://localhost:5000{COLORS['END']}")
    print(f"\n{COLORS['YELLOW']}To login with Gmail:{COLORS['END']}")
    print("  1. Click 'Email' tab in sidebar")
    print("  2. Click 'Đăng nhập Gmail' button")
    print("  3. Select your Gmail account")
    print("  4. Grant permissions")
    print(f"\n{COLORS['CYAN']}Press Ctrl+C to stop the server{COLORS['END']}\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "flask", "--app", "backend.app", "run", "--debug"],
            cwd=PROJECT_ROOT,
            check=False
        )
    except KeyboardInterrupt:
        print(f"\n{COLORS['YELLOW']}Server stopped.{COLORS['END']}")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(
        description='TeacherBot - Unified Startup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py              # Setup + Run (default)
  python start.py --setup      # Setup only
  python start.py --run        # Run only
  python start.py --deps       # Install dependencies only
        """
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Run setup only (no server start)'
    )
    parser.add_argument(
        '--run',
        action='store_true',
        help='Run server only (skip setup)'
    )
    parser.add_argument(
        '--deps',
        action='store_true',
        help='Install dependencies only'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean cache and restart'
    )
    
    args = parser.parse_args()
    
    print_header("🎓 TeacherBot Startup")
    
    # Handle --clean flag
    if args.clean:
        print_info("Cleaning cache...")
        import shutil
        for pattern in ['__pycache__', '.pytest_cache', '*.pyc']:
            for item in PROJECT_ROOT.rglob(pattern):
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except:
                    pass
        print_success("Cache cleaned")
    
    # Default behavior: setup + run
    if not (args.setup or args.run or args.deps or args.clean):
        args.setup = True
        args.run = True
    
    # Setup phase
    if args.setup or (not args.run and not args.deps):
        if not setup_dependencies():
            sys.exit(1)
        if not setup_environment():
            print_warning("Some setup steps failed, but continuing...")
        print_success("Setup complete!\n")
    
    # Dependencies only
    if args.deps:
        if not setup_dependencies():
            sys.exit(1)
        print_success("Dependencies installed")
        return
    
    # Run phase
    if args.run or (not args.setup and not args.deps):
        try:
            run_app()
        except Exception as e:
            print_error(f"Failed to start app: {e}")
            sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{COLORS['YELLOW']}Interrupted by user.{COLORS['END']}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)
