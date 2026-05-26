document.addEventListener("DOMContentLoaded", () => {
    // Initialize sidebar functionality
    initializeSidebar();
    
    // Real-time JAMB registration validation
    const jambInputs = document.querySelectorAll('input[name="jamb_reg_number"]');
    jambInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', (e) => {
            clearTimeout(timeout);
            const value = e.target.value.trim();
            const feedback = e.target.parentNode.querySelector('.jamb-feedback') || createJambFeedback(e.target);
            
            if (value.length >= 10) {
                timeout = setTimeout(() => validateJambNumber(value, feedback), 800);
            } else {
                feedback.innerHTML = '';
                feedback.className = 'jamb-feedback small mt-1';
            }
        });
    });

    // Dynamic O'Level subject entry for manual forms
    const olevelJsonTextarea = document.querySelector('textarea[name="olevel_results_json"]');
    if (olevelJsonTextarea) {
        addDynamicOlevelControls(olevelJsonTextarea);
    }
});

// Sidebar functionality
function initializeSidebar() {
    // Set active navigation based on current URL
    setActiveNavigation();
    
    // Handle sidebar toggle on desktop
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarClose = document.getElementById('sidebarClose');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    if (sidebarClose) {
        sidebarClose.addEventListener('click', closeSidebar);
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }
    
    // Handle responsive sidebar
    handleResponsiveSidebar();
    
    // Add keyboard shortcuts
    setupKeyboardShortcuts();
}

function setActiveNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        // Remove existing active classes
        link.classList.remove('active');
        
        // Check if link matches current path
        const href = link.getAttribute('href');
        if (href === currentPath) {
            link.classList.add('active');
        }
        
        // Handle page-specific active states
        const pageAttribute = link.getAttribute('data-page');
        if (pageAttribute) {
            // Check if current page matches the data-page attribute
            if (isCurrentPage(pageAttribute)) {
                link.classList.add('active');
            }
        }
    });
}

function isCurrentPage(pageName) {
    const currentPath = window.location.pathname;
    
    switch(pageName) {
        case 'dashboard':
            return currentPath.includes('/admin/dashboard') || currentPath === '/';
        case 'university':
            return currentPath.includes('/admin/university');
        case 'catchment':
            return currentPath.includes('/admin/catchment');
        case 'faculties':
            return currentPath.includes('/admin/faculties');
        case 'candidates':
            return currentPath.includes('/admin/candidates');
        case 'programmes':
            return currentPath.includes('/admin/programmes');
        case 'reports':
            return currentPath.includes('/admin/reports');
        case 'users':
            return currentPath.includes('/auth/register');
        default:
            return false;
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    const footer = document.querySelector('.app-footer');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            // Mobile: toggle 'show' on sidebar and overlay
            const isShown = sidebar.classList.contains('show');
            if (isShown) {
                sidebar.classList.remove('show');
                if (overlay) overlay.classList.remove('show');
            } else {
                sidebar.classList.add('show');
                if (overlay) overlay.classList.add('show');
            }
            // Ensure desktop classes don't cause styling conflicts on mobile
            sidebar.classList.remove('collapsed');
            if (mainContent) mainContent.classList.remove('expanded');
            if (footer) footer.classList.remove('expanded');
        } else {
            // Desktop: toggle 'collapsed' on sidebar and 'expanded' on content/footer
            const isCollapsed = sidebar.classList.contains('collapsed');
            if (isCollapsed) {
                sidebar.classList.remove('collapsed');
                if (mainContent) mainContent.classList.remove('expanded');
                if (footer) footer.classList.remove('expanded');
            } else {
                sidebar.classList.add('collapsed');
                if (mainContent) mainContent.classList.add('expanded');
                if (footer) footer.classList.add('expanded');
            }
            // Ensure mobile classes are removed on desktop
            sidebar.classList.remove('show');
            if (overlay) overlay.classList.remove('show');
        }
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    const footer = document.querySelector('.app-footer');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            sidebar.classList.remove('show');
            if (overlay) overlay.classList.remove('show');
        } else {
            sidebar.classList.add('collapsed');
            if (mainContent) mainContent.classList.add('expanded');
            if (footer) footer.classList.add('expanded');
        }
    }
}

