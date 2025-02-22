from tika import parser, initVM
import os
import mimetypes

class FileClassifier:
    def __init__(self):
        # Initialize Tika VM
        initVM()
        
        self.category_mapping = {
            'image': [
                'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
                'image/tiff', 'image/x-icon', 'image/svg+xml'
            ],
            'video': [
                'video/mp4', 'video/mpeg', 'video/x-msvideo', 'video/quicktime',
                'video/x-matroska', 'video/webm', 'video/x-flv'
            ],
            'document': [
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain', 'application/rtf', 'text/csv',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            ],
            'audio': [
                'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp3',
                'audio/aac', 'audio/ogg', 'audio/flac'
            ],
            'archive': [
                'application/zip', 'application/x-rar-compressed',
                'application/x-7z-compressed', 'application/x-tar',
                'application/x-bzip2', 'application/gzip'
            ]
        }

    def get_mime_type(self, file_path):
        try:
            # First try python-magic
            import magic
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(file_path)
            
            # If mime type is too generic, try mimetypes
            if mime_type == 'application/octet-stream':
                mime_type, _ = mimetypes.guess_type(file_path)
            
            # If still no mime type, try Tika
            if not mime_type:
                parsed = parser.from_file(file_path)
                mime_type = parsed.get("metadata", {}).get("Content-Type", "")
                
                # Handle multiple mime types
                if isinstance(mime_type, list):
                    mime_type = mime_type[0]
            
            return mime_type
        except Exception as e:
            print(f"Error getting mime type for {file_path}: {e}")
            return None

    def classify_file(self, file_path):
        if not os.path.exists(file_path):
            return 'other'

        try:
            mime_type = self.get_mime_type(file_path)
            if not mime_type:
                return 'other'

            # Check category mapping
            for category, mime_types in self.category_mapping.items():
                if any(mime_type.lower().startswith(t.lower()) for t in mime_types):
                    return category

            # Check file extensions for common types
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                return 'image'
            elif ext in ['.mp4', '.avi', '.mkv', '.mov']:
                return 'video'
            elif ext in ['.mp3', '.wav', '.flac', '.m4a']:
                return 'audio'
            elif ext in ['.doc', '.docx', '.pdf', '.txt', '.xlsx']:
                return 'document'
            elif ext in ['.zip', '.rar', '.7z', '.tar']:
                return 'archive'

            return 'other'
        except Exception as e:
            print(f"Error classifying {file_path}: {e}")
            return 'other'

    def get_file_metadata(self, file_path):
        try:
            parsed = parser.from_file(file_path)
            return parsed.get("metadata", {})
        except Exception:
            return {}