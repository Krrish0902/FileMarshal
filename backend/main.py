from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import platform
import string
import json
from concurrent.futures import ThreadPoolExecutor
import time
from file_classifier import FileClassifier
import mimetypes
from ctypes import windll  # Add at the top with other imports
import urllib.parse  # Add at the top

app = Flask(__name__)
CORS(app)

# Add global variable for file cache
file_cache = {}

# Initialize the classifier
file_classifier = FileClassifier()

def get_system_drives():
    if platform.system() == "Windows":
        try:
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            if bitmask == 0:  # Add check for invalid bitmask
                raise OSError("Failed to get logical drives")
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive = f"{letter}:"
                    try:
                        # Check if drive is ready and accessible
                        if os.path.exists(drive + "\\"):
                            drives.append(drive)
                    except Exception as e:
                        print(f"Error checking drive {drive}: {e}")
                bitmask >>= 1
            print(f"Found drives: {drives}")  # Debug log
            if not drives:
                # Fallback to default system drive
                system_drive = os.getenv('SystemDrive', 'C:')
                if os.path.exists(system_drive):
                    drives.append(system_drive)
            return drives
        except Exception as e:
            print(f"Error getting drives: {e}")
            return ["C:"]  # Fallback to C: drive
    else:
        return ["/"]  # For Unix-like systems

def scan_directory(path):
    try:
        items = []
        # Handle root directory for Windows drives
        if path.endswith(':'):
            path = path + '\\'
            
        with os.scandir(path) as entries:
            for entry in entries:
                # Skip hidden files and directories
                if entry.name.startswith('.'):
                    continue
                    
                try:
                    stats = entry.stat()
                    item = {
                        "name": entry.name,
                        "path": entry.path,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stats.st_size if entry.is_file() else 0,
                        "modified": stats.st_mtime
                    }
                    items.append(item)
                except (PermissionError, OSError) as e:
                    print(f"Error accessing {entry.path}: {e}")
                    continue
                
        # Sort items: directories first, then files alphabetically
        return sorted(items, 
                     key=lambda x: (x['type'] != 'directory', x['name'].lower()))
    except Exception as e:
        print(f"Error scanning directory {path}: {e}")
        return {"error": str(e)}

@app.route('/api/drives')
def get_drives():
    try:
        drives = get_system_drives()
        print(f"Found drives: {drives}")  # Debug log
        return jsonify(drives)
    except Exception as e:
        print(f"Error getting drives: {e}")
        return jsonify({"error": str(e)})

@app.route('/api/files/<path:directory>')
def get_files(directory):
    try:
        # Handle Windows drive paths
        if platform.system() == "Windows":
            # Handle URL encoding and normalization
            directory = urllib.parse.unquote(directory)
            directory = directory.replace('|', ':')
            directory = os.path.normpath(directory)
            
            # Add backslash for root directory
            if directory.endswith(':'):
                directory += '\\'
        
        print(f"Scanning directory: {directory}")  # Debug log
        
        # Validate path exists
        if not os.path.exists(directory):
            return jsonify({"error": f"Path does not exist: {directory}"})
            
        items = []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        # Skip hidden files and directories
                        if entry.name.startswith('.'):
                            continue
                            
                        stats = entry.stat()
                        item = {
                            "name": entry.name,
                            "path": entry.path.replace('\\', '/'),  # Normalize path for frontend
                            "type": "directory" if entry.is_dir() else "file",
                            "size": stats.st_size if entry.is_file() else 0,
                            "modified": stats.st_mtime
                        }
                        items.append(item)
                    except (PermissionError, OSError) as e:
                        print(f"Error accessing {entry.path}: {e}")
                        continue
                        
            # Sort items: directories first, then files alphabetically
            items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
            print(f"Found {len(items)} items in {directory}")  # Debug log
            return jsonify(items)
            
        except PermissionError as e:
            return jsonify({"error": f"Permission denied: {str(e)}"})
            
    except Exception as e:
        print(f"Error scanning directory {directory}: {e}")  # Debug log
        return jsonify({"error": str(e)})

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

