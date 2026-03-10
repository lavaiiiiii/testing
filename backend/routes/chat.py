from flask import Blueprint, request, jsonify, session
import os
import sys
import logging
import re
from datetime import datetime, timedelta, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService
from services.schedule_service import ScheduleService
from services.calendar_service import CalendarService
from services.gmail_service import GmailService
from models.history import History
from models.schedule import Schedule
from config import Config
from utils.user_context import get_current_user_id, get_user_db_path, get_user_token_file

# Configure module logger
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
ai_service = AIService()


def _format_vi_datetime(value):
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.strftime('%H:%M, %d/%m/%Y')
    except Exception:
        return str(value)


def _parse_datetime_text(text):
    if not text:
        return None

    value = str(text).strip()
    patterns = [
        '%d/%m/%Y %H:%M',
        '%d-%m-%Y %H:%M',
        '%Y-%m-%d %H:%M',
        '%H:%M %d/%m/%Y',
        '%H:%M %d-%m-%Y',
        '%Y-%m-%dT%H:%M'
    ]

    for pattern in patterns:
        try:
            parsed = datetime.strptime(value, pattern)
            return parsed.isoformat()
        except ValueError:
            continue

    return None


def _compact_history_text(text, limit):
    value = (text or '').strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + ' ...'


def _extract_duration_minutes_from_text(text, default_minutes=30):
    raw = (text or '').strip().lower()
    if not raw:
        return ScheduleService.sanitize_duration_minutes(default_minutes, default_minutes=30)

    minute_match = re.search(
        r'(?:thời\s*lượng|duration|kéo\s*dài|trong)\s*(?::|=)?\s*(\d{1,3})\s*(phút|p|mins?|minutes?)\b',
        raw,
        re.IGNORECASE
    )
    if minute_match:
        return ScheduleService.sanitize_duration_minutes(minute_match.group(1), default_minutes=default_minutes)

    hour_match = re.search(
        r'(?:thời\s*lượng|duration|kéo\s*dài|trong)\s*(?::|=)?\s*(\d{1,2})\s*(giờ|h|hours?)\b',
        raw,
        re.IGNORECASE
    )
    if hour_match:
        return ScheduleService.sanitize_duration_minutes(int(hour_match.group(1)) * 60, default_minutes=default_minutes)

    return ScheduleService.sanitize_duration_minutes(default_minutes, default_minutes=30)


def _extract_schedule_payload_from_prompt(user_message):
    text = (user_message or '').strip()
    lower = text.lower()

    # Date parsing
    base_date = datetime.now().date()
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    if date_match:
        date_text = date_match.group(1)
        for date_format in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y'):
            try:
                base_date = datetime.strptime(date_text, date_format).date()
                break
            except ValueError:
                continue
    elif 'ngày mai' in lower or 'tomorrow' in lower:
        base_date = (datetime.now() + timedelta(days=1)).date()
    elif 'tuần sau' in lower or 'next week' in lower:
        base_date = (datetime.now() + timedelta(weeks=1)).date()

    # Time parsing
    hour = 9
    minute = 0

    hm_match = re.search(r'(\d{1,2})\s*[:hH]\s*(\d{1,2})', text)
    if hm_match:
        hour = int(hm_match.group(1))
        minute = int(hm_match.group(2))
    else:
        hour_match = re.search(r'(\d{1,2})\s*giờ(?:\s*(sáng|chiều|tối|đêm))?', lower)
        if hour_match:
            hour = int(hour_match.group(1))
            period = (hour_match.group(2) or '').strip()
            if period in ('chiều', 'tối', 'đêm') and hour < 12:
                hour += 12
            if period == 'sáng' and hour == 12:
                hour = 0

    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    start_time = datetime.combine(base_date, time(hour, minute)).isoformat()

    # Description / title parsing
    content_match = re.search(r'nội dung\s*[:\-]\s*(.+)$', text, flags=re.IGNORECASE | re.DOTALL)
    description = ''
    if content_match:
        description = content_match.group(1).strip()
    else:
        description = text

    description = re.sub(r'\s+', ' ', description).strip(' .;')
    if not description:
        description = 'Nhắc lịch hẹn cá nhân'

    title = description.split(',')[0].strip()
    if len(title) > 80:
        title = title[:80].strip()
    if not title:
        title = 'Lịch hẹn'

    duration_minutes = _extract_duration_minutes_from_text(text, default_minutes=30)

    return {
        'title': title,
        'description': description,
        'start_time': start_time,
        'attendees': [],
        'duration_minutes': duration_minutes
    }


