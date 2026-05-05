/**
 * CAPS Integration JavaScript Module
 * Handles JAMB Central Admissions Processing System operations
 */

class CAPSManager {
    constructor() {
        this.uploadPollingIntervals = new Map(); // Track multiple upload polls
        this.verificationInProgress = new Set(); // Track ongoing verifications
    }

    /**
     * Initialize CAPS functionality
     */
    init() {
        this.bindEvents();
        this.initializeTooltips();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Auto-refresh functionality
        const autoRefreshToggle = document.getElementById('autoRefreshToggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                this.toggleAutoRefresh(e.target.checked);
            });
        }

        // Search functionality
        const searchInputs = document.querySelectorAll('input[placeholder*="Search"]');
        searchInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.handleSearch(e.target);
            });
        });

        // Filter dropdowns
        const filterSelects = document.querySelectorAll('select[onchange*="filter"]');
        filterSelects.forEach(select => {
            select.addEventListener('change', (e) => {
                this.handleFilter(e.target);
            });
        });
    }

    /**
     * Initialize tooltips
     */
    initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Verify a single candidate against CAPS
     */
    async verifyCandidate(candidateId) {
        if (this.verificationInProgress.has(candidateId)) {
            this.showNotification('Verification already in progress', 'warning');
            return;
        }

        this.verificationInProgress.add(candidateId);
        this.updateCandidateRow(candidateId, 'verifying');

        try {
            const response = await fetch(`/admission/caps/verify/${candidateId}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.updateCandidateRow(candidateId, 'verified', result.verification);
                this.showNotification(result.message, 'success');
                
                // Update verification status in table
                this.updateVerificationStatus(candidateId, result.verification);
            } else {
                this.updateCandidateRow(candidateId, 'error');
                this.showNotification(result.message, 'danger');
            }
        } catch (error) {
            this.updateCandidateRow(candidateId, 'error');
            this.showNotification(`Verification failed: ${error.message}`, 'danger');
        } finally {
            this.verificationInProgress.delete(candidateId);
        }
    }

    /**
     * Bulk verify multiple candidates
     */
    async bulkVerifyCandidates(candidateIds) {
        if (candidateIds.length === 0) {
            this.showNotification('No candidates selected', 'warning');
            return;
        }

        if (candidateIds.some(id => this.verificationInProgress.has(id))) {
            this.showNotification('Some verifications already in progress', 'warning');
            return;
        }

        // Mark all as in progress
        candidateIds.forEach(id => this.verificationInProgress.add(id));
        candidateIds.forEach(id => this.updateCandidateRow(id, 'verifying'));

        try {
            const response = await fetch('/admission/caps/bulk-verify', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ candidate_ids: candidateIds })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(
                    `Successfully verified ${result.successful_verifications} candidates`,
                    'success'
                );
                
                // Update all candidate rows
                result.results.forEach(candidateResult => {
                    const row = document.querySelector(`tr[data-candidate-id="${candidateResult.candidate_id}"]`);
                    if (row) {
                        this.updateRowWithResult(row, candidateResult);
                    }
                });

                // Refresh page after a delay
                setTimeout(() => location.reload(), 2000);
            } else {
                this.showNotification(result.message, 'danger');
                candidateIds.forEach(id => {
                    this.verificationInProgress.delete(id);
                    this.updateCandidateRow(id, 'error');
                });
            }
        } catch (error) {
            this.showNotification(`Bulk verification failed: ${error.message}`, 'danger');
            candidateIds.forEach(id => {
                this.verificationInProgress.delete(id);
                this.updateCandidateRow(id, 'error');
            });
        }
    }

    /**
     * Upload admission list to CAPS
     */
    async uploadAdmissionList(programmeId) {
        try {
            this.showLoadingOverlay('Uploading admission list to CAPS...');

            const response = await fetch(`/admission/caps/upload/${programmeId}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                
                // Show tracking information
                this.showUploadTracking(result.upload_id, result.tracking_url);
                
                // Start polling for status
                this.pollUploadStatus(result.upload_id);
            } else {
                this.showNotification(result.message, 'danger');
            }
        } catch (error) {
            this.showNotification(`Upload failed: ${error.message}`, 'danger');
        } finally {
            this.hideLoadingOverlay();
        }
    }

    /**
     * Poll upload status
     */
    pollUploadStatus(uploadId, onUpdate = null) {
        if (this.uploadPollingIntervals.has(uploadId)) {
            return; // Already polling
        }

        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/admission/caps/status/${uploadId}`);
                const status = await response.json();

                if (onUpdate) {
                    onUpdate(status);
                }

                if (status.success && status.status.status === 'completed') {
                    clearInterval(this.uploadPollingIntervals.get(uploadId));
                    this.uploadPollingIntervals.delete(uploadId);
                    this.showNotification('Upload processing completed!', 'success');
                    setTimeout(() => location.reload(), 3000);
                } else if (!status.success) {
                    clearInterval(this.uploadPollingIntervals.get(uploadId));
                    this.uploadPollingIntervals.delete(uploadId);
                    this.showNotification(status.message, 'danger');
                }
            } catch (error) {
                console.error('Status polling error:', error);
            }
        }, 3000); // Poll every 3 seconds

        this.uploadPollingIntervals.set(uploadId, pollInterval);
    }

    /**
     * Simulate candidate acceptance
     */
    async simulateCandidateAcceptance(jambReg) {
        try {
            const response = await fetch(`/admission/caps/acceptance/${jambReg}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(
                    `Candidate ${jambReg}: ${result.acceptance.message}`,
                    result.acceptance.action === 'accepted' ? 'success' : 'info'
                );
                
                // Update candidate row
                this.updateAcceptanceStatus(jambReg, result.acceptance.action);
            } else {
                this.showNotification(result.message, 'danger');
            }
        } catch (error) {
            this.showNotification(`Failed to simulate acceptance: ${error.message}`, 'danger');
        }
    }

    /**
     * Sync all candidates to CAPS
     */
    async syncAllCandidates() {
        try {
            this.showLoadingOverlay('Syncing all candidates to CAPS...');

            const response = await fetch('/admission/caps/sync', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                setTimeout(() => location.reload(), 2000);
            } else {
                this.showNotification(result.message, 'danger');
            }
        } catch (error) {
            this.showNotification(`Sync failed: ${error.message}`, 'danger');
        } finally {
            this.hideLoadingOverlay();
        }
    }

    /**
     * Reset CAPS database
     */
    async resetCAPSDatabase() {
        if (!confirm('Reset CAPS mock database? This will clear all verification and upload data.')) {
            return;
        }

        try {
            const response = await fetch('/admission/caps/reset', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                setTimeout(() => location.reload(), 2000);
            } else {
                this.showNotification(result.message, 'danger');
            }
        } catch (error) {
            this.showNotification(`Reset failed: ${error.message}`, 'danger');
        }
    }

    /**
     * Update candidate row status
     */
    updateCandidateRow(candidateId, status, data = null) {
        const row = document.querySelector(`tr[data-candidate-id="${candidateId}"]`);
        if (!row) return;

        // Remove existing status classes
        row.classList.remove('table-warning', 'table-success', 'table-danger');

        switch (status) {
            case 'verifying':
                row.classList.add('table-warning');
                this.updateRowStatus(row, '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...');
                break;
            case 'verified':
                row.classList.add('table-success');
                this.updateRowStatus(row, '<i class="fa-solid fa-check-circle text-success"></i> Verified');
                if (data && data.verified) {
                    this.addVerificationBadge(row, 'success');
                } else {
                    this.addVerificationBadge(row, 'warning');
                }
                break;
            case 'error':
                row.classList.add('table-danger');
                this.updateRowStatus(row, '<i class="fa-solid fa-times-circle text-danger"></i> Error');
                break;
        }
    }

    /**
     * Update row with verification result
     */
    updateRowWithResult(row, result) {
        const statusCell = row.querySelector('.verification-status');
        if (statusCell) {
            if (result.verified) {
                statusCell.innerHTML = '<i class="fa-solid fa-check-circle text-success"></i> Verified';
                this.addVerificationBadge(row, 'success');
            } else {
                statusCell.innerHTML = '<i class="fa-solid fa-exclamation-triangle text-warning"></i> Queried';
                this.addVerificationBadge(row, 'warning');
            }
        }
    }

    /**
     * Update verification status cell
     */
    updateRowStatus(row, html) {
        const statusCell = row.querySelector('.verification-status');
        if (statusCell) {
            statusCell.innerHTML = html;
        }
    }

    /**
     * Add verification badge
     */
    addVerificationBadge(row, type) {
        const badgeClass = type === 'success' ? 'bg-success' : 'bg-warning';
        const badgeText = type === 'success' ? 'Verified' : 'Issues';
        
        // Remove existing badges
        const existingBadge = row.querySelector('.verification-badge');
        if (existingBadge) {
            existingBadge.remove();
        }
        
        // Add new badge
        const badge = document.createElement('span');
        badge.className = `badge ${badgeClass} verification-badge ms-2`;
        badge.textContent = badgeText;
        
        const statusCell = row.querySelector('.verification-status');
        if (statusCell) {
            statusCell.appendChild(badge);
        }
    }

    /**
     * Update acceptance status
     */
    updateAcceptanceStatus(jambReg, action) {
        const row = document.querySelector(`tr[data-jamb-reg="${jambReg}"]`);
        if (!row) return;

        const acceptanceCell = row.querySelector('.acceptance-status');
        if (acceptanceCell) {
            const statusClass = action === 'accepted' ? 'text-success' : 
                               action === 'pending' ? 'text-warning' : 'text-danger';
            const statusIcon = action === 'accepted' ? 'fa-check-circle' : 
                              action === 'pending' ? 'fa-clock' : 'fa-times-circle';
            
            acceptanceCell.innerHTML = `<i class="fa-solid ${statusIcon} ${statusClass}"></i> ${action}`;
        }
    }

    /**
     * Show upload tracking information
     */
    showUploadTracking(uploadId, trackingUrl) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Upload Tracking</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class="fa-solid fa-info-circle me-2"></i>
                            <strong>Upload ID:</strong> <code>${uploadId}</code>
                        </div>
                        <div class="mb-3">
                            <strong>Tracking URL:</strong><br>
                            <a href="${trackingUrl}" target="_blank" class="text-break">
                                ${trackingUrl}
                            </a>
                        </div>
                        <div class="mb-3">
                            <strong>Status:</strong> <span class="badge bg-secondary">Processing</span>
                        </div>
                        <p class="text-muted mb-0">
                            <small>This upload is being processed by JAMB CAPS. Status will be updated automatically.</small>
                        </p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        // Cleanup on modal hide
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    /**
     * Handle search functionality
     */
    handleSearch(input) {
        const searchTerm = input.value.toLowerCase();
        const table = input.closest('.card-body').querySelector('table');
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });

        // Update result count
        this.updateSearchResultCount(table, searchTerm);
    }

    /**
     * Handle filter functionality
     */
    handleFilter(select) {
        const filterValue = select.value.toLowerCase();
        const table = select.closest('.card-body').querySelector('table');
        if (!table) return;

        if (!filterValue) {
            // Show all rows
            table.querySelectorAll('tbody tr').forEach(row => {
                row.style.display = '';
            });
            return;
        }

        const columnIndex = select.getAttribute('data-column');
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const cell = row.querySelector(`td:nth-child(${columnIndex})`);
            if (cell) {
                const cellText = cell.textContent.toLowerCase();
                row.style.display = cellText.includes(filterValue) ? '' : 'none';
            }
        });
    }

    /**
     * Update search result count
     */
    updateSearchResultCount(table, searchTerm) {
        const visibleRows = Array.from(table.querySelectorAll('tbody tr')).filter(row => row.style.display !== 'none');
        const totalRows = table.querySelectorAll('tbody tr').length;

        // Remove existing count
        const existingCount = table.querySelector('.search-count');
        if (existingCount) {
            existingCount.remove();
        }

        // Add new count
        if (searchTerm) {
            const countDiv = document.createElement('div');
            countDiv.className = 'search-count small text-muted mt-2';
            countDiv.textContent = `Showing ${visibleRows.length} of ${totalRows} results`;
            table.parentNode.insertBefore(countDiv, table.nextSibling);
        }
    }

    /**
     * Toggle auto-refresh
     */
    toggleAutoRefresh(enabled) {
        if (enabled) {
            // Start auto-refresh every 30 seconds
            this.autoRefreshInterval = setInterval(() => {
                location.reload();
            }, 30000);
            this.showNotification('Auto-refresh enabled', 'info');
        } else {
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
                this.showNotification('Auto-refresh disabled', 'info');
            }
        }
    }

    /**
     * Show loading overlay
     */
    showLoadingOverlay(message = 'Processing...') {
        const overlay = document.createElement('div');
        overlay.id = 'capsLoadingOverlay';
        overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        overlay.style.cssText = `
            background: rgba(0,0,0,0.7);
            z-index: 9999;
            backdrop-filter: blur(5px);
        `;
        overlay.innerHTML = `
            <div class="bg-white p-4 rounded-3 text-center">
                <div class="fa-solid fa-spinner fa-spin fa-3x mb-3"></div>
                <h5>${message}</h5>
            </div>
        `;

        document.body.appendChild(overlay);
    }

    /**
     * Hide loading overlay
     */
    hideLoadingOverlay() {
        const overlay = document.getElementById('capsLoadingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Clear polling intervals
        this.uploadPollingIntervals.forEach(interval => clearInterval(interval));
        this.uploadPollingIntervals.clear();
        
        // Clear verification tracking
        this.verificationInProgress.clear();
        
        // Clear auto-refresh
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
    }
}