@app.route('/api/files/category/<category>')
def get_files_by_category(category):
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify([])

        print(f"Searching category '{category}' in '{path}'")  # Debug log

        results = []
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                full_path = os.path.join(root, file)
                try:
                    # Get file category
                    file_category = file_classifier.classify_file(full_path) if category != 'all' else 'all'
                    if file_category is None:  # Add check for failed classification
                        continue
                    
                    # Debug log
                    print(f"File: {file}, Category: {file_category}")
                    
                    # Include file if it matches the category or if 'all' is selected
                    if category == 'all' or file_category == category:
                        size = os.path.getsize(full_path) if os.path.isfile(full_path) else 0
                        results.append({
                            "name": file,
                            "path": full_path,
                            "type": "file",
                            "category": file_category,
                            "size": size,
                            "modified": os.path.getmtime(full_path)
                        })
                        
                except (PermissionError, OSError) as e:
                    print(f"Error accessing {full_path}: {e}")
                    continue

            # Limit results to prevent overwhelming
            if len(results) >= 1000:
                break

        print(f"Found {len(results)} files in category {category}")  # Debug log
        return jsonify(results)
    except Exception as e:
        print(f"Category error: {e}")  # Debug log
        return jsonify({"error": str(e)})

@app.route('/api/organize', methods=['POST'])
def organize_files():
    try:
        if request.content_length > 1024 * 1024:  # 1MB limit
            return jsonify({"error": "Request too large"})
        data = request.json
        files = data.get('files', [])
        
        if not files:
            return jsonify({"error": "No files selected"})
        
        organized = []
        errors = []
        
        for file_path in files:
            try:
                if not os.path.exists(file_path):
                    errors.append(f"File not found: {file_path}")
                    continue
                if os.path.exists(file_path):
                    # Get file category
                    category = file_classifier.classify_file(file_path)
                    
                    # Create category directory in same location as file
                    parent_dir = os.path.dirname(file_path)
                    category_dir = os.path.join(parent_dir, category)
                    
                    # Create directory if it doesn't exist
                    if not os.path.exists(category_dir):
                        os.makedirs(category_dir)
                    
                    # Move file to category directory
                    filename = os.path.basename(file_path)
                    new_path = os.path.join(category_dir, filename)
                    
                    # Handle duplicate filenames
                    counter = 1
                    while os.path.exists(new_path):
                        name, ext = os.path.splitext(filename)
                        new_path = os.path.join(category_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    os.rename(file_path, new_path)
                    organized.append(file_path)
            except Exception as e:
                # Try to restore file if move failed
                if 'new_path' in locals() and os.path.exists(new_path):
                    try:
                        os.rename(new_path, file_path)
                    except:
                        pass
                errors.append(f"Error organizing {file_path}: {str(e)}")
        
        return jsonify({
            "organized": organized,
            "errors": errors,
            "message": f"Successfully organized {len(organized)} files"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/folders/tree')
def get_folder_tree():
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify([])
            
        def scan_folder(current_path, depth=0):
            if depth > 3:  # Limit depth to prevent too deep scanning
                return None
                
            try:
                items = []
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        if entry.is_dir() and not entry.name.startswith('.'):
                            children = scan_folder(entry.path, depth + 1)
                            items.append({
                                "name": entry.name,
                                "path": entry.path,
                                "children": children
                            })
                return sorted(items, key=lambda x: x['name'].lower())
            except (PermissionError, OSError):
                return None
                
        tree = scan_folder(path)
        return jsonify(tree or [])
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/open', methods=['POST'])
def open_file():
    try:
        data = request.json
        file_path = data.get('path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({"error": "Invalid file path"})

        try:
            # For Windows
            if platform.system() == "Windows":
                os.startfile(file_path)
            # For macOS
            elif platform.system() == "Darwin":
                subprocess.call(('open', file_path))
            # For Linux
            else:
                subprocess.call(('xdg-open', file_path))
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": f"Failed to open file: {str(e)}"})
            
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