def _find_schedule_from_prompt(user_message, db_path):
    schedules = Schedule.get_all(limit=200, db_path=db_path)
    if not schedules:
        return None

    lower_message = user_message.lower()

    id_match = re.search(r'(?:id|#)\s*(\d+)', lower_message)
    if id_match:
        schedule_id = int(id_match.group(1))
        for item in schedules:
            if int(item.get('id', 0)) == schedule_id:
                return item

    quote_match = re.search(r'"([^"]+)"|“([^”]+)”', user_message)
    if quote_match:
        keyword = (quote_match.group(1) or quote_match.group(2) or '').strip().lower()
        if keyword:
            for item in schedules:
                title = (item.get('title') or '').lower()
                if keyword in title:
                    return item

    pending_sorted = sorted(
        [item for item in schedules if item.get('status') != 'completed'],
        key=lambda item: item.get('start_time') or ''
    )
    return pending_sorted[0] if pending_sorted else schedules[0]


def _handle_schedule_command(user_message, user_id, db_path):
    text = (user_message or '').strip()
    lower = text.lower()

    action = None
    if any(keyword in lower for keyword in ['đặt lịch', 'tạo lịch', 'lên lịch hẹn', 'lên lịch']):
        action = 'create'
    if any(keyword in lower for keyword in ['hoàn thành lịch', 'đánh dấu hoàn thành', 'xong lịch', 'mark complete']):
        action = 'complete'
    elif any(keyword in lower for keyword in ['chưa hoàn thành lịch', 'mở lại lịch', 'đánh dấu chưa hoàn thành']):
        action = 'incomplete'
    elif any(keyword in lower for keyword in ['xóa lịch', 'huỷ lịch', 'hủy lịch', 'delete lịch']):
        action = 'delete'
    elif any(keyword in lower for keyword in ['sửa lịch', 'cập nhật lịch', 'đổi lịch']):
        action = 'update'

    if not action:
        return None

    if action == 'create':
        payload = _extract_schedule_payload_from_prompt(text)
        end_time = ScheduleService.build_end_time(payload['start_time'], duration_minutes=payload.get('duration_minutes', 30))
        conflict = ScheduleService.find_conflicting_schedule(
            start_time=payload['start_time'],
            end_time=end_time,
            db_path=db_path
        )
        if conflict:
            conflict_time = _format_vi_datetime(conflict.get('start_time'))
            return {
                'handled': True,
                'action': 'create_conflict',
                'schedule': conflict,
                'response': f"Không thể tạo lịch. Khung giờ đã có lịch '{conflict.get('title', '')}' lúc {conflict_time}."
            }

        schedule_id, normalized_duration = ScheduleService.create_schedule(
            title=payload['title'],
            description=payload['description'],
            start_time=payload['start_time'],
            attendees=payload['attendees'],
            duration_minutes=payload.get('duration_minutes', 30),
            db_path=db_path
        )

        calendar_synced = False
        token_file = get_user_token_file(user_id)
        calendar_service = CalendarService(token_file=token_file)
        if calendar_service.is_ready():
            event_id = calendar_service.create_event(
                title=payload['title'],
                description=payload['description'],
                start_time=payload['start_time'],
                end_time=end_time,
                attendees=payload['attendees']
            )
            if event_id:
                Schedule.update(schedule_id, google_event_id=event_id, db_path=db_path)
                calendar_synced = True

        History.create(
            f"Tạo lịch hẹn: {payload['title']}",
            f"Lịch hẹn lúc {payload['start_time']}",
            action_type='schedule_created',
            related_id=schedule_id,
            db_path=db_path
        )

        time_text = datetime.fromisoformat(payload['start_time']).strftime('%H:%M, %d/%m/%Y')
        sync_text = 'đã đồng bộ Google Calendar.' if calendar_synced else 'chưa đồng bộ Google Calendar (hãy đăng nhập Gmail lại để cấp quyền Calendar).'
        return {
            'handled': True,
            'action': action,
            'schedule': {'id': schedule_id, **payload, 'duration_minutes': normalized_duration},
            'response': f"Đã tạo lịch hẹn: {payload['title']} lúc {time_text} (trong {normalized_duration} phút); {sync_text}",
            'effect': {'refresh': ['schedule', 'history']}
        }

    schedule = _find_schedule_from_prompt(text, db_path=db_path)
    if not schedule:
        return {
            'handled': True,
            'response': 'Không tìm thấy lịch hẹn để thao tác.',
            'action': action,
            'schedule': None
        }

    schedule_id = schedule.get('id')
    token_file = get_user_token_file(user_id)
    calendar_service = CalendarService(token_file=token_file)

    if action == 'complete':
        Schedule.update_status(schedule_id, 'completed', db_path=db_path)
        updated = Schedule.get_by_id(schedule_id, db_path=db_path)
        return {
            'handled': True,
            'action': action,
            'schedule': updated,
            'response': f"Đã đánh dấu hoàn thành lịch hẹn ID {schedule_id}: {updated.get('title', '')}."
        }

    if action == 'incomplete':
        Schedule.update_status(schedule_id, 'pending', db_path=db_path)
        updated = Schedule.get_by_id(schedule_id, db_path=db_path)
        return {
            'handled': True,
            'action': action,
            'schedule': updated,
            'response': f"Đã cập nhật lịch hẹn ID {schedule_id} về trạng thái chưa hoàn thành."
        }

    if action == 'delete':
        event_id = schedule.get('google_event_id')
        if event_id and calendar_service.is_ready():
            calendar_service.delete_event(event_id)

        Schedule.delete(schedule_id, db_path=db_path)
        return {
            'handled': True,
            'action': action,
            'schedule': {'id': schedule_id},
            'response': f"Đã xóa lịch hẹn ID {schedule_id}: {schedule.get('title', '')}."
        }

    if action == 'update':
        updates = {}

        title_match = re.search(r'tiêu đề\s*[:=]\s*([^\n;]+)', text, re.IGNORECASE)
        if title_match:
            updates['title'] = title_match.group(1).strip()

        desc_match = re.search(r'mô tả\s*[:=]\s*([^\n;]+)', text, re.IGNORECASE)
        if desc_match:
            updates['description'] = desc_match.group(1).strip()

        time_match = re.search(r'(?:thời gian|lúc|vào)\s*[:=]\s*([^\n;]+)', text, re.IGNORECASE)
        if time_match:
            parsed_time = _parse_datetime_text(time_match.group(1).strip())
            if parsed_time:
                updates['start_time'] = parsed_time

        duration_match = re.search(r'(?:thời lượng|duration)\s*[:=]\s*(\d{1,3})\s*(phút|p|mins?|minutes?)?', text, re.IGNORECASE)
        if duration_match:
            duration_minutes = ScheduleService.sanitize_duration_minutes(duration_match.group(1), default_minutes=30)
            candidate_start = updates.get('start_time', schedule.get('start_time'))
            updates['end_time'] = ScheduleService.build_end_time(candidate_start, duration_minutes=duration_minutes)

        if not updates:
            return {
                'handled': True,
                'action': action,
                'schedule': schedule,
                'response': 'Để sửa lịch hẹn, hãy ghi rõ dạng: sửa lịch id 3; tiêu đề: ...; thời gian: 11/03/2026 12:00; mô tả: ...'
            }

        candidate_start = updates.get('start_time', schedule.get('start_time'))
        candidate_end = updates.get('end_time', schedule.get('end_time'))
        conflict = ScheduleService.find_conflicting_schedule(
            start_time=candidate_start,
            end_time=candidate_end,
            db_path=db_path,
            exclude_schedule_id=schedule_id
        )
        if conflict:
            conflict_time = _format_vi_datetime(conflict.get('start_time'))
            return {
                'handled': True,
                'action': 'update_conflict',
                'schedule': conflict,
                'response': f"Không thể cập nhật lịch. Khung giờ trùng với '{conflict.get('title', '')}' ({conflict_time})."
            }

        Schedule.update(schedule_id, db_path=db_path, **updates)
        updated = Schedule.get_by_id(schedule_id, db_path=db_path)

        if updated and calendar_service.is_ready():
            attendees_value = updated.get('attendees') or ''
            attendees_list = [item.strip() for item in str(attendees_value).split(',') if item.strip()]
            event_id = updated.get('google_event_id')
            if event_id:
                calendar_service.update_event(
                    event_id=event_id,
                    title=updated.get('title'),
                    description=updated.get('description'),
                    start_time=updated.get('start_time'),
                    end_time=updated.get('end_time'),
                    attendees=attendees_list
                )

        changed_fields = ', '.join(updates.keys())
        return {
            'handled': True,
            'action': action,
            'schedule': updated,
            'response': f"Đã cập nhật lịch hẹn ID {schedule_id} ({changed_fields})."
        }

    return None


