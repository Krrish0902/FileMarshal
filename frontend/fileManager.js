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

async function loadFiles(path) {
    try {
        const encodedPath = encodeURIComponent(path);
        const response = await fetch(`http://localhost:5000/api/files/${encodedPath}`);
        const files = await response.json();
        displayFiles(files);
    } catch (error) {
        console.error('Error loading files:', error);
    }
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