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
        drive = path[0] + ":" if platform.system() == "Windows" else "/"
        
        # Search in cache if available
        if drive in file_cache:
            cached_files = file_cache[drive]
            for item in cached_files:
                if (item['path'].startswith(path) and 
                    query in item['name'].lower()):
                    name = item['name']
                    query_pos = name.lower().find(query)
                    
                    item['highlightedName'] = [
                        {"text": name[:query_pos], "highlight": False},
                        {"text": name[query_pos:query_pos + len(query)], "highlight": True},
                        {"text": name[query_pos + len(query):], "highlight": False}
                    ]
                    results.append(item)
                    
                    if len(results) >= 100:
                        break
        
        return jsonify(results)
    except Exception as e:
        print(f"Search error: {e}")
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
