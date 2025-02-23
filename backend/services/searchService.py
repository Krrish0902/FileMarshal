import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.highlightText import highlight_text

class SearchService:
    def __init__(self, file_classifier):
        self.file_classifier = file_classifier

    def search_files(self, query, path):
        results = []
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
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

            results.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
            return results[:100]  # Limit results
            
        except Exception as e:
            return {"error": str(e)}