import sqlite3
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

class History:
    @staticmethod
    def init_db(db_path=None):
        """Initialize history table"""
        db_path = db_path or Config.DATABASE_PATH
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                action_type TEXT,
                related_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def create(user_message, assistant_response, action_type='chat', related_id=None, db_path=None):
        """Create history record"""
        db_path = db_path or Config.DATABASE_PATH
        History.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (user_message, assistant_response, action_type, related_id)
            VALUES (?, ?, ?, ?)
        ''', (user_message, assistant_response, action_type, related_id))
        conn.commit()
        history_id = cursor.lastrowid
        conn.close()
        return history_id
    
    @staticmethod
    def get_all(limit=100, db_path=None):
        """Get all history records"""
        db_path = db_path or Config.DATABASE_PATH
        History.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM history ORDER BY created_at DESC LIMIT ?', (limit,))
        records = cursor.fetchall()
        conn.close()
        return [dict(r) for r in records]
    
    @staticmethod
    def get_recent(limit=20, db_path=None):
        """Get recent history"""
        db_path = db_path or Config.DATABASE_PATH
        History.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM history 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        records = cursor.fetchall()
        conn.close()
        return [dict(r) for r in records]
    
    @staticmethod
    def clear_all(action_type=None, db_path=None):
        """Clear history records - optionally by action type"""
        db_path = db_path or Config.DATABASE_PATH
        History.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if action_type:
            cursor.execute('DELETE FROM history WHERE action_type = ?', (action_type,))
        else:
            cursor.execute('DELETE FROM history')
        
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()
        return deleted_count
