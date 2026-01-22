// Button state management patch
// This file adds proper button state management based on backend status

// Function to update control buttons based on bot status
window.updateButtonStates = function(status) {
    const startBtn = document.getElementById('btn-start');
    const pauseBtn = document.getElementById('btn-pause');
    const stopBtn = document.getElementById('btn-stop');
    
    if (!startBtn || !pauseBtn || !stopBtn) return;
    
    const botStatus = status ? status.toUpperCase() : 'STOPPED';
    
    // START button: enabled only when STOPPED
    startBtn.disabled = botStatus !== 'STOPPED';
    
    // PAUSE button: enabled only when RUNNING
    pauseBtn.disabled = botStatus !== 'RUNNING';
    
    // STOP button: enabled when RUNNING or PAUSED
    stopBtn.disabled = botStatus === 'STOPPED';
};

// Patch the updateDashboard function to call updateButtonStates
(function() {
    const originalFetch = window.fetchAPI;
    if (!originalFetch) return;
    
    // Call updateButtonStates whenever status is updated
    const observer = new MutationObserver((mutations) => {
        const statusBadge = document.getElementById('status-badge');
        if (statusBadge) {
            const text = statusBadge.textContent;
            let status = 'STOPPED';
            if (text.includes('RUNNING')) status = 'RUNNING';
            else if (text.includes('PAUSED')) status = 'PAUSED';
            window.updateButtonStates(status);
        }
    });
    
    const statusBadge = document.getElementById('status-badge');
    if (statusBadge) {
        observer.observe(statusBadge, { childList: true, characterData: true, subtree: true });
    }
    
    // Initial state
    setTimeout(() => {
        const statusBadge = document.getElementById('status-badge');
        if (statusBadge) {
            const text = statusBadge.textContent;
            let status = 'STOPPED';
            if (text.includes('RUNNING'))  status = 'RUNNING';
            else if (text.includes('PAUSED')) status = 'PAUSED';
            window.updateButtonStates(status);
        }
    }, 500);
})();