def _load_user_gmail_service(user_id):
    token_file = get_user_token_file(user_id)
    if not token_file or not os.path.exists(token_file):
        return None
    try:
        return GmailService(token_file=token_file)
    except Exception:
        return None


def _handle_email_command(user_message, user_id):
    text = (user_message or '').strip()
    lower = text.lower()

    if not any(keyword in lower for keyword in ['email', 'gmail', 'hộp thư']):
        return None

    service = _load_user_gmail_service(user_id)
    if not service:
        return {
            'handled': True,
            'action': 'email_auth_required',
            'response': 'Bạn chưa đăng nhập Gmail. Vào tab Email để đăng nhập trước nhé.',
            'effect': {'target_page': 'emails'}
        }

    if any(keyword in lower for keyword in ['xem email', 'kiểm tra email', 'email chưa đọc', 'hộp thư']):
        emails = service.get_emails(max_results=5, query='is:unread')
        if not emails:
            return {
                'handled': True,
                'action': 'email_list',
                'response': 'Không có email chưa đọc mới.',
                'effect': {'target_page': 'emails', 'refresh': ['email']}
            }

        lines = []
        for item in emails:
            message_id = (item.get('id') or '')[:8]
            subject = item.get('subject') or 'Không tiêu đề'
            sender = item.get('sender') or 'Không rõ'
            lines.append(f"- [{message_id}] {subject} — {sender}")

        return {
            'handled': True,
            'action': 'email_list',
            'response': "Đây là 5 email chưa đọc gần nhất:\n" + "\n".join(lines),
            'effect': {'target_page': 'emails', 'refresh': ['email']}
        }

    read_match = re.search(r'(?:đánh dấu|mark)\s+(?:email\s+)?(?:id\s*)?([a-zA-Z0-9_-]+)\s+(?:đã đọc|read)', lower)
    unread_match = re.search(r'(?:đánh dấu|mark)\s+(?:email\s+)?(?:id\s*)?([a-zA-Z0-9_-]+)\s+(?:chưa đọc|unread)', lower)

    if read_match:
        message_id = read_match.group(1)
        success = service.mark_as_read(message_id)
        return {
            'handled': True,
            'action': 'email_mark_read',
            'response': 'Đã đánh dấu email là đã đọc.' if success else 'Không thể đánh dấu email đã đọc. Vui lòng kiểm tra lại ID email.',
            'effect': {'target_page': 'emails', 'refresh': ['email']}
        }

    if unread_match:
        message_id = unread_match.group(1)
        success = service.mark_as_unread(message_id)
        return {
            'handled': True,
            'action': 'email_mark_unread',
            'response': 'Đã đánh dấu email là chưa đọc.' if success else 'Không thể đánh dấu email chưa đọc. Vui lòng kiểm tra lại ID email.',
            'effect': {'target_page': 'emails', 'refresh': ['email']}
        }

    return None


