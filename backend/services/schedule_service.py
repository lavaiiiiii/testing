from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schedule import Schedule

class ScheduleService:
    @staticmethod
    def parse_schedule_request(text):
        """Parse schedule request from user text"""
        # Simple pattern matching - can be enhanced
        result = {
            'title': '',
            'description': '',
            'start_time': None,
            'attendees': [],
            'action': 'create'
        }
        
        # Basic parsing logic
        if 'hôm nay' in text.lower() or 'today' in text.lower():
            result['start_time'] = datetime.now()
        elif 'ngày mai' in text.lower() or 'tomorrow' in text.lower():
            result['start_time'] = datetime.now() + timedelta(days=1)
        
        # Extract email addresses (simple pattern)
        import re
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        result['attendees'] = emails
        
        return result
    
    @staticmethod
    def create_schedule(title, description, start_time, attendees, db_path=None):
        """Create new schedule"""
        end_time = datetime.fromisoformat(start_time) + timedelta(hours=1)
        schedule_id = Schedule.create(
            title,
            description,
            start_time,
            end_time.isoformat(),
            ','.join(attendees),
            db_path=db_path
        )
        return schedule_id
    
    @staticmethod
    def get_upcoming_schedules(db_path=None):
        """Get upcoming schedules"""
        schedules = Schedule.get_all(db_path=db_path)
        upcoming = []
        now = datetime.now()
        
        for schedule in schedules:
            if datetime.fromisoformat(schedule['start_time']) > now:
                upcoming.append(schedule)
        
        return sorted(upcoming, key=lambda x: x['start_time'])[:5]
