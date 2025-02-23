import os
import sys
from flask import jsonify, request
from urllib.parse import unquote
import platform
import subprocess

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.getDrives import get_system_drives
from utils.fileOperations import FileOperations

def register_routes(app, file_classifier, backup_manager, file_service, search_service):
    @app.route('/api/drives')
    def get_drives():
        return jsonify(get_system_drives())

    @app.route('/api/files/<path:directory>')
    def get_files(directory):
        return jsonify(FileOperations.scan_directory(directory))

    @app.route('/api/search')
    def search_files():
        query = request.args.get('query', '').lower().strip()
        path = request.args.get('path', '').strip()
        if not query or not path:
            return jsonify([])
        return jsonify(search_service.search_files(query, path))

    @app.route('/api/analyze_file/<path:file_path>')
    def analyze_file(file_path):
        decoded_path = unquote(file_path)
        if not os.path.exists(decoded_path):
            return jsonify({"error": f"File not found: {decoded_path}"}), 404
        if not os.path.isfile(decoded_path):
            return jsonify({"error": "Path is not a file"}), 400
        return jsonify(file_service.scan_and_classify_file(decoded_path))

    @app.route('/api/files/category/<category>')
    def get_files_by_category(category):
        path = request.args.get('path', '').strip()
        if not path:
            return jsonify({"error": "Path parameter is required"}), 400
        return jsonify(file_service.get_files_by_category(category, path))

    @app.route('/api/organize', methods=['POST'])
    def organize_files():
        data = request.json
        files = data.get('files', [])
        if not files:
            return jsonify({"error": "No files selected"}), 400
        return jsonify(file_service.organize_files(files))

    @app.route('/api/watch_directory', methods=['POST'])
    def watch_directory():
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        watch_dir = data.get('watch_directory')
        organization_dir = data.get('organization_directory')
        
        if not watch_dir or not organization_dir:
            return jsonify({
                "error": "Both watch_directory and organization_directory are required"
            }), 400
            
        return jsonify(file_service.setup_watch_directory(watch_dir, organization_dir))

    @app.route('/api/backup/flatten-directory', methods=['POST'])
    def flatten_directory():
        data = request.json
        directory = data.get('directory')
        if not directory:
            return jsonify({"error": "Directory is required"}), 400
        return jsonify(backup_manager.move_to_parent(directory))

    @app.route('/api/backup/undo/<operation_id>', methods=['POST'])
    def undo_backup(operation_id):
        return jsonify(backup_manager.undo_last_move(operation_id))

    @app.route('/api/open', methods=['POST'])
    def open_file():
        data = request.json
        if not data or 'path' not in data:
            return jsonify({"error": "File path is required"}), 400
            
        file_path = data['path']
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
            
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            else:
                subprocess.run(['xdg-open', file_path])
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": f"Failed to open file: {str(e)}"}), 500

    @app.route('/api/initialize')
    def initialize_app():
        try:
            drives = get_system_drives()
            return jsonify({
                "status": "success",
                "drives": drives
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500