def _handle_history_command(user_message, db_path):
    text = (user_message or '').strip()
    lower = text.lower()

    if any(keyword in lower for keyword in ['xóa lịch sử chat', 'clear chat history']):
        deleted = History.clear_all(action_type='chat', db_path=db_path)
        return {
            'handled': True,
            'action': 'history_clear_chat',
            'response': f'Đã xóa {deleted} tin nhắn chat.',
            'effect': {'target_page': 'history', 'refresh': ['history', 'chat']}
        }

    if any(keyword in lower for keyword in ['xóa toàn bộ lịch sử', 'clear all history']):
        deleted = History.clear_all(db_path=db_path)
        return {
            'handled': True,
            'action': 'history_clear_all',
            'response': f'Đã xóa {deleted} bản ghi lịch sử.',
            'effect': {'target_page': 'history', 'refresh': ['history', 'chat', 'schedule']}
        }

    if any(keyword in lower for keyword in ['xem lịch sử', 'lịch sử gần đây', 'history']):
        records = History.get_recent(limit=5, db_path=db_path)
        if not records:
            return {
                'handled': True,
                'action': 'history_view',
                'response': 'Chưa có lịch sử hoạt động.',
                'effect': {'target_page': 'history', 'refresh': ['history']}
            }

        lines = []
        for row in records:
            action_type = row.get('action_type', 'unknown')
            user_msg = (row.get('user_message') or '')[:60]
            lines.append(f"- {action_type}: {user_msg}")

        return {
            'handled': True,
            'action': 'history_view',
            'response': '5 hoạt động gần nhất:\n' + '\n'.join(lines),
            'effect': {'target_page': 'history', 'refresh': ['history']}
        }

    return None


