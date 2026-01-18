import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Database path
HISTORY_DB_PATH = BASE_DIR / os.getenv('HISTORY_DB_PATH', 'history.db')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Flask
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'