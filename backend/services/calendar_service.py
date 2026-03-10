import os
import pickle
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from googleapiclient.discovery import build


class CalendarService:
    REMINDER_OVERRIDES = [
        {'method': 'popup', 'minutes': 30},
        {'method': 'popup', 'minutes': 10},
        {'method': 'email', 'minutes': 30}
    ]

    def __init__(self, token_file):
        self.token_file = token_file
        self.creds = None

    def _load_creds(self):
        if not self.token_file or not os.path.exists(self.token_file):
            return None

        try:
            with open(self.token_file, 'rb') as token_handle:
                self.creds = pickle.load(token_handle)
        except Exception:
            self.creds = None
            return None

        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                with open(self.token_file, 'wb') as token_handle:
                    pickle.dump(self.creds, token_handle)
            except Exception:
                return None

        return self.creds if self.creds and self.creds.valid else None

    def is_ready(self):
        return self._load_creds() is not None

    def _service(self):
        creds = self._load_creds()
        if not creds:
            return None
        return build('calendar', 'v3', credentials=creds)

    @staticmethod
    def _normalize_datetime(value):
        if not value:
            return None

        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception:
            return None

        if dt.tzinfo is None:
            return dt.isoformat()
        return dt.isoformat()

    @staticmethod
    def _to_attendees(attendees):
        if not attendees:
            return []

        if isinstance(attendees, str):
            items = [item.strip() for item in attendees.split(',') if item.strip()]
        else:
            items = [str(item).strip() for item in attendees if str(item).strip()]

        return [{'email': email} for email in items]

    def _build_event_body(self, title, description, start_iso, end_iso, attendees=None):
        return {
            'summary': title or 'Lịch hẹn',
            'description': description or '',
            'eventType': 'default',
            'start': {
                'dateTime': start_iso,
                'timeZone': 'Asia/Ho_Chi_Minh'
            },
            'end': {
                'dateTime': end_iso,
                'timeZone': 'Asia/Ho_Chi_Minh'
            },
            'attendees': self._to_attendees(attendees),
            'reminders': {
                'useDefault': False,
                'overrides': self.REMINDER_OVERRIDES
            }
        }

    def create_event(self, title, description, start_time, end_time=None, attendees=None):
        service = self._service()
        if not service:
            return None

        start_iso = self._normalize_datetime(start_time)
        if not start_iso:
            return None

        if end_time:
            end_iso = self._normalize_datetime(end_time)
        else:
            start_dt = datetime.fromisoformat(start_iso)
            end_iso = (start_dt + timedelta(minutes=30)).isoformat()

        body = self._build_event_body(title, description, start_iso, end_iso, attendees=attendees)

        event = service.events().insert(calendarId='primary', body=body, sendUpdates='all').execute()
        return event.get('id')

    def update_event(self, event_id, title, description, start_time, end_time=None, attendees=None):
        if not event_id:
            return False

        service = self._service()
        if not service:
            return False

        start_iso = self._normalize_datetime(start_time)
        if not start_iso:
            return False

        if end_time:
            end_iso = self._normalize_datetime(end_time)
        else:
            start_dt = datetime.fromisoformat(start_iso)
            end_iso = (start_dt + timedelta(minutes=30)).isoformat()

        body = self._build_event_body(title, description, start_iso, end_iso, attendees=attendees)

        service.events().update(calendarId='primary', eventId=event_id, body=body, sendUpdates='all').execute()
        return True

    def delete_event(self, event_id):
        if not event_id:
            return False

        service = self._service()
        if not service:
            return False

        try:
            service.events().delete(calendarId='primary', eventId=event_id, sendUpdates='all').execute()
            return True
        except Exception:
            return False