def _handle_cross_tab_command(user_message, user_id, db_path):
    for handler in (
        lambda msg: _handle_schedule_command(msg, user_id=user_id, db_path=db_path),
        lambda msg: _handle_email_command(msg, user_id=user_id),
        lambda msg: _handle_history_command(msg, db_path=db_path),
    ):
        result = handler(user_message)
        if result and result.get('handled'):
            return result
    return None

def extract_schedule_from_response(response, user_message):
    """
    Detect if AI response contains scheduling information
    Returns dict with schedule data or None
    """
    # Keywords that suggest scheduling
    schedule_keywords = [
        'lịch hẹn', 'schedule', 'đặt lịch', 'set schedule',
        'gặp gỡ', 'meeting', 'cuộc họp', 'appointment',
        'hẹn gặp', 'lên lịch', 'tối hôm nay', 'ngày mai',
        'tuần sau', 'tháng sau', 'lúc', 'vào', 'at'
    ]
    
    combined_text = (user_message + ' ' + response).lower()
    
    # Check if response contains scheduling keywords
    has_schedule_keyword = any(keyword in combined_text for keyword in schedule_keywords)
    
    if not has_schedule_keyword:
        return None
    
    # Try to extract schedule details
    schedule_info = {
        'title': '',
        'description': response,
        'start_time': None,
        'attendees': [],
        'duration_minutes': 30
    }
    
    # Extract title (first meaningful part of response or user message)
    if 'lịch hẹn:' in response.lower():
        title_match = re.search(r'lịch hẹn:\s*([^\n]+)', response, re.IGNORECASE)
        if title_match:
            schedule_info['title'] = title_match.group(1).strip()[:100]
    
    if not schedule_info['title']:
        # Use first few words from user message
        words = user_message.split()[:5]
        schedule_info['title'] = ' '.join(words)[:100]
    
    now = datetime.now()

    # 1) Parse date first (if user provided exact date)
    target_date = now.date()
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', combined_text, re.IGNORECASE)
    if date_match:
        date_text = date_match.group(1)
        parsed_date = None
        for date_format in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y'):
            try:
                parsed_date = datetime.strptime(date_text, date_format).date()
                break
            except ValueError:
                continue
        if parsed_date:
            target_date = parsed_date
    elif 'ngày mai' in combined_text or 'tomorrow' in combined_text:
        target_date = (now + timedelta(days=1)).date()
    elif 'tuần sau' in combined_text or 'next week' in combined_text:
        target_date = (now + timedelta(weeks=1)).date()

    # 2) Parse time explicitly provided by user
    target_time = time(9, 0)  # default fixed reminder time if only date exists
    time_match = re.search(r'(\d{1,2}:\d{1,2})', combined_text, re.IGNORECASE)
    if time_match:
        try:
            target_time = datetime.strptime(time_match.group(1), '%H:%M').time()
        except ValueError:
            pass

    start_time = datetime.combine(target_date, target_time)
    
    schedule_info['start_time'] = start_time.isoformat()

    schedule_info['duration_minutes'] = _extract_duration_minutes_from_text(combined_text, default_minutes=30)
    
    # Extract email addresses (attendees)
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', combined_text)
    schedule_info['attendees'] = list(set(emails))  # Remove duplicates
    
    return schedule_info if schedule_info['title'] else None


