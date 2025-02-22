from flask import Flask
from controllers.file_controllers import FileController

app = Flask(__name__)

# Initialize the FileController
file_controller = FileController()

# Define routes
@app.route('/files', methods=['GET'])
def get_files():
    return file_controller.get_files()

@app.route('/files/categorize', methods=['POST'])
def categorize_files():
    return file_controller.categorize_files()

@app.route('/files/sort', methods=['POST'])
def sort_files():
    return file_controller.sort_files()

if __name__ == '__main__':
    app.run(debug=True)