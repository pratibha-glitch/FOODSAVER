from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
import models

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"success": False, "error": "Authentication required. Please sign in."}), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({"success": False, "error": "Authentication required."}), 401
            user_role = session.get('role')
            if user_role not in allowed_roles:
                return jsonify({"success": False, "error": f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    identifier = data.get('identifier', '').strip()
    password = data.get('password', '').strip()

    if not identifier or not password:
        return jsonify({"success": False, "error": "Please provide username/email and password."}), 400

    user = models.get_user_by_username_or_email(identifier)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"success": False, "error": "Invalid username/email or password."}), 401

    # Store user in session
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['full_name'] = user['full_name']
    session['is_verified'] = bool(user['is_verified'])

    # Return safe user profile
    safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['full_name']}!",
        "user": safe_user
    })

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Signed out successfully."})

@auth_bp.route('/api/auth/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": True, "authenticated": False, "user": None})

    user = models.get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"success": True, "authenticated": False, "user": None})

    safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
    return jsonify({
        "success": True,
        "authenticated": True,
        "user": safe_user
    })

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'volunteer').strip()
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()
    location_id = data.get('location_id')

    if not username or not email or not password or not full_name:
        return jsonify({"success": False, "error": "All required fields must be filled."}), 400

    if role not in ('staff', 'volunteer'):
        return jsonify({"success": False, "error": "Public registration is only permitted for staff or volunteer roles."}), 400

    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400

    existing = models.get_user_by_username_or_email(username)
    if existing:
        return jsonify({"success": False, "error": "Username is already in use."}), 400

    existing_email = models.get_user_by_username_or_email(email)
    if existing_email:
        return jsonify({"success": False, "error": "Email is already registered."}), 400

    # New volunteers start as is_verified=0 to guarantee verification requirements
    is_verified = 0

    password_hash = generate_password_hash(password)
    user_id = models.create_user(username, email, password_hash, role, full_name, phone, location_id, is_verified)

    return jsonify({
        "success": True,
        "message": "Registration successful! Your account has been submitted for administrator verification.",
        "user_id": user_id
    })
