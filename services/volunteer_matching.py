from datetime import datetime
from database import get_db_connection

def match_volunteers_for_listing(listing_id):
    """
    Evaluates eligible verified volunteers for a given listing using deterministic rules,
    workload constraints, and location proximity, generating plain-language explanations.
    """
    conn = get_db_connection()
    try:
        # 1. Fetch listing details
        listing = conn.execute("""
            SELECT l.*, loc.name as loc_name, loc.zone, loc.building
            FROM food_listings l
            JOIN campus_locations loc ON l.location_id = loc.id
            WHERE l.id = ?;
        """, (listing_id,)).fetchone()

        if not listing:
            return {"success": False, "error": "Listing not found.", "recommendations": []}

        # 2. Fetch all verified volunteers
        volunteers = conn.execute("""
            SELECT u.*, loc.name as volunteer_loc_name, loc.zone as volunteer_zone, loc.building as volunteer_building
            FROM users u
            LEFT JOIN campus_locations loc ON u.campus_location_id = loc.id
            WHERE u.role = 'volunteer' AND u.is_verified = 1;
        """).fetchall()

        if not volunteers:
            return {
                "success": True,
                "has_sufficient_data": False,
                "summary": "No verified volunteers are currently registered in the system.",
                "recommendations": []
            }

        # 3. Calculate active workload per volunteer
        workloads = {}
        workload_rows = conn.execute("""
            SELECT claimed_by_volunteer_id, COUNT(*) as active_count
            FROM food_listings
            WHERE status IN ('claimed', 'pickup_in_progress')
            GROUP BY claimed_by_volunteer_id;
        """).fetchall()
        for r in workload_rows:
            workloads[r['claimed_by_volunteer_id']] = r['active_count']

        recommendations = []
        now = datetime.now()
        try:
            deadline = datetime.fromisoformat(listing['operational_deadline'])
            minutes_left = max(0, int((deadline - now).total_seconds() / 60))
        except Exception:
            minutes_left = 120

        for vol in volunteers:
            vol_id = vol['id']
            active_load = workloads.get(vol_id, 0)
            is_available = bool(vol['is_available'])

            # Deterministic Eligibility Check: Max 2 active pickups
            if active_load >= 2:
                continue # Ineligible due to capacity constraints

            score = 100
            reasons = []

            # Availability factor
            if not is_available:
                score -= 30
                reasons.append("Marked currently unavailable in profile")
            else:
                reasons.append("Currently active and available on campus")

            # Location proximity factor
            if vol['campus_location_id'] and vol['campus_location_id'] == listing['location_id']:
                score += 40
                reasons.append(f"Stationed directly at {listing['loc_name']}")
            elif vol['volunteer_zone'] and vol['volunteer_zone'] == listing['zone']:
                score += 25
                reasons.append(f"Located nearby in {listing['zone']}")
            else:
                score += 5
                reasons.append("Available elsewhere on campus")

            # Workload factor
            if active_load == 0:
                score += 20
                reasons.append("0 active pickups in progress (immediate availability)")
            elif active_load == 1:
                score += 5
                reasons.append("1 active pickup in progress (manageable capacity)")

            # Deadline time window compatibility
            if minutes_left < 45:
                if vol['campus_location_id'] == listing['location_id']:
                    score += 15
                    reasons.append("Close enough to meet urgent deadline (<45m)")
                else:
                    score -= 10
                    reasons.append("Tight deadline requires fast transit")
            else:
                reasons.append(f"Ample time ({minutes_left} mins remaining) to complete pickup")

            # Construct plain language explanation
            explanation = (
                f"Recommended for '{listing['food_name']}': {vol['full_name']} is "
                f"{'at the same facility' if vol['campus_location_id'] == listing['location_id'] else 'in the ' + (vol['volunteer_zone'] or 'campus area')}, "
                f"has {active_load} current pickup assignments, and has sufficient time before the {listing['loc_name']} operational deadline."
            )

            recommendations.append({
                "volunteer_id": vol['id'],
                "volunteer_name": vol['full_name'],
                "email": vol['email'],
                "phone": vol['phone'],
                "score": score,
                "active_load": active_load,
                "location_name": vol['volunteer_loc_name'] or "Campus Wide",
                "explanation": explanation,
                "positive_factors": reasons
            })

        # Rank by score descending
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        return {
            "success": True,
            "has_sufficient_data": len(recommendations) > 0,
            "listing_id": listing_id,
            "listing_food": listing['food_name'],
            "pickup_location": listing['loc_name'],
            "minutes_remaining": minutes_left,
            "recommendations": recommendations
        }
    finally:
        conn.close()
