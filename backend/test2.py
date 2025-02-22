import mimetypes
import os

def classify_file(file_path):
    """Classifies a file into categories like Text, Video, Audio, Image, etc."""
    
    # Get file extension
    file_ext = os.path.splitext(file_path)[-1].lower()
    
    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(file_path)

    # Define categories
    text_formats = {".txt", ".pdf", ".docx", ".srt", ".csv", ".json", ".xml"}
    image_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg"}
    audio_formats = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
    video_formats = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"}
    compressed_formats = {".zip", ".rar", ".tar", ".gz", ".7z"}
    
    # Classification logic
    if file_ext in text_formats:
        return "Text File"
    elif file_ext in image_formats:
        return "Image File"
    elif file_ext in audio_formats:
        return "Audio File"
    elif file_ext in video_formats:
        return "Video File"
    elif file_ext in compressed_formats:
        return "Compressed File"
    elif mime_type and mime_type.startswith("application"):
        return "Other Document"
    else:
        return "Unknown File Type"

# Example Usage
file_path = r"C:\Users\ANANTHAKRISHNAN\Downloads\largepreview.png" # Change this to any file
file_type = classify_file(file_path)
print(f"File Type: {file_type}")
