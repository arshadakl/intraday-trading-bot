/**
 * Tailwind Utility Functions for Trading Bot Dashboard
 * Provides helper functions for dynamic class management with Tailwind CSS
 */

// ==================== Class Management Utilities ====================

/**
 * Updates element classes for status badges
 */
function updateStatusBadge(element, status) {
    // Remove all status classes
    element.classList.remove(
        'badge-status-stopped', 'badge-status-running', 'badge-status-paused',
        'bg-bg-elevated', 'text-text-muted',
        'bg-success/15', 'text-success', 'border-success/30',
        'bg-warning/15', 'text-warning', 'border-warning/30'
    );
    
    // Add appropriate classes based on status
    switch (status) {
        case 'running':
            element.classList.add('bg-success/15', 'text-success', 'border', 'border-success/30');
            break;
        case 'paused':
            element.classList.add('bg-warning/15', 'text-warning', 'border', 'border-warning/30');
            break;
        default: // stopped
            element.classList.add('bg-bg-elevated', 'text-text-muted');
    }
}

/**
 * Updates element classes for mode badges
 */
function updateModeBadge(element, mode) {
    // Remove all mode classes
    element.classList.remove(
        'bg-teal/15', 'text-teal', 'border-teal/30',
        'bg-danger/15', 'text-danger', 'border-danger/30'
    );
    
    // Add appropriate classes based on mode
    switch (mode) {
        case 'live':
            element.classList.add('bg-danger/15', 'text-danger', 'border', 'border-danger/30');
            break;
        default: // paper
            element.classList.add('bg-teal/15', 'text-teal', 'border', 'border-teal/30');
    }
}

/**
 * Updates element classes for startup mode badges
 */
function updateStartupModeBadge(element, startupMode) {
    // Remove all startup mode classes
    element.classList.remove(
        'bg-purple-custom/15', 'text-purple-custom', 'border-purple-custom/30',
        'bg-success/15', 'text-success', 'border-success/30',
        'bg-bg-elevated', 'text-text-muted'
    );
    
    // Add appropriate classes based on startup mode
    switch (startupMode) {
        case 'PRE-MARKET':
            element.classList.add('bg-purple-custom/15', 'text-purple-custom', 'border', 'border-purple-custom/30');
            break;
        case 'MARKET':
            element.classList.add('bg-success/15', 'text-success', 'border', 'border-success/30');
            break;
        default: // NON-MARKET
            element.classList.add('bg-bg-elevated', 'text-text-muted');
    }
}

/**
 * Updates P&L text color based on value
 */
function updatePnLClasses(element, value) {
    element.classList.remove('text-pnl-positive', 'text-pnl-negative', 'text-text-primary');
    
    if (value > 0) {
        element.classList.add('text-pnl-positive');
    } else if (value < 0) {
        element.classList.add('text-pnl-negative');
    } else {
        element.classList.add('text-text-primary');
    }
}

/**
 * Updates progress bar classes
 */
function updateProgressBar(element, percentage, type = 'success') {
    const fillElement = element.querySelector('.progress-fill');
    if (fillElement) {
        // Remove all progress type classes
        fillElement.classList.remove('bg-success', 'bg-warning', 'bg-danger');
        
        // Add appropriate color class
        switch (type) {
            case 'warning':
                fillElement.classList.add('bg-warning');
                break;
            case 'danger':
                fillElement.classList.add('bg-danger');
                break;
            default:
                fillElement.classList.add('bg-success');
        }
        
        // Update width
        fillElement.style.width = `${percentage}%`;
    }
}

/**
 * Shows/hides elements with animation
 */
function toggleElementVisibility(element, show, animationClass = 'animate-fade-in') {
    if (show) {
        element.classList.remove('hidden');
        element.classList.add(animationClass);
    } else {
        element.classList.add('hidden');
        element.classList.remove(animationClass);
    }
}

/**
 * Updates button states (enabled/disabled)
 */
function updateButtonState(element, enabled) {
    if (enabled) {
        element.disabled = false;
        element.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        element.disabled = true;
        element.classList.add('opacity-50', 'cursor-not-allowed');
    }
}

/**
 * Shows success message with Tailwind styling
 */
