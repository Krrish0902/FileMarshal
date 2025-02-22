from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import platform
import string
import json
import time
import shutil
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor
import mimetypes
import hashlib
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from concurrent.futures import ThreadPoolExecutor
import time
from file_classifier import FileClassifier
import mimetypes
import subprocess

app = Flask(__name__)
CORS(app)

# Global variables from both files
previous_files = {}
file_cache = {}

FILE_CATEGORIES = {
    "text": {".txt", ".srt", ".md", ".json", ".xml" },
    "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp"},
    "audio": {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"},
    "video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"},
    "compressed": {".zip", ".rar", ".tar", ".gz", ".7z"},
    "document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".tex", ".csv", ".tsv" },
    "code": {".py", ".js", ".java", ".cpp", ".h", ".cs", ".php", ".rb", ".c", ".html", ".css", ".jsx", ".ts", ".tsx", ".go", ".swift", ".pl", ".sql", ".r", ".sh", ".bat", ".ps1", ".cmd", ".yaml", ".yml", ".ini", ".cfg", ".rst", ".ipynb", ".rmd", }
}

# Add global variable for file cache
file_cache = {}

# Initialize the classifier
file_classifier = FileClassifier()

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
            # Skip hidden files and directories (from maintest.py)
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
                
        # Sort items: directories first, then files (from maintest.py)
        return sorted(items, 
                     key=lambda x: (x['type'] != 'directory', x['name'].lower()))
    except Exception as e:
        return {"error": str(e)}

def move_files(source_dir, target_dir):
    global previous_files
    
    # Get current files in source directory
    current_files = {entry.name: entry.path for entry in os.scandir(source_dir)}
    
    # Determine new files
    source_key = source_dir
    new_files = []
    if source_key not in previous_files:
        previous_files[source_key] = set()
        new_files = list(current_files.keys())
    else:
        new_files = [name for name in current_files if name not in previous_files[source_key]]
    
    # Move new files
    moved_files = []
    for new_file in new_files:
        source_path = current_files[new_file]
        target_path = os.path.join(target_dir, new_file)
        try:
            shutil.move(source_path, target_path)
            moved_files.append(new_file)
        except Exception as e:
            print(f"Error moving {new_file}: {str(e)}")
    
    # Update previous files
    previous_files[source_key] = set(current_files.keys())
    
    return moved_files

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

def scan_and_classify_file(file_path):
    """Scans a file and returns both metadata and classification"""
    try:
        # Basic file information
        file_stat = os.stat(file_path)
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # Calculate file hash
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)

        # Classify file type
        file_category = "other"
        for category, extensions in FILE_CATEGORIES.items():
            if file_extension in extensions:
                file_category = category
                break

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Build metadata object
        metadata = {
            "basic_info": {
                "name": file_name,
                "extension": file_extension,
                "category": file_category,
                "size": file_stat.st_size,
                "size_readable": f"{file_stat.st_size / (1024*1024):.2f} MB"
            },
            "classification": {
                "category": file_category,
                "mime_type": mime_type or "unknown",
                "is_hidden": file_name.startswith('.'),
                "is_system_file": any(file_name.endswith(ext) for ext in ['.sys', '.dll', '.exe'])
            },
            "timestamps": {
                "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(file_stat.st_atime).isoformat()
            },
            "security": {
                "md5_hash": md5_hash.hexdigest(),
                "permissions": oct(file_stat.st_mode)[-3:]
            }
        }

        # Add preview for text files
        if file_category in ["text", "code"]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    preview = f.read(1000)  # Read first 1000 characters
                    metadata["preview"] = {
                        "content": preview,
                        "encoding": "utf-8",
                        "truncated": len(preview) == 1000
                    }
            except UnicodeDecodeError:
                metadata["preview"] = {
                    "error": "File content cannot be previewed (binary or unknown encoding)"
                }

        return metadata

    except Exception as e:
        return {"error": str(e)}

