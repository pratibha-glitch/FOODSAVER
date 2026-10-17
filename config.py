import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartplate-campus-secret-key-2026-sdg2')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'smartplate.db'))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'static' / 'uploads'))
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB upload limit
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # AI Vision Service Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
    
    # Operational Rules Default Configuration (in hours)
    DEFAULT_DEADLINE_HOT_HOLDING_HOURS = float(os.environ.get('DEADLINE_HOT_HOLDING_HOURS', 3.0))
    DEFAULT_DEADLINE_AMBIENT_DRY_HOURS = float(os.environ.get('DEADLINE_AMBIENT_DRY_HOURS', 4.0))
    DEFAULT_DEADLINE_AMBIENT_WET_HOURS = float(os.environ.get('DEADLINE_AMBIENT_WET_HOURS', 2.5))
    DEFAULT_DEADLINE_DAIRY_HOURS = float(os.environ.get('DEADLINE_DAIRY_HOURS', 2.0))
    DEFAULT_DEADLINE_CHILLED_HOURS = float(os.environ.get('DEADLINE_CHILLED_HOURS', 8.0))
    
    # Defensible CO2 calculation factor: 1 kg diverted food waste avoids ~2.5 kg CO2-eq (FAO guidelines)
    CO2_SAVED_PER_KG = 2.5
