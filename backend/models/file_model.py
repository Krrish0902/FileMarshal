class FileModel:
    def __init__(self, file_name, file_path, file_type):
        self.file_name = file_name
        self.file_path = file_path
        self.file_type = file_type

    def get_file_info(self):
        return {
            "name": self.file_name,
            "path": self.file_path,
            "type": self.file_type
        }