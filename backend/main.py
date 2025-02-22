from flask import Flask, jsonify
from flask_cors import CORS
import os
import platform
import string  # Add this import
import json

app = Flask(__name__)
CORS(app)

def get_system_drives():
    if platform.system() == "Windows":
        from ctypes import windll
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(f"{letter}:")
            bitmask >>= 1
        return drives
    return ["/"]  # For Unix-based systems

def scan_directory(path):
    try:
        items = []
        for entry in os.scandir(path):
            item = {
                "name": entry.name,
                "path": entry.path,
                "type": "directory" if entry.is_dir() else "file",
                "size": os.path.getsize(entry.path) if entry.is_file() else 0,
                "modified": os.path.getmtime(entry.path)
            }
            items.append(item)
        return items
    except Exception as e:
        return {"error": str(e)}

@app.route('/api/drives')
def get_drives():
    return jsonify(get_system_drives())

@app.route('/api/files/<path:directory>')
def get_files(directory):
    return jsonify(scan_directory(directory))

if __name__ == '__main__':
    app.run(port=5000, debug=True)
=======
from flask import Flask
from controllers.file_controller import FileController

app = Flask(__name__)

# Initialize the FileController
file_controller = FileController()

# Define routes
@app.route('/files', methods=['GET'])
def get_files():
    return file_controller.get_files()

@app.route('/files/categorize', methods=['POST'])
def categorize_files():
    return file_controller.categorize_files()

@app.route('/files/sort', methods=['POST'])
def sort_files():
    return file_controller.sort_files()

if __name__ == '__main__':
    app.run(debug=True)