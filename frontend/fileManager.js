let navigationHistory = [];
let currentIndex = -1;
let searchTimeout = null;
const SEARCH_DELAY = 300;
let lastSearchQuery = '';
let currentSort = { field: 'name', direction: 'asc' };
let currentView = 'grid';
let selectedFiles = new Set();
let isSelectionMode = false;
let lastClickTime = 0;
const doubleClickDelay = 300;
let selectAllState = false;

async function loadDrives() {
    try {
        console.log('Fetching drives...'); // Debug log
        const response = await fetch('http://localhost:5000/api/drives');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const drives = await response.json();
        console.log('Received drives:', drives); // Debug log
        
        if (!Array.isArray(drives)) {
            throw new Error('Invalid drive data received');
        }
        
        // If no drives found, default to C: drive
        if (drives.length === 0) {
            console.log('No drives found, defaulting to C:'); // Debug log
            return ['C:'];
        }
        
        return drives;
    } catch (error) {
        console.error('Error loading drives:', error);
        // Default to C: drive on error
        return ['C:'];
    }
}

// Update the loadFiles function
async function loadFiles(path, addToHistory = true) {
    try {
        console.log(`Loading files from: ${path}`); // Debug log
        
        // Handle Windows drive paths
        const encodedPath = encodeURIComponent(path.replace(':', '|'));
        const response = await fetch(`http://localhost:5000/api/files/${encodedPath}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Update history only if successful
        if (addToHistory) {
            currentIndex++;
            navigationHistory = navigationHistory.slice(0, currentIndex);
            navigationHistory.push(path);
        }
        
        // Update UI elements safely
        displayFiles(data);
        
        const pathElement = document.querySelector('.current-path');
        if (pathElement) {
            pathElement.textContent = path;
        }
        
        const titleElement = document.querySelector('h1');
        if (titleElement) {
            titleElement.textContent = `${path} (${data.length} items)`;
        }
        
        // Update navigation buttons after successful load
        updateNavigationButtons();
        
    } catch (error) {
        console.error('Error loading files:', error);
        displayError(`Failed to load files from ${path}: ${error.message}`);
    }
}

async function loadFilesByCategory(category, path) {
    try {
        // Clean the path if it contains results text
        if (path.includes('Found') || path.includes('No results')) {
            path = path.split(' in ').pop();
        }

        console.log(`Loading category: ${category} from path: ${path}`); // Debug log
        
        const encodedPath = encodeURIComponent(path);
        const response = await fetch(`http://localhost:5000/api/files/category/${category}?path=${encodedPath}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const files = await response.json();
        
        if (files.error) {
            throw new Error(files.error);
        }
        
        console.log(`Found ${files.length} files in category ${category}`); // Debug log
        
        displayFiles(files);
        
        // Update header and path
        document.querySelector('h1').textContent = 
            `${category.charAt(0).toUpperCase() + category.slice(1)} (${files.length} items)`;
        document.querySelector('.current-path').textContent = 
            `Showing ${category} in ${path}`;
            
    } catch (error) {
        console.error('Error loading files by category:', error);
        displayError(`Failed to load ${category} files: ${error.message}`);
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

// Update error display function
function displayError(message) {
    const filesContainer = document.querySelector('.files');
    if (filesContainer) {
        filesContainer.innerHTML = `
            <div class="no-results">
                <p style="color: #ff6b6b;">${message}</p>
            </div>
        `;
    } else {
        console.error('Files container not found:', message);
    }
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

    const sortedFiles = sortFiles(files, currentSort.field, currentSort.direction);

    sortedFiles.forEach(file => {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-item';
        fileElement.dataset.path = file.path;
        if (selectedFiles.has(file.path)) {
            fileElement.classList.add('selected');
        }

        // Add checkbox (hidden by default)
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'file-checkbox';
        checkbox.checked = selectedFiles.has(file.path);

        // Handle click events
        fileElement.addEventListener('click', (e) => {
            const currentTime = new Date().getTime();
            const isDoubleClick = currentTime - lastClickTime < doubleClickDelay;
            lastClickTime = currentTime;

            if (isDoubleClick) {
                // Double click - open file/folder
                if (file.type === 'directory') {
                    loadFiles(file.path);
                } else {
                    openFile(file);
                }
            } else {
                // Single click - select item
                handleFileSelection(file, e.ctrlKey, e.shiftKey);
            }
        });

        // Update checkbox behavior
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            handleFileSelection(file, e.ctrlKey, e.shiftKey);
        });

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
        } else {
            // Add click handler for files
            fileElement.addEventListener('click', () => openFile(file));
        }

        // Add context menu
        fileElement.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            showContextMenu(e, file);
        });

        // Add checkbox as first child
        fileElement.insertBefore(checkbox, fileElement.firstChild);
        
        filesContainer.appendChild(fileElement);
    });
    
    selectAllState = false;
    document.getElementById('selectAllBtn').textContent = '☐';
    document.getElementById('selectAllBtn').classList.remove('active');
    
    updateSelectionCount();
}

