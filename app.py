import os
from flask import Flask, render_template, send_from_directory, jsonify
from config import Config
from database import init_db

# Initialize Flask Application
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Register Blueprints
from routes.auth import auth_bp
from routes.staff import staff_bp
from routes.volunteer import volunteer_bp
from routes.admin import admin_bp
from routes.api import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(volunteer_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)

@app.route('/')
def index():
    """Serves the main SmartPlate AI application dashboard."""
    return render_template('index.html')

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Requested resource was not found."}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    # Initialize database on startup
    init_db()
    print("================================================================")
    print("🍽️  SmartPlate AI — AI-Powered Campus Food Waste Reduction")
    print("   Target: UN SDG 2 (Zero Hunger) • Turn Surplus into Shared Meals")
    print("   Application running at: http://127.0.0.1:5000/")
    print("================================================================")
    app.run(debug=True, port=5000)