function handleResponsiveSidebar() {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    
    function handleMediaChange(e) {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        const footer = document.querySelector('.app-footer');
        const overlay = document.getElementById('sidebarOverlay');
        
        if (e.matches) {
            // Mobile view: hide sidebar by default
            if (sidebar) {
                sidebar.classList.remove('show');
                sidebar.classList.remove('collapsed');
            }
            if (mainContent) mainContent.classList.remove('expanded');
            if (footer) footer.classList.remove('expanded');
            if (overlay) overlay.classList.remove('show');
        } else {
            // Desktop view: show sidebar by default
            if (sidebar) {
                sidebar.classList.remove('collapsed');
                sidebar.classList.remove('show');
            }
            if (mainContent) mainContent.classList.remove('expanded');
            if (footer) footer.classList.remove('expanded');
            if (overlay) overlay.classList.remove('show');
        }
    }
    
    // Initial check
    handleMediaChange(mediaQuery);
    
    // Listen for changes
    mediaQuery.addListener(handleMediaChange);
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + B to toggle sidebar
        if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            toggleSidebar();
        }
        
        // Escape to close sidebar on mobile
        if (e.key === 'Escape') {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && sidebar.classList.contains('collapsed')) {
                closeSidebar();
            }
        }
    });
}

// Enhanced search functionality
function initializeSearch() {
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });
    }
}

function handleSearch() {
    const searchInput = document.querySelector('.search-bar input');
    const searchTerm = searchInput?.value.trim();
    
    if (searchTerm) {
        // Redirect to candidates page with search parameter
        window.location.href = `/admin/candidates?search=${encodeURIComponent(searchTerm)}`;
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Notification system
function initializeNotifications() {
    const notificationBtn = document.querySelector('.header-btn[aria-label="Notifications"]');
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            // Mark notifications as read
            const badge = notificationBtn.querySelector('.notification-badge');
            if (badge) {
                badge.style.display = 'none';
            }
        });
    }
}

// Theme toggle (optional enhancement)
function initializeThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });
        
        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
        }
    }
}

