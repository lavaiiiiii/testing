import os
import sys
import logging
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify, session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.schedule_service import ScheduleService
from services.calendar_service import CalendarService
from models.schedule import Schedule
from models.history import History
from utils.user_context import get_current_user_id, get_user_db_path, get_user_token_file

schedule_bp = Blueprint('schedule', __name__, url_prefix='/api/schedule')


def _format_vi_datetime(value):
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.strftime('%H:%M, %d/%m/%Y')
    except Exception:
        return str(value)


def _sync_create_calendar_event(user_id, schedule_id, title, description, start_time, end_time, attendees, db_path):
    token_file = get_user_token_file(user_id)
    calendar_service = CalendarService(token_file=token_file)
    if not calendar_service.is_ready():
        return None

    event_id = calendar_service.create_event(
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        attendees=attendees
    )
    if event_id:
        Schedule.update(schedule_id, google_event_id=event_id, db_path=db_path)
    return event_id


def _sync_update_calendar_event_async(user_id, schedule_id, db_path):
    try:
        updated = Schedule.get_by_id(schedule_id, db_path=db_path)
        if not updated:
            return

        token_file = get_user_token_file(user_id)
        calendar_service = CalendarService(token_file=token_file)
        if not calendar_service.is_ready():
            return

        event_id = updated.get('google_event_id')
        attendees_value = updated.get('attendees') or ''
        attendees_list = [e.strip() for e in str(attendees_value).split(',') if e.strip()]

        if event_id:
            calendar_service.update_event(
                event_id=event_id,
                title=updated.get('title'),
                description=updated.get('description'),
                start_time=updated.get('start_time'),
                end_time=updated.get('end_time'),
                attendees=attendees_list
            )
        else:
            created_event_id = calendar_service.create_event(
                title=updated.get('title'),
                description=updated.get('description'),
                start_time=updated.get('start_time'),
                end_time=updated.get('end_time'),
                attendees=attendees_list
            )
            if created_event_id:
                Schedule.update(schedule_id, google_event_id=created_event_id, db_path=db_path)
    except Exception as ex:
        logging.exception(f"Calendar sync update failed for schedule {schedule_id}: {ex}")

