from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import platform
import string
import json
from concurrent.futures import ThreadPoolExecutor
import time

app = Flask(__name__)
CORS(app)

# Add global variable for file cache
file_cache = {}

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
            # Skip hidden files and directories
            if entry.name.startswith('.'):
                continue
                
            try:
                item = {
                    "name": entry.name,
                    "path": entry.path,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": os.path.getsize(entry.path) if entry.is_file() else 0,
                    "modified": os.path.getmtime(entry.path)
                }
                items.append(item)
            except (PermissionError, OSError):
                continue
                
        # Sort items: directories first, then files
        return sorted(items, 
                     key=lambda x: (x['type'] != 'directory', x['name'].lower()))
    except Exception as e:
        return {"error": str(e)}

@app.route('/api/drives')
def get_drives():
    return jsonify(get_system_drives())

@app.route('/api/files/<path:directory>')
def get_files(directory):
    return jsonify(scan_directory(directory))

@app.route('/api/search')
def search_files():
    query = request.args.get('query', '').lower().strip()
    path = request.args.get('path', '').strip()
    
    if not query or not path:
        return jsonify([])
    
    try:
        results = []
        # Search in current directory and subdirectories
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # Search in directories first
            for dirname in dirs:
                if query in dirname.lower():
                    full_path = os.path.join(root, dirname)
                    try:
                        results.append({
                            "name": dirname,
                            "path": full_path,
                            "type": "directory",
                            "size": 0,
                            "modified": os.path.getmtime(full_path),
                            "highlightedName": highlight_text(dirname, query)
                        })
                    except (PermissionError, OSError):
                        continue

            # Then search in files
            for filename in files:
                if query in filename.lower():
                    full_path = os.path.join(root, filename)
                    try:
                        results.append({
                            "name": filename,
                            "path": full_path,
                            "type": "file",
                            "size": os.path.getsize(full_path),
                            "modified": os.path.getmtime(full_path),
                            "highlightedName": highlight_text(filename, query)
                        })
                    except (PermissionError, OSError):
                        continue

            # Limit results to first 100 matches
            if len(results) >= 100:
                break

        # Sort results: directories first, then alphabetically
        results.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Search error: {e}")  # Debug log
        return jsonify({"error": str(e)})

@app.route('/api/initialize')
def initialize_app():
    try:
        drives = get_system_drives()
        return jsonify({"status": "success", "drives": drives})
    except Exception as e:
        return jsonify({"error": str(e)})

def highlight_text(text, query):
    """Split text into parts to be highlighted"""
    lower_text = text.lower()
    lower_query = query.lower()
    parts = []
    last_idx = 0
    
    idx = lower_text.find(lower_query)
    while idx != -1:
        # Add non-matching part
        if idx > last_idx:
            parts.append({"text": text[last_idx:idx], "highlight": False})
        # Add matching part
        parts.append({"text": text[idx:idx + len(query)], "highlight": True})
        last_idx = idx + len(query)
        idx = lower_text.find(lower_query, last_idx)
    
    # Add remaining text
    if last_idx < len(text):
        parts.append({"text": text[last_idx:], "highlight": False})
    
    return parts

if __name__ == '__main__':
    app.run(port=5000, debug=True)