// Toast Notification System
function showToast(message, type = 'info', title = null, duration = 5000) {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const toastTitle = title || type.charAt(0).toUpperCase() + type.slice(1);
    
    const toastHTML = `
        <div id="${toastId}" class="toast ${type}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <div class="toast-icon ${type}">
                    <i class="fa-solid ${getToastIcon(type)}"></i>
                </div>
                <h6 class="toast-title">${toastTitle}</h6>
                <button type="button" class="toast-close" aria-label="Close" onclick="hideToast('${toastId}')">
                    <i class="fa-solid fa-times"></i>
                </button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
            <div class="toast-progress"></div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration
    });
    
    toast.show();
    
    // Auto-remove from DOM after hiding
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

function getToastIcon(type) {
    const icons = {
        success: 'fa-check',
        error: 'fa-times',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info'
    };
    return icons[type] || icons.info;
}

function hideToast(toastId) {
    const toastElement = document.getElementById(toastId);
    if (toastElement) {
        const toast = bootstrap.Toast.getInstance(toastElement);
        if (toast) {
            toast.hide();
        } else {
            toastElement.remove();
        }
    }
}

// Convenience methods for different toast types
function showSuccessToast(message, title = null) {
    showToast(message, 'success', title);
}

function showErrorToast(message, title = null) {
    showToast(message, 'error', title);
}

function showWarningToast(message, title = null) {
    showToast(message, 'warning', title);
}

function showInfoToast(message, title = null) {
    showToast(message, 'info', title);
}

// Initialize all features when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeSidebar();
    initializeSearch();
    initializeNotifications();
    initializeThemeToggle();
    initializeToasts();
    
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add loading states to forms
    const forms = document.querySelectorAll('form[data-loading]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                setButtonLoading(submitBtn, submitBtn.textContent);
            }
            showLoading('Submitting form...');
        });
    });
    
    // Add confirmation to delete buttons
    const deleteButtons = document.querySelectorAll('button[data-confirm], a[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const message = this.dataset.confirm || 'Are you sure you want to delete this item?';
            const action = () => {
                if (this.tagName === 'A') {
                    window.location.href = this.href;
                } else if (this.tagName === 'BUTTON' && this.type === 'submit') {
                    this.form.submit();
                } else {
                    this.click();
                }
            };
            showConfirmModal(message, action);
        });
    });
});

function initializeToasts() {
    // Convert flash messages to toasts
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(alert => {
        const message = alert.textContent.trim();
        const type = getAlertType(alert);
        
        // Create toast
        showToast(message, type, null, 5000);
        
        // Remove the original alert
        alert.remove();
    });
}

function getAlertType(alertElement) {
    const classList = alertElement.classList;
    if (classList.contains('alert-success')) return 'success';
    if (classList.contains('alert-danger')) return 'error';
    if (classList.contains('alert-warning')) return 'warning';
    if (classList.contains('alert-info')) return 'info';
    return 'info';
}

// Tour/Onboarding System
class TourGuide {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.overlay = null;
        this.tooltip = null;
        this.skipButton = null;
        this.isActive = false;
    }

    init() {
        this.createOverlay();
        this.createTooltip();
        this.createSkipButton();
        this.setupSteps();
    }

    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        this.overlay.id = 'tourOverlay';
        document.body.appendChild(this.overlay);
    }

    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tour-tooltip';
        this.tooltip.innerHTML = `
            <div class="tour-tooltip-header">
                <h6 class="tour-tooltip-title"></h6>
                <button class="tour-tooltip-close" onclick="tourGuide.endTour()">
                    <i class="fa-solid fa-times"></i>
                </button>
            </div>
            <div class="tour-tooltip-body"></div>
            <div class="tour-tooltip-footer">
                <span class="tour-tooltip-progress"></span>
                <div class="tour-tooltip-actions">
                    <button class="tour-tooltip-btn tour-tooltip-btn-prev" onclick="tourGuide.previousStep()">Previous</button>
                    <button class="tour-tooltip-btn tour-tooltip-btn-next" onclick="tourGuide.nextStep()">Next</button>
                </div>
            </div>
        `;
        document.body.appendChild(this.tooltip);
    }

    createSkipButton() {
        this.skipButton = document.createElement('button');
        this.skipButton.className = 'tour-skip-btn';
        this.skipButton.innerHTML = 'Skip Tour';
        this.skipButton.onclick = () => this.endTour();
        document.body.appendChild(this.skipButton);
    }

    setupSteps() {
        this.steps = [
            {
                selector: '#sidebarToggle',
                title: 'Navigation Menu',
                content: 'Use this button to toggle the navigation sidebar. You can access all sections of the admission system from here.',
                position: 'right'
            },
            {
                selector: '.quick-stats-bar',
                title: 'Quick Stats',
                content: 'View important system information at a glance including current session, programmes, faculties, and system status.',
                position: 'bottom'
            },
            {
                selector: '.stat-card:first-child',
                title: 'Total Candidates',
                content: 'See the total number of candidates in the current session. Click here to view detailed candidate information.',
                position: 'left'
            },
            {
                selector: '#quotaChart',
                title: 'Admission Charts',
                content: 'Visualize admission data by quota categories and status distribution. These charts update in real-time.',
                position: 'top'
            },
            {
                selector: '.quick-action-card:first-child',
                title: 'Quick Actions',
                content: 'Perform common tasks quickly with these action buttons. Upload candidates, run screening, and more.',
                position: 'top'
            },
            {
                selector: '.system-health',
                title: 'System Health',
                content: 'Monitor the health of your system including database connectivity, CAPS service status, and backup information.',
                position: 'top'
            }
        ];
    }

    startTour() {
        if (this.isActive) return;
        
        // Check if user has already completed the tour
        if (localStorage.getItem('tourCompleted') === 'true') {
            return;
        }
        
        this.isActive = true;
        this.currentStep = 0;
        this.overlay.classList.add('active');
        this.skipButton.style.display = 'block';
        this.showStep();
    }

    showStep() {
        const step = this.steps[this.currentStep];
        if (!step) {
            this.endTour();
            return;
        }

        // Remove previous highlight
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
        });

        // Highlight current element
        const element = document.querySelector(step.selector);
        if (element) {
            element.classList.add('tour-highlight');
            
            // Position tooltip
            this.positionTooltip(element, step.position);
            
            // Update tooltip content
            this.updateTooltipContent(step);
        } else {
            // Skip to next step if element not found
            this.nextStep();
        }
    }

    positionTooltip(element, position) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();
        
        // Remove all position classes
        this.tooltip.classList.remove('top', 'bottom', 'left', 'right', 'center');
        
        let top, left;
        
        switch (position) {
            case 'top':
                top = rect.top - tooltipRect.height - 10;
                left = rect.left + (rect.width - tooltipRect.width) / 2;
                this.tooltip.classList.add('top');
                break;
            case 'bottom':
                top = rect.bottom + 10;
                left = rect.left + (rect.width - tooltipRect.width) / 2;
                this.tooltip.classList.add('bottom');
                break;
            case 'left':
                top = rect.top + (rect.height - tooltipRect.height) / 2;
                left = rect.left - tooltipRect.width - 10;
                this.tooltip.classList.add('left');
                break;
            case 'right':
                top = rect.top + (rect.height - tooltipRect.height) / 2;
                left = rect.right + 10;
                this.tooltip.classList.add('right');
                break;
            case 'center':
                this.tooltip.classList.add('center');
                return;
        }
        
        // Adjust position to keep tooltip within viewport
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top < 10) top = 10;
        if (top + tooltipRect.height > window.innerHeight - 10) {
            top = window.innerHeight - tooltipRect.height - 10;
        }
        
        this.tooltip.style.top = top + 'px';
        this.tooltip.style.left = left + 'px';
    }

    updateTooltipContent(step) {
        const title = this.tooltip.querySelector('.tour-tooltip-title');
        const body = this.tooltip.querySelector('.tour-tooltip-body');
        const progress = this.tooltip.querySelector('.tour-tooltip-progress');
        const prevBtn = this.tooltip.querySelector('.tour-tooltip-btn-prev');
        const nextBtn = this.tooltip.querySelector('.tour-tooltip-btn-next');
        
        title.textContent = step.title;
        body.textContent = step.content;
        progress.textContent = `${this.currentStep + 1} of ${this.steps.length}`;
        
        // Update button states
        prevBtn.style.display = this.currentStep === 0 ? 'none' : 'block';
        nextBtn.textContent = this.currentStep === this.steps.length - 1 ? 'Finish' : 'Next';
        
        // Show tooltip with animation
        this.tooltip.classList.add('active');
    }

    nextStep() {
        this.currentStep++;
        if (this.currentStep >= this.steps.length) {
            this.endTour();
        } else {
            this.showStep();
        }
    }

    previousStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.showStep();
        }
    }

    endTour() {
        this.isActive = false;
        
        // Remove highlights
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
        });
        
        // Hide overlay and tooltip
        this.overlay.classList.remove('active');
        this.tooltip.classList.remove('active');
        this.skipButton.style.display = 'none';
        
        // Mark tour as completed
        localStorage.setItem('tourCompleted', 'true');
        
        // Show completion toast
        showSuccessToast('Tour completed! You can always restart it from the help menu.');
    }
}

// Initialize tour guide
const tourGuide = new TourGuide();

// Add tour initialization to main DOM ready event
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tour guide
    tourGuide.init();
    
    // Start tour after a delay for first-time users
    setTimeout(() => {
        if (!localStorage.getItem('tourCompleted')) {
            tourGuide.startTour();
        }
    }, 2000);
});

// Add tour restart function
function restartTour() {
    localStorage.removeItem('tourCompleted');
    tourGuide.startTour();
}

function createJambFeedback(input) {
    const feedback = document.createElement('div');
    feedback.className = 'jamb-feedback small mt-1';
    input.parentNode.appendChild(feedback);
    return feedback;
}

async function validateJambNumber(jambNumber, feedbackElement) {
    try {
        const response = await fetch(`/admin/candidates/validate-jamb?jamb_reg_number=${encodeURIComponent(jambNumber)}`);
        const data = await response.json();
        
        if (data.valid) {
            feedbackElement.innerHTML = `<span class="text-success"><i class="fa-solid fa-check"></i> ${data.message}</span>`;
            feedbackElement.className = 'jamb-feedback small mt-1 text-success';
        } else {
            feedbackElement.innerHTML = `<span class="text-danger"><i class="fa-solid fa-times"></i> ${data.message}</span>`;
            feedbackElement.className = 'jamb-feedback small mt-1 text-danger';
        }
    } catch (error) {
        feedbackElement.innerHTML = '<span class="text-warning"><i class="fa-solid fa-exclamation-triangle"></i> Validation error</span>';
        feedbackElement.className = 'jamb-feedback small mt-1 text-warning';
    }
}

function addDynamicOlevelControls(textarea) {
    const container = textarea.parentNode;
    const controlsDiv = document.createElement('div');
    controlsDiv.className = 'mt-2';
    controlsDiv.innerHTML = `
        <button type="button" class="btn btn-sm btn-outline-primary" onclick="showOlevelBuilder()">
            <i class="fa-solid fa-plus"></i> Build O'Level Results
        </button>
        <div id="olevelBuilder" class="d-none mt-3 p-3 border rounded bg-light"></div>
    `;
    container.appendChild(controlsDiv);
}

function showOlevelBuilder() {
    const builder = document.getElementById('olevelBuilder');
    if (builder.classList.contains('d-none')) {
        builder.classList.remove('d-none');
        builder.innerHTML = `
            <div class="row g-2 mb-2">
                <div class="col-md-3">
                    <select class="form-select form-select-sm" id="examBody">
                        <option value="">Exam Body</option>
                        <option value="WAEC">WAEC</option>
                        <option value="NECO">NECO</option>
                        <option value="NABTEB">NABTEB</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control form-control-sm" id="examYear" placeholder="Year" min="1980" max="2100">
                </div>
                <div class="col-md-2">
                    <input type="text" class="form-control form-control-sm" id="examNumber" placeholder="Exam No">
                </div>
                <div class="col-md-2">
                    <select class="form-select form-select-sm" id="sittingNumber">
                        <option value="1">Sitting 1</option>
                        <option value="2">Sitting 2</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <button type="button" class="btn btn-sm btn-success" onclick="addSubjectRow()">Add Subject</button>
                </div>
            </div>
            <div id="subjectsContainer"></div>
            <div class="mt-2">
                <button type="button" class="btn btn-sm btn-primary" onclick="generateOlevelJson()">Generate JSON</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="hideOlevelBuilder()">Cancel</button>
            </div>
        `;
    } else {
        hideOlevelBuilder();
    }
}

function hideOlevelBuilder() {
    const builder = document.getElementById('olevelBuilder');
    builder.classList.add('d-none');
}

let subjectRowCount = 0;
function addSubjectRow() {
    const container = document.getElementById('subjectsContainer');
    const rowId = `subject_${subjectRowCount++}`;
    const row = document.createElement('div');
    row.className = 'row g-2 mb-2 align-items-center';
    row.id = rowId;
    row.innerHTML = `
        <div class="col-md-4">
            <select class="form-select form-select-sm" id="subject_${rowId}">
                <option value="">Subject</option>
                <option value="English">English</option>
                <option value="Mathematics">Mathematics</option>
                <option value="Physics">Physics</option>
                <option value="Chemistry">Chemistry</option>
                <option value="Biology">Biology</option>
                <option value="Economics">Economics</option>
                <option value="Government">Government</option>
                <option value="Literature">Literature</option>
                <option value="Geography">Geography</option>
                <option value="Agricultural Science">Agricultural Science</option>
                <option value="Commerce">Commerce</option>
                <option value="CRS">CRS</option>
                <option value="IRS">IRS</option>
            </select>
        </div>
        <div class="col-md-3">
            <select class="form-select form-select-sm" id="grade_${rowId}">
                <option value="">Grade</option>
                <option value="A1">A1</option>
                <option value="B2">B2</option>
                <option value="B3">B3</option>
                <option value="C4">C4</option>
                <option value="C5">C5</option>
                <option value="C6">C6</option>
            </select>
        </div>
        <div class="col-md-2">
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeSubjectRow('${rowId}')">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `;
    container.appendChild(row);
}

function removeSubjectRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) row.remove();
}

function generateOlevelJson() {
    const examBody = document.getElementById('examBody').value;
    const examYear = document.getElementById('examYear').value;
    const examNumber = document.getElementById('examNumber').value;
    const sittingNumber = document.getElementById('sittingNumber').value;
    
    if (!examBody || !examYear || !examNumber) {
        alert('Please fill in exam details first');
        return;
    }
    
    const results = [];
    const subjectRows = document.querySelectorAll('[id^="subject_"]');
    
    subjectRows.forEach(row => {
        const subjectSelect = document.querySelector(`#subject_${row.id} select`);
        const gradeSelect = document.querySelector(`#grade_${row.id} select`);
        
        if (subjectSelect.value && gradeSelect.value) {
            results.push({
                exam_body: examBody,
                exam_number: examNumber,
                exam_year: parseInt(examYear),
                sitting_number: parseInt(sittingNumber),
                subject: subjectSelect.value,
                grade: gradeSelect.value
            });
        }
    });
    
    if (results.length === 0) {
        alert('Please add at least one subject');
        return;
    }
    
    const textarea = document.querySelector('textarea[name="olevel_results_json"]');
    textarea.value = JSON.stringify(results, null, 2);
    hideOlevelBuilder();
}

// Batch screening functionality
document.addEventListener('DOMContentLoaded', function() {
    // Add batch screening button to candidates page
    const candidatesTable = document.getElementById('candidateTable');
    if (candidatesTable) {
        // addBatchScreeningControls(); // Disabled - checkboxes removed from candidates table
    }
});

