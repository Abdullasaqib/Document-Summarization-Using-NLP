const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const loadingDiv = document.getElementById('loading');
const resultSection = document.getElementById('result-section');
const summaryText = document.getElementById('summary-text');
const originalLenSpan = document.getElementById('original-len');
const summaryLenSpan = document.getElementById('summary-len');
const copyBtn = document.getElementById('copy-btn');
const resetBtn = document.getElementById('reset-btn');

// Drag & Drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--primary-color)';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = 'var(--border-color)';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--border-color)';
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

// Click to Upload
uploadArea.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

// Reset
resetBtn.addEventListener('click', () => {
    resultSection.classList.add('hidden');
    uploadArea.classList.remove('hidden');
    fileInput.value = '';
});

// Copy
copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(summaryText.innerText);
    copyBtn.innerText = 'Copied!';
    setTimeout(() => copyBtn.innerText = 'Copy Text', 2000);
});

async function handleFile(file) {
    if (!file) return;

    // UI Updates
    uploadArea.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    resultSection.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('http://127.0.0.1:8000/summarize', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to summarize');
        }

        // Show Results immediately
        loadingDiv.classList.add('hidden');
        resultSection.classList.remove('hidden');
        summaryText.innerText = ''; // Clear previous

        // Read Stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let summaryLength = 0;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            summaryText.innerText += chunk;
            summaryLength += chunk.length;

            // Auto-scroll to bottom of summary
            // resultSection.scrollTop = resultSection.scrollHeight; 
        }

        // Final update (optional stats)
        summaryLenSpan.innerText = `Summary Chars: ${summaryLength}`;
        originalLenSpan.innerText = `Stream Complete`;

    } catch (error) {
        console.error(error);
        alert(`Error: ${error.message}`);
        loadingDiv.classList.add('hidden');
        uploadArea.classList.remove('hidden');
    }
}