function handleFileSelection(file, ctrlKey, shiftKey) {
    if (!isSelectionMode) {
        isSelectionMode = true;
        document.querySelector('.files').classList.add('selection-mode');
    }

    if (shiftKey && lastSelectedFile) {
        // Handle range selection
        const files = Array.from(document.querySelectorAll('.file-item'));
        const startIndex = files.findIndex(el => el.dataset.path === lastSelectedFile);
        const endIndex = files.findIndex(el => el.dataset.path === file.path);
        const [min, max] = [Math.min(startIndex, endIndex), Math.max(startIndex, endIndex)];
        
        files.slice(min, max + 1).forEach(fileEl => {
            const filePath = fileEl.dataset.path;
            selectedFiles.add(filePath);
            fileEl.classList.add('selected');
            fileEl.querySelector('.file-checkbox').checked = true;
        });
    } else if (ctrlKey) {
        // Toggle single selection
        if (selectedFiles.has(file.path)) {
            selectedFiles.delete(file.path);
        } else {
            selectedFiles.add(file.path);
        }
    } else {
        // Clear previous selection and select single file
        selectedFiles.clear();
        document.querySelectorAll('.file-item').forEach(item => {
            item.classList.remove('selected');
            item.querySelector('.file-checkbox').checked = false;
        });
        selectedFiles.add(file.path);
    }

    lastSelectedFile = file.path;
    updateSelectionControls();
}

function updateSelectionControls() {
    const selectionCount = selectedFiles.size;
    let selectionControls = document.querySelector('.selection-controls');
    
    if (selectionCount > 0 || isSelectionMode) {
        if (!selectionControls) {
            const controls = document.createElement('div');
            controls.className = 'selection-controls';
            controls.innerHTML = `
                <div class="selection-info">
                    <input type="checkbox" class="select-all-checkbox" title="Select All">
                    <span>${selectionCount} item(s) selected</span>
                </div>
                <div class="selection-actions">
                    <button id="organizeBtn">Organize Selected Files</button>
                    <button id="clearSelectionBtn">Clear Selection</button>
                </div>
            `;
            document.querySelector('.file-view').insertBefore(
                controls, 
                document.querySelector('.files')
            );
            
            // Add event listeners
            const selectAllCheckbox = controls.querySelector('.select-all-checkbox');
            selectAllCheckbox.addEventListener('change', handleSelectAll);
            document.getElementById('organizeBtn').addEventListener('click', organizeSelectedFiles);
            document.getElementById('clearSelectionBtn').addEventListener('click', exitSelectionMode);
        } else {
            selectionControls.querySelector('span').textContent = `${selectionCount} item(s) selected`;
            selectionControls.querySelector('.select-all-checkbox').checked = 
                selectionCount === document.querySelectorAll('.file-item').length;
        }
    } else if (selectionControls) {
        selectionControls.remove();
    }
}

function handleSelectAll() {
    selectAllState = !selectAllState;
    const selectAllBtn = document.getElementById('selectAllBtn');
    selectAllBtn.textContent = selectAllState ? '☑' : '☐';
    selectAllBtn.classList.toggle('active', selectAllState);

    const fileItems = document.querySelectorAll('.file-item');
    fileItems.forEach(item => {
        const filePath = item.querySelector('.file-name').dataset.path;
        if (selectAllState) {
            selectedFiles.add(filePath);
            item.classList.add('selected');
        } else {
            selectedFiles.delete(filePath);
            item.classList.remove('selected');
        }
    });

    updateSelectionCount();
}

function updateSelectionCount() {
    const count = selectedFiles.size;
    const totalFiles = document.querySelectorAll('.file-item').length;
    
    let selectionControls = document.querySelector('.selection-controls');
    if (count > 0) {
        if (!selectionControls) {
            selectionControls = document.createElement('div');
            selectionControls.className = 'selection-controls';
            selectionControls.innerHTML = `
                <div class="selection-info">
                    <span class="selection-count">${count} of ${totalFiles} selected</span>
                </div>
                <div class="selection-actions">
                    <button id="organizeBtn">Organize Selected Files</button>
                    <button id="clearSelectionBtn">Clear Selection</button>
                </div>
            `;
            document.querySelector('.file-view').insertBefore(
                selectionControls,
                document.querySelector('.files')
            );

            document.getElementById('organizeBtn').addEventListener('click', organizeSelectedFiles);
            document.getElementById('clearSelectionBtn').addEventListener('click', exitSelectionMode);
        } else {
            selectionControls.querySelector('.selection-count').textContent = 
                `${count} of ${totalFiles} selected`;
        }
    } else if (selectionControls) {
        selectionControls.remove();
        selectAllState = false;
        document.getElementById('selectAllBtn').textContent = '☐';
        document.getElementById('selectAllBtn').classList.remove('active');
    }
}

