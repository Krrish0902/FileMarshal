import os

class Config:
    """Configuration settings for the Flask application."""
    
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    TESTING = os.getenv('FLASK_TESTING', 'False') == 'True'
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')
    DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///app.db')
    AI_MODEL_PATH = os.getenv('AI_MODEL_PATH', 'path/to/your/model')