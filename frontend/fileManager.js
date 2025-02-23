let navigationHistory = [];
let currentIndex = -1;
let searchTimeout = null;
const SEARCH_DELAY = 300;
let lastSearchQuery = '';
let currentSort = { field: 'name', direction: 'asc' };
let currentView = 'grid';
let selectedFiles = new Set();

async function loadDrives() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/drives');
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
        const response = await fetch(`http://127.0.0.1:5000/api/files/${encodedPath}`);
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

async function loadFilesByCategory(category, path) {
    try {
        // Clean the path if it contains results text
        if (path.includes('Found') || path.includes('No results')) {
            path = path.split(' in ').pop();
        }

        console.log(`Loading category: ${category} from path: ${path}`); // Debug log
        
        const encodedPath = encodeURIComponent(path);
        const response = await fetch(`http://127.0.0.1:5000/api/files/category/${category}?path=${encodedPath}`);
        
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
        const response = await fetch(`http://127.0.0.1:5000/api/search?query=${encodedQuery}&path=${encodedPath}`);
        
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

    const sortedFiles = sortFiles(files, currentSort.field, currentSort.direction);

    sortedFiles.forEach(file => {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-item';
        if (selectedFiles.has(file.path)) {
            fileElement.classList.add('selected');
        }
        
        // Add checkbox for selection
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'file-checkbox';
        checkbox.checked = selectedFiles.has(file.path);
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            if (e.target.checked) {
                selectedFiles.add(file.path);
                fileElement.classList.add('selected');
            } else {
                selectedFiles.delete(file.path);
                fileElement.classList.remove('selected');
            }
            updateSelectionControls();
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
    
    updateSelectionControls();
}

async function openFile(file) {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/open', {
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

// Remove all previous event listeners and add new ones
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the sidebar with drives
    initializeSidebar();
    
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

function updateSelectionControls() {
    const selectionCount = selectedFiles.size;
    const selectionControls = document.querySelector('.selection-controls');
    
    if (selectionCount > 0) {
        if (!selectionControls) {
            const controls = document.createElement('div');
            controls.className = 'selection-controls';
            controls.innerHTML = `
                <span>${selectionCount} item(s) selected</span>
                <button id="organizeBtn">Organize Selected Files</button>
                <button id="clearSelectionBtn">Clear Selection</button>
            `;
            document.querySelector('.file-view').insertBefore(
                controls, 
                document.querySelector('.files')
            );
            
            // Add event listeners
            document.getElementById('organizeBtn').addEventListener('click', organizeSelectedFiles);
            document.getElementById('clearSelectionBtn').addEventListener('click', clearSelection);
        } else {
            selectionControls.querySelector('span').textContent = `${selectionCount} item(s) selected`;
        }
    } else if (selectionControls) {
        selectionControls.remove();
    }
}

function clearSelection() {
    selectedFiles.clear();
    document.querySelectorAll('.file-item').forEach(item => {
        item.classList.remove('selected');
        item.querySelector('.file-checkbox').checked = false;
    });
    updateSelectionControls();
}

async function organizeSelectedFiles() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/organize', {
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

// Update loadDirectoryContents function
async function loadDirectoryContents(path) {
    try {
        // Ensure path is absolute
        const absolutePath = path.startsWith('C:') ? path : `C:${path}`;
        const encodedPath = encodeURIComponent(absolutePath);
        const response = await fetch(`http://127.0.0.1:5000/api/files/${encodedPath}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const files = await response.json();
        
        if (files.error) {
            throw new Error(files.error);
        }
        
        return files;
    } catch (error) {
        console.error('Error loading directory contents:', error);
        return [];
    }
}

// Update createTreeItem function
function createTreeItem(name, path, isDirectory) {
    const item = document.createElement('div');
    item.className = 'tree-item';
    
    const content = document.createElement('div');
    content.className = 'tree-content';
    
    if (isDirectory) {
        const expandBtn = document.createElement('span');
        expandBtn.className = 'expand-button';
        expandBtn.textContent = '►';
        content.appendChild(expandBtn);
        
        const childList = document.createElement('div');
        childList.className = 'tree-list hidden';
        
        expandBtn.onclick = async (e) => {
            e.stopPropagation();
            const isExpanded = expandBtn.textContent === '▼';
            expandBtn.textContent = isExpanded ? '►' : '▼';
            childList.classList.toggle('hidden');
            
            if (!isExpanded && childList.children.length === 0) {
                try {
                    // Ensure we're using the full path
                    const fullPath = path.includes(':') ? path : `${name}:\\`;
                    const children = await loadDirectoryContents(fullPath);
                    const MAX_VISIBLE_ITEMS = 50;
                    
                    children.slice(0, MAX_VISIBLE_ITEMS).forEach(child => {
                        const childPath = child.path;
                        childList.appendChild(
                            createTreeItem(child.name, childPath, child.type === 'directory')
                        );
                    });
                    
                    if (children.length > MAX_VISIBLE_ITEMS) {
                        const moreItem = document.createElement('div');
                        moreItem.className = 'tree-item more-items';
                        moreItem.textContent = `... ${children.length - MAX_VISIBLE_ITEMS} more items`;
                        childList.appendChild(moreItem);
                    }
                } catch (error) {
                    console.error('Error loading directory:', error);
                    // Show error in the tree
                    const errorItem = document.createElement('div');
                    errorItem.className = 'tree-item error';
                    errorItem.textContent = 'Error loading contents';
                    childList.appendChild(errorItem);
                }
            }
        };
        
        item.appendChild(childList);
    }
    
    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    icon.textContent = isDirectory ? '📁' : '📄';
    
    const label = document.createElement('span');
    label.className = 'tree-label';
    label.textContent = name;
    
    content.appendChild(icon);
    content.appendChild(label);
    item.insertBefore(content, item.firstChild);
    
    // Update click handler to use full path
    content.onclick = () => {
        if (isDirectory) {
            const fullPath = path.includes(':') ? path : `${name}:\\`;
            loadFiles(fullPath);
        } else {
            openFile({ path: path, name: name });
        }
    };
    
    return item;
}

// Update initializeSidebar function
async function initializeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.innerHTML = '<h2>File Explorer</h2>';
    
    const treeRoot = document.createElement('ul');
    treeRoot.className = 'tree-root';
    sidebar.appendChild(treeRoot);
    
    try {
        const drives = await loadDrives();
        drives.forEach(drive => {
            // Create drive items with proper formatting
            const drivePath = `${drive}\\`;
            treeRoot.appendChild(createTreeItem(drive, drivePath, true));
        });
    } catch (error) {
        console.error('Error loading drives:', error);
        const errorItem = document.createElement('li');
        errorItem.className = 'error-message';
        errorItem.textContent = 'Failed to load drives';
        treeRoot.appendChild(errorItem);
    }
}