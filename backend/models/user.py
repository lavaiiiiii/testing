import sqlite3
import os
from datetime import datetime
from backend.config import Config


class User:
    @staticmethod
    def init_db():
        """Initialize users table"""
        db_path = Config.DATABASE_PATH
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                name TEXT,
                email TEXT,
                avatar_url TEXT,
                gmail_connected INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def get_or_create(user_id, name='Teacher', email=''):
        """Get or create user"""
        db_path = Config.DATABASE_PATH
        User.init_db()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute('''
                INSERT INTO users (user_id, name, email)
                VALUES (?, ?, ?)
            ''', (user_id, name, email))
            conn.commit()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
        
        conn.close()
        return dict(user) if user else None

    @staticmethod
    def update(user_id, **kwargs):
        """Update user info"""
        db_path = Config.DATABASE_PATH
        User.init_db()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        allowed_fields = ['name', 'email', 'avatar_url', 'gmail_connected']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            conn.close()
            return False
        
        updates['updated_at'] = datetime.now().isoformat()
        
        set_clause = ', '.join([f'{k} = ?' for k in updates.keys()])
        values = list(updates.values())
        values.append(user_id)
        
        cursor.execute(f'''
            UPDATE users
            SET {set_clause}
            WHERE user_id = ?
        ''', values)
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    @staticmethod
    def get(user_id):
        """Get user by ID"""
        db_path = Config.DATABASE_PATH
        User.init_db()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
