from flask import Flask
from flask_cors import CORS
import tika
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routes import register_routes
from backend.file_classifier import FileClassifier
from backend.services.fileService import FileService
from backend.services.searchService import SearchService
from backend.backup import BackupManager, WatchdogBackupHandler

tika.initVM()

app = Flask(__name__)
CORS(app)

# Initialize components
file_classifier = FileClassifier()
file_service = FileService(file_classifier)
search_service = SearchService(file_classifier)
backup_manager = BackupManager()
backup_handler = WatchdogBackupHandler(backup_manager)

# Register routes
register_routes(app, file_classifier, backup_manager, file_service, search_service)

if __name__ == '__main__':
    app.run(port=5000, debug=True)