// Global functions for template compatibility
window.verifyCandidate = function(candidateId) {
    window.capsManager.verifyCandidate(candidateId);
};

window.bulkVerifyCandidates = function(candidateIds) {
    window.capsManager.bulkVerifyCandidates(candidateIds);
};

window.uploadAdmissionList = function(programmeId) {
    window.capsManager.uploadAdmissionList(programmeId);
};

window.simulateCandidateAcceptance = function(jambReg) {
    window.capsManager.simulateCandidateAcceptance(jambReg);
};

window.syncAllCandidates = function() {
    window.capsManager.syncAllCandidates();
};

window.resetCAPSDatabase = function() {
    window.capsManager.resetCAPSDatabase();
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.capsManager = new CAPSManager();
    window.capsManager.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.capsManager) {
        window.capsManager.cleanup();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+V: Verify selected candidates
    if (e.ctrlKey && e.key === 'v') {
        e.preventDefault();
        const selectedIds = window.getSelectedCandidateIds ? window.getSelectedCandidateIds() : [];
        if (selectedIds.length > 0) {
            window.bulkVerifyCandidates(selectedIds);
        }
    }
    
    // Ctrl+U: Upload to CAPS
    if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        const programmeId = window.getCurrentProgrammeId ? window.getCurrentProgrammeId() : null;
        if (programmeId) {
            window.uploadAdmissionList(programmeId);
        }
    }
    
    // Ctrl+R: Refresh
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        location.reload();
    }
});