class FileHandler(FileSystemEventHandler):
    def __init__(self, watch_directory, organization_directory):
        self.watch_directory = watch_directory
        self.organization_directory = organization_directory
        self.previous_files = {}

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def process_file(self, file_path):
        try:
            # Analyze and classify file
            metadata = self.scan_and_classify_file(file_path)
            category = metadata['classification']['category']
            
            # Create category directory if it doesn't exist
            category_dir = os.path.join(self.organization_directory, category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)

            # Move file to appropriate category directory
            file_name = os.path.basename(file_path)
            target_path = os.path.join(category_dir, file_name)
            
            # Move the file
            shutil.move(file_path, target_path)
            
            # Update tracking
            if self.watch_directory not in self.previous_files:
                self.previous_files[self.watch_directory] = set()
            self.previous_files[self.watch_directory].add(file_name)
            
            print(f"Processed and moved: {file_name} to {category}")
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

    def scan_and_classify_file(self, file_path):
        """Enhanced scan and classify function"""
        try:
            # Basic file information
            file_stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            file_extension = os.path.splitext(file_name)[1].lower()
            
            # Calculate file hash
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)

            # Classify file type using FILE_CATEGORIES
            file_category = "other"
            for category, extensions in FILE_CATEGORIES.items():
                if file_extension in extensions:
                    file_category = category
                    break

            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Build metadata
            metadata = {
                "basic_info": {
                    "name": file_name,
                    "extension": file_extension,
                    "category": file_category,
                    "size": file_stat.st_size,
                    "size_readable": f"{file_stat.st_size / (1024*1024):.2f} MB"
                },
                "classification": {
                    "category": file_category,
                    "mime_type": mime_type or "unknown",
                    "is_hidden": file_name.startswith('.'),
                    "is_system_file": any(file_name.endswith(ext) for ext in ['.sys', '.dll', '.exe'])
                },
                "timestamps": {
                    "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "accessed": datetime.fromtimestamp(file_stat.st_atime).isoformat()
                }
            }
            
            return metadata
            
        except Exception as e:
            return {"error": str(e)}

# Routes
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

@app.route('/api/sort_new_files/<path:paths>')
def sort_new_files_with_separator(paths):
    try:
        paths_list = paths.split('>')
        
        if len(paths_list) != 2:
            return jsonify({
                "error": "Invalid path format. Use 'source>destination' format"
            }), 400
            
        source_dir = unquote(paths_list[0])
        target_dir = unquote(paths_list[1])
        
        # Validate drive letters are present
        if not (source_dir[1:3] == ':/') or not (target_dir[1:3] == ':/'):
            return jsonify({
                "error": "Drive letter missing. Both paths must start with drive letter (e.g. 'C:/')"
            }), 400
            
        # Normalize paths
        source_dir = os.path.normpath(source_dir)
        target_dir = os.path.normpath(target_dir)
        
        # Validate directories exist
        if not os.path.exists(source_dir):
            return jsonify({
                "error": f"Source directory not found: {source_dir}"
            }), 404
            
        if not os.path.exists(target_dir):
            return jsonify({
                "error": f"Target directory not found: {target_dir}"
            }), 404
        
        print(f"Source directory: {source_dir}")
        print(f"Target directory: {target_dir}")
        
        moved_files = move_files(source_dir, target_dir)
        return jsonify({
            "success": True,
            "files_moved": moved_files
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/initialize')
def initialize_app():
    try:
        drives = get_system_drives()
        return jsonify({"status": "success", "drives": drives})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/analyze_file/<path:file_path>')
def analyze_file(file_path):
    """API endpoint to analyze a specific file"""
    try:
        # Decode URL-encoded path
        decoded_path = unquote(file_path)
        
        # Validate file exists
        if not os.path.exists(decoded_path):
            return jsonify({
                "error": f"File not found: {decoded_path}"
            }), 404
            
        # Validate it's a file
        if not os.path.isfile(decoded_path):
            return jsonify({
                "error": f"Path is not a file: {decoded_path}"
            }), 400
            
        # Analyze the file
        result = scan_and_classify_file(decoded_path)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/watch_directory', methods=['POST'])
def watch_directory():
    try:
        data = request.json
        watch_dir = data.get('watch_directory')
        organization_dir = data.get('organization_directory')

        if not watch_dir or not organization_dir:
            return jsonify({"error": "Both watch_directory and organization_directory are required"}), 400

        # Validate directories
        if not os.path.exists(watch_dir):
            return jsonify({"error": f"Watch directory not found: {watch_dir}"}), 404
        if not os.path.exists(organization_dir):
            os.makedirs(organization_dir)

        # Initialize watchdog
        event_handler = FileHandler(watch_dir, organization_dir)
        observer = Observer()
        observer.schedule(event_handler, watch_dir, recursive=False)
        observer.start()

        # Process existing files
        for entry in os.scandir(watch_dir):
            if entry.is_file():
                event_handler.process_file(entry.path)

        return jsonify({
            "status": "success",
            "message": f"Now watching {watch_dir} and organizing to {organization_dir}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
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
                    if category == 'all':
                        file_category = 'all'
                    else:
                        file_category = file_classifier.classify_file(full_path)
                    
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
        data = request.json
        files = data.get('files', [])
        
        if not files:
            return jsonify({"error": "No files selected"})
        
        organized = []
        errors = []
        
        for file_path in files:
            try:
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
                errors.append(f"Error organizing {file_path}: {str(e)}")
        
        return jsonify({
            "organized": organized,
            "errors": errors,
            "message": f"Successfully organized {len(organized)} files"
        })
        
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
            if platform.system() == "Windows":
                os.startfile(file_path)
            else:
                opener = "open" if platform.system() == "Darwin" else "xdg-open"
                subprocess.call([opener, file_path])
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