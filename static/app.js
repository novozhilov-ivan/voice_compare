// API Configuration
const API_BASE_URL = window.location.origin;
let currentJobId = null;
let pollInterval = null;

// Tab Management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Activate button
    event.target.classList.add('active');
}

// Parse time range string (e.g., "120-300", "60-", "0-180")
function parseTimeRange(timeStr) {
    if (!timeStr || !timeStr.trim()) {
        return null;
    }

    const parts = timeStr.trim().split('-');
    if (parts.length !== 2) {
        return null;
    }

    const start = parts[0] ? parseFloat(parts[0]) : 0;
    const end = parts[1] ? parseFloat(parts[1]) : null;

    return { start, end };
}

// Build video with time range object
function buildVideoWithTimeRange(url, timeRange) {
    if (!timeRange) {
        return url;
    }
    return {
        url: url,
        time_range: timeRange
    };
}

// Compare Speakers
async function compareSpeakers() {
    const urls1 = document.getElementById('speaker1-urls').value.trim().split('\n').filter(url => url);
    const urls2 = document.getElementById('speaker2-urls').value.trim().split('\n').filter(url => url);
    const times1 = document.getElementById('speaker1-times').value.trim().split('\n');
    const times2 = document.getElementById('speaker2-times').value.trim().split('\n');
    const name1 = document.getElementById('speaker1-name').value.trim();
    const name2 = document.getElementById('speaker2-name').value.trim();
    const useTranscripts = document.getElementById('compare-use-transcripts').checked;

    if (urls1.length === 0 || urls2.length === 0) {
        showError('Please enter video URLs for both speakers');
        return;
    }

    // Build video objects with time ranges
    const video1Objects = urls1.map((url, i) => {
        const timeRange = parseTimeRange(times1[i]);
        return buildVideoWithTimeRange(url, timeRange);
    });

    const video2Objects = urls2.map((url, i) => {
        const timeRange = parseTimeRange(times2[i]);
        return buildVideoWithTimeRange(url, timeRange);
    });

    try {
        showResults();
        showProgress('Starting comparison...');

        const response = await fetch(`${API_BASE_URL}/api/compare-speakers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video1_urls: video1Objects,
                video2_urls: video2Objects,
                target_speaker1: name1 || null,
                target_speaker2: name2 || null,
                use_transcripts: useTranscripts
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentJobId = data.job_id;
            startPolling();
        } else {
            showError(`Error: ${data.detail || 'Unknown error'}`);
        }

    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

// Analyze Voice
async function analyzeVoice() {
    const urls = document.getElementById('analyze-urls').value.trim().split('\n').filter(url => url);
    const name = document.getElementById('analyze-name').value.trim();
    const useTranscripts = document.getElementById('analyze-use-transcripts').checked;

    if (urls.length === 0) {
        showError('Please enter at least one video URL');
        return;
    }

    try {
        showResults();
        showProgress('Starting analysis...');

        const response = await fetch(`${API_BASE_URL}/api/download-video`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                urls: urls,
                target_speaker: name || null,
                use_transcripts: useTranscripts
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentJobId = data.job_id;
            startPolling();
        } else {
            showError(`Error: ${data.detail || 'Unknown error'}`);
        }

    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

// Process Playlist
async function processPlaylist() {
    const playlistUrl = document.getElementById('playlist-url').value.trim();
    const speaker = document.getElementById('playlist-speaker').value.trim();
    const useTranscripts = document.getElementById('playlist-use-transcripts').checked;

    if (!playlistUrl) {
        showError('Please enter a playlist URL');
        return;
    }

    try {
        showResults();
        showProgress('Getting playlist videos...');

        const response = await fetch(`${API_BASE_URL}/api/download-playlist`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                playlist_url: playlistUrl,
                target_speaker: speaker || null,
                use_transcripts: useTranscripts
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentJobId = data.job_id;
            startPolling();
        } else {
            showError(`Error: ${data.detail || 'Unknown error'}`);
        }

    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

// Polling for job status
function startPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
    }

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/job/${currentJobId}`);
            const data = await response.json();

            updateProgress(data);

            if (data.status === 'completed') {
                clearInterval(pollInterval);
                displayResults(data);
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                showError(data.message);
            }

        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 2000);
}

