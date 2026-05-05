/**
 * Batch Screening JavaScript Module
 * Handles batch screening operations, progress monitoring, and UI interactions
 */

class BatchScreener {
    constructor() {
        this.selectedIds = new Set();
        this.currentBatchId = null;
        this.progressInterval = null;
        this.logInterval = null;
        this.startTime = null;
    }

    /**
     * Initialize batch screening functionality
     */
    init() {
        this.bindEvents();
        this.updateSelectionCount();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Checkbox events
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('candidate-checkbox')) {
                this.handleCheckboxChange(e.target);
            }
        });

        // Select all checkbox
        const selectAllCheckbox = document.getElementById('selectAllCandidates');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', () => this.toggleAllCandidates());
        }

        // Header checkbox
        const headerCheckbox = document.getElementById('headerCheckbox');
        if (headerCheckbox) {
            headerCheckbox.addEventListener('change', () => this.toggleAllFromHeader());
        }

        // Cancel button
        const cancelBtn = document.getElementById('cancelScreening');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.cancelScreening());
        }
    }

    /**
     * Handle individual checkbox change
     */
    handleCheckboxChange(checkbox) {
        const candidateId = parseInt(checkbox.value);
        
        if (checkbox.checked) {
            this.selectedIds.add(candidateId);
        } else {
            this.selectedIds.delete(candidateId);
        }
        
        this.updateSelectionCount();
        this.updateHeaderCheckbox();
    }

    /**
     * Toggle all candidates selection
     */
    toggleAllCandidates() {
        const selectAll = document.getElementById('selectAllCandidates');
        const checkboxes = document.querySelectorAll('.candidate-checkbox');
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = selectAll.checked;
            const candidateId = parseInt(checkbox.value);
            
            if (selectAll.checked) {
                this.selectedIds.add(candidateId);
            } else {
                this.selectedIds.delete(candidateId);
            }
        });
        
        this.updateSelectionCount();
        this.updateHeaderCheckbox();
    }

    /**
     * Toggle selection from header checkbox
     */
    toggleAllFromHeader() {
        const headerCheckbox = document.getElementById('headerCheckbox');
        const selectAllCheckbox = document.getElementById('selectAllCandidates');
        
        selectAllCheckbox.checked = headerCheckbox.checked;
        this.toggleAllCandidates();
    }

    /**
     * Update selection count display
     */
    updateSelectionCount() {
        const checkboxes = document.querySelectorAll('.candidate-checkbox:checked');
        this.selectedIds.clear();
        checkboxes.forEach(cb => this.selectedIds.add(parseInt(cb.value)));
        
        const count = this.selectedIds.size;
        const countBadge = document.getElementById('selectionCount');
        const screenBtn = document.getElementById('screenSelectedBtn');
        
        if (countBadge) countBadge.textContent = `${count} selected`;
        if (screenBtn) screenBtn.disabled = count === 0;
        
        this.updateHeaderCheckbox();
    }

    /**
     * Update header checkbox state
     */
    updateHeaderCheckbox() {
        const headerCheckbox = document.getElementById('headerCheckbox');
        const allCheckboxes = document.querySelectorAll('.candidate-checkbox');
        const checkedCheckboxes = document.querySelectorAll('.candidate-checkbox:checked');
        
        if (!headerCheckbox || allCheckboxes.length === 0) return;
        
        if (checkedCheckboxes.length === 0) {
            headerCheckbox.checked = false;
            headerCheckbox.indeterminate = false;
        } else if (checkedCheckboxes.length === allCheckboxes.length) {
            headerCheckbox.checked = true;
            headerCheckbox.indeterminate = false;
        } else {
            headerCheckbox.checked = false;
            headerCheckbox.indeterminate = true;
        }
    }

    /**
     * Run batch screening on selected candidates
     */
    async runScreening(candidateIds = null) {
        const idsToScreen = candidateIds || Array.from(this.selectedIds);
        
        if (idsToScreen.length === 0) {
            this.showAlert('Please select at least one candidate to screen.', 'warning');
            return;
        }
        
        try {
            this.showProgressModal();
            this.startTime = Date.now();
            
            // Start screening via API
            const response = await fetch('/api/admission/screen', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    candidate_ids: idsToScreen
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentBatchId = result.batch_id;
                this.startProgressMonitoring();
                this.addLogEntry('info', 'Screening started successfully');
            } else {
                throw new Error(result.message || 'Screening failed to start');
            }
            
        } catch (error) {
            console.error('Screening error:', error);
            this.hideProgressModal();
            this.showAlert('Screening failed: ' + error.message, 'danger');
        }
    }

    /**
     * Start monitoring screening progress
     */
    startProgressMonitoring() {
        if (!this.currentBatchId) return;
        
        this.progressInterval = setInterval(() => this.updateProgress(), 1000);
        this.logInterval = setInterval(() => this.updateLogs(), 2000);
        
        // Initial updates
        this.updateProgress();
        this.updateLogs();
    }

    /**
     * Update progress display
     */
    async updateProgress() {
        if (!this.currentBatchId) return;
        
        try {
            const response = await fetch(`/admission/screening/status/${this.currentBatchId}`);
            const status = await response.json();
            
            if (response.ok) {
                this.updateProgressUI(status);
                
                if (status.status === 'completed') {
                    this.completeScreening();
                }
            } else {
                throw new Error(status.message || 'Failed to get status');
            }
        } catch (error) {
            console.error('Progress update error:', error);
            this.addLogEntry('error', 'Failed to update progress: ' + error.message);
        }
    }

    /**
     * Update progress UI elements
     */
    updateProgressUI(status) {
        const progressBar = document.getElementById('progressBar');
        const progressPercent = document.getElementById('progressPercent');
        const progressText = document.getElementById('progressText');
        const processedCount = document.getElementById('processedCount');
        const totalCount = document.getElementById('totalCount');
        const timeRemaining = document.getElementById('timeRemaining');
        
        // Update progress bar
        if (progressBar) {
            progressBar.style.width = `${status.progress_percent}%`;
            progressBar.setAttribute('aria-valuenow', status.progress_percent);
        }
        
        if (progressPercent) progressPercent.textContent = `${Math.round(status.progress_percent)}%`;
        if (progressText) progressText.textContent = status.message;
        if (processedCount) processedCount.textContent = status.processed;
        if (totalCount) totalCount.textContent = status.total_candidates;
        
        // Calculate and update time remaining
        if (timeRemaining && status.processed < status.total_candidates && status.processed > 0) {
            const remaining = status.total_candidates - status.processed;
            const elapsedTime = (Date.now() - this.startTime) / 1000;
            const rate = status.processed / elapsedTime;
            const etaSeconds = Math.ceil(remaining / rate);
            
            timeRemaining.textContent = this.formatTimeRemaining(etaSeconds);
        } else if (timeRemaining && status.processed >= status.total_candidates) {
            timeRemaining.textContent = 'Completed';
        }
        
        // Update status alert
        this.updateStatusAlert(status);
    }

    /**
     * Update status alert styling
     */
    updateStatusAlert(status) {
        const statusAlert = document.getElementById('statusMessage');
        const statusText = document.getElementById('statusText');
        
        if (!statusAlert || !statusText) return;
        
        statusAlert.className = 'alert alert-info';
        
        if (status.status === 'completed') {
            statusAlert.className = 'alert alert-success';
            statusText.innerHTML = '<i class="fa-solid fa-check-circle me-2"></i>Screening completed successfully!';
        } else if (status.progress_percent > 75) {
            statusAlert.className = 'alert alert-warning';
        }
    }

    /**
     * Format time remaining display
     */
    formatTimeRemaining(seconds) {
        if (seconds < 60) {
            return `${seconds} seconds`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }

    /**
     * Update screening logs
     */
    async updateLogs() {
        if (!this.currentBatchId) return;
        
        try {
            const response = await fetch(`/api/admission/logs/${this.currentBatchId}`);
            const logs = await response.json();
            
            if (response.ok && logs.logs) {
                this.displayLogs(logs.logs);
            }
        } catch (error) {
            console.error('Log update error:', error);
        }
    }

    /**
     * Display log entries
     */
    displayLogs(logs) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;
        
        logContainer.innerHTML = logs.map(log => 
            `<div class="text-${log.level || 'muted'} small mb-1">
                [${new Date(log.timestamp).toLocaleTimeString()}] ${log.message}
            </div>`
        ).join('');
        
        // Auto-scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    /**
     * Add log entry
     */
    addLogEntry(level, message) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;
        
        const logEntry = document.createElement('div');
        logEntry.className = `text-${level} small mb-1`;
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    /**
     * Complete screening process
     */
    completeScreening() {
        clearInterval(this.progressInterval);
        clearInterval(this.logInterval);
        
        this.addLogEntry('success', 'Screening completed successfully!');
        
        setTimeout(() => {
            this.hideProgressModal();
            window.location.href = `/admission/screening/results/${this.currentBatchId}`;
        }, 2000);
    }

    /**
     * Cancel screening process
     */
    cancelScreening() {
        if (!confirm('Are you sure you want to cancel the screening process?')) {
            return;
        }
        
        this.hideProgressModal();
        this.cleanup();
    }

    /**
     * Show progress modal
     */
    showProgressModal() {
        const modal = new bootstrap.Modal(document.getElementById('progressModal'));
        modal.show();
        
        // Reset progress display
        this.updateProgressUI({
            progress_percent: 0,
            message: 'Starting screening...',
            processed: 0,
            total_candidates: 0,
            status: 'processing'
        });
    }

    /**
     * Hide progress modal
     */
    hideProgressModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
        if (modal) modal.hide();
    }

    /**
     * Cleanup intervals and reset state
     */
    cleanup() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        if (this.logInterval) {
            clearInterval(this.logInterval);
            this.logInterval = null;
        }
        
        this.currentBatchId = null;
        this.startTime = null;
    }

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.content : '';
    }

    /**
     * Show alert message
     */
    showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container-fluid');
        if (container) {
            container.prepend(alertDiv);
        }
    }

    /**
     * Export selected candidates
     */
    exportSelected() {
        if (this.selectedIds.size === 0) {
            this.showAlert('Please select candidates to export.', 'warning');
            return;
        }
        
        // Create form for export
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/admin/candidates';
        
        // Add CSRF token
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = this.getCSRFToken();
        form.appendChild(csrfInput);
        
        // Add export flag
        const exportInput = document.createElement('input');
        exportInput.type = 'hidden';
        exportInput.name = 'export';
        exportInput.value = 'csv';
        form.appendChild(exportInput);
        
        // Add candidate IDs
        this.selectedIds.forEach(id => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'candidate_ids';
            input.value = id;
            form.appendChild(input);
        });
        
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }
}

// Global functions for template compatibility
window.toggleAllCandidates = function() {
    window.batchScreener.toggleAllCandidates();
};

window.toggleAllFromHeader = function() {
    window.batchScreener.toggleAllFromHeader();
};

window.updateSelectionCount = function() {
    window.batchScreener.updateSelectionCount();
};

window.screenSelected = function() {
    window.batchScreener.runScreening();
};

window.screenAllEligible = function() {
    if (!confirm('Screen all eligible candidates on this page? This may take several minutes.')) {
        return;
    }
    
    // Get all candidate IDs on current page
    const allCheckboxes = document.querySelectorAll('.candidate-checkbox');
    const allIds = Array.from(allCheckboxes).map(cb => parseInt(cb.value));
    
    window.batchScreener.runScreening(allIds);
};

window.screenSingle = function(candidateId) {
    window.batchScreener.runScreening([candidateId]);
};

window.exportSelected = function() {
    window.batchScreener.exportSelected();
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.batchScreener = new BatchScreener();
    window.batchScreener.init();
});
