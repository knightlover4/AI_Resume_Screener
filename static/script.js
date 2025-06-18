// static/script.js (NEW - Detailed View Version)

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContainer = document.getElementById('resultsContainer');
    const thresholdSlider = document.getElementById('thresholdSlider');
    const thresholdValue = document.getElementById('thresholdValue');
    const errorMessage = document.getElementById('error-message');

    let rankedCandidates = [];

    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const formData = new FormData(uploadForm);
        if (!document.getElementById('resumeFiles').files.length) {
            showError("Please select at least one resume file.");
            return;
        }

        loadingSpinner.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        errorMessage.classList.add('hidden');
        resultsContainer.innerHTML = '';

        try {
            const response = await fetch('/api/rank_resumes/', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            rankedCandidates = data.candidates || [];
            resultsSection.classList.remove('hidden');
            renderResults();

        } catch (error) {
            showError(error.message);
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    });

    thresholdSlider.addEventListener('input', () => {
        thresholdValue.textContent = thresholdSlider.value;
        renderResults();
    });

    function renderResults() {
        resultsContainer.innerHTML = '';
        const currentThreshold = parseFloat(thresholdSlider.value);

        if (rankedCandidates.length === 0) {
            resultsContainer.innerHTML = '<p>No valid candidates found or processed.</p>';
            return;
        }

        rankedCandidates.forEach(candidate => {
            const isQualified = candidate.score >= currentThreshold;
            const statusClass = isQualified ? 'qualified' : 'disqualified';
            const details = candidate.details;

            // Generate HTML for skill tags
            const skillsHtml = details.skills.length
                ? details.skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')
                : '<span>No matching skills found</span>';
            
            const candidateCard = document.createElement('div');
            candidateCard.className = `candidate-card ${statusClass}`;
            
            candidateCard.innerHTML = `
                <div class="card-header">
                    <div class="candidate-name">
                        <span class="status-icon">${isQualified ? '✅' : '❌'}</span>
                        <h3>${details.name}</h3>
                    </div>
                    <div class="candidate-score">
                        <span>Score: <strong>${candidate.score}%</strong></span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="contact-info">
                        <p><strong>📧 Email:</strong> ${details.email}</p>
                        <p><strong>📞 Phone:</strong> ${details.phone}</p>
                    </div>
                    <div class="professional-info">
                        <p><strong>🎓 Education:</strong> ${details.education}</p>
                        <p><strong>💼 Experience:</strong> ${details.experience}</p>
                    </div>
                </div>
                <div class="card-footer">
                    <h4>Matching Skills</h4>
                    <div class="skills-container">
                        ${skillsHtml}
                    </div>
                </div>
            `;
            resultsContainer.appendChild(candidateCard);
        });
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }
});