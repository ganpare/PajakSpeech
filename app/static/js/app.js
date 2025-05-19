/**
 * Main application JavaScript
 */

// Utility to format time in seconds to HH:MM:SS.mmm format
function formatTime(seconds) {
    if (isNaN(seconds)) return "00:00:00.000";
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds - Math.floor(seconds)) * 1000);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}

// Handle audio segment playback
function playAudioSegment(jobId, startTime, endTime) {
    const audioPlayer = document.getElementById('segment-player');
    if (!audioPlayer) return;
    
    // Update audio source with the segment
    const audioUrl = `/api/segment_audio/${jobId}?start_time=${startTime}&end_time=${endTime}`;
    audioPlayer.src = audioUrl;
    
    // Play the audio
    audioPlayer.play().catch(error => {
        console.error('Error playing audio segment:', error);
    });
}

// Setup popovers and tooltips (Bootstrap)
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
