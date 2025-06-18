document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const form = document.getElementById('resume-form');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('resume-files');
    const fileListDisplay = document.getElementById('file-list');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('results-container');
    const resultsList = document.getElementById('results-list');
    const errorContainer = document.getElementById('error-container');

    let selectedFiles = [];

    // --- Drag & Drop Logic ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        handleFiles(files);
    });
    
    fileInput.addEventListener('change', () => {
        const files = fileInput.files;
        handleFiles(files);
    });

    function handleFiles(files) {
        if (files.length === 0) return;
        
        selectedFiles = []; // Reset the list for a new selection
        
        for (const file of files) {
            if (file.type === "application/pdf" || file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
                if (!selectedFiles.some(f => f.name === file.name)) {
                    selectedFiles.push(file);
                }
            }
        }
        updateFileList();
    }
    
    function updateFileList() {
        fileListDisplay.innerHTML = '';
        if (selectedFiles.length > 0) {
            const listContainer = document.createElement('div');
            listContainer.innerHTML = `<strong>Selected files:</strong>`;
            selectedFiles.forEach(file => {
                const fileItem = document.createElement('p');
                fileItem.textContent = file.name;
                listContainer.appendChild(fileItem);
            });
            fileListDisplay.appendChild(listContainer);
        }
    }


    // --- Form Submission Logic ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const jobDescription = document.getElementById('job-description').value;

        if (!jobDescription.trim() || selectedFiles.length === 0) {
            alert('Please provide a job description and at least one resume.');
            return;
        }

        // Show loader and hide previous results/errors
        loader.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        errorContainer.classList.add('hidden');
        
        // Create FormData object
        const formData = new FormData();
        formData.append('job_description', jobDescription);
        selectedFiles.forEach(file => {
            formData.append('resumes', file, file.name);
        });

        try {
            const response = await fetch('/api/rank_resumes/', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            displayResults(data.candidates);

        } catch (error) {
            console.error('Error:', error);
            errorContainer.classList.remove('hidden');
        } finally {
            loader.classList.add('hidden');
        }
    });

    // --- Display Results ---
    function displayResults(candidates) {
        resultsList.innerHTML = ''; // Clear previous results
        
        if (candidates && candidates.length > 0) {
            candidates.forEach(candidate => {
                const card = createCandidateCard(candidate);
                resultsList.appendChild(card);
            });
            resultsContainer.classList.remove('hidden');
        } else {
            errorContainer.innerHTML = '<p>No candidates could be processed or ranked.</p>';
            errorContainer.classList.remove('hidden');
        }
    }

    function createCandidateCard(candidate) {
        const card = document.createElement('div');
        card.className = 'candidate-card';

        const score = candidate.score || 0;
        const scoreColor = getScoreColor(score);
        card.style.borderLeftColor = scoreColor;

        const skillsHtml = candidate.details.skills.length > 0
            ? candidate.details.skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')
            : '<span>No specific skills found.</span>';

        card.innerHTML = `
            <div class="card-header">
                <span class="name">${candidate.details.name || 'Name Not Found'}</span>
                <span class="score" style="color: ${scoreColor};">${score}% Match</span>
            </div>
            <div class="score-bar">
                <div class="score-bar-inner" style="width: ${score}%; background-color: ${scoreColor};"></div>
            </div>
            <div class="details-grid">
                <div class="detail-item">
                    <strong><i class="fas fa-envelope"></i> Email</strong>
                    <span>${candidate.details.email || 'Not Found'}</span>
                </div>
                <div class="detail-item">
                    <strong><i class="fas fa-briefcase"></i> Experience</strong>
                    <span>${candidate.details.experience || 'Not Found'}</span>
                </div>
                <div class="detail-item">
                    <strong><i class="fas fa-graduation-cap"></i> Education</strong>
                    <span>${candidate.details.education || 'Not Found'}</span>
                </div>
                 <div class="detail-item">
                    <strong><i class="fas fa-file-alt"></i> Original File</strong>
                    <span>${candidate.filename}</span>
                </div>
            </div>
            <div class="detail-item">
                <strong><i class="fas fa-cogs"></i> Skills</strong>
                <div class="skills-list">${skillsHtml}</div>
            </div>
        `;
        return card;
    }

    function getScoreColor(score) {
        if (score >= 80) return 'var(--success-color)';
        if (score >= 60) return 'var(--primary-color)';
        if (score >= 40) return 'var(--warning-color)';
        return 'var(--error-color)';
    }
});