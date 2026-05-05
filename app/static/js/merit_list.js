/**
 * Merit List Management JavaScript Module
 * Handles tab switching, real-time updates, and merit list interactions
 */

class MeritListManager {
    constructor() {
        this.currentProgrammeId = null;
        this.currentQuota = 'merit';
        this.autoRefreshInterval = null;
        this.searchTimeout = null;
    }

    /**
     * Initialize merit list functionality
     */
    init() {
        this.bindEvents();
        this.initializeTabs();
        this.startAutoRefresh();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Tab switching
        const quotaTabs = document.querySelectorAll('#quotaTabs button[data-bs-toggle="tab"]');
        quotaTabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.handleTabSwitch(e.target.id);
            });
        });

        // Search functionality
        const searchInputs = document.querySelectorAll('input[placeholder*="Search"]');
        searchInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.handleSearch(e.target);
            });
        });

        // Export buttons
        const exportButtons = document.querySelectorAll('[onclick*="exportMeritList"]');
        exportButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.handleExport(e);
            });
        });

        // Refresh buttons
        const refreshButtons = document.querySelectorAll('[onclick*="refresh"]');
        refreshButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.handleRefresh(e);
            });
        });

        // Finalize modal
        const finalizeModal = document.getElementById('finalizeModal');
        if (finalizeModal) {
            finalizeModal.addEventListener('show.bs.modal', () => {
                this.showFinalizeWarning();
            });
        }
    }

    /**
     * Initialize tab functionality
     */
    initializeTabs() {
        // Restore active tab from localStorage
        const activeTab = localStorage.getItem('activeMeritTab');
        if (activeTab) {
            const tabButton = document.getElementById(activeTab);
            if (tabButton) {
                const tab = new bootstrap.Tab(tabButton);
                tab.show();
            }
        }
    }

    /**
     * Handle tab switching
     */
    handleTabSwitch(tabId) {
        this.currentQuota = tabId.replace('-tab', '');
        localStorage.setItem('activeMeritTab', tabId);
        
        // Clear search when switching tabs
        const activeSearchInput = document.querySelector('.tab-pane.show input[placeholder*="Search"]');
        if (activeSearchInput) {
            activeSearchInput.value = '';
            this.filterTable('', activeSearchInput);
        }
        
        // Update export button context
        this.updateExportButtons();
    }

    /**
     * Handle search functionality
     */
    handleSearch(input) {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.filterTable(input.value, input);
        }, 300);
    }

    /**
     * Filter table rows based on search term
     */
    filterTable(searchTerm, input) {
        const table = input.closest('.tab-pane').querySelector('table');
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');
        const lowerSearchTerm = searchTerm.toLowerCase();

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const shouldShow = !searchTerm || text.includes(lowerSearchTerm);
            row.style.display = shouldShow ? '' : 'none';
        });

        // Update result count
        this.updateResultCount(table, searchTerm);
    }

    /**
     * Update result count display
     */
    updateResultCount(table, searchTerm) {
        const visibleRows = table.querySelectorAll('tbody tr:not([style*="display: none"])');
        const totalRows = table.querySelectorAll('tbody tr');
        
        // Update or create result count element
        let resultCount = table.querySelector('.search-results');
        if (!resultCount) {
            resultCount = document.createElement('div');
            resultCount.className = 'search-results small text-muted mt-2';
            table.parentNode.insertBefore(resultCount, table.nextSibling);
        }
        
        if (searchTerm) {
            resultCount.textContent = `Showing ${visibleRows.length} of ${totalRows.length} results`;
        } else {
            resultCount.textContent = '';
        }
    }

    /**
     * Handle export functionality
     */
    handleExport(e) {
        const button = e.currentTarget;
        const quota = button.getAttribute('onclick').match(/exportMeritList\('([^']*)'\)/)?.[1];
        
        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Exporting...';
        button.disabled = true;

        // Perform export
        const url = `/admission/merit-list/${this.getCurrentProgrammeId()}/export${quota ? '?quota=' + quota : ''}`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) throw new Error('Export failed');
                return response.blob();
            })
            .then(blob => {
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = this.getExportFilename(quota);
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(downloadUrl);
                document.body.removeChild(a);
                
                this.showNotification('Export completed successfully!', 'success');
            })
            .catch(error => {
                console.error('Export error:', error);
                this.showNotification('Export failed: ' + error.message, 'danger');
            })
            .finally(() => {
                // Restore button state
                button.innerHTML = originalText;
                button.disabled = false;
            });
    }

    /**
     * Get export filename
     */
    getExportFilename(quota) {
        const programmeName = document.querySelector('h1').textContent.split(' Merit List')[0].trim();
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        return `${programmeName}_${quota || 'full'}_merit_list_${timestamp}.xlsx`;
    }

    /**
     * Handle refresh functionality
     */
    handleRefresh(e) {
        const button = e.currentTarget;
        const originalText = button.innerHTML;
        
        // Show loading state
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Refreshing...';
        button.disabled = true;

        // Refresh the page
        setTimeout(() => {
            location.reload();
        }, 500);
    }

    /**
     * Show finalize warning
     */
    showFinalizeWarning() {
        const modal = document.getElementById('finalizeModal');
        const warningDiv = modal.querySelector('.alert-warning');
        
        // Add dynamic information
        const stats = this.getCurrentStatistics();
        if (stats) {
            const additionalInfo = document.createElement('div');
            additionalInfo.className = 'mt-2';
            additionalInfo.innerHTML = `
                <strong>Current Status:</strong><br>
                - ${stats.filled} slots filled out of ${stats.total_slots}<br>
                - ${stats.available} slots still available<br>
                - ${stats.total_recommended} candidates recommended
            `;
            warningDiv.appendChild(additionalInfo);
        }
    }

    /**
     * Get current programme ID
     */
    getCurrentProgrammeId() {
        if (!this.currentProgrammeId) {
            // Extract from URL
            const pathParts = window.location.pathname.split('/');
            const programmeIndex = pathParts.indexOf('merit-list');
            if (programmeIndex !== -1 && pathParts[programmeIndex + 1]) {
                this.currentProgrammeId = pathParts[programmeIndex + 1];
            }
        }
        return this.currentProgrammeId;
    }

    /**
     * Get current statistics
     */
    getCurrentStatistics() {
        // Extract statistics from the page
        const statsCards = document.querySelectorAll('.card-body .h4');
        if (statsCards.length >= 4) {
            return {
                total_slots: parseInt(statsCards[0].textContent),
                filled: parseInt(statsCards[1].textContent),
                available: parseInt(statsCards[2].textContent),
                total_recommended: parseInt(statsCards[3].textContent)
            };
        }
        return null;
    }

    /**
     * Update export buttons context
     */
    updateExportButtons() {
        const exportButtons = document.querySelectorAll('[onclick*="exportMeritList"]');
        exportButtons.forEach(button => {
            const onclick = button.getAttribute('onclick');
            if (onclick && !onclick.includes(this.currentQuota)) {
                button.setAttribute('onclick', onclick.replace(/exportMeritList\([^)]*\)/, `exportMeritList('${this.currentQuota}')`));
            }
        });
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        // Auto-refresh every 5 minutes
        this.autoRefreshInterval = setInterval(() => {
            this.refreshData();
        }, 300000);
    }

    /**
     * Refresh data without full page reload
     */
    async refreshData() {
        try {
            const programmeId = this.getCurrentProgrammeId();
            const response = await fetch(`/api/admission/status/${programmeId}`);
            
            if (response.ok) {
                const data = await response.json();
                this.updateStatistics(data);
                this.showNotification('Data refreshed', 'info');
            }
        } catch (error) {
            console.error('Auto-refresh error:', error);
        }
    }

    /**
     * Update statistics on page
     */
    updateStatistics(data) {
        // Update statistics cards
        const statsCards = document.querySelectorAll('.card-body .h4');
        if (statsCards.length >= 4 && data.statistics) {
            statsCards[0].textContent = data.statistics.total_slots;
            statsCards[1].textContent = data.statistics.filled;
            statsCards[2].textContent = data.statistics.available;
            statsCards[3].textContent = data.statistics.total_recommended;
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
     * Cleanup resources
     */
    cleanup() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
    }
}

// Global functions for template compatibility
window.exportMeritList = function(quota) {
    window.meritListManager.handleExport({ currentTarget: { getAttribute: () => null } });
};

window.refreshTable = function() {
    window.meritListManager.handleRefresh({ currentTarget: { innerHTML: '' } });
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.meritListManager = new MeritListManager();
    window.meritListManager.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.meritListManager) {
        window.meritListManager.cleanup();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+E: Export
    if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        const exportButton = document.querySelector('button[onclick*="exportMeritList"]');
        if (exportButton) exportButton.click();
    }
    
    // Ctrl+F: Focus search
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        const searchInput = document.querySelector('.tab-pane.show input[placeholder*="Search"]');
        if (searchInput) searchInput.focus();
    }
    
    // Ctrl+R: Refresh
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        location.reload();
    }
});
