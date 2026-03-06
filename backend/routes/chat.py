from flask import Blueprint, request, jsonify
import os
import sys
import logging
import re
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService
from services.schedule_service import ScheduleService
from models.history import History
from models.schedule import Schedule
from utils.user_context import get_current_user_id, get_user_db_path

# Configure module logger
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
ai_service = AIService()

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
        'attendees': []
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
    
    # Extract time information
    time_patterns = [
        r'(\d{1,2}:\d{1,2})',  # HH:MM
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY
        r'(hôm nay|today)',
        r'(ngày mai|tomorrow)',
        r'(tuần sau|next week)',
    ]
    
    now = datetime.now()
    start_time = None
    
    for pattern in time_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            time_str = match.group(1).lower()
            
            try:
                # Try to parse time
                if ':' in time_str:
                    time_obj = datetime.strptime(time_str, '%H:%M').time()
                    start_time = datetime.combine(now.date(), time_obj)
                elif 'hôm nay' in time_str or 'today' in time_str:
                    start_time = datetime.combine(now.date(), datetime.now().time())
                elif 'ngày mai' in time_str or 'tomorrow' in time_str:
                    tomorrow = now + timedelta(days=1)
                    start_time = datetime.combine(tomorrow.date(), now.time())
                elif 'tuần sau' in time_str or 'next week' in time_str:
                    next_week = now + timedelta(weeks=1)
                    start_time = datetime.combine(next_week.date(), now.time())
                
                if start_time:
                    break
            except:
                pass
    
    # Default to tomorrow at same time if not found
    if not start_time:
        start_time = now + timedelta(days=1)
    
    schedule_info['start_time'] = start_time.isoformat()
    
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
    
    user_id = get_current_user_id(request)
    db_path = get_user_db_path(user_id)
    History.init_db(db_path=db_path)
    Schedule.init_db(db_path=db_path)

    # Build messages for AI with recent chat context for smarter responses
    messages = [
        {
            "role": "system",
            "content": "Bạn là TeacherBot, trợ lý giáo viên. Trả lời ngắn gọn, chuyên nghiệp, hữu ích về email, lịch hẹn và công việc giảng dạy."
        }
    ]

    recent_history = History.get_recent(limit=8, db_path=db_path)
    for record in reversed(recent_history):
        if record.get('action_type') != 'chat':
            continue

        prev_user = (record.get('user_message') or '').strip()
        prev_assistant = (record.get('assistant_response') or '').strip()
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
            schedule_id = ScheduleService.create_schedule(
                title=schedule_info['title'],
                description=schedule_info['description'],
                start_time=schedule_info['start_time'],
                attendees=schedule_info['attendees'],
                db_path=db_path
            )
            
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
                'start_time': schedule_info['start_time']
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
    
    user_id = get_current_user_id(request)
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
    
    user_id = get_current_user_id(request)
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
    user_id = get_current_user_id(request)
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
    user_id = get_current_user_id(request)
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
    user_id = get_current_user_id(request)
    db_path = get_user_db_path(user_id)
    
    deleted_count = History.clear_all(db_path=db_path)
    
    return jsonify({
        'success': True,
        'message': f'Đã xóa {deleted_count} bản ghi lịch sử',
        'deleted_count': deleted_count
    })
