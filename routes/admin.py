from flask import Blueprint, request, jsonify, session
import models
from routes.auth import login_required, role_required
from services.metrics_service import get_system_metrics

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/metrics', methods=['GET'])
@login_required
def admin_get_metrics():
    """Returns honest system metrics derived from actual database records."""
    metrics = get_system_metrics()
    return jsonify({"success": True, "metrics": metrics})

@admin_bp.route('/api/admin/users', methods=['GET'])
@login_required
@role_required('admin')
def admin_get_users():
    role = request.args.get('role')
    users = models.get_all_users(role=role)
    return jsonify({"success": True, "users": users})

@admin_bp.route('/api/admin/users/<int:user_id>/verify', methods=['POST'])
@login_required
@role_required('admin')
def admin_verify_user(user_id):
    data = request.get_json(silent=True) or {}
    is_verified = bool(data.get('is_verified', True))

    models.update_user_verification(user_id, is_verified)
    action_text = "verified" if is_verified else "unverified"
    return jsonify({
        "success": True,
        "message": f"User verification status updated to: {action_text}."
    })

@admin_bp.route('/api/admin/locations', methods=['GET', 'POST'])
@login_required
def admin_locations():
    if request.method == 'POST':
        # Admin only for creating locations
        if session.get('role') != 'admin':
            return jsonify({"success": False, "error": "Admin privileges required."}), 403

        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        code = data.get('code', '').strip()
        building = data.get('building', '').strip()
        floor = data.get('floor', '').strip()
        zone = data.get('zone', 'Central Zone').strip()
        contact = data.get('contact_person', '').strip()
        phone = data.get('phone', '').strip()

        if not name or not code or not building:
            return jsonify({"success": False, "error": "Location Name, Code, and Building are required."}), 400

        loc_id = models.create_location(name, code, building, floor, zone, contact, phone)
        return jsonify({"success": True, "message": "Campus location created.", "location_id": loc_id})

    # GET: Any authenticated user can view locations list for forms/filters
    locations = models.get_all_locations()
    return jsonify({"success": True, "locations": locations})

@admin_bp.route('/api/admin/config', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_config():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        for k, v in data.items():
            models.update_system_config_item(k, v)
        return jsonify({"success": True, "message": "System configuration updated successfully."})

    config = models.get_system_config()
    return jsonify({"success": True, "config": config})

@admin_bp.route('/api/admin/audit-logs', methods=['GET'])
@login_required
@role_required('admin')
def admin_audit_logs():
    listing_id = request.args.get('listing_id')
    logs = models.get_audit_logs(listing_id=listing_id, limit=100)
    return jsonify({"success": True, "logs": logs})

@admin_bp.route('/api/admin/listings', methods=['GET'])
@login_required
@role_required('admin')
def admin_all_listings():
    status = request.args.get('status')
    location_id = request.args.get('location_id')
    listings = models.get_listings(status=status, location_id=location_id, limit=200)
    return jsonify({"success": True, "listings": listings})

@admin_bp.route('/api/listings/<int:listing_id>/cancel', methods=['POST'])
@login_required
def cancel_listing_endpoint(listing_id):
    """Allows staff, assigned volunteer, or admin to cancel with a required reason."""
    data = request.get_json(silent=True) or {}
    reason = data.get('reason', '').strip()
    user_id = session['user_id']

    if not reason:
        return jsonify({"success": False, "error": "A clear cancellation reason is mandatory."}), 400

    success, message = models.cancel_listing(listing_id, user_id, reason)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({"success": True, "message": message})
