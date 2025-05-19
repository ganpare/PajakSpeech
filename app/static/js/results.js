/**
 * JavaScript for results page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    const jobId = document.getElementById('results-container')?.dataset.jobId;
    const resultsContainer = document.getElementById('results-content');
    const segmentsContainer = document.getElementById('segments-container');
    const wordsContainer = document.getElementById('words-container');
    const loadingSpinner = document.getElementById('loading-spinner');
    const errorAlert = document.getElementById('error-alert');
    
    // Start polling for status if job is not completed
    if (jobId) {
        fetchJobStatus();
    }
    
    /**
     * Fetch job status and results
     */
    function fetchJobStatus() {
        fetch(`/api/status/${jobId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Status check failed: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                // Update status display
                const statusBadge = document.getElementById('status-badge');
                if (statusBadge) {
                    statusBadge.textContent = data.status;
                    
                    // Update badge color based on status
                    statusBadge.className = 'badge';
                    if (data.status === 'completed') {
                        statusBadge.classList.add('bg-success');
                        // Fetch results
                        fetchResults();
                    } else if (data.status === 'failed') {
                        statusBadge.classList.add('bg-danger');
                        showError('Transcription failed. Please try again.');
                        hideLoading();
                    } else {
                        statusBadge.classList.add('bg-info');
                        
                        // Update progress if available
                        if (data.progress) {
                            const progressBar = document.getElementById('progress-bar');
                            if (progressBar) {
                                const progress = Math.round(data.progress);
                                progressBar.style.width = `${progress}%`;
                                progressBar.setAttribute('aria-valuenow', progress);
                                progressBar.textContent = `${progress}%`;
                            }
                        }
                        
                        // Continue polling
                        setTimeout(fetchJobStatus, 2000);
                    }
                }
            })
            .catch(error => {
                console.error('Status check error:', error);
                showError(`Error checking status: ${error.message}`);
                hideLoading();
            });
    }
    
    /**
     * Fetch transcription results
     */
    function fetchResults() {
        fetch(`/api/results/${jobId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch results: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Display results
                    displayResults(data.results);
                    
                    // Show download links
                    const downloadSection = document.getElementById('download-section');
                    if (downloadSection) {
                        downloadSection.classList.remove('d-none');
                    }
                    
                    // Hide loading spinner
                    hideLoading();
                } else {
                    throw new Error(data.message || 'Failed to retrieve results');
                }
            })
            .catch(error => {
                console.error('Results fetch error:', error);
                showError(`Error fetching results: ${error.message}`);
                hideLoading();
            });
    }
    
    /**
     * Display transcription results
     */
    function displayResults(results) {
        // Make sure we have segments
        if (!results || !results.segments || results.segments.length === 0) {
            showError('No transcription segments found in results');
            return;
        }
        
        // Display segments
        if (segmentsContainer) {
            segmentsContainer.innerHTML = renderSegmentsTable(results.segments);
            segmentsContainer.classList.remove('d-none');
        }
        
        // Display words if they exist
        const hasWords = results.segments.some(segment => segment.words && segment.words.length > 0);
        if (hasWords && wordsContainer) {
            wordsContainer.innerHTML = renderWordsView(results.segments);
            wordsContainer.classList.remove('d-none');
        }
        
        // Add event listeners for segment playback
        document.querySelectorAll('.play-segment').forEach(button => {
            button.addEventListener('click', function() {
                const startTime = parseFloat(this.dataset.start);
                const endTime = parseFloat(this.dataset.end);
                playAudioSegment(jobId, startTime, endTime);
            });
        });
    }
    
    /**
     * Render segments table
     */
    function renderSegmentsTable(segments) {
        let html = `
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Start Time</th>
                        <th>End Time</th>
                        <th>Duration</th>
                        <th>Text</th>
                        <th>Play</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        segments.forEach((segment, index) => {
            const duration = (segment.end - segment.start).toFixed(2);
            
            html += `
                <tr>
                    <td>${index + 1}</td>
                    <td>${formatTime(segment.start)}</td>
                    <td>${formatTime(segment.end)}</td>
                    <td>${duration}s</td>
                    <td>${segment.text}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary play-segment" 
                                data-start="${segment.start}" 
                                data-end="${segment.end}"
                                title="Play segment">
                            <i class="bi bi-play-fill"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
        `;
        
        return html;
    }
    
    /**
     * Render words visualization
     */
    function renderWordsView(segments) {
        let html = `<div class="word-timeline">`;
        
        segments.forEach(segment => {
            if (segment.words && segment.words.length > 0) {
                html += `<div class="segment-words mb-2">`;
                
                // Add segment start time
                html += `<small class="text-muted me-2">${formatTime(segment.start)}</small>`;
                
                // Add words
                segment.words.forEach(word => {
                    html += `
                        <span class="word-item" 
                              data-start="${word.start}" 
                              data-end="${word.end}"
                              onclick="playAudioSegment('${jobId}', ${word.start}, ${word.end})">
                            ${word.word}
                        </span>
                    `;
                });
                
                // Add segment end time
                html += `<small class="text-muted ms-2">${formatTime(segment.end)}</small>`;
                
                html += `</div>`;
            }
        });
        
        html += `</div>`;
        return html;
    }
    
    /**
     * Hide loading spinner
     */
    function hideLoading() {
        if (loadingSpinner) {
            loadingSpinner.classList.add('d-none');
        }
    }
    
    /**
     * Show error message
     */
    function showError(message) {
        if (errorAlert) {
            errorAlert.textContent = message;
            errorAlert.classList.remove('d-none');
        }
    }
    
    /**
     * Initialize download buttons
     */
    document.querySelectorAll('.download-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const format = this.dataset.format;
            window.location.href = `/api/download/${jobId}/${format}`;
        });
    });
});
