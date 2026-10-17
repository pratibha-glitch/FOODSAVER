from datetime import datetime
from database import get_db_connection
from config import Config

def get_system_metrics():
    """
    Computes honest metrics strictly derived from database records.
    Separates units (kg, portions, boxes) and calculates defensible CO2 diversion
    only on verified collected food in kilograms (FAO standard 2.5 kg CO2-eq per kg food).
    """
    conn = get_db_connection()
    try:
        # 1. Total confirmed quantity collected, grouped by unit
        # STRICT RULE: Never count unclaimed or in-progress listings as collected food!
        collected_by_unit_rows = conn.execute("""
            SELECT actual_collected_quantity_unit as unit, 
                   SUM(actual_collected_quantity_value) as total_value,
                   COUNT(*) as record_count
            FROM food_listings
            WHERE status = 'collected' AND actual_collected_quantity_value IS NOT NULL
            GROUP BY actual_collected_quantity_unit;
        """).fetchall()

        collected_breakdown = {}
        total_kg_collected = 0.0

        for r in collected_by_unit_rows:
            unit = r['unit'] or 'unspecified'
            val = round(float(r['total_value'] or 0.0), 2)
            collected_breakdown[unit] = {
                "total_quantity": val,
                "pickups_count": r['record_count']
            }
            if unit.lower() == 'kg':
                total_kg_collected += val

        # 2. Status counts
        status_rows = conn.execute("""
            SELECT status, COUNT(*) as count 
            FROM food_listings 
            GROUP BY status;
        """).fetchall()

        status_counts = {r['status']: r['count'] for r in status_rows}

        completed_pickups = status_counts.get('collected', 0)
        active_listings = status_counts.get('available', 0)
        claimed_listings = status_counts.get('claimed', 0) + status_counts.get('pickup_in_progress', 0)
        cancelled_count = status_counts.get('cancelled', 0)
        expired_count = status_counts.get('expired', 0)
        draft_count = status_counts.get('draft', 0)
        total_all_listings = sum(status_counts.values())

        # 3. Active verified volunteers
        verified_volunteers = conn.execute("""
            SELECT COUNT(*) FROM users WHERE role = 'volunteer' AND is_verified = 1;
        """).fetchone()[0]

        active_available_volunteers = conn.execute("""
            SELECT COUNT(*) FROM users WHERE role = 'volunteer' AND is_verified = 1 AND is_available = 1;
        """).fetchone()[0]

        # 4. Average time from listing creation to volunteer claim (in minutes)
        time_to_claim_rows = conn.execute("""
            SELECT created_at, claimed_at 
            FROM food_listings 
            WHERE claimed_at IS NOT NULL AND status IN ('claimed', 'pickup_in_progress', 'collected');
        """).fetchall()

        claim_durations_minutes = []
        for r in time_to_claim_rows:
            try:
                c_at = datetime.fromisoformat(r['created_at'])
                cl_at = datetime.fromisoformat(r['claimed_at'])
                diff = (cl_at - c_at).total_seconds() / 60
                if diff >= 0:
                    claim_durations_minutes.append(diff)
            except Exception:
                continue

        if claim_durations_minutes:
            avg_time_to_claim_minutes = round(sum(claim_durations_minutes) / len(claim_durations_minutes), 1)
        else:
            avg_time_to_claim_minutes = 0.0

        # 5. Defensible CO2 Emissions Prevented
        # Documented standard: 1 kg diverted food waste prevents ~2.5 kg CO2-eq (FAO / WRAP guidelines)
        # Applied exclusively to confirmed collected food in kg.
        co2_emissions_prevented_kg = round(total_kg_collected * Config.CO2_SAVED_PER_KG, 2)

        return {
            "completed_pickups": completed_pickups,
            "active_available_listings": active_listings,
            "active_claimed_in_progress": claimed_listings,
            "draft_listings": draft_count,
            "cancelled_listings": cancelled_count,
            "expired_listings": expired_count,
            "total_all_listings": total_all_listings,
            "verified_volunteers_count": verified_volunteers,
            "available_volunteers_count": active_available_volunteers,
            "collected_quantity_by_unit": collected_breakdown,
            "total_kg_collected": total_kg_collected,
            "avg_time_to_claim_minutes": avg_time_to_claim_minutes,
            "environmental_impact": {
                "co2_prevented_kg": co2_emissions_prevented_kg,
                "calculation_basis": (
                    f"Calculated as {total_kg_collected} kg verified collected food * {Config.CO2_SAVED_PER_KG} kg CO2-eq/kg "
                    "(FAO Food Wastage Footprint methodology). Non-kg portions are excluded from this specific metric."
                )
            }
        }
    finally:
        conn.close()
