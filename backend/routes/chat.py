from flask import Blueprint, request, jsonify
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService
from models.history import History
from models.schedule import Schedule
from utils.user_context import get_current_user_id, get_user_db_path

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
ai_service = AIService()

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
    
    return jsonify({
        'success': True,
        'response': response,
        'provider': ai_service.last_provider_used,
        'demo_mode': ai_service.last_provider_used == 'demo'
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
