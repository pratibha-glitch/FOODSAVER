from flask import Blueprint, request, jsonify, session
import models
from routes.auth import login_required, role_required
from services.urgency_ranker import rank_listings_by_urgency
from services.volunteer_matching import match_volunteers_for_listing

volunteer_bp = Blueprint('volunteer', __name__)

@volunteer_bp.route('/api/volunteer/listings', methods=['GET'])
@login_required
def volunteer_get_available_listings():
    """
    Returns available food listings for verified student volunteers,
    enriched with AI urgency prioritization and logistical deadlines.
    """
    # Auto-expire any items past operational deadline
    models.check_and_expire_listings()

    category = request.args.get('category')
    location_id = request.args.get('location_id')
    urgency_filter = request.args.get('urgency')

    # Only fetch 'available' listings for volunteer discovery
    listings = models.get_listings(status='available', category=category, location_id=location_id)

    # Rank and annotate with urgency priority
    ranked = rank_listings_by_urgency(listings)

    if urgency_filter:
        ranked = [l for l in ranked if l['urgency']['level'].upper() == urgency_filter.upper()]

    return jsonify({
        "success": True,
        "count": len(ranked),
        "listings": ranked
    })

@volunteer_bp.route('/api/volunteer/listings/<int:listing_id>/matching', methods=['GET'])
@login_required
def volunteer_get_smart_matching(listing_id):
    """
    Feature 2: Smart Volunteer Matching recommendations with plain language explanations.
    """
    result = match_volunteers_for_listing(listing_id)
    return jsonify(result)

@volunteer_bp.route('/api/volunteer/listings/<int:listing_id>/claim', methods=['POST'])
@login_required
@role_required('volunteer', 'admin')
def volunteer_claim_listing(listing_id):
    """
    Atomically claims a food listing for a verified volunteer.
    Prevents race condition / duplicate claims.
    """
    volunteer_id = session['user_id']
    success, message = models.claim_listing(listing_id, volunteer_id)

    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({"success": True, "message": message})

@volunteer_bp.route('/api/volunteer/listings/<int:listing_id>/start-pickup', methods=['POST'])
@login_required
@role_required('volunteer', 'admin')
def volunteer_start_pickup(listing_id):
    """Marks pickup as in progress (volunteer en route)."""
    volunteer_id = session['user_id']
    success, message = models.start_pickup_progress(listing_id, volunteer_id)

    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({"success": True, "message": message})

@volunteer_bp.route('/api/volunteer/listings/<int:listing_id>/collect', methods=['POST'])
@login_required
@role_required('volunteer', 'staff', 'admin')
def volunteer_complete_collection(listing_id):
    """
    Confirms physical collection and records verified actual collected quantity.
    """
    data = request.get_json(silent=True) or {}
    user_id = session['user_id']

    actual_val = data.get('actual_quantity_value')
    actual_unit = data.get('actual_quantity_unit', '').strip()

    if actual_val is None or not actual_unit:
        return jsonify({"success": False, "error": "Actual collected quantity value and unit are required."}), 400

    try:
        qty_num = float(actual_val)
        if qty_num <= 0:
            return jsonify({"success": False, "error": "Actual collected quantity must be greater than zero."}), 400
    except ValueError:
        return jsonify({"success": False, "error": "Actual quantity must be a valid number."}), 400

    success, message = models.complete_collection(listing_id, user_id, qty_num, actual_unit)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({"success": True, "message": message})

@volunteer_bp.route('/api/volunteer/my-pickups', methods=['GET'])
@login_required
@role_required('volunteer', 'admin')
def volunteer_get_my_pickups():
    """Returns pickups assigned to the currently logged in volunteer."""
    volunteer_id = session['user_id']
    pickups = models.get_listings(volunteer_id=volunteer_id)
    return jsonify({
        "success": True,
        "pickups": pickups
    })

@volunteer_bp.route('/api/volunteer/availability', methods=['POST'])
@login_required
@role_required('volunteer', 'admin')
def volunteer_toggle_availability():
    """Toggles availability status for smart matching."""
    data = request.get_json(silent=True) or {}
    user_id = session['user_id']
    is_available = bool(data.get('is_available', True))

    models.update_user_availability(user_id, is_available)
    session['is_available'] = is_available
    return jsonify({
        "success": True, 
        "message": f"Availability status updated to {'Available' if is_available else 'Busy / Offline'}."
    })
