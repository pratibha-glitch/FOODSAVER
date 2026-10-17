import json
from datetime import datetime
from database import get_db_connection

# ============================================================================
# USER & AUTHENTICATION MODELS
# ============================================================================

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute("""
            SELECT u.*, loc.name as location_name 
            FROM users u
            LEFT JOIN campus_locations loc ON u.campus_location_id = loc.id
            WHERE u.id = ?;
        """, (user_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_user_by_username_or_email(identifier):
    conn = get_db_connection()
    try:
        user = conn.execute("""
            SELECT u.*, loc.name as location_name 
            FROM users u
            LEFT JOIN campus_locations loc ON u.campus_location_id = loc.id
            WHERE LOWER(u.username) = LOWER(?) OR LOWER(u.email) = LOWER(?);
        """, (identifier, identifier)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def create_user(username, email, password_hash, role, full_name, phone="", location_id=None, is_verified=0):
    conn = get_db_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, full_name, phone, campus_location_id, is_verified, is_available, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
        """, (username, email, password_hash, role, full_name, phone, location_id, is_verified, now))
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    finally:
        conn.close()

def get_all_users(role=None):
    conn = get_db_connection()
    try:
        if role:
            rows = conn.execute("""
                SELECT u.id, u.username, u.email, u.role, u.full_name, u.phone, u.campus_location_id, 
                       u.is_verified, u.is_available, u.created_at, loc.name as location_name
                FROM users u
                LEFT JOIN campus_locations loc ON u.campus_location_id = loc.id
                WHERE u.role = ?
                ORDER BY u.created_at DESC;
            """, (role,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT u.id, u.username, u.email, u.role, u.full_name, u.phone, u.campus_location_id, 
                       u.is_verified, u.is_available, u.created_at, loc.name as location_name
                FROM users u
                LEFT JOIN campus_locations loc ON u.campus_location_id = loc.id
                ORDER BY u.created_at DESC;
            """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def update_user_verification(user_id, is_verified):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET is_verified = ? WHERE id = ?;", (1 if is_verified else 0, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def update_user_availability(user_id, is_available):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET is_available = ? WHERE id = ?;", (1 if is_available else 0, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

# ============================================================================
# CAMPUS LOCATION MODELS
# ============================================================================

def get_all_locations(active_only=True):
    conn = get_db_connection()
    try:
        query = "SELECT * FROM campus_locations"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name ASC;"
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_location_by_id(location_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM campus_locations WHERE id = ?;", (location_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_location(name, code, building, floor, zone, contact_person="", phone=""):
    conn = get_db_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO campus_locations (name, code, building, floor, zone, contact_person, phone, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?);
        """, (name, code, building, floor, zone, contact_person, phone, now))
        loc_id = cursor.lastrowid
        conn.commit()
        return loc_id
    finally:
        conn.close()

# ============================================================================
# FOOD LISTING MODELS & LIFECYCLE (CONCURRENCY-SAFE)
# ============================================================================

def create_food_listing(data, staff_id):
    conn = get_db_connection()
    try:
        now = datetime.now().isoformat()
        status = data.get('status', 'draft')
        
        # Enforce that a listing cannot be published as 'available' unless checklist is confirmed
        checklist_confirmed = 1 if data.get('safety_checklist_confirmed') else 0
        if status == 'available' and not checklist_confirmed:
            status = 'draft'

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO food_listings (
                created_by_staff_id, location_id, food_name, category,
                quantity_value, quantity_unit, quantity_source, photo_filename,
                cooking_time, storage_condition, known_allergens, staff_notes,
                operational_deadline, safety_checklist_confirmed, safety_notes,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            staff_id,
            data['location_id'],
            data['food_name'].strip(),
            data['category'],
            float(data['quantity_value']),
            data['quantity_unit'],
            data.get('quantity_source', 'manually_estimated'),
            data.get('photo_filename'),
            data.get('cooking_time'),
            data.get('storage_condition', 'ambient_covered'),
            data.get('known_allergens', ''),
            data.get('staff_notes', ''),
            data['operational_deadline'],
            checklist_confirmed,
            data.get('safety_notes', ''),
            status,
            now,
            now
        ))
        listing_id = cursor.lastrowid

        # Record audit log
        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, 'none', ?, ?, 'Listing created by canteen staff.', ?);
        """, (listing_id, status, staff_id, now))

        # If created directly as available, create notification for volunteers
        if status == 'available':
            cursor.execute("""
                INSERT INTO in_app_notifications (recipient_user_id, target_role, listing_id, title, message, notification_type, created_at)
                VALUES (NULL, 'volunteer', ?, 'Surplus Food Published', ?, 'broadcast', ?);
            """, (
                listing_id, 
                f"New surplus: {data['food_name']} ({data['quantity_value']} {data['quantity_unit']}) available for pickup.",
                now
            ))

        conn.commit()
        return listing_id
    finally:
        conn.close()

def update_food_listing(listing_id, data, staff_id):
    conn = get_db_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.cursor()

        # Check existing listing
        existing = cursor.execute("SELECT * FROM food_listings WHERE id = ?;", (listing_id,)).fetchone()
        if not existing:
            return False, "Listing not found."
        
        # Check permissions: only creator staff or admin can edit
        if existing['created_by_staff_id'] != staff_id:
            user = get_user_by_id(staff_id)
            if not user or user['role'] != 'admin':
                return False, "Unauthorized to edit this listing."

        # Cannot edit if already claimed, collected, or cancelled
        if existing['status'] in ('claimed', 'pickup_in_progress', 'collected', 'cancelled'):
            return False, f"Cannot edit listing in '{existing['status']}' state."

        old_status = existing['status']
        new_status = data.get('status', old_status)
        checklist_confirmed = 1 if data.get('safety_checklist_confirmed', existing['safety_checklist_confirmed']) else 0

        # Cannot move to 'available' without checklist
        if new_status == 'available' and not checklist_confirmed:
            return False, "Cannot publish listing without confirming safety and handling verification."

        cursor.execute("""
            UPDATE food_listings SET
                location_id = ?,
                food_name = ?,
                category = ?,
                quantity_value = ?,
                quantity_unit = ?,
                quantity_source = ?,
                photo_filename = COALESCE(?, photo_filename),
                cooking_time = ?,
                storage_condition = ?,
                known_allergens = ?,
                staff_notes = ?,
                operational_deadline = ?,
                safety_checklist_confirmed = ?,
                safety_notes = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            data.get('location_id', existing['location_id']),
            data.get('food_name', existing['food_name']),
            data.get('category', existing['category']),
            float(data.get('quantity_value', existing['quantity_value'])),
            data.get('quantity_unit', existing['quantity_unit']),
            data.get('quantity_source', existing['quantity_source']),
            data.get('photo_filename'),
            data.get('cooking_time', existing['cooking_time']),
            data.get('storage_condition', existing['storage_condition']),
            data.get('known_allergens', existing['known_allergens']),
            data.get('staff_notes', existing['staff_notes']),
            data.get('operational_deadline', existing['operational_deadline']),
            checklist_confirmed,
            data.get('safety_notes', existing['safety_notes']),
            new_status,
            now,
            listing_id
        ))

        if old_status != new_status:
            cursor.execute("""
                INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
                VALUES (?, ?, ?, ?, 'Status updated by staff.', ?);
            """, (listing_id, old_status, new_status, staff_id, now))

            if new_status == 'available':
                cursor.execute("""
                    INSERT INTO in_app_notifications (recipient_user_id, target_role, listing_id, title, message, notification_type, created_at)
                    VALUES (NULL, 'volunteer', ?, 'Surplus Food Published', ?, 'broadcast', ?);
                """, (
                    listing_id, 
                    f"Surplus food: {data.get('food_name', existing['food_name'])} is now available for pickup.",
                    now
                ))

        conn.commit()
        return True, "Listing updated successfully."
    finally:
        conn.close()

def get_listing_by_id(listing_id):
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT l.*, 
                   loc.name as location_name, loc.building, loc.floor, loc.zone, loc.contact_person, loc.phone as location_phone,
                   creator.full_name as staff_name, creator.email as staff_email, creator.phone as staff_phone,
                   vol.full_name as volunteer_name, vol.email as volunteer_email, vol.phone as volunteer_phone
            FROM food_listings l
            JOIN campus_locations loc ON l.location_id = loc.id
            JOIN users creator ON l.created_by_staff_id = creator.id
            LEFT JOIN users vol ON l.claimed_by_volunteer_id = vol.id
            WHERE l.id = ?;
        """, (listing_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_listings(status=None, category=None, location_id=None, staff_id=None, volunteer_id=None, limit=100):
    conn = get_db_connection()
    try:
        query = """
            SELECT l.*, 
                   loc.name as location_name, loc.building, loc.zone,
                   creator.full_name as staff_name,
                   vol.full_name as volunteer_name
            FROM food_listings l
            JOIN campus_locations loc ON l.location_id = loc.id
            JOIN users creator ON l.created_by_staff_id = creator.id
            LEFT JOIN users vol ON l.claimed_by_volunteer_id = vol.id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND l.status = ?"
            params.append(status)
        if category:
            query += " AND l.category = ?"
            params.append(category)
        if location_id:
            query += " AND l.location_id = ?"
            params.append(location_id)
        if staff_id:
            query += " AND l.created_by_staff_id = ?"
            params.append(staff_id)
        if volunteer_id:
            query += " AND l.claimed_by_volunteer_id = ?"
            params.append(volunteer_id)

        query += " ORDER BY l.operational_deadline ASC, l.created_at DESC LIMIT ?;"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

# ============================================================================
# CONCURRENCY-SAFE CLAIMING AND LIFECYCLE TRANSITIONS
# ============================================================================

def claim_listing(listing_id, volunteer_id):
    """
    Atomically claims a listing for a verified volunteer.
    Guarantees no race condition or double claims via atomic conditional update.
    """
    conn = get_db_connection()
    try:
        now = datetime.now()
        now_str = now.isoformat()

        cursor = conn.cursor()
        
        # 1. Verify user exists, is a volunteer, and is verified
        volunteer = cursor.execute("SELECT * FROM users WHERE id = ?;", (volunteer_id,)).fetchone()
        if not volunteer:
            return False, "Volunteer user not found."
        if volunteer['role'] != 'volunteer':
            return False, "Only volunteers are authorized to claim food."
        if not volunteer['is_verified']:
            return False, "Volunteer account is pending administrator verification. You cannot claim food until verified."

        # 2. Check volunteer's active claim load
        active_claims = cursor.execute("""
            SELECT COUNT(*) FROM food_listings 
            WHERE claimed_by_volunteer_id = ? AND status IN ('claimed', 'pickup_in_progress');
        """, (volunteer_id,)).fetchone()[0]

        max_allowed = 2
        config_max = cursor.execute("SELECT value FROM system_config WHERE key = 'volunteer_max_concurrent_claims';").fetchone()
        if config_max:
            try:
                max_allowed = int(config_max['value'])
            except ValueError:
                pass

        if active_claims >= max_allowed:
            return False, f"You already have {active_claims} active pickups in progress (limit is {max_allowed}). Please complete or release existing pickups first."

        # 3. Check listing existence and expiry
        listing = cursor.execute("SELECT * FROM food_listings WHERE id = ?;", (listing_id,)).fetchone()
        if not listing:
            return False, "Listing not found."

        if listing['status'] != 'available':
            return False, f"Listing cannot be claimed because its current status is '{listing['status']}'."

        # Check if deadline has passed
        try:
            deadline_dt = datetime.fromisoformat(listing['operational_deadline'])
            if now > deadline_dt:
                # Mark as expired
                cursor.execute("UPDATE food_listings SET status = 'expired', updated_at = ? WHERE id = ?;", (now_str, listing_id))
                cursor.execute("""
                    INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
                    VALUES (?, 'available', 'expired', ?, 'System auto-expired: operational deadline passed before claim.', ?);
                """, (listing_id, volunteer_id, now_str))
                conn.commit()
                return False, "Operational pickup deadline has passed for this listing. It is no longer available."
        except Exception:
            pass

        # 4. ATOMIC CONCURRENCY-SAFE UPDATE
        # Ensures that if 2 volunteers attempt to claim simultaneously, only ONE succeeds.
        cursor.execute("""
            UPDATE food_listings
            SET status = 'claimed',
                claimed_by_volunteer_id = ?,
                claimed_at = ?,
                updated_at = ?
            WHERE id = ? AND status = 'available';
        """, (volunteer_id, now_str, now_str, listing_id))

        if cursor.rowcount == 0:
            conn.rollback()
            return False, "Conflict: This listing was just claimed by another volunteer or is no longer available."

        # 5. Insert audit log
        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, 'available', 'claimed', ?, ?, ?);
        """, (listing_id, volunteer_id, f"Claimed by verified volunteer {volunteer['full_name']}.", now_str))

        # 6. Notify canteen staff that their listing was claimed
        cursor.execute("""
            INSERT INTO in_app_notifications (recipient_user_id, target_role, listing_id, title, message, notification_type, created_at)
            VALUES (?, 'staff', ?, 'Food Listing Claimed', ?, 'claim_alert', ?);
        """, (
            listing['created_by_staff_id'],
            listing_id,
            f"Your listing '{listing['food_name']}' was claimed by volunteer {volunteer['full_name']} ({volunteer['phone']}).",
            now_str
        ))

        conn.commit()
        return True, "Listing successfully claimed! Please coordinate pickup before the operational deadline."
    finally:
        conn.close()

def start_pickup_progress(listing_id, volunteer_id):
    """Volunteer marks that they are en route / pickup in progress."""
    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        cursor = conn.cursor()

        listing = cursor.execute("SELECT * FROM food_listings WHERE id = ?;", (listing_id,)).fetchone()
        if not listing:
            return False, "Listing not found."
        if listing['claimed_by_volunteer_id'] != volunteer_id:
            return False, "Only the claiming volunteer can mark pickup in progress."
        if listing['status'] != 'claimed':
            return False, f"Cannot start pickup from status '{listing['status']}'."

        cursor.execute("""
            UPDATE food_listings
            SET status = 'pickup_in_progress',
                pickup_started_at = ?,
                updated_at = ?
            WHERE id = ? AND status = 'claimed';
        """, (now_str, now_str, listing_id))

        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, 'claimed', 'pickup_in_progress', ?, 'Volunteer is en route / arrived at canteen.', ?);
        """, (listing_id, volunteer_id, now_str))

        conn.commit()
        return True, "Pickup marked as In Progress."
    finally:
        conn.close()

def complete_collection(listing_id, user_id, actual_quantity_value, actual_quantity_unit):
    """
    Confirms actual physical collection and records verified collected quantity.
    Can be confirmed by the assigned volunteer or the canteen staff.
    """
    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        cursor = conn.cursor()

        listing = cursor.execute("SELECT * FROM food_listings WHERE id = ?;", (listing_id,)).fetchone()
        if not listing:
            return False, "Listing not found."

        # Permission check: assigned volunteer, creator staff, or admin
        user = cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        if not user:
            return False, "User not found."

        is_assigned_vol = listing['claimed_by_volunteer_id'] == user_id
        is_creator_staff = listing['created_by_staff_id'] == user_id
        is_admin = user['role'] == 'admin'

        if not (is_assigned_vol or is_creator_staff or is_admin):
            return False, "Unauthorized to confirm collection."

        if listing['status'] not in ('claimed', 'pickup_in_progress'):
            return False, f"Cannot complete collection for listing in '{listing['status']}' status."

        cursor.execute("""
            UPDATE food_listings
            SET status = 'collected',
                collected_at = ?,
                actual_collected_quantity_value = ?,
                actual_collected_quantity_unit = ?,
                updated_at = ?
            WHERE id = ?;
        """, (now_str, float(actual_quantity_value), actual_quantity_unit, now_str, listing_id))

        note = f"Collection verified by {user['full_name']} ({user['role']}). Actual collected: {actual_quantity_value} {actual_quantity_unit}."
        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, ?, 'collected', ?, ?, ?);
        """, (listing_id, listing['status'], user_id, note, now_str))

        # Notify other party
        target_id = listing['created_by_staff_id'] if is_assigned_vol else listing['claimed_by_volunteer_id']
        if target_id:
            cursor.execute("""
                INSERT INTO in_app_notifications (recipient_user_id, target_role, listing_id, title, message, notification_type, created_at)
                VALUES (?, NULL, ?, 'Food Collection Completed', ?, 'status_update', ?);
            """, (target_id, listing_id, f"Food collection confirmed for '{listing['food_name']}'. Thank you for supporting SDG 2 Zero Hunger!", now_str))

        conn.commit()
        return True, "Food collection confirmed and recorded in impact statistics."
    finally:
        conn.close()

def cancel_listing(listing_id, user_id, reason):
    """Cancels a listing with mandatory cancellation reason and audit log."""
    if not reason or not reason.strip():
        return False, "A clear cancellation reason is required."

    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        cursor = conn.cursor()

        listing = cursor.execute("SELECT * FROM food_listings WHERE id = ?;", (listing_id,)).fetchone()
        if not listing:
            return False, "Listing not found."

        user = cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        if not user:
            return False, "User not found."

        # Permission check
        is_creator_staff = listing['created_by_staff_id'] == user_id
        is_assigned_vol = listing['claimed_by_volunteer_id'] == user_id
        is_admin = user['role'] == 'admin'

        if not (is_creator_staff or is_assigned_vol or is_admin):
            return False, "Unauthorized to cancel this listing."

        if listing['status'] in ('collected', 'cancelled', 'expired'):
            return False, f"Listing cannot be cancelled because it is already '{listing['status']}'."

        old_status = listing['status']
        cursor.execute("""
            UPDATE food_listings
            SET status = 'cancelled',
                cancelled_at = ?,
                cancellation_reason = ?,
                updated_at = ?
            WHERE id = ?;
        """, (now_str, reason.strip(), now_str, listing_id))

        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, ?, 'cancelled', ?, ?, ?);
        """, (listing_id, old_status, user_id, f"Cancelled by {user['full_name']} ({user['role']}). Reason: {reason.strip()}", now_str))

        conn.commit()
        return True, "Listing cancelled successfully."
    finally:
        conn.close()

def check_and_expire_listings():
    """Finds all available/claimed listings past their operational deadline and marks them expired."""
    conn = get_db_connection()
    try:
        now = datetime.now()
        now_str = now.isoformat()
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT id, operational_deadline, status FROM food_listings
            WHERE status IN ('available', 'claimed');
        """).fetchall()

        expired_count = 0
        for r in rows:
            try:
                deadline = datetime.fromisoformat(r['operational_deadline'])
                if now > deadline:
                    cursor.execute("""
                        UPDATE food_listings SET status = 'expired', updated_at = ? WHERE id = ?;
                    """, (now_str, r['id']))
                    cursor.execute("""
                        INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
                        VALUES (?, ?, 'expired', 1, 'Automatic operational deadline expiration.', ?);
                    """, (r['id'], r['status'], now_str))
                    expired_count += 1
            except Exception:
                continue

        conn.commit()
        return expired_count
    finally:
        conn.close()

# ============================================================================
# AUDIT LOG & NOTIFICATIONS
# ============================================================================

def get_audit_logs(listing_id=None, limit=50):
    conn = get_db_connection()
    try:
        if listing_id:
            rows = conn.execute("""
                SELECT a.*, u.full_name as user_name, u.role as user_role, l.food_name
                FROM status_audit_log a
                JOIN users u ON a.changed_by_user_id = u.id
                JOIN food_listings l ON a.listing_id = l.id
                WHERE a.listing_id = ?
                ORDER BY a.created_at DESC LIMIT ?;
            """, (listing_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT a.*, u.full_name as user_name, u.role as user_role, l.food_name
                FROM status_audit_log a
                JOIN users u ON a.changed_by_user_id = u.id
                JOIN food_listings l ON a.listing_id = l.id
                ORDER BY a.created_at DESC LIMIT ?;
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_notifications(user_id=None, role=None, unread_only=False, limit=20):
    conn = get_db_connection()
    try:
        query = """
            SELECT n.*, l.food_name, l.status as listing_status
            FROM in_app_notifications n
            LEFT JOIN food_listings l ON n.listing_id = l.id
            WHERE 1=1
        """
        params = []
        if user_id:
            query += " AND (n.recipient_user_id = ? OR n.target_role = ? OR n.target_role = 'all')"
            params.extend([user_id, role])
        elif role:
            query += " AND (n.target_role = ? OR n.target_role = 'all')"
            params.append(role)

        if unread_only:
            query += " AND n.is_read = 0"

        query += " ORDER BY n.created_at DESC LIMIT ?;"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def mark_notification_read(notification_id, user_id):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE in_app_notifications SET is_read = 1 WHERE id = ?;", (notification_id,))
        conn.commit()
        return True
    finally:
        conn.close()

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

def get_system_config():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT key, value, description FROM system_config;").fetchall()
        return {r['key']: r['value'] for r in rows}
    finally:
        conn.close()

def update_system_config_item(key, value):
    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO system_config (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at;
        """, (key, str(value), now_str))
        conn.commit()
        return True
    finally:
        conn.close()

# ============================================================================
# AI ANALYSIS LOGGING
# ============================================================================

def save_ai_analysis_log(listing_id, photo_filename, raw_ai, parsed_data):
    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_analysis_logs (
                listing_id, photo_filename, raw_ai_response, parsed_food_name,
                parsed_category, parsed_quantity_estimate, confidence_score,
                confidence_reasoning, fields_requiring_staff_input, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            listing_id,
            photo_filename,
            json.dumps(raw_ai) if isinstance(raw_ai, (dict, list)) else str(raw_ai),
            parsed_data.get('food_name'),
            parsed_data.get('category'),
            parsed_data.get('approximate_quantity_range'),
            parsed_data.get('confidence_score'),
            parsed_data.get('confidence_reasoning'),
            json.dumps(parsed_data.get('fields_requiring_staff_input', [])),
            now_str
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
