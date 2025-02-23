# FileMarshal 📂

A modern, cross-platform file organization application that helps users efficiently manage and navigate their files using intelligent categorization and a sleek dark-mode interface.

## Features

- 🚀 **Smart File Organization**
  - Automatic file categorization by type (images, documents, videos, etc.)
  - Drag-and-drop file organization
  - Bulk file operations
  
- 🔍 **Advanced Search**
  - Real-time file search with highlighting
  - Search across multiple drives
  - Filter by file types and categories
  
- 📁 **Intuitive Navigation**
  - Directory-first sorting
  - Forward/backward navigation
  - Breadcrumb path display
  - Drive and folder tree view

- 🎯 **Smart Features**
  - File type detection
  - Category-based organization
  - File preview support
  - Multiple view options (grid/list)

## Tech Stack

### Frontend
- Electron.js (Desktop Application)
- HTML/CSS/JavaScript
- Modern UI with fluid animations
- Dark mode interface

### Backend
- Flask (Python)
- Apache Tika for file type detection
- RESTful API architecture
- Cross-platform file system operations

## Installation

### Prerequisites
- Node.js (v14 or higher)
- Python (v3.8 or higher)
- pip (Python package manager)

### Setup Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/FileMarshal.git
cd FileMarshal
```

2. Set up the backend:
```bash
cd backend
pip install -r requirements.txt
python main.py
```

3. Set up the frontend:
```bash
cd ../frontend
npm install
npm start
```

## Usage Guide

### Getting Started
1. Launch the application
2. Click "Get Started" on the welcome screen
3. Navigate through your file system using the sidebar
4. Use the search bar for quick file lookup

### File Organization
- Select files using checkboxes or Ctrl+Click
- Use the "Organize" button to automatically sort files by category
- Drag and drop files between folders
- Right-click for additional options

### View Options
- Toggle between grid and list views
- Sort files by name, size, type, or date
- Use the folder tree for quick navigation
- Enable/disable file previews

## Project Structure
```
FileMarshal/
├── backend/
│   ├── file_classifier.py
│   ├── main.py
│   └── requirements.txt
└── frontend/
    ├── dashboard.html
    ├── fileManager.js
    ├── index.html
    ├── loading.html
    ├── main.js
    ├── package.json
    └── styles.css
```

## Development

### Running in Development Mode
1. Start the Flask backend:
```bash
cd backend
python main.py
```

2. Start the Electron frontend:
```bash
cd frontend
npm run dev
```

### Building for Production
```bash
cd frontend
npm run build
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, feature requests, or bug reports, please open an issue on GitHub.
