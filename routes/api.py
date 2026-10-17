from flask import Blueprint, request, jsonify, session
import models
from routes.auth import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/locations', methods=['GET'])
def get_locations():
    """Returns active campus locations for dropdown menus and filters."""
    locations = models.get_all_locations(active_only=True)
    return jsonify({"success": True, "locations": locations})

@api_bp.route('/api/notifications', methods=['GET'])
@login_required
def get_user_notifications():
    """Returns notifications applicable to current user or role."""
    user_id = session.get('user_id')
    role = session.get('role')
    unread_only = request.args.get('unread') == '1'

    notifications = models.get_notifications(user_id=user_id, role=role, unread_only=unread_only)
    return jsonify({"success": True, "notifications": notifications})

@api_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def read_notification(notification_id):
    user_id = session.get('user_id')
    models.mark_notification_read(notification_id, user_id)
    return jsonify({"success": True, "message": "Notification marked as read."})

@api_bp.route('/api/auth/demo-switch', methods=['POST'])
def demo_switch():
    """
    Convenience endpoint for college evaluation & demo purposes.
    Quickly switches active session between pre-seeded test roles:
    'admin', 'staff_north', 'staff_central', 'volunteer_priya', 'volunteer_pending'.
    """
    data = request.get_json(silent=True) or {}
    target_username = data.get('username', '')
    ROLE_MAPPING = {
        'admin': 'admin',
        'staff': 'staff_north',
        'canteen_staff': 'staff_north',
        'staff_north': 'staff_north',
        'volunteer': 'volunteer_priya',
        'verified_volunteer': 'volunteer_priya',
        'volunteer_priya': 'volunteer_priya',
        'volunteer_pending': 'volunteer_pending'
    }
    actual_username = ROLE_MAPPING.get(target_username, target_username)

    user = models.get_user_by_username_or_email(actual_username)
    if not user:
        return jsonify({"success": False, "error": f"Demo role user '{target_username}' not found."}), 404

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['full_name'] = user['full_name']
    session['is_verified'] = bool(user['is_verified'])

    safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
    return jsonify({
        "success": True,
        "message": f"Switched session to {user['full_name']} ({user['role']})",
        "user": safe_user
    })

@api_bp.route('/api/listings/<int:listing_id>', methods=['GET'])
@login_required
def get_listing_details(listing_id):
    """Returns dedicated details view for a listing including audit history and urgency."""
    from services.urgency_ranker import calculate_urgency_priority
    listing = models.get_listing_by_id(listing_id)
    if not listing:
        return jsonify({"success": False, "error": "Food listing not found."}), 404

    urgency = calculate_urgency_priority(listing)
    audit_logs = models.get_audit_logs(listing_id=listing_id)

    listing_dict = dict(listing)
    listing_dict['urgency'] = urgency

    return jsonify({
        "success": True,
        "listing": listing_dict,
        "audit_logs": audit_logs
    })
