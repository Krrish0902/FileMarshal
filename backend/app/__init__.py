from flask import Flask
from flask_cors import CORS
from app.routes import register_routes
from app.database import init_db

def create_app():
    app = Flask(__name__)
    
    # Load configurations
    app.config.from_pyfile("config.py")
    
    # Enable CORS for frontend communication
    CORS(app)

    # Initialize database
    init_db()

    # Register API routes
    register_routes(app)

    return app