@schedule_bp.route('/create', methods=['POST'])
def create_schedule():
    """Create new schedule"""
    data = request.get_json()
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    start_time = data.get('start_time', '').strip()
    attendees = data.get('attendees', [])
    duration_minutes = ScheduleService.sanitize_duration_minutes(data.get('duration_minutes', 30), default_minutes=30)
    
    if not all([title, start_time]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        end_time = ScheduleService.build_end_time(start_time, duration_minutes=duration_minutes)
        conflict = ScheduleService.find_conflicting_schedule(start_time=start_time, end_time=end_time, db_path=db_path)
        if conflict:
            conflict_time = _format_vi_datetime(conflict.get('start_time', ''))
            return jsonify({
                'error': f"Khung giờ này đã có lịch: {conflict.get('title', 'Lịch hẹn')} ({conflict_time})"
            }), 409

        schedule_id, normalized_duration = ScheduleService.create_schedule(
            title,
            description,
            start_time,
            attendees,
            duration_minutes=duration_minutes,
            db_path=db_path
        )
        created = Schedule.get_by_id(schedule_id, db_path=db_path)
        event_id = _sync_create_calendar_event(
            user_id,
            schedule_id,
            title,
            description,
            start_time,
            (created or {}).get('end_time') or end_time,
            attendees,
            db_path
        )
        
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
            'schedule_id': schedule_id,
            'duration_minutes': normalized_duration,
            'calendar_synced': bool(event_id)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@schedule_bp.route('/list', methods=['GET'])
def list_schedules():
    """Get all schedules"""
    try:
        user_id = get_current_user_id(request, session=session)
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
        user_id = get_current_user_id(request, session=session)
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
        user_id = get_current_user_id(request, session=session)
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


@schedule_bp.route('/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """Update schedule information"""
    data = request.get_json() or {}
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    
    # Get current schedule
    schedule = Schedule.get_by_id(schedule_id, db_path=db_path)
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    # Prepare update data
    update_data = {}
    if 'title' in data:
        update_data['title'] = data.get('title', '').strip()
    if 'description' in data:
        update_data['description'] = data.get('description', '').strip()
    if 'start_time' in data:
        update_data['start_time'] = data.get('start_time', '').strip()
    duration_minutes = None
    if 'duration_minutes' in data:
        duration_minutes = ScheduleService.sanitize_duration_minutes(data.get('duration_minutes', 30), default_minutes=30)
    if 'end_time' in data:
        update_data['end_time'] = data.get('end_time', '').strip() or None
    if 'attendees' in data:
        attendees = data.get('attendees', [])
        update_data['attendees'] = ','.join(attendees) if isinstance(attendees, list) else attendees
    
    try:
        candidate_start = update_data.get('start_time', schedule.get('start_time'))
        candidate_end = update_data.get('end_time')
        if not candidate_end and duration_minutes is not None:
            candidate_end = ScheduleService.build_end_time(candidate_start, duration_minutes=duration_minutes)
            update_data['end_time'] = candidate_end
        elif not candidate_end and 'start_time' in update_data:
            inferred = ScheduleService.infer_duration_minutes(
                schedule.get('start_time'),
                schedule.get('end_time'),
                default_minutes=30
            )
            candidate_end = ScheduleService.build_end_time(candidate_start, duration_minutes=inferred)
            update_data['end_time'] = candidate_end
        if not candidate_end:
            candidate_end = schedule.get('end_time')

        conflict = ScheduleService.find_conflicting_schedule(
            start_time=candidate_start,
            end_time=candidate_end,
            db_path=db_path,
            exclude_schedule_id=schedule_id
        )
        if conflict:
            conflict_time = _format_vi_datetime(conflict.get('start_time', ''))
            return jsonify({
                'error': f"Không thể cập nhật: khung giờ trùng với lịch '{conflict.get('title', 'Lịch hẹn')}' ({conflict_time})"
            }), 409

        Schedule.update(schedule_id, db_path=db_path, **update_data)

        threading.Thread(
            target=_sync_update_calendar_event_async,
            args=(user_id, schedule_id, db_path),
            daemon=True
        ).start()
        
        History.create(
            f"Chỉnh sửa lịch hẹn: {schedule.get('title', '')}",
            f"Cập nhật: {', '.join(update_data.keys())}",
            action_type='schedule_updated',
            related_id=schedule_id,
            db_path=db_path
        )

        updated = Schedule.get_by_id(schedule_id, db_path=db_path)
        return jsonify({
            'success': True,
            'schedule': updated
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete schedule"""
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)
    
    # Get schedule info before deleting
    schedule = Schedule.get_by_id(schedule_id, db_path=db_path)
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    try:
        event_id = schedule.get('google_event_id')
        if event_id:
            token_file = get_user_token_file(user_id)
            calendar_service = CalendarService(token_file=token_file)
            if calendar_service.is_ready():
                calendar_service.delete_event(event_id)

        Schedule.delete(schedule_id, db_path=db_path)
        
        History.create(
            f"Xóa lịch hẹn: {schedule.get('title', '')}",
            f"Lịch hẹn đã bị xóa",
            action_type='schedule_deleted',
            related_id=schedule_id,
            db_path=db_path
        )
        
        return jsonify({
            'success': True,
            'message': f"Đã xóa lịch hẹn: {schedule.get('title', '')}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/sync-calendar', methods=['POST'])
def sync_schedules_to_calendar():
    """Sync all schedules to Google Calendar as events with reminders"""
    user_id = get_current_user_id(request, session=session)
    db_path = get_user_db_path(user_id)

    try:
        token_file = get_user_token_file(user_id)
        calendar_service = CalendarService(token_file=token_file)
        if not calendar_service.is_ready():
            return jsonify({'error': 'Google Calendar chưa sẵn sàng. Vui lòng đăng nhập Gmail lại.'}), 400

        schedules = Schedule.get_all(limit=2000, db_path=db_path)
        synced = 0
        failed = 0

        for item in schedules:
            try:
                schedule_id = item.get('id')
                title = item.get('title') or 'Lịch hẹn'
                description = item.get('description') or ''
                start_time = item.get('start_time')
                end_time = item.get('end_time')
                attendees_value = item.get('attendees') or ''
                attendees = [email.strip() for email in str(attendees_value).split(',') if email.strip()]
                event_id = item.get('google_event_id')

                if not start_time:
                    continue

                if event_id:
                    ok = calendar_service.update_event(
                        event_id=event_id,
                        title=title,
                        description=description,
                        start_time=start_time,
                        end_time=end_time,
                        attendees=attendees
                    )
                    if ok:
                        synced += 1
                    else:
                        failed += 1
                else:
                    created_event_id = calendar_service.create_event(
                        title=title,
                        description=description,
                        start_time=start_time,
                        end_time=end_time,
                        attendees=attendees
                    )
                    if created_event_id:
                        Schedule.update(schedule_id, google_event_id=created_event_id, db_path=db_path)
                        synced += 1
                    else:
                        failed += 1
            except Exception:
                failed += 1

        return jsonify({
            'success': True,
            'synced': synced,
            'failed': failed,
            'total': len(schedules)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