@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Send message to AI assistant"""
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    task = (data.get('task', 'chat') or 'chat').strip().lower()
    if task not in ['chat', 'summary', 'reply', 'analyze']:
        task = 'chat'
    
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400
    
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    History.init_db(db_path=db_path)
    Schedule.init_db(db_path=db_path)

    command_result = _handle_cross_tab_command(user_message, user_id=user_id, db_path=db_path)
    if command_result and command_result.get('handled'):
        response_text = command_result.get('response') or 'Đã xử lý lệnh lịch hẹn.'
        History.create(user_message, response_text, action_type='chat', db_path=db_path)
        return jsonify({
            'success': True,
            'response': response_text,
            'provider': 'system',
            'demo_mode': False,
            'schedule_created': None,
            'schedule_action': command_result.get('action'),
            'schedule': command_result.get('schedule'),
            'command_effect': command_result.get('effect')
        })

    # Build messages for AI with recent chat context for smarter responses
    messages = [
        {
            "role": "system",
            "content": "Bạn là AI Agent, trợ lý giáo viên. Trả lời ngắn gọn, chuyên nghiệp, hữu ích về email, lịch hẹn và công việc giảng dạy."
        }
    ]

    max_turns = max(2, Config.AI_MAX_CONTEXT_MESSAGES // 2)
    recent_history = History.get_recent(limit=max_turns, db_path=db_path)
    for record in reversed(recent_history):
        if record.get('action_type') != 'chat':
            continue

        prev_user = _compact_history_text(record.get('user_message'), limit=220)
        prev_assistant = _compact_history_text(record.get('assistant_response'), limit=260)
        if prev_user:
            messages.append({"role": "user", "content": prev_user})
        if prev_assistant:
            messages.append({"role": "assistant", "content": prev_assistant})

    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Generate response
    response = ai_service.generate_response(messages, task=task)
    
    # Save to history
    History.create(user_message, response, action_type='chat', db_path=db_path)
    
    # Auto-detect and save schedule if mentioned in response
    schedule_info = extract_schedule_from_response(response, user_message)
    schedule_created = None
    
    if schedule_info:
        try:
            schedule_end_time = ScheduleService.build_end_time(
                schedule_info['start_time'],
                duration_minutes=schedule_info.get('duration_minutes', 30)
            )
            conflict = ScheduleService.find_conflicting_schedule(
                start_time=schedule_info['start_time'],
                end_time=schedule_end_time,
                db_path=db_path
            )
            if conflict:
                logger.info(f"Skipped auto-created schedule due to conflict with ID {conflict.get('id')}")
                return jsonify({
                    'success': True,
                    'response': response,
                    'provider': ai_service.last_provider_used,
                    'demo_mode': ai_service.last_provider_used == 'demo',
                    'schedule_created': None,
                    'schedule_conflict': {
                        'id': conflict.get('id'),
                        'title': conflict.get('title'),
                        'start_time': conflict.get('start_time')
                    }
                })

            schedule_id, normalized_duration = ScheduleService.create_schedule(
                title=schedule_info['title'],
                description=schedule_info['description'],
                start_time=schedule_info['start_time'],
                attendees=schedule_info['attendees'],
                duration_minutes=schedule_info.get('duration_minutes', 30),
                db_path=db_path
            )

            token_file = get_user_token_file(user_id)
            calendar_service = CalendarService(token_file=token_file)
            if calendar_service.is_ready():
                event_id = calendar_service.create_event(
                    title=schedule_info['title'],
                    description=schedule_info['description'],
                    start_time=schedule_info['start_time'],
                    end_time=schedule_end_time,
                    attendees=schedule_info['attendees']
                )
                if event_id:
                    Schedule.update(schedule_id, google_event_id=event_id, db_path=db_path)
            
            # Also save to chat history for reference
            History.create(
                f"Tạo lịch hẹn: {schedule_info['title']}",
                f"Lịch hẹn được tạo tự động từ chat",
                action_type='schedule_created',
                related_id=schedule_id,
                db_path=db_path
            )
            
            schedule_created = {
                'id': schedule_id,
                'title': schedule_info['title'],
                'start_time': schedule_info['start_time'],
                'duration_minutes': normalized_duration
            }
            
            logger.info(f"Auto-created schedule: {schedule_info['title']}")
        except Exception as e:
            logger.error(f"Failed to auto-create schedule: {e}")
    
    return jsonify({
        'success': True,
        'response': response,
        'provider': ai_service.last_provider_used,
        'demo_mode': ai_service.last_provider_used == 'demo',
        'schedule_created': schedule_created
    })

@chat_bp.route('/summarize-email', methods=['POST'])
def summarize_email():
    """Summarize email content"""
    data = request.get_json()
    email_content = data.get('content', '').strip()
    
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)

    if not email_content:
        return jsonify({'error': 'Empty email content'}), 400
    
    summary = ai_service.summarize_email(email_content)
    
    # Save to history
    History.create(f"Tóm tắt email", summary, action_type='email_summary', db_path=db_path)
    
    return jsonify({
        'success': True,
        'summary': summary
    })

@chat_bp.route('/generate-reply', methods=['POST'])
def generate_reply():
    """Generate automatic email reply"""
    data = request.get_json()
    context = data.get('context', '').strip()
    choice = data.get('choice', '').strip()
    
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)

    if not context or not choice:
        return jsonify({'error': 'Missing context or choice'}), 400
    
    reply = ai_service.generate_reply(context, choice)
    
    # Save to history
    History.create(f"Tạo email trả lời: {choice}", reply, action_type='email_reply', db_path=db_path)
    
    return jsonify({
        'success': True,
        'reply': reply
    })

@chat_bp.route('/history', methods=['GET'])
def get_history():
    """Get chat history"""
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    limit = request.args.get('limit', 20, type=int)
    history = History.get_recent(limit=limit, db_path=db_path)
    
    return jsonify({
        'success': True,
        'history': history
    })

@chat_bp.route('/providers', methods=['GET'])
def get_ai_providers():
    """Get AI provider status and fallback chain"""
    return jsonify({
        'success': True,
        'providers': ai_service.get_provider_status()
    })

@chat_bp.route('/clear', methods=['POST'])
def clear_conversation():
    """Clear conversation history"""
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    
    # Delete only chat messages, preserve email and schedule history
    deleted_count = History.clear_all(action_type='chat', db_path=db_path)
    
    return jsonify({
        'success': True,
        'message': f'Đã xóa {deleted_count} tin nhắn',
        'deleted_count': deleted_count
    })

@chat_bp.route('/clear-all', methods=['POST'])
def clear_all_history():
    """Clear all history including emails and schedules"""
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    
    deleted_count = History.clear_all(db_path=db_path)
    
    return jsonify({
        'success': True,
        'message': f'Đã xóa {deleted_count} bản ghi lịch sử',
        'deleted_count': deleted_count
    })