function showSuccessMessage(container, message, autoHide = true) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-success animate-slide-up';
    wrapper.textContent = String(message);
    container.innerHTML = '';
    container.appendChild(wrapper);
    
    if (autoHide) {
        setTimeout(() => {
            container.innerHTML = '';
        }, 3000);
    }
}

/**
 * Shows error message with Tailwind styling
 */
function showErrorMessage(container, message) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-error animate-slide-up';
    wrapper.textContent = String(message);
    container.innerHTML = '';
    container.appendChild(wrapper);
}

/**
 * Shows warning message with Tailwind styling
 */
function showWarningMessage(container, message) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-warning animate-slide-up';
    wrapper.textContent = String(message);
    container.innerHTML = '';
    container.appendChild(wrapper);
}

/**
 * Shows info message with Tailwind styling
 */
function showInfoMessage(container, message) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-info animate-slide-up';
    wrapper.textContent = String(message);
    container.innerHTML = '';
    container.appendChild(wrapper);
}

/**
 * Creates a table row with Tailwind styling
 */
function createTableRow(cells, isHeader = false) {
    const tag = isHeader ? 'th' : 'td';
    const baseClass = isHeader ? 'table-header' : 'table-cell';
    const borderClass = isHeader ? 'border-b border-border-subtle' : '';
    
    const row = document.createElement('tr');
    if (borderClass) {
        row.className = borderClass;
    }
    
    cells.forEach((cell, index) => {
        const cellElement = document.createElement(tag);
        const alignment = cell.align || (isHeader ? 'text-left' : 'text-left');
        cellElement.className = `${baseClass} ${alignment} ${cell.class || ''}`.trim();
        
        // Safely set content - use textContent for strings, innerHTML only for trusted HTML
        if (typeof cell.content === 'string' && !cell.allowHTML) {
            cellElement.textContent = cell.content;
        } else if (cell.allowHTML && cell.content) {
            // Only allow HTML if explicitly marked as safe
            cellElement.innerHTML = cell.content;
        } else {
            cellElement.textContent = String(cell.content || '');
        }
        
        row.appendChild(cellElement);
    });
    
    return row;
}

/**
 * Creates an empty table row
 */
function createEmptyTableRow(colspan, message) {
    return `
        <tr>
            <td colspan="${colspan}" class="text-center py-8 text-text-muted">
                ${message}
            </td>
        </tr>
    `;
}

/**
 * Updates tab active state
 */
function updateTabState(activeBtn, allBtns) {
    // Reset all tabs
    allBtns.forEach(btn => {
        btn.classList.remove('bg-accent', 'text-white');
        btn.classList.add('text-text-secondary', 'hover:text-text-primary', 'hover:bg-bg-hover');
    });
    
    // Activate selected tab
    activeBtn.classList.add('bg-accent', 'text-white');
    activeBtn.classList.remove('text-text-secondary', 'hover:text-text-primary', 'hover:bg-bg-hover');
}

/**
 * Creates a loading spinner
 */
function createLoadingSpinner() {
    return `
        <div class="flex items-center justify-center py-4">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-accent"></div>
        </div>
    `;
}

/**
 * Creates a badge element
 */
function createBadge(text, type = 'default') {
    const typeClasses = {
        'success': 'bg-success/15 text-success border-success/30',
        'warning': 'bg-warning/15 text-warning border-warning/30',
        'danger': 'bg-danger/15 text-danger border-danger/30',
        'info': 'bg-accent/15 text-accent border-accent/30',
        'default': 'bg-bg-elevated text-text-muted'
    };
    
    const classes = typeClasses[type] || typeClasses.default;
    const borderClass = type !== 'default' ? 'border' : '';
    
    return `<span class="badge ${classes} ${borderClass}">${text}</span>`;
}

// ==================== Export functions for use in other files ====================
window.TailwindUtils = {
    updateStatusBadge,
    updateModeBadge,
    updateStartupModeBadge,
    updatePnLClasses,
    updateProgressBar,
    toggleElementVisibility,
    updateButtonState,
    showSuccessMessage,
    showErrorMessage,
    showWarningMessage,
    showInfoMessage,
    createTableRow,
    createEmptyTableRow,
    updateTabState,
    createLoadingSpinner,
    createBadge
};