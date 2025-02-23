from watchdog.events import FileSystemEventHandler
import os
from utils.fileOperations import FileOperations

class FileHandler(FileSystemEventHandler):
    def __init__(self, watch_directory, organization_directory, file_classifier, file_service, backup_handler):
        self.watch_directory = watch_directory
        self.organization_directory = organization_directory
        self.file_classifier = file_classifier
        self.file_service = file_service
        self.backup_handler = backup_handler

    def on_created(self, event):
        if event.is_directory:
            result = self.backup_handler.process_directory(event.src_path)
            if result['success']:
                for item in result.get('moved_items', []):
                    if os.path.isfile(item['new_path']):
                        self.process_file(item['new_path'])
        else:
            self.process_file(event.src_path)

    def process_file(self, file_path):
        try:
            metadata = self.file_service.scan_and_classify_file(file_path)
            category = metadata['basic_info']['category']
            category_dir = os.path.join(self.organization_directory, category)
            os.makedirs(category_dir, exist_ok=True)
            
            target_path = os.path.join(category_dir, os.path.basename(file_path))
            FileOperations.move_file(file_path, target_path)
            
            print(f"Processed and moved: {os.path.basename(file_path)} to {category}")
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")