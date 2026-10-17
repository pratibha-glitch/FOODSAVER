from datetime import datetime

def calculate_urgency_priority(listing):
    """
    Ranks listing urgency based on remaining operational pickup deadline window.
    CRITICAL FOOD SAFETY REQUIREMENT:
    Urgency priority strictly reflects logistical collection deadlines remaining;
    it must NEVER be equated with or represented as a food safety determination.
    """
    now = datetime.now()
    try:
        deadline = datetime.fromisoformat(listing['operational_deadline'])
        seconds_left = (deadline - now).total_seconds()
        minutes_left = int(seconds_left / 60)
    except Exception:
        minutes_left = 180

    status = listing.get('status', 'available')

    if status == 'expired' or minutes_left <= 0:
        return {
            "level": "EXPIRED",
            "badge_color": "danger",
            "minutes_left": 0,
            "rank_weight": 0,
            "explanation": "Operational pickup deadline has elapsed. Item must be audited and discarded per food safety protocol.",
            "safety_disclaimer": "Expired operational deadline. Do not consume."
        }

    if minutes_left < 45:
        level = "CRITICAL"
        badge_color = "danger"
        rank_weight = 100
        explanation = f"Urgent logistical priority: Only {minutes_left} minutes remain before pickup window closes at {listing.get('location_name', 'canteen')}."
    elif minutes_left < 90:
        level = "HIGH"
        badge_color = "warning"
        rank_weight = 75
        explanation = f"High logistical priority: {minutes_left} minutes remain for pickup coordination."
    elif minutes_left < 180:
        level = "MODERATE"
        badge_color = "info"
        rank_weight = 50
        explanation = f"Standard priority: {minutes_left} minutes remaining in configured operational collection window."
    else:
        hours = round(minutes_left / 60, 1)
        level = "LOW"
        badge_color = "success"
        rank_weight = 25
        explanation = f"Flexible window: ~{hours} hours remaining before pickup deadline."

    return {
        "level": level,
        "badge_color": badge_color,
        "minutes_left": minutes_left,
        "rank_weight": rank_weight,
        "explanation": explanation,
        "safety_disclaimer": (
            "Logistical deadline based on canteen operational schedule. "
            "Physical inspection and food safety checklist confirmed by staff."
        )
    }

def rank_listings_by_urgency(listings):
    """Sorts listings by urgency priority (highest urgency first)."""
    annotated = []
    for l in listings:
        urgency = calculate_urgency_priority(l)
        item = dict(l)
        item['urgency'] = urgency
        annotated.append(item)

    # Sort: highest rank_weight first, then earliest deadline
    annotated.sort(key=lambda x: (x['urgency']['rank_weight'], -x['urgency']['minutes_left']), reverse=True)
    return annotated