function addBatchScreeningControls() {
    const toolbar = document.querySelector('.d-flex.justify-content-between.align-items-center.mb-3 .d-flex');
    if (!toolbar) return;
    
    // Add checkbox column to table header
    const tableHeader = document.querySelector('#candidateTable thead tr');
    if (tableHeader && !tableHeader.querySelector('th:first-child input[type="checkbox"]')) {
        const checkboxHeader = document.createElement('th');
        checkboxHeader.width = '40';
        checkboxHeader.innerHTML = '<input type="checkbox" id="batchSelectAll" onchange="toggleAllCandidateCheckboxes()">';
        tableHeader.insertBefore(checkboxHeader, tableHeader.firstChild);
    }
    
    // Add checkboxes to table rows
    const tableRows = document.querySelectorAll('#candidateTable tbody tr');
    tableRows.forEach((row, index) => {
        if (!row.querySelector('td:first-child input[type="checkbox"]')) {
            const firstCell = row.querySelector('td:first-child');
            const candidateId = firstCell.querySelector('a')?.href?.match(/\/candidates\/(\d+)/)?.[1];
            
            if (candidateId) {
                const checkboxCell = document.createElement('td');
                checkboxCell.innerHTML = `<input type="checkbox" class="candidate-checkbox" value="${candidateId}">`;
                row.insertBefore(checkboxCell, firstCell);
            }
        }
    });
    
    // Add batch screening button
    const batchButton = document.createElement('button');
    batchButton.className = 'btn btn-warning';
    batchButton.innerHTML = '<i class="fa-solid fa-users me-1"></i>Batch Screen';
    batchButton.onclick = openBatchScreenModal;
    toolbar.appendChild(batchButton);
    
    // Update selection count
    updateBatchSelectionCount();
}

