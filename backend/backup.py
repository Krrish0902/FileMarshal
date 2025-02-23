import os
import shutil
import ctypes
import sys
import json
from datetime import datetime

class BackupManager:
    def __init__(self):
        self.backup_history = {}
        # Create backups directory if it doesn't exist
        self.backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        self.history_file = os.path.join(self.backup_dir, "backup_history.json")
        self.load_history()

    def get_backup_path(self, operation_id):
        """Generate a path for backup files"""
        return os.path.join(self.backup_dir, f"backup_{operation_id}.json")

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.backup_history = json.load(f)
                    
                # Verify individual backup files
                for operation_id in list(self.backup_history.keys()):
                    backup_file = self.get_backup_path(operation_id)
                    if not os.path.exists(backup_file):
                        # Remove from history if backup file is missing
                        del self.backup_history[operation_id]
                        
        except Exception as e:
            print(f"Error loading history: {e}")
            self.backup_history = {}

    def save_history(self):
        """Save backup history to the backups directory"""
        try:
            # Ensure backup directory exists
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Save main history file
            with open(self.history_file, 'w') as f:
                json.dump(self.backup_history, f, indent=4)
                
            # Save individual backup files
            for operation_id, operation in self.backup_history.items():
                backup_file = self.get_backup_path(operation_id)
                with open(backup_file, 'w') as f:
                    json.dump(operation, f, indent=4)
                    
        except Exception as e:
            print(f"Error saving history: {e}")

    def move_to_parent(self, source_dir):
        """Recursively flatten directory structure while preserving original filenames"""
        try:
            timestamp = datetime.now().isoformat()
            operation_record = {
                "timestamp": timestamp,
                "source_dir": source_dir,
                "moved_items": [],
                "removed_dirs": []
            }

            # Keep track of files already in target directory
            existing_files = set()
            for item in os.listdir(source_dir):
                if os.path.isfile(os.path.join(source_dir, item)):
                    existing_files.add(item)

            def process_directory(current_dir, target_dir):
                moved = []
                # Process all subdirectories first
                for item in os.listdir(current_dir):
                    item_path = os.path.join(current_dir, item)
                    if os.path.isdir(item_path):
                        # Recursively process subdirectory
                        moved.extend(process_directory(item_path, target_dir))
                        # Record directory for removal
                        operation_record["removed_dirs"].append(item_path)

                # Move all files in current directory
                for item in os.listdir(current_dir):
                    source_path = os.path.join(current_dir, item)
                    if os.path.isfile(source_path):
                        target_path = os.path.join(target_dir, item)
                        
                        # Only add number suffix if file already exists in target
                        if item in existing_files:
                            base, ext = os.path.splitext(item)
                            counter = 0
                            while os.path.exists(os.path.join(target_dir, f"{base}{' (' + str(counter) + ')' if counter > 0 else ''}{ext}")):
                                counter += 1
                            target_path = os.path.join(target_dir, f"{base}{' (' + str(counter) + ')' if counter > 0 else ''}{ext}")
                        else:
                            existing_files.add(item)

                        # Move file and record operation
                        shutil.move(source_path, target_path)
                        moved.append({
                            "name": item,
                            "original_path": source_path,
                            "new_path": target_path,
                            "original_dir": current_dir
                        })

                return moved

            # Start recursive processing
            moved_items = process_directory(source_dir, source_dir)
            operation_record["moved_items"] = moved_items

            # Remove empty directories (bottom-up)
            for dir_path in reversed(operation_record["removed_dirs"]):
                if os.path.exists(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)

            # Save operation history
            self.backup_history[timestamp] = operation_record
            self.save_history()

            return {
                "success": True,
                "operation_id": timestamp,
                "moved_items": moved_items,
                "total_files": len(moved_items),
                "directories_removed": len(operation_record["removed_dirs"])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def undo_last_move(self, operation_id):
        """Undo a flattening operation by restoring directory structure"""
        try:
            if operation_id not in self.backup_history:
                return {
                    "success": False,
                    "error": "Operation not found"
                }

            operation = self.backup_history[operation_id]
            restored_items = []
            
            # Recreate directory structure
            for dir_path in operation["removed_dirs"]:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)

            # Move files back to their original locations
            for item in operation["moved_items"]:
                current_path = item["new_path"]
                original_path = item["original_path"]
                original_dir = item["original_dir"]

                if os.path.exists(current_path):
                    # Ensure original directory exists
                    os.makedirs(original_dir, exist_ok=True)
                    # Move file back
                    shutil.move(current_path, original_path)
                    restored_items.append(item["name"])

            # Remove operation from history
            del self.backup_history[operation_id]
            self.save_history()

            return {
                "success": True,
                "restored_items": restored_items,
                "total_restored": len(restored_items)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class WatchdogBackupHandler:
    def __init__(self, backup_manager):
        self.backup_manager = backup_manager

    def process_directory(self, directory_path):
        """Process new directory detected by watchdog"""
        result = self.backup_manager.move_to_parent(directory_path)
        return result

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def move_files_up_and_clean(root_dir, current_path=None, parent_path=None, undo_log=[]):
    if current_path is None:
        current_path = root_dir
        parent_path = root_dir  
    
    subdirs = [d for d in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, d))]
    files = [f for f in os.listdir(current_path) if os.path.isfile(os.path.join(current_path, f))]
    
    if files and parent_path:
        for file in files:
            file_src = os.path.join(current_path, file)
            file_dest = os.path.join(parent_path, file)

            if os.path.exists(file_dest):
                base, ext = os.path.splitext(file)
                counter = 1
                new_file_dest = os.path.join(parent_path, f"{base}_{counter}{ext}")
                
                while os.path.exists(new_file_dest):
                    counter += 1
                    new_file_dest = os.path.join(parent_path, f"{base}_{counter}{ext}")
                
                file_dest = new_file_dest  

            shutil.move(file_src, file_dest)
            undo_log.append({"new_path": file_dest, "old_path": file_src})  
    
    for subdir in subdirs:
        move_files_up_and_clean(root_dir, os.path.join(current_path, subdir), current_path, undo_log)
    
    if not os.listdir(current_path) and current_path != root_dir:
        os.rmdir(current_path)
        undo_log.append({"deleted_dir": current_path})  
    
    if not any(os.path.isdir(os.path.join(root_dir, d)) for d in os.listdir(root_dir)):
        print("All files have been moved to the root directory. No subdirectories remain.")