// Update Progress
function updateProgress(data) {
    const progressFill = document.getElementById('progress-fill');
    const progressMessage = document.getElementById('progress-message');

    const percentage = Math.round(data.progress * 100);
    progressFill.style.width = `${percentage}%`;
    progressFill.textContent = `${percentage}%`;
    progressMessage.textContent = data.message || 'Processing...';
}

// Display Results
function displayResults(data) {
    hideProgress();

    const resultContent = document.getElementById('result-content');

    if (data.result.similarity_score !== undefined) {
        // Comparison results
        resultContent.innerHTML = `
            <div class="similarity-score">${(data.result.similarity_score * 100).toFixed(1)}%</div>
            <div class="interpretation">${data.result.interpretation}</div>

            <div class="result-section">
                <h3>Comparison Details</h3>
                <div class="result-item">
                    <span class="result-label">Confidence:</span>
                    <span class="result-value">${(data.result.confidence * 100).toFixed(1)}%</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Same Person Probability:</span>
                    <span class="result-value">${(data.result.same_person_probability * 100).toFixed(1)}%</span>
                </div>
            </div>

            <div class="result-section">
                <h3>Speaker 1 Quality</h3>
                ${renderQualityMetrics(data.result.quality_speaker1)}
            </div>

            <div class="result-section">
                <h3>Speaker 2 Quality</h3>
                ${renderQualityMetrics(data.result.quality_speaker2)}
            </div>
        `;
    } else {
        // Analysis results
        resultContent.innerHTML = `
            <div class="success">
                <strong>Analysis Complete!</strong><br>
                Voice profile created successfully.
            </div>

            <div class="result-section">
                <h3>Voice Profile</h3>
                <div class="result-item">
                    <span class="result-label">Videos Processed:</span>
                    <span class="result-value">${data.result.videos_processed}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Profile Samples:</span>
                    <span class="result-value">${data.result.speaker_profile.num_samples}</span>
                </div>
            </div>

            <div class="result-section">
                <h3>Audio Quality</h3>
                ${renderQualityMetrics(data.result.quality_metrics)}
            </div>
        `;
    }
}

// Render Quality Metrics
function renderQualityMetrics(quality) {
    const qualityLevel = quality.quality_level || 'unknown';
    const qualityClass = `quality-${qualityLevel}`;

    return `
        <div class="result-item">
            <span class="result-label">Quality Level:</span>
            <span class="result-value">
                <span class="${qualityClass} quality-badge">${qualityLevel.toUpperCase()}</span>
            </span>
        </div>
        <div class="result-item">
            <span class="result-label">Total Duration:</span>
            <span class="result-value">${quality.total_duration?.toFixed(1) || 0}s</span>
        </div>
        <div class="result-item">
            <span class="result-label">Speech Duration:</span>
            <span class="result-value">${quality.speech_duration?.toFixed(1) || 0}s</span>
        </div>
        <div class="result-item">
            <span class="result-label">Speech Ratio:</span>
            <span class="result-value">${((quality.speech_ratio || 0) * 100).toFixed(1)}%</span>
        </div>
        <div class="result-item">
            <span class="result-label">Average Quality Score:</span>
            <span class="result-value">${((quality.average_quality || 0) * 100).toFixed(1)}%</span>
        </div>
        <div class="result-item">
            <span class="result-label">Sufficient Data:</span>
            <span class="result-value">${quality.sufficient_data ? '✓ Yes' : '✗ No'}</span>
        </div>
    `;
}

// UI Helpers
function showResults() {
    document.getElementById('results').style.display = 'block';
    document.getElementById('result-content').innerHTML = '';
}

function showProgress(message) {
    document.getElementById('progress').style.display = 'block';
    document.getElementById('progress-message').textContent = message;
    document.getElementById('progress-fill').style.width = '0%';
}

function hideProgress() {
    document.getElementById('progress').style.display = 'none';
}

function showError(message) {
    hideProgress();
    showResults();
    document.getElementById('result-content').innerHTML = `
        <div class="error">
            <strong>Error:</strong> ${message}
        </div>
    `;
}

// Health check on load
window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) {
            console.warn('API health check failed');
        }
    } catch (error) {
        console.error('Could not connect to API:', error);
    }
});
