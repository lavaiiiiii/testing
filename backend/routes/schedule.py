from flask import Blueprint, request, jsonify
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.schedule_service import ScheduleService
from models.schedule import Schedule
from models.history import History
from utils.user_context import get_current_user_id, get_user_db_path

schedule_bp = Blueprint('schedule', __name__, url_prefix='/api/schedule')

@schedule_bp.route('/create', methods=['POST'])
def create_schedule():
    """Create new schedule"""
    data = request.get_json()
    user_id = get_current_user_id(request)
    db_path = get_user_db_path(user_id)
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    start_time = data.get('start_time', '').strip()
    attendees = data.get('attendees', [])
    
    if not all([title, start_time]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        schedule_id = ScheduleService.create_schedule(title, description, start_time, attendees, db_path=db_path)
        
        # Save to history
        attendee_list = ', '.join(attendees) if attendees else 'Không có người tham dự'
        History.create(
            f"Tạo lịch hẹn: {title}",
            f"Lịch hẹn: {title} vào {start_time}\nNguời tham dự: {attendee_list}",
            action_type='schedule_created',
            related_id=schedule_id,
            db_path=db_path
        )
        
        return jsonify({
            'success': True,
            'schedule_id': schedule_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@schedule_bp.route('/list', methods=['GET'])
def list_schedules():
    """Get all schedules"""
    try:
        user_id = get_current_user_id(request)
        db_path = get_user_db_path(user_id)
        schedules = Schedule.get_all(db_path=db_path)
        return jsonify({
            'success': True,
            'schedules': schedules
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@schedule_bp.route('/upcoming', methods=['GET'])
def get_upcoming():
    """Get upcoming schedules"""
    try:
        user_id = get_current_user_id(request)
        db_path = get_user_db_path(user_id)
        upcoming = ScheduleService.get_upcoming_schedules(db_path=db_path)
        return jsonify({
            'success': True,
            'schedules': upcoming
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@schedule_bp.route('/<int:schedule_id>/update-status', methods=['PATCH'])
def update_status(schedule_id):
    """Update schedule status"""
    data = request.get_json()
    status = data.get('status', '').strip()
    
    if not status:
        return jsonify({'error': 'Missing status'}), 400
    
    try:
        user_id = get_current_user_id(request)
        db_path = get_user_db_path(user_id)
        Schedule.update_status(schedule_id, status, db_path=db_path)
        History.create(
            f"Cập nhật trạng thái lịch hẹn",
            f"Trạng thái: {status}",
            action_type='schedule_updated',
            related_id=schedule_id,
            db_path=db_path
        )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