function toggleAllCandidateCheckboxes() {
    const selectAll = document.getElementById('batchSelectAll');
    const checkboxes = document.querySelectorAll('.candidate-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
    updateBatchSelectionCount();
}

function updateBatchSelectionCount() {
    const checkboxes = document.querySelectorAll('.candidate-checkbox:checked');
    const batchButton = document.querySelector('button[onclick="openBatchScreenModal()"]');
    if (batchButton) {
        const count = checkboxes.length;
        batchButton.innerHTML = `<i class="fa-solid fa-users me-1"></i>Batch Screen${count > 0 ? ` (${count})` : ''}`;
        batchButton.disabled = count === 0;
    }
}

// Add event listeners for checkbox changes
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('candidate-checkbox')) {
        updateBatchSelectionCount();
        
        // Update select all checkbox state
        const allCheckboxes = document.querySelectorAll('.candidate-checkbox');
        const checkedCheckboxes = document.querySelectorAll('.candidate-checkbox:checked');
        const selectAllCheckbox = document.getElementById('batchSelectAll');
        
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = allCheckboxes.length === checkedCheckboxes.length;
            selectAllCheckbox.indeterminate = checkedCheckboxes.length > 0 && checkedCheckboxes.length < allCheckboxes.length;
        }
    }
});

