from flask import Blueprint, request, jsonify, session
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User
from utils.user_context import get_current_user_id

user_bp = Blueprint('user', __name__, url_prefix='/api/user')


@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    user_id = get_current_user_id(request)
    user = User.get(user_id)
    
    if not user:
        user = User.get_or_create(user_id)
    
    return jsonify({
        'success': True,
        'user': user
    })


@user_bp.route('/profile', methods=['POST'])
def update_profile():
    """Update user profile"""
    user_id = get_current_user_id(request)
    data = request.get_json() or {}
    
    # Allow updating name, email, avatar_url
    update_data = {
        k: v for k, v in data.items()
        if k in ['name', 'email', 'avatar_url']
    }
    
    success = User.update(user_id, **update_data)
    
    if success:
        user = User.get(user_id)
        return jsonify({
            'success': True,
            'message': 'Profile updated',
            'user': user
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No changes made'
        }), 400


@user_bp.route('/gmail-connected', methods=['POST'])
def mark_gmail_connected():
    """Mark user Gmail as connected"""
    user_id = get_current_user_id(request)
    User.update(user_id, gmail_connected=1)
    
    user = User.get(user_id)
    return jsonify({
        'success': True,
        'user': user
    })


@user_bp.route('/gmail-disconnected', methods=['POST'])
def mark_gmail_disconnected():
    """Mark user Gmail as disconnected"""
    user_id = get_current_user_id(request)
    User.update(user_id, gmail_connected=0)
    
    user = User.get(user_id)
    return jsonify({
        'success': True,
        'user': user
    })
