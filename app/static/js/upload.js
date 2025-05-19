/**
 * JavaScript for file upload functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const fileLabel = document.getElementById('file-label');
    const uploadProgress = document.getElementById('upload-progress');
    const uploadStatus = document.getElementById('upload-status');
    const transcribeBtn = document.getElementById('transcribe-btn');
    const errorAlert = document.getElementById('error-alert');
    
    let jobId = null;
    let statusCheckInterval = null;
    
    // Update file label when file is selected
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                fileLabel.textContent = fileInput.files[0].name;
            } else {
                fileLabel.textContent = 'Choose audio file...';
            }
        });
    }
    
    // Handle file upload
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Validate file
            if (!fileInput.files.length) {
                showError('Please select an audio file to upload');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Check file type (audio files only)
            if (!file.type.startsWith('audio/')) {
                showError('Please select an audio file (WAV, MP3, etc.)');
                return;
            }
            
            // Show progress bar
            uploadProgress.classList.remove('d-none');
            uploadStatus.textContent = 'Uploading...';
            
            // Create form data
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                // Upload file
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`Upload failed: ${response.statusText}`);
                }
                
                const data = await response.json();
                jobId = data.job_id;
                
                // Update UI
                uploadStatus.textContent = 'Upload complete!';
                uploadProgress.querySelector('.progress-bar').style.width = '100%';
                
                // Enable transcribe button
                transcribeBtn.classList.remove('d-none');
                transcribeBtn.dataset.jobId = jobId;
                
            } catch (error) {
                console.error('Upload error:', error);
                showError(`Upload failed: ${error.message}`);
                
                // Reset progress
                uploadProgress.classList.add('d-none');
                uploadStatus.textContent = '';
            }
        });
    }
    
    // Handle transcribe button click
    if (transcribeBtn) {
        transcribeBtn.addEventListener('click', async function() {
            // Get job ID
            const jobId = transcribeBtn.dataset.jobId;
            if (!jobId) {
                showError('No job ID found, please upload a file first');
                return;
            }
            
            // Disable button
            transcribeBtn.disabled = true;
            transcribeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            
            try {
                // Start transcription
                const response = await fetch(`/api/transcribe/${jobId}`, {
                    method: 'POST'
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to start transcription: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // Start checking status
                    startStatusCheck(jobId);
                } else {
                    throw new Error(data.message || 'Failed to start transcription');
                }
                
            } catch (error) {
                console.error('Transcription error:', error);
                showError(`Transcription failed: ${error.message}`);
                
                // Reset button
                transcribeBtn.disabled = false;
                transcribeBtn.innerHTML = 'Start Transcription';
            }
        });
    }
    
    // Function to check job status
    function startStatusCheck(jobId) {
        // Clear any existing interval
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        
        // Create progress container if not exists
        let progressContainer = document.getElementById('progress-container');
        if (!progressContainer) {
            progressContainer = document.createElement('div');
            progressContainer.id = 'progress-container';
            progressContainer.classList.add('mt-4');
            progressContainer.innerHTML = `
                <h5>Transcription Progress</h5>
                <div class="progress">
                    <div id="transcription-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <p id="transcription-status" class="mt-2">Starting transcription...</p>
            `;
            
            uploadForm.parentNode.appendChild(progressContainer);
        }
        
        const progressBar = document.getElementById('transcription-progress-bar');
        const statusText = document.getElementById('transcription-status');
        
        // Start checking status
        statusCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                if (!response.ok) {
                    throw new Error(`Status check failed: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                // Update progress
                if (data.progress) {
                    const progress = Math.round(data.progress);
                    progressBar.style.width = `${progress}%`;
                    progressBar.setAttribute('aria-valuenow', progress);
                }
                
                // Update status text
                statusText.textContent = `Status: ${data.status}`;
                
                // Check if completed or failed
                if (data.status === 'completed') {
                    clearInterval(statusCheckInterval);
                    statusText.textContent = 'Transcription completed successfully!';
                    
                    // Redirect to results page
                    window.location.href = `/results/${jobId}`;
                    
                } else if (data.status === 'failed') {
                    clearInterval(statusCheckInterval);
                    showError('Transcription failed. Please try again.');
                    
                    // Reset button
                    transcribeBtn.disabled = false;
                    transcribeBtn.innerHTML = 'Start Transcription';
                }
                
            } catch (error) {
                console.error('Status check error:', error);
                // Don't stop the interval for transient errors
            }
        }, 2000); // Check every 2 seconds
    }
    
    // Function to show error message
    function showError(message) {
        if (errorAlert) {
            errorAlert.textContent = message;
            errorAlert.classList.remove('d-none');
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorAlert.classList.add('d-none');
            }, 5000);
        }
    }
});