def classify_files(root_dir, undo_log):
    categories = {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"],
        "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
        "Documents": [".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"],
        "Others": []
    }
    
    print("WARNING: This will classify files into separate folders.")
    confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Classification canceled.")
        return
    
    for category in categories:
        category_path = os.path.join(root_dir, category)
        os.makedirs(category_path, exist_ok=True)
    
    for file in os.listdir(root_dir):
        file_path = os.path.join(root_dir, file)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(file)
            moved = False
            for category, extensions in categories.items():
                if ext.lower() in extensions:
                    new_path = os.path.join(root_dir, category, file)
                    shutil.move(file_path, new_path)
                    undo_log.append({"new_path": new_path, "old_path": file_path})
                    moved = True
                    break
            if not moved:
                new_path = os.path.join(root_dir, "Others", file)
                shutil.move(file_path, new_path)
                undo_log.append({"new_path": new_path, "old_path": file_path})
    
    print("Classification completed.")

def undo_changes(undo_log):
    print("Undoing changes...")
    for entry in reversed(undo_log):
        if "deleted_dir" in entry:
            os.makedirs(entry["deleted_dir"], exist_ok=True)
        else:
            shutil.move(entry["new_path"], entry["old_path"])
    print("Undo completed.")

if __name__ == "__main__":
    if not is_admin():
        print("This script requires admin access. Please run as administrator.")
        sys.exit(1)
    
    root_directory = input("Enter the directory to be scanned: ")
    if os.path.exists(root_directory) and os.path.isdir(root_directory):
        print("WARNING: This will move all files from subdirectories into the main directory and delete empty folders.")
        confirm = input("Do you want to continue? (yes/no): ").strip().lower()
        
        if confirm == "yes":
            undo_log = []
            while any(os.path.isdir(os.path.join(root_directory, d)) for d in os.listdir(root_directory)):
                move_files_up_and_clean(root_directory, root_directory, root_directory, undo_log)
            print("Process completed successfully.")
            
            classify_files(root_directory, undo_log)
            
            with open(os.path.join(root_directory, "undo_log.json"), "w") as log_file:
                json.dump(undo_log, log_file, indent=4)
                
            undo_confirm = input("Do you want to undo the changes? (yes/no): ").strip().lower()
            if undo_confirm == "yes":
                undo_changes(undo_log)
        else:
            print("Operation canceled.")
    else:
        print("Invalid directory path. Please provide a valid directory.")