function openBatchScreenModal() {
    const selectedIds = Array.from(document.querySelectorAll('.candidate-checkbox:checked'))
        .map(cb => cb.value);
    
    if (selectedIds.length === 0) {
        alert('Please select at least one candidate for batch screening.');
        return;
    }
    
    // Create modal for batch screening
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Batch Screening Selection</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Selected <strong>${selectedIds.length}</strong> candidates for batch screening.</p>
                    <form id="quickBatchForm">
                        <div class="mb-3">
                            <label class="form-label">Programme *</label>
                            <select class="form-select" name="programme_id" required>
                                <option value="">Select Programme</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Session *</label>
                            <select class="form-select" name="session_id" required>
                                <option value="">Select Session</option>
                            </select>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="submitQuickBatchScreen()">
                        <i class="fa-solid fa-play me-1"></i>Start Screening
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Load programmes and sessions
    loadProgrammesAndSessions(modal);
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Clean up on modal hide
    modal.addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(modal);
    });
}

async function loadProgrammesAndSessions(modal) {
    try {
        // Load programmes
        const programmesResponse = await fetch('/admin/programmes?format=json');
        const programmesData = await programmesResponse.json();
        const programmeSelect = modal.querySelector('select[name="programme_id"]');
        
        programmesData.programmes?.forEach(programme => {
            const option = document.createElement('option');
            option.value = programme.id;
            option.textContent = `${programme.name} (${programme.code})`;
            programmeSelect.appendChild(option);
        });
        
        // Load sessions
        const sessionsResponse = await fetch('/admin/sessions?format=json');
        const sessionsData = await sessionsResponse.json();
        const sessionSelect = modal.querySelector('select[name="session_id"]');
        
        sessionsData.sessions?.forEach(session => {
            const option = document.createElement('option');
            option.value = session.id;
            option.textContent = session.name;
            sessionSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading programmes and sessions');
    }
}

function submitQuickBatchScreen() {
    const form = document.getElementById('quickBatchForm');
    const formData = new FormData(form);
    
    if (!formData.get('programme_id') || !formData.get('session_id')) {
        alert('Please select both programme and session.');
        return;
    }
    
    // Get selected candidate IDs
    const selectedIds = Array.from(document.querySelectorAll('.candidate-checkbox:checked'))
        .map(cb => cb.value);
    
    // Create form and submit
    const submitForm = document.createElement('form');
    submitForm.method = 'POST';
    submitForm.action = '/admin/admission/batch-screen';
    
    // Add CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (csrfToken) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken;
        submitForm.appendChild(csrfInput);
    }
    
    // Add programme and session
    const programmeInput = document.createElement('input');
    programmeInput.type = 'hidden';
    programmeInput.name = 'programme_id';
    programmeInput.value = formData.get('programme_id');
    submitForm.appendChild(programmeInput);
    
    const sessionInput = document.createElement('input');
    sessionInput.type = 'hidden';
    sessionInput.name = 'session_id';
    sessionInput.value = formData.get('session_id');
    submitForm.appendChild(sessionInput);
    
    // Add candidate IDs
    selectedIds.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'candidate_ids';
        input.value = id;
        submitForm.appendChild(input);
    });
    
    document.body.appendChild(submitForm);
    submitForm.submit();
}
