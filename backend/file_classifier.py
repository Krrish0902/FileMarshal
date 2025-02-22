from tika import parser, detector
import mimetypes
import os
import re

class FileClassifier:
    def __init__(self):
        # Single source of truth for file categories with extensions
        self.FILE_CATEGORIES = {
            "text": {".txt", ".srt", ".md", ".json", ".xml", ".log", ".ini", ".cfg"},
            "document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"},
            "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg"},
            "audio": {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"},
            "video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"},
            "compressed": {".zip", ".rar", ".tar", ".gz", ".7z"},
            "code": {".py", ".js", ".java", ".cpp", ".h", ".cs", ".php", ".html", ".css"}
        }
        
        # MIME type mappings
        self.MIME_CATEGORIES = {
            'text': ['text/plain', 'text/markdown', 'text/json', 'text/xml', 'text/html'],
            'document': [
                'application/pdf', 
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ],
            'image': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff'],
            'audio': ['audio/mpeg', 'audio/wav', 'audio/aac', 'audio/flac'],
            'video': ['video/mp4', 'video/avi', 'video/x-matroska'],
            'compressed': ['application/zip', 'application/x-rar-compressed', 'application/x-tar']
        }

        self.content_subcategories = {
            "text": {
                "source_code": lambda content: any(pattern in content.lower() 
                    for pattern in ['def ', 'class ', 'function', 'import ', 'include']),
                "configuration": lambda content: any(pattern in content.lower() 
                    for pattern in ['config', 'settings', 'env', 'properties']),
                "data": lambda content: any(pattern in content.lower() 
                    for pattern in ['json', 'xml', 'csv', 'data:']),
                "documentation": lambda content: any(pattern in content.lower() 
                    for pattern in ['readme', 'documentation', 'guide', 'manual']),
                "logs": lambda content: any(pattern in content.lower() 
                    for pattern in ['error:', 'warning:', 'info:', 'debug:'])
            },
            "document": {
                "report": lambda content: any(pattern in content.lower() 
                    for pattern in ['report', 'analysis', 'summary', 'findings']),
                "presentation": lambda content: any(pattern in content.lower() 
                    for pattern in ['slide', 'presentation', 'deck']),
                "spreadsheet": lambda content: any(pattern in content.lower() 
                    for pattern in ['sheet', 'table', 'column', 'row']),
                "form": lambda content: any(pattern in content.lower() 
                    for pattern in ['form', 'application', 'questionnaire'])
            },
            "code": {
                "web": lambda content: any(pattern in content.lower() 
                    for pattern in ['html', 'css', 'javascript', 'react', 'angular']),
                "backend": lambda content: any(pattern in content.lower() 
                    for pattern in ['server', 'database', 'api', 'rest']),
                "data_science": lambda content: any(pattern in content.lower() 
                    for pattern in ['pandas', 'numpy', 'sklearn', 'tensorflow']),
                "system": lambda content: any(pattern in content.lower() 
                    for pattern in ['system', 'os', 'kernel', 'driver'])
            }
        }

    def get_mime_type(self, file_path):
        """Get MIME type using both mimetypes and Tika"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            try:
                parsed = parser.from_file(file_path)
                mime_type = parsed.get('metadata', {}).get('Content-Type')
            except:
                pass
        return mime_type or "application/octet-stream"

    def analyze_content(self, file_path, category):
        """Analyze file content using Tika and determine subcategory"""
        try:
            # Parse content using Tika
            parsed = parser.from_file(file_path)
            content = parsed.get("content", "")
            
            if not content:
                return "general"
                
            # Get subcategories for the main category
            subcategories = self.content_subcategories.get(category, {})
            
            # Check each subcategory's conditions
            for subcategory, condition in subcategories.items():
                if condition(content):
                    return subcategory
                    
            return "general"
            
        except Exception as e:
            print(f"Content analysis error: {str(e)}")
            return "general"

    def classify_file(self, file_path):
        """Classify file and determine subcategory"""
        try:
            # Get file extension
            ext = os.path.splitext(file_path)[1].lower()
            
            # First try extension-based classification
            for category, extensions in self.FILE_CATEGORIES.items():
                if ext in extensions:
                    # Debug logging
                    print(f"Classified {file_path} as {category} based on extension {ext}")
                    
                    # If category supports content analysis, get subcategory
                    if category in self.content_subcategories:
                        subcategory = self.analyze_content(file_path, category)
                        return f"{category}/{subcategory}"
                    return category
            
            # If no match by extension, try MIME type
            mime_type = self.get_mime_type(file_path)
            if mime_type:
                for category, mime_types in self.MIME_CATEGORIES.items():
                    if any(mime_type.lower().startswith(m.lower()) for m in mime_types):
                        print(f"Classified {file_path} as {category} based on MIME type {mime_type}")
                        return category
            
            # Debug logging for unclassified files
            print(f"Could not classify {file_path} (ext: {ext}, mime: {mime_type})")
            return "other"
            
        except Exception as e:
            print(f"Classification error for {file_path}: {str(e)}")
            return "other"