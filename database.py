import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection(db_path=None):
    """Returns a SQLite connection configured with Row factory and foreign keys."""
    if db_path is None:
        try:
            from flask import current_app
            if current_app and current_app.config.get('DATABASE_PATH'):
                db_path = current_app.config['DATABASE_PATH']
        except Exception:
            pass
    path = db_path or Config.DATABASE_PATH
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(db_path=None):
    """Initializes the database schema and seeds initial data if needed."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'staff', 'volunteer')),
        full_name TEXT NOT NULL,
        phone TEXT,
        campus_location_id INTEGER,
        is_verified INTEGER NOT NULL DEFAULT 0,
        is_available INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );
    """)

    # 2. Campus Locations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campus_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        code TEXT UNIQUE NOT NULL,
        building TEXT NOT NULL,
        floor TEXT,
        zone TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );
    """)

    # 3. Food Listings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_by_staff_id INTEGER NOT NULL REFERENCES users(id),
        location_id INTEGER NOT NULL REFERENCES campus_locations(id),
        food_name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN (
            'cooked_rice', 'curry_gravy', 'bread_roti', 'fruit_veg', 
            'packaged_meal', 'dairy_sweets', 'snacks', 'other'
        )),
        quantity_value REAL NOT NULL,
        quantity_unit TEXT NOT NULL CHECK(quantity_unit IN ('kg', 'portions', 'meal_boxes', 'plates', 'pieces')),
        quantity_source TEXT NOT NULL CHECK(quantity_source IN ('measured', 'manually_estimated', 'ai_estimated')),
        photo_filename TEXT,
        cooking_time TEXT,
        storage_condition TEXT NOT NULL CHECK(storage_condition IN ('hot_holding', 'ambient_covered', 'chilled_refrigerated')),
        known_allergens TEXT,
        staff_notes TEXT,
        operational_deadline TEXT NOT NULL,
        safety_checklist_confirmed INTEGER NOT NULL DEFAULT 0,
        safety_notes TEXT,
        status TEXT NOT NULL CHECK(status IN ('draft', 'available', 'claimed', 'pickup_in_progress', 'collected', 'cancelled', 'expired')),
        claimed_by_volunteer_id INTEGER REFERENCES users(id),
        claimed_at TEXT,
        pickup_started_at TEXT,
        collected_at TEXT,
        cancelled_at TEXT,
        cancellation_reason TEXT,
        actual_collected_quantity_value REAL,
        actual_collected_quantity_unit TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 4. AI Analysis Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_analysis_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER REFERENCES food_listings(id) ON DELETE SET NULL,
        photo_filename TEXT,
        raw_ai_response TEXT,
        parsed_food_name TEXT,
        parsed_category TEXT,
        parsed_quantity_estimate TEXT,
        confidence_score REAL,
        confidence_reasoning TEXT,
        fields_requiring_staff_input TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 5. Status Audit Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS status_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL REFERENCES food_listings(id) ON DELETE CASCADE,
        old_status TEXT NOT NULL,
        new_status TEXT NOT NULL,
        changed_by_user_id INTEGER NOT NULL REFERENCES users(id),
        change_note TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 6. In-App Notifications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS in_app_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        target_role TEXT CHECK(target_role IN ('volunteer', 'staff', 'admin', 'all')),
        listing_id INTEGER REFERENCES food_listings(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        notification_type TEXT NOT NULL DEFAULT 'broadcast',
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    """)

    # 7. System Config
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT,
        updated_at TEXT NOT NULL
    );
    """)

    # Indexes for fast lookups and high concurrency
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_status ON food_listings(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_location ON food_listings(location_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_staff ON food_listings(created_by_staff_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_volunteer ON food_listings(claimed_by_volunteer_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_listing ON status_audit_log(listing_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON in_app_notifications(recipient_user_id, is_read);")

    conn.commit()

    # Seed initial system configuration and sample data if database is fresh
    seed_database(conn)
    conn.close()

def seed_database(conn):
    """Seeds locations, system configurations, and demo accounts if empty."""
    cursor = conn.cursor()

    # 1. System Config seeding
    cursor.execute("SELECT COUNT(*) FROM system_config;")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        configs = [
            ('deadline_hot_holding_hours', str(Config.DEFAULT_DEADLINE_HOT_HOLDING_HOURS), 'Max operational window for hot-held food items (>60C)', now),
            ('deadline_ambient_dry_hours', str(Config.DEFAULT_DEADLINE_AMBIENT_DRY_HOURS), 'Max operational window for dry cooked foods (rotis, bread, dry sabzi)', now),
            ('deadline_ambient_wet_hours', str(Config.DEFAULT_DEADLINE_AMBIENT_WET_HOURS), 'Max operational window for ambient wet curries and cooked rice', now),
            ('deadline_dairy_hours', str(Config.DEFAULT_DEADLINE_DAIRY_HOURS), 'Max operational window for dairy and dessert items', now),
            ('deadline_chilled_hours', str(Config.DEFAULT_DEADLINE_CHILLED_HOURS), 'Max operational window for safely chilled/refrigerated items', now),
            ('require_human_checklist', 'true', 'Require staff to confirm physical sensory and storage checklist before publishing', now),
            ('volunteer_max_concurrent_claims', '2', 'Max active food claims a volunteer can hold concurrently', now),
        ]
        cursor.executemany("INSERT INTO system_config (key, value, description, updated_at) VALUES (?, ?, ?, ?);", configs)

    # 2. Campus Locations seeding
    cursor.execute("SELECT COUNT(*) FROM campus_locations;")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        locations = [
            ("Campus Dining Hall", "LOC-MAIN", "Student Centre Building", "Ground Floor - Service Hall 1", "Central Zone", "Canteen Manager", "9876543210", 1, now),
            ("Main Student Mess", "LOC-MESS", "Main Campus Hub", "1st Floor - Buffet Area", "North Zone", "Mess Supervisor", "9876543211", 1, now),
            ("Hostel Canteen A", "LOC-HST-A", "Hostel Block A", "Ground Floor Mess", "South Zone", "Shift Supervisor", "9876543212", 1, now),
            ("Hostel Canteen B", "LOC-HST-B", "Hostel Block B", "Ground Floor Dining", "West Zone", "Canteen Incharge", "9876543213", 1, now),
            ("Faculty Dining Hall", "LOC-FAC", "Administration Block", "2nd Floor Dining", "East Zone", "Supervisor", "9876543214", 1, now)
        ]
        cursor.executemany("""
            INSERT INTO campus_locations (name, code, building, floor, zone, contact_person, phone, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, locations)

    # 3. Users seeding
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        users = [
            # Admin User
            ("admin", "admin@smartplate.campus", generate_password_hash("AdminPassword123!"), "admin", "Admin", "9800000001", 1, 1, 1, now),
            # Canteen Staff Users
            ("staff_north", "staff@smartplate.campus", generate_password_hash("StaffPassword123!"), "staff", "Canteen Staff", "9800000002", 1, 1, 1, now),
            ("staff_central", "staff2@smartplate.campus", generate_password_hash("StaffPassword123!"), "staff", "Canteen Staff", "9800000003", 2, 1, 1, now),
            # Verified Volunteers
            ("volunteer_priya", "volunteer@smartplate.campus", generate_password_hash("VolunteerPassword123!"), "volunteer", "Verified Volunteer", "9800000004", 1, 1, 1, now),
            ("volunteer_rohit", "volunteer2@smartplate.campus", generate_password_hash("VolunteerPassword123!"), "volunteer", "Verified Volunteer", "9800000005", 2, 1, 1, now),
            # Unverified Volunteer (to demonstrate pending verification check)
            ("volunteer_pending", "volunteer.pending@smartplate.campus", generate_password_hash("VolunteerPassword123!"), "volunteer", "Unverified Volunteer", "9800000006", 3, 0, 1, now),
        ]
        cursor.executemany("""
            INSERT INTO users (username, email, password_hash, role, full_name, phone, campus_location_id, is_verified, is_available, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, users)

    # 4. Sample realistic listings with verified data
    cursor.execute("SELECT COUNT(*) FROM food_listings;")
    if cursor.fetchone()[0] == 0:
        now = datetime.now()
        now_str = now.isoformat()
        
        # Available listing
        deadline_1 = (now + timedelta(hours=2, minutes=30)).isoformat()
        cursor.execute("""
            INSERT INTO food_listings (
                created_by_staff_id, location_id, food_name, category, 
                quantity_value, quantity_unit, quantity_source, photo_filename,
                cooking_time, storage_condition, known_allergens, staff_notes,
                operational_deadline, safety_checklist_confirmed, safety_notes,
                status, created_at, updated_at
            ) VALUES (
                2, 1, 'Jeera Rice & Dal Makhani', 'cooked_rice',
                7.5, 'kg', 'measured', 'preset_dal_rice.jpg',
                ?, 'hot_holding', 'Dairy (Butter/Cream in Dal)', 'Freshly prepared for lunch service, kept in insulated hot containers.',
                ?, 1, 'Inspected aroma, appearance, temperature >65C.',
                'available', ?, ?
            );
        """, ((now - timedelta(minutes=45)).strftime('%Y-%m-%d %H:%M'), deadline_1, now_str, now_str))
        listing_1_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, 'draft', 'available', 2, 'Initial listing created and published with human checklist confirmed.', ?);
        """, (listing_1_id, now_str))

        # Claimed listing
        deadline_2 = (now + timedelta(hours=1, minutes=15)).isoformat()
        claimed_time = (now - timedelta(minutes=20)).isoformat()
        cursor.execute("""
            INSERT INTO food_listings (
                created_by_staff_id, location_id, food_name, category, 
                quantity_value, quantity_unit, quantity_source, photo_filename,
                cooking_time, storage_condition, known_allergens, staff_notes,
                operational_deadline, safety_checklist_confirmed, safety_notes,
                status, claimed_by_volunteer_id, claimed_at, created_at, updated_at
            ) VALUES (
                3, 2, 'Tandoori Roti & Mixed Veg Sabzi', 'bread_roti',
                35, 'portions', 'manually_estimated', 'preset_roti_sabzi.jpg',
                ?, 'ambient_covered', 'Gluten (Wheat flour)', 'Kept covered in clean insulated chafing dishes.',
                ?, 1, 'Confirmed fresh batch from evening buffet.',
                'claimed', 5, ?, ?, ?
            );
        """, ((now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'), deadline_2, claimed_time, now_str, now_str))
        listing_2_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, 'draft', 'available', 3, 'Published by staff.', ?);
        """, (listing_2_id, (now - timedelta(minutes=30)).isoformat()))
        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, 'available', 'claimed', 5, 'Claimed by verified volunteer.', ?);
        """, (listing_2_id, claimed_time))

        # Collected listing (Demonstrates completed impact metrics)
        collected_time = (now - timedelta(hours=3)).isoformat()
        created_earlier = (now - timedelta(hours=6)).isoformat()
        deadline_3 = (now - timedelta(hours=2)).isoformat()
        cursor.execute("""
            INSERT INTO food_listings (
                created_by_staff_id, location_id, food_name, category, 
                quantity_value, quantity_unit, quantity_source, photo_filename,
                cooking_time, storage_condition, known_allergens, staff_notes,
                operational_deadline, safety_checklist_confirmed, safety_notes,
                status, claimed_by_volunteer_id, claimed_at, pickup_started_at, collected_at,
                actual_collected_quantity_value, actual_collected_quantity_unit, created_at, updated_at
            ) VALUES (
                2, 1, 'Vegetable Pulao & Raita', 'cooked_rice',
                12.0, 'kg', 'measured', 'preset_dal_rice.jpg',
                ?, 'ambient_covered', 'Dairy in curd raita', 'Surplus from hostel event.',
                ?, 1, 'Inspected and certified clean.',
                'collected', 5, ?, ?, ?,
                12.0, 'kg', ?, ?
            );
        """, (
            (now - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M'),
            deadline_3,
            (now - timedelta(hours=4, minutes=45)).isoformat(),
            (now - timedelta(hours=4)).isoformat(),
            collected_time,
            created_earlier,
            collected_time
        ))
        listing_3_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO status_audit_log (listing_id, old_status, new_status, changed_by_user_id, change_note, created_at)
            VALUES (?, 'pickup_in_progress', 'collected', 5, 'Food collected and handed over to campus community night shelter.', ?);
        """, (listing_3_id, collected_time))

        # Initial in-app notification
        cursor.execute("""
            INSERT INTO in_app_notifications (recipient_user_id, target_role, listing_id, title, message, notification_type, created_at)
            VALUES (NULL, 'volunteer', 1, 'New Surplus Food Available', '7.5 kg Jeera Rice & Dal Makhani is available at Campus Dining Hall. Pickup deadline in 2.5 hours.', 'broadcast', ?);
        """, (now_str,))

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized and verified successfully.")
