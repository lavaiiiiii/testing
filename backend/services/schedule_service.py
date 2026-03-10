import os
import sys
import re
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schedule import Schedule

class ScheduleService:
    @staticmethod
    def sanitize_duration_minutes(value, default_minutes=30):
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            minutes = int(default_minutes)

        if minutes < 5:
            return 5
        if minutes > 720:
            return 720
        return minutes

    @staticmethod
    def build_end_time(start_time, duration_minutes=30):
        start_dt = ScheduleService._to_datetime(start_time)
        if not start_dt:
            return None

        minutes = ScheduleService.sanitize_duration_minutes(duration_minutes, default_minutes=30)
        return (start_dt + timedelta(minutes=minutes)).isoformat()

    @staticmethod
    def infer_duration_minutes(start_time, end_time, default_minutes=30):
        start_dt = ScheduleService._to_datetime(start_time)
        end_dt = ScheduleService._to_datetime(end_time)
        if not start_dt or not end_dt or end_dt <= start_dt:
            return ScheduleService.sanitize_duration_minutes(default_minutes, default_minutes=30)

        delta_minutes = int((end_dt - start_dt).total_seconds() // 60)
        return ScheduleService.sanitize_duration_minutes(delta_minutes, default_minutes=default_minutes)

    @staticmethod
    def _to_datetime(value):
        if value is None:
            return None
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception:
            return None

    @staticmethod
    def find_conflicting_schedule(start_time, end_time=None, db_path=None, exclude_schedule_id=None):
        """Return conflicting schedule if time range overlaps, else None."""
        start_dt = ScheduleService._to_datetime(start_time)
        if not start_dt:
            return None

        end_dt = ScheduleService._to_datetime(end_time) if end_time else (start_dt + timedelta(minutes=30))
        if not end_dt or end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=30)

        schedules = Schedule.get_all(limit=500, db_path=db_path)
        for item in schedules:
            item_id = item.get('id')
            if exclude_schedule_id is not None and int(item_id) == int(exclude_schedule_id):
                continue

            item_start = ScheduleService._to_datetime(item.get('start_time'))
            item_end = ScheduleService._to_datetime(item.get('end_time'))
            if not item_start:
                continue
            if not item_end or item_end <= item_start:
                item_end = item_start + timedelta(minutes=30)

            # Overlap condition: [start, end) intersects [item_start, item_end)
            if start_dt < item_end and end_dt > item_start:
                return item

        return None

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
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        result['attendees'] = emails
        
        return result
    
    @staticmethod
    def create_schedule(title, description, start_time, attendees, duration_minutes=30, db_path=None):
        """Create new schedule"""
        end_time = ScheduleService.build_end_time(start_time, duration_minutes=duration_minutes)
        if not end_time:
            end_time = (datetime.fromisoformat(start_time) + timedelta(minutes=30)).isoformat()

        normalized_duration = ScheduleService.infer_duration_minutes(start_time, end_time, default_minutes=30)
        schedule_id = Schedule.create(
            title,
            description,
            start_time,
            end_time,
            ','.join(attendees),
            db_path=db_path
        )
        return schedule_id, normalized_duration
    
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
