let navigationHistory = [];
let currentIndex = -1;

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
            // Add new path to history
            currentIndex++;
            navigationHistory = navigationHistory.slice(0, currentIndex);
            navigationHistory.push(path);
            updateNavigationButtons();
        }
        
        displayFiles(files);
        document.querySelector('.current-path').textContent = path;
    } catch (error) {
        console.error('Error loading files:', error);
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

function displayFiles(files) {
    const filesContainer = document.querySelector('.files');
    filesContainer.innerHTML = '';

    files.forEach(file => {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-item';
        fileElement.innerHTML = `
            <div class="file-icon">${file.type === 'directory' ? '📁' : '📄'}</div>
            <div class="file-name">${file.name}</div>
        `;

        if (file.type === 'directory') {
            fileElement.addEventListener('click', () => loadFiles(file.path));
        }

        filesContainer.appendChild(fileElement);
    });
}