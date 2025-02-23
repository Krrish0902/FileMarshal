import os
import sys
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.fileOperations import FileOperations
from file_classifier import FileClassifier

class FileWatchHandler(FileSystemEventHandler):
    def __init__(self, file_service, organization_dir):
        self.file_service = file_service
        self.organization_dir = organization_dir

    def on_created(self, event):
        if not event.is_directory:
            self.file_service.organize_files([event.src_path])

    def on_modified(self, event):
        if not event.is_directory:
            self.file_service.organize_files([event.src_path])

class FileService:
    def __init__(self, file_classifier):
        self.file_classifier = file_classifier
        self.observer = None
        self.watch_handler = None

    def scan_and_classify_file(self, file_path):
        """Scans a file and returns both metadata and classification"""
        try:
            file_stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            
            classification = self.file_classifier.classify_file(file_path)
            category, subcategory = classification.split('/') if '/' in classification else (classification, None)
            
            return {
                "basic_info": {
                    "name": file_name,
                    "category": category,
                    "subcategory": subcategory,
                    "size": file_stat.st_size,
                    "size_readable": f"{file_stat.st_size / (1024*1024):.2f} MB"
                },
                "timestamps": {
                    "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "accessed": datetime.fromtimestamp(file_stat.st_atime).isoformat()
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def setup_watch_directory(self, watch_dir, organization_dir):
        """Set up directory watching and automatic organization"""
        try:
            # Validate directories
            if not os.path.exists(watch_dir):
                os.makedirs(watch_dir)
            if not os.path.exists(organization_dir):
                os.makedirs(organization_dir)

            # Stop existing observer if any
            if self.observer:
                self.observer.stop()
                self.observer.join()

            # Create and start new observer
            self.watch_handler = FileWatchHandler(self, organization_dir)
            self.observer = Observer()
            self.observer.schedule(self.watch_handler, watch_dir, recursive=True)
            self.observer.start()

            # Process existing files in the directory
            existing_files = []
            for root, _, files in os.walk(watch_dir):
                for file in files:
                    existing_files.append(os.path.join(root, file))
            
            if existing_files:
                self.organize_files(existing_files)

            return {
                "success": True,
                "message": "Directory watch setup successful",
                "watch_directory": watch_dir,
                "organization_directory": organization_dir,
                "files_processed": len(existing_files)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def organize_files(self, files):
        """Organize files into categories"""
        try:
            results = {
                "success": True,
                "organized": [],
                "errors": []
            }

            for file_path in files:
                try:
                    if not os.path.exists(file_path):
                        results["errors"].append(f"File not found: {file_path}")
                        continue

                    classification = self.file_classifier.classify_file(file_path)
                    target_dir = os.path.join(self.watch_handler.organization_dir, classification)
                    os.makedirs(target_dir, exist_ok=True)

                    filename = os.path.basename(file_path)
                    target_path = os.path.join(target_dir, filename)

                    # Handle duplicate filenames
                    if os.path.exists(target_path):
                        base, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(target_path):
                            new_name = f"{base}_{counter}{ext}"
                            target_path = os.path.join(target_dir, new_name)
                            counter += 1

                    os.rename(file_path, target_path)
                    results["organized"].append({
                        "file": filename,
                        "category": classification,
                        "new_path": target_path
                    })

                except Exception as e:
                    results["errors"].append(f"Error processing {file_path}: {str(e)}")

            return results

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def __del__(self):
        """Cleanup observer on service destruction"""
        if self.observer:
            self.observer.stop()
            self.observer.join()