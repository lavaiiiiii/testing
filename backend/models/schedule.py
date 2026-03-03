from datetime import datetime
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

class Schedule:
    @staticmethod
    def init_db(db_path=None):
        """Initialize schedule table"""
        db_path = db_path or Config.DATABASE_PATH
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                attendees TEXT,
                email_body TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def create(title, description, start_time, end_time, attendees, email_body='', db_path=None):
        """Create new schedule"""
        db_path = db_path or Config.DATABASE_PATH
        Schedule.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO schedules (title, description, start_time, end_time, attendees, email_body, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (title, description, start_time, end_time, attendees, email_body))
        conn.commit()
        schedule_id = cursor.lastrowid
        conn.close()
        return schedule_id
    
    @staticmethod
    def get_all(limit=50, db_path=None):
        """Get all schedules"""
        db_path = db_path or Config.DATABASE_PATH
        Schedule.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedules ORDER BY start_time DESC LIMIT ?', (limit,))
        schedules = cursor.fetchall()
        conn.close()
        return [dict(s) for s in schedules]
    
    @staticmethod
    def get_by_id(schedule_id, db_path=None):
        """Get schedule by ID"""
        db_path = db_path or Config.DATABASE_PATH
        Schedule.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
        schedule = cursor.fetchone()
        conn.close()
        return dict(schedule) if schedule else None
    
    @staticmethod
    def update_status(schedule_id, status, db_path=None):
        """Update schedule status"""
        db_path = db_path or Config.DATABASE_PATH
        Schedule.init_db(db_path=db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE schedules 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, schedule_id))
        conn.commit()
        conn.close()
