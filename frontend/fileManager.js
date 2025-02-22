let navigationHistory = [];
let currentIndex = -1;
let searchTimeout = null;
const SEARCH_DELAY = 300;
let lastSearchQuery = '';
let currentSort = { field: 'name', direction: 'asc' };
let currentView = 'grid';

async function loadDrives() {
    try {
        const response = await fetch('http://localhost:5000/api/drives');
        const drives = await response.json();
        return drives;
    } catch (error) {
        console.error('Error loading drives:', error);
        return [];
    }
}

async function loadFiles(path, addToHistory = true) {
    try {
        const encodedPath = encodeURIComponent(path);
        const response = await fetch(`http://localhost:5000/api/files/${encodedPath}`);
        const files = await response.json();
        
        if (addToHistory) {
            currentIndex++;
            navigationHistory = navigationHistory.slice(0, currentIndex);
            navigationHistory.push(path);
            updateNavigationButtons();
        }
        
        displayFiles(files);
        document.querySelector('.current-path').textContent = path;
    } catch (error) {
        console.error('Error loading files:', error);
        displayError(`Failed to load files from ${path}`);
    }
}

async function searchFiles(query, path) {
    try {
        // Clean the path if it contains search results text
        if (path.includes('Found') || path.includes('No results')) {
            path = path.split(' in ').pop();
        }

        const encodedPath = encodeURIComponent(path);
        const encodedQuery = encodeURIComponent(query.trim());
        const response = await fetch(`http://localhost:5000/api/search?query=${encodedQuery}&path=${encodedPath}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const files = await response.json();
        
        if (files.error) {
            throw new Error(files.error);
        }
        
        // Sort results: directories first, then files
        files.sort((a, b) => {
            if (a.type === b.type) {
                return a.name.localeCompare(b.name);
            }
            return a.type === 'directory' ? -1 : 1;
        });
        
        displayFiles(files);
        
        // Update status message
        const statusMsg = document.querySelector('.current-path');
        statusMsg.textContent = files.length > 0 
            ? `Found ${files.length} results for "${query}" in ${path}`
            : `No results found for "${query}" in ${path}`;
            
    } catch (error) {
        console.error('Search error:', error);
        displayError(`Search failed: ${error.message}`);
    }
}

function displayError(message) {
    const filesContainer = document.querySelector('.files');
    filesContainer.innerHTML = `
        <div class="no-results">
            <p style="color: #ff6b6b;">${message}</p>
        </div>
    `;
}

function goBack() {
    if (currentIndex > 0) {
        currentIndex--;
        loadFiles(navigationHistory[currentIndex], false);
        updateNavigationButtons();
    }
}

function goForward() {
    if (currentIndex < navigationHistory.length - 1) {
        currentIndex++;
        loadFiles(navigationHistory[currentIndex], false);
        updateNavigationButtons();
    }
}

function updateNavigationButtons() {
    const backBtn = document.getElementById('backBtn');
    const forwardBtn = document.getElementById('forwardBtn');
    
    backBtn.disabled = currentIndex <= 0;
    forwardBtn.disabled = currentIndex >= navigationHistory.length - 1;
}

function sortFiles(files, field, direction) {
    return [...files].sort((a, b) => {
        let compareVal;
        switch (field) {
            case 'name':
                compareVal = a.name.localeCompare(b.name);
                break;
            case 'size':
                compareVal = (a.size || 0) - (b.size || 0);
                break;
            case 'modified':
                compareVal = (a.modified || 0) - (b.modified || 0);
                break;
            case 'type':
                compareVal = a.type.localeCompare(b.type);
                break;
            default:
                compareVal = 0;
        }
        return direction === 'asc' ? compareVal : -compareVal;
    });
}

function displayFiles(files) {
    const filesContainer = document.querySelector('.files');
    filesContainer.innerHTML = '';
    filesContainer.className = `files ${currentView}-view`;

    if (!files || files.length === 0) {
        filesContainer.innerHTML = '<div class="no-results">No files found</div>';
        return;
    }

    // Sort files before display
    const sortedFiles = sortFiles(files, currentSort.field, currentSort.direction);

    sortedFiles.forEach(file => {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-item';
        
        const iconElement = document.createElement('div');
        iconElement.className = 'file-icon';
        iconElement.textContent = file.type === 'directory' ? '📁' : '📄';
        
        const nameElement = document.createElement('div');
        nameElement.className = 'file-name';
        
        if (file.highlightedName && Array.isArray(file.highlightedName)) {
            file.highlightedName.forEach(part => {
                const span = document.createElement('span');
                span.textContent = part.text;
                if (part.highlight) {
                    span.className = 'highlight';
                }
                nameElement.appendChild(span);
            });
        } else {
            nameElement.textContent = file.name;
        }

        if (currentView === 'list') {
            const details = document.createElement('div');
            details.className = 'file-details';
            details.innerHTML = `
                <span>${file.type}</span>
                <span>${formatSize(file.size)}</span>
                <span>${formatDate(file.modified)}</span>
            `;
            fileElement.appendChild(iconElement);
            fileElement.appendChild(nameElement);
            fileElement.appendChild(details);
        } else {
            fileElement.appendChild(iconElement);
            fileElement.appendChild(nameElement);
        }

        if (file.type === 'directory') {
            fileElement.addEventListener('click', () => loadFiles(file.path));
        }

        // Add context menu
        fileElement.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            showContextMenu(e, file);
        });

        filesContainer.appendChild(fileElement);
    });
}

function formatSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleDateString();
}

function showContextMenu(event, file) {
    const contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.innerHTML = `
        <div class="context-menu-item">Open</div>
        <div class="context-menu-item">Copy</div>
        <div class="context-menu-item">Cut</div>
        <div class="context-menu-item">Delete</div>
        <div class="context-menu-item">Rename</div>
        <div class="context-menu-item">Properties</div>
    `;

    contextMenu.style.left = `${event.pageX}px`;
    contextMenu.style.top = `${event.pageY}px`;
    document.body.appendChild(contextMenu);

    // Close menu on click outside
    document.addEventListener('click', function closeMenu() {
        contextMenu.remove();
        document.removeEventListener('click', closeMenu);
    });
}

function handleSearch(event) {
    const searchInput = event.target;
    const query = searchInput.value.trim();
    const currentPath = document.querySelector('.current-path').textContent.split(' in ').pop();

    // Store original path on first search
    if (!searchInput.dataset.originalPath) {
        searchInput.dataset.originalPath = currentPath;
    }

    clearTimeout(searchTimeout);

    if (!query) {
        // Reset to original path when search is cleared
        const originalPath = searchInput.dataset.originalPath;
        if (originalPath) {
            loadFiles(originalPath);
            document.querySelector('.current-path').textContent = originalPath;
            searchInput.dataset.originalPath = '';
        }
        return;
    }

    searchTimeout = setTimeout(() => {
        searchFiles(query, searchInput.dataset.originalPath || currentPath);
    }, SEARCH_DELAY);
}

// Remove all previous event listeners and add new ones
document.addEventListener('DOMContentLoaded', () => {
    const searchContainer = document.querySelector('.search-container');
    const oldSearchInput = document.getElementById('searchInput');
    const oldSearchBtn = document.getElementById('searchBtn');

    // Clone and replace search input to remove old listeners
    const searchInput = oldSearchInput.cloneNode(true);
    oldSearchInput.parentNode.replaceChild(searchInput, oldSearchInput);

    // Clone and replace search button to remove old listeners
    const searchBtn = oldSearchBtn.cloneNode(true);
    oldSearchBtn.parentNode.replaceChild(searchBtn, oldSearchBtn);

    // Add new event listeners
    searchInput.addEventListener('input', handleSearch);

    searchBtn.addEventListener('click', () => {
        const query = searchInput.value.trim();
        const currentPath = document.querySelector('.current-path').textContent;
        if (currentPath && query) {
            searchFiles(query, currentPath);
        }
    });

    searchInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            const query = searchInput.value.trim();
            const currentPath = document.querySelector('.current-path').textContent;
            if (currentPath && query) {
                searchFiles(query, currentPath);
            }
        }
    });

    // Add sort button listener
    document.getElementById('sortBtn').addEventListener('click', function() {
        const dropdown = document.querySelector('.sort-dropdown');
        dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    });

    // Add view button listener
    document.getElementById('viewBtn').addEventListener('click', function() {
        const dropdown = document.querySelector('.view-dropdown');
        dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    });

    // Add sort options listeners
    document.querySelectorAll('.sort-option').forEach(option => {
        option.addEventListener('click', function() {
            const field = this.dataset.sort;
            currentSort.direction = currentSort.field === field ? 
                (currentSort.direction === 'asc' ? 'desc' : 'asc') : 'asc';
            currentSort.field = field;
            
            // Update active sort option
            document.querySelectorAll('.sort-option').forEach(opt => {
                opt.classList.remove('active', 'desc');
            });
            this.classList.add('active');
            if (currentSort.direction === 'desc') {
                this.classList.add('desc');
            }
            
            // Refresh current view
            const currentPath = document.querySelector('.current-path').textContent;
            loadFiles(currentPath);
        });
    });

    // Add view options listeners
    document.querySelectorAll('.view-option').forEach(option => {
        option.addEventListener('click', function() {
            currentView = this.dataset.view;
            const currentPath = document.querySelector('.current-path').textContent;
            loadFiles(currentPath);
        });
    });
});