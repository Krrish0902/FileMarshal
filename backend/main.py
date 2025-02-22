from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import platform
import string
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

@app.route('/api/search')
def search_files():
    query = request.args.get('query', '').lower().strip()
    path = request.args.get('path', '').strip()
    
    if not query or not path:
        return jsonify([])
    
    try:
        results = []
        # Limit search depth to prevent hanging
        max_depth = 5
        
        for root, dirs, files in os.walk(path):
            # Check search depth
            relative_path = os.path.relpath(root, path)
            if relative_path != '.' and relative_path.count(os.sep) >= max_depth:
                continue
            
            # Search in directory names
            for dir_name in dirs[:]:  # Copy the list to avoid modification during iteration
                if query in dir_name.lower():
                    full_path = os.path.join(root, dir_name)
                    try:
                        modified = os.path.getmtime(full_path)
                        query_pos = dir_name.lower().find(query)
                        
                        results.append({
                            "name": dir_name,
                            "highlightedName": [
                                {"text": dir_name[:query_pos], "highlight": False},
                                {"text": dir_name[query_pos:query_pos + len(query)], "highlight": True},
                                {"text": dir_name[query_pos + len(query):], "highlight": False}
                            ],
                            "path": full_path,
                            "type": "directory",
                            "size": 0,
                            "modified": modified
                        })
                    except (OSError, PermissionError):
                        continue
            
            # Search in file names
            for file_name in files:
                if query in file_name.lower():
                    full_path = os.path.join(root, file_name)
                    try:
                        size = os.path.getsize(full_path)
                        modified = os.path.getmtime(full_path)
                        query_pos = file_name.lower().find(query)
                        
                        results.append({
                            "name": file_name,
                            "highlightedName": [
                                {"text": file_name[:query_pos], "highlight": False},
                                {"text": file_name[query_pos:query_pos + len(query)], "highlight": True},
                                {"text": file_name[query_pos + len(query):], "highlight": False}
                            ],
                            "path": full_path,
                            "type": "file",
                            "size": size,
                            "modified": modified
                        })
                    except (OSError, PermissionError):
                        continue
            
            # Limit results to prevent overwhelming
            if len(results) >= 100:
                break
                
        return jsonify(results)
    except Exception as e:
        print(f"Search error: {e}")
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
