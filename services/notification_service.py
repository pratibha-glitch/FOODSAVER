from datetime import datetime
from database import get_db_connection

def generate_notification_draft(listing_data):
    """
    Generates a concise notification draft strictly from confirmed database fields.
    Staff can review, modify, and confirm this draft before dispatching in-app alerts.
    """
    food_name = listing_data.get('food_name', 'Surplus Food')
    qty = f"{listing_data.get('quantity_value', '')} {listing_data.get('quantity_unit', '')}".strip()
    loc = listing_data.get('location_name', 'Campus Dining Hall')
    storage = listing_data.get('storage_condition', '').replace('_', ' ').title()
    notes = listing_data.get('staff_notes', '')

    deadline_str = listing_data.get('operational_deadline', '')
    try:
        dt = datetime.fromisoformat(deadline_str)
        formatted_deadline = dt.strftime('%I:%M %p (%b %d)')
    except Exception:
        formatted_deadline = deadline_str

    # In-App Broadcast Title and Message
    title = f"🌾 Surplus Food Alert: {food_name} at {loc}"
    in_app_body = (
        f"Available immediately: {food_name} ({qty}). "
        f"Pickup location: {loc}. "
        f"Operational pickup deadline: {formatted_deadline}. "
        f"Storage condition: {storage}. "
        f"{'Notes: ' + notes if notes else ''}"
    ).strip()

    # Documented Optional WhatsApp Simulation Message
    # Explicitly labeled as formatted broadcast text template
    whatsapp_template = (
        f"🚨 *SMARTPLATE AI SURPLUS ALERT (SDG 2)* 🚨\n"
        f"----------------------------------------\n"
        f"🍲 *Item:* {food_name} ({qty})\n"
        f"📍 *Pickup Location:* {loc}\n"
        f"⏳ *Pickup Deadline:* {formatted_deadline}\n"
        f"🛡️ *Handling:* {storage}\n"
        f"----------------------------------------\n"
        f"👉 Log in to SmartPlate AI to claim this pickup (Verified NSS Volunteers only)."
    )

    return {
        "title": title,
        "in_app_body": in_app_body,
        "whatsapp_template": whatsapp_template,
        "is_whatsapp_live_integrated": False,
        "integration_note": (
            "WhatsApp message is a formatted template preview. "
            "In-app notifications are saved to database and broadcast to verified volunteers."
        )
    }

def dispatch_in_app_notification(listing_id, title, message, target_role="volunteer"):
    """Creates a real in-app notification record in the database."""
    conn = get_db_connection()
    try:
        now_str = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO in_app_notifications (recipient_user_id, target_role, listing_id, title, message, notification_type, is_read, created_at)
            VALUES (NULL, ?, ?, ?, ?, 'broadcast', 0, ?);
        """, (target_role, listing_id, title, message, now_str))
        notif_id = cursor.lastrowid
        conn.commit()
        return notif_id
    finally:
        conn.close()
