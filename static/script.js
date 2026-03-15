document.addEventListener('DOMContentLoaded', () => {
    const noteForm = document.getElementById('noteForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorContainer = document.getElementById('errorContainer');
    const notesContainer = document.getElementById('notesContainer');
    const notesContent = document.getElementById('notesContent');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');

    // Form submission
    noteForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get form data
        const topic = document.getElementById('topic').value.trim();
        const level = document.getElementById('level').value.trim();
        const program = document.getElementById('program').value.trim();

        // Clear previous errors
        clearError();

        // Validate
        if (!topic || !level || !program) {
            showError('All fields are required');
            return;
        }

        if (topic.length > 200) {
            showError('Topic is too long (max 200 characters)');
            return;
        }

        // Show spinner, hide previous notes
        showSpinner();
        notesContainer.classList.add('hidden');

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    topic: topic,
                    level: level,
                    program: program
                })
            });

            const data = await response.json();

            hideSpinner();

            if (!response.ok) {
                showError(data.error || 'Failed to generate notes');
                return;
            }

            // Display notes
            notesContent.textContent = data.notes;
            notesContainer.classList.remove('hidden');

            // Scroll to notes
            notesContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        } catch (error) {
            hideSpinner();
            showError('Network error. Please try again.');
            console.error('Error:', error);
        }
    });

    // Copy notes
    copyBtn.addEventListener('click', () => {
        const text = notesContent.textContent;
        navigator.clipboard.writeText(text).then(() => {
            showFeedback(copyBtn, 'Copied! ✓');
        }).catch(() => {
            showError('Failed to copy');
        });
    });

    // Download notes
    downloadBtn.addEventListener('click', () => {
        const topic = document.getElementById('topic').value;
        const text = notesContent.textContent;
        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
        element.setAttribute('download', `notes_${topic.replace(/\s+/g, '_')}.txt`);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        showFeedback(downloadBtn, 'Downloaded! ✓');
    });

    // Helper functions
    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.classList.add('show');
        setTimeout(() => {
            errorContainer.classList.remove('show');
        }, 5000);
    }

    function clearError() {
        errorContainer.classList.remove('show');
        errorContainer.textContent = '';
    }

    function showSpinner() {
        loadingSpinner.classList.remove('hidden');
    }

    function hideSpinner() {
        loadingSpinner.classList.add('hidden');
    }

    function showFeedback(element, message) {
        const originalText = element.textContent;
        element.textContent = message;
        setTimeout(() => {
            element.textContent = originalText;
        }, 2000);
    }
});