function exitSelectionMode() {
    isSelectionMode = false;
    selectedFiles.clear();
    document.querySelector('.files').classList.remove('selection-mode');
    document.querySelectorAll('.file-item').forEach(item => {
        item.classList.remove('selected');
        item.querySelector('.file-checkbox').checked = false;
    });
    updateSelectionControls();
}

async function openFile(file) {
    try {
        const response = await fetch('http://localhost:5000/api/open', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                path: file.path
            })
        });
        
        const result = await response.json();
        if (result.error) {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Error opening file:', error);
        displayError(`Failed to open file: ${error.message}`);
    }
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
        <div class="context-menu-item" data-action="open">
            <span>🔍</span> Open
        </div>
        <div class="context-menu-item" data-action="select">
            <span>☑️</span> Select
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" data-action="copy">
            <span>📋</span> Copy
        </div>
        <div class="context-menu-item" data-action="cut">
            <span>✂️</span> Cut
        </div>
        <div class="context-menu-item" data-action="delete">
            <span>🗑️</span> Delete
        </div>
        <div class="context-menu-item" data-action="rename">
            <span>✏️</span> Rename
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" data-action="properties">
            <span>ℹ️</span> Properties
        </div>
    `;

    contextMenu.style.left = `${event.pageX}px`;
    contextMenu.style.top = `${event.pageY}px`;
    document.body.appendChild(contextMenu);

    // Add click handlers for menu items
    contextMenu.querySelectorAll('.context-menu-item').forEach(item => {
        item.addEventListener('click', () => {
            const action = item.dataset.action;
            switch(action) {
                case 'select':
                    handleFileSelection(file, false, false);
                    break;
                case 'open':
                    if (file.type === 'directory') {
                        loadFiles(file.path);
                    } else {
                        openFile(file);
                    }
                    break;
                // Other actions can be added here
            }
            contextMenu.remove();
        });
    });

    // Close menu on click outside
    document.addEventListener('click', function closeMenu(e) {
        if (!contextMenu.contains(e.target)) {
            contextMenu.remove();
            document.removeEventListener('click', closeMenu);
        }
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

// Update initialization in dashboard.html
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('Initializing dashboard...'); // Debug log
        
        // Load drives
        const drives = await loadDrives();
        console.log('Available drives:', drives); // Debug log
        
        if (!drives || drives.length === 0) {
            throw new Error('No drives found');
        }
        
        const drivesList = document.getElementById('drives-list');
        if (!drivesList) {
            throw new Error('Drives list element not found');
        }
        
        drivesList.innerHTML = '';
        
        // Add drives to sidebar
        drives.forEach(drive => {
            const driveElement = document.createElement('div');
            driveElement.className = 'drive-item';
            driveElement.textContent = drive;
            driveElement.addEventListener('click', () => {
                console.log(`Clicking drive: ${drive}`); // Debug log
                loadFiles(drive);
            });
            drivesList.appendChild(driveElement);
        });

        // Load first drive's contents
        if (drives.length > 0) {
            console.log(`Loading initial drive: ${drives[0]}`); // Debug log
            await loadFiles(drives[0]);
        }
        
    } catch (error) {
        console.error('Dashboard initialization error:', error);
        displayError(`Failed to initialize: ${error.message}`);
    }
});

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

    // Add category click handlers
    document.querySelectorAll('.sidebar li').forEach(item => {
        item.addEventListener('click', () => {
            const category = item.dataset.type;
            const currentPath = document.querySelector('.current-path').textContent;
            if (currentPath) {
                loadFilesByCategory(category, currentPath);
            }
        });
    });

    document.getElementById('selectAllBtn').addEventListener('click', handleSelectAll);
});

async function organizeSelectedFiles() {
    try {
        const response = await fetch('http://localhost:5000/api/organize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                files: Array.from(selectedFiles)
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // Refresh current view
        const currentPath = document.querySelector('.current-path').textContent;
        loadFiles(currentPath);
        clearSelection();
        
        // Show success message
        displaySuccess(`Successfully organized ${selectedFiles.size} files`);
    } catch (error) {
        console.error('Error organizing files:', error);
        displayError(`Failed to organize files: ${error.message}`);
    }
}

function displaySuccess(message) {
    const successElement = document.createElement('div');
    successElement.className = 'success-message';
    successElement.textContent = message;
    document.querySelector('.file-view').insertBefore(
        successElement,
        document.querySelector('.files')
    );
    setTimeout(() => successElement.remove(), 3000);
}