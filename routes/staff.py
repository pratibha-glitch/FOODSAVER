import os
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from PIL import Image

import models
from config import Config
from routes.auth import login_required, role_required
from services.ai_vision import analyze_food_photo
from services.notification_service import generate_notification_draft, dispatch_in_app_notification

staff_bp = Blueprint('staff', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS

@staff_bp.route('/api/staff/analyze-photo', methods=['POST'])
@login_required
@role_required('staff', 'admin')
def staff_analyze_photo():
    """
    Handles staff food photo upload, runs real AI vision analysis,
    and returns structured suggestions for review.
    """
    if 'photo' not in request.files:
        return jsonify({"success": False, "error": "No food photograph uploaded."}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({"success": False, "error": "Selected file has an empty filename."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False, 
            "error": f"Unsupported format. Allowed formats: {', '.join(Config.ALLOWED_IMAGE_EXTENSIONS)}"
        }), 400

    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Secure random filename to avoid collisions and directory traversal
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"food_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(Config.UPLOAD_FOLDER, unique_filename)

    try:
        file.save(filepath)

        # Validate with PIL and create optimized web version if huge
        with Image.open(filepath) as img:
            img.verify()
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"success": False, "error": f"Image validation failed: {str(e)}"}), 400

    # Run AI Analysis
    analysis_result = analyze_food_photo(filepath)
    if not analysis_result['success']:
        # Return honest error while preserving uploaded photo for manual entry
        return jsonify({
            "success": True,
            "ai_available": False,
            "photo_filename": unique_filename,
            "photo_url": f"/static/uploads/{unique_filename}",
            "warning": analysis_result['error'],
            "ai_data": None
        })

    ai_data = analysis_result['data']

    # Log AI analysis
    models.save_ai_analysis_log(
        listing_id=None,
        photo_filename=unique_filename,
        raw_ai=ai_data,
        parsed_data=ai_data
    )

    return jsonify({
        "success": True,
        "ai_available": True,
        "photo_filename": unique_filename,
        "photo_url": f"/static/uploads/{unique_filename}",
        "ai_data": ai_data
    })

@staff_bp.route('/api/staff/listings', methods=['POST'])
@login_required
@role_required('staff', 'admin')
def staff_create_listing():
    """
    Creates a new food listing.
    Enforces that 'available' status requires confirmed human safety verification.
    """
    data = request.get_json(silent=True) or {}
    staff_id = session['user_id']

    # Validation
    required_fields = ['food_name', 'category', 'quantity_value', 'quantity_unit', 'location_id', 'operational_deadline']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"success": False, "error": f"Missing required field: '{field}'."}), 400

    try:
        qty_val = float(data['quantity_value'])
        if qty_val <= 0:
            return jsonify({"success": False, "error": "Quantity must be greater than zero."}), 400
    except ValueError:
        return jsonify({"success": False, "error": "Quantity value must be a valid number."}), 400

    # Human safety checklist check
    if data.get('status') == 'available' and not data.get('safety_checklist_confirmed'):
        return jsonify({
            "success": False, 
            "error": "A listing cannot be published as 'available' to volunteers without confirming the human food safety & handling checklist."
        }), 400

    listing_id = models.create_food_listing(data, staff_id)
    return jsonify({
        "success": True,
        "message": "Food listing created successfully.",
        "listing_id": listing_id
    })

@staff_bp.route('/api/staff/listings', methods=['GET'])
@login_required
@role_required('staff', 'admin')
def staff_get_listings():
    staff_id = session['user_id']
    user_role = session['role']

    status = request.args.get('status')
    location_id = request.args.get('location_id')

    # If staff, default to own listings unless admin
    filter_staff_id = None if user_role == 'admin' else staff_id
    listings = models.get_listings(status=status, location_id=location_id, staff_id=filter_staff_id)

    return jsonify({
        "success": True,
        "listings": listings
    })

@staff_bp.route('/api/staff/listings/<int:listing_id>', methods=['GET'])
@login_required
def staff_get_listing_detail(listing_id):
    listing = models.get_listing_by_id(listing_id)
    if not listing:
        return jsonify({"success": False, "error": "Listing not found."}), 404

    audit_logs = models.get_audit_logs(listing_id=listing_id)
    return jsonify({
        "success": True,
        "listing": listing,
        "audit_logs": audit_logs
    })

@staff_bp.route('/api/staff/listings/<int:listing_id>', methods=['PUT'])
@login_required
@role_required('staff', 'admin')
def staff_update_listing(listing_id):
    data = request.get_json(silent=True) or {}
    staff_id = session['user_id']

    success, message = models.update_food_listing(listing_id, data, staff_id)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({"success": True, "message": message})

@staff_bp.route('/api/staff/listings/<int:listing_id>/draft-notification', methods=['POST'])
@login_required
@role_required('staff', 'admin')
def staff_draft_notification(listing_id):
    """Generates AI-drafted notification from verified database listing."""
    listing = models.get_listing_by_id(listing_id)
    if not listing:
        return jsonify({"success": False, "error": "Listing not found."}), 404

    draft = generate_notification_draft(listing)
    return jsonify({"success": True, "draft": draft})

@staff_bp.route('/api/staff/listings/<int:listing_id>/send-notification', methods=['POST'])
@login_required
@role_required('staff', 'admin')
def staff_send_notification(listing_id):
    """Dispatches reviewed in-app notification to verified volunteers."""
    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()
    message = data.get('message', '').strip()

    if not title or not message:
        return jsonify({"success": False, "error": "Notification title and message are required."}), 400

    notif_id = dispatch_in_app_notification(listing_id, title, message, target_role="volunteer")
    return jsonify({
        "success": True, 
        "message": "In-app broadcast notification dispatched to all verified volunteers.",
        "notification_id": notif_id
    })
