import os
import shutil

class FileOperations:
    @staticmethod
    def validate_directory(directory):
        if not directory or not os.path.exists(directory):
            raise ValueError("Invalid directory")
        if not os.path.isdir(directory):
            raise ValueError("Path is not a directory")
        return os.path.normpath(directory)

    @staticmethod
    def move_file(source_path, target_path, handle_duplicates=True):
        if handle_duplicates:
            target_path = FileOperations.get_unique_path(target_path)
        shutil.move(source_path, target_path)
        return target_path

    @staticmethod
    def get_unique_path(path):
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    @staticmethod
    def scan_directory(path):
        try:
            items = []
            for entry in os.scandir(path):
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
                    
            return sorted(items, key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        except Exception as e:
            return {"error": str(e)}