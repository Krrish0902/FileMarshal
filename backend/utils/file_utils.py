# filepath: /backend/src/utils/file_utils.py

import os

def read_file_contents(file_path):
    """Reads the contents of a file and returns it."""
    with open(file_path, 'r') as file:
        return file.read()

def check_file_type(file_path):
    """Returns the file type based on the file extension."""
    return os.path.splitext(file_path)[1]

def create_directory(directory_path):
    """Creates a directory if it does not exist."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)