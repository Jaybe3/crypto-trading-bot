/**
 * Dashboard v2 - Common JavaScript utilities
 */

// Price formatting utility
function formatPrice(price) {
    if (price === null || price === undefined) return '--';
    if (price >= 10000) {
        return price.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0});
    }
    if (price >= 100) {
        return price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
    if (price >= 1) {
        return price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 4});
    }
    return price.toLocaleString('en-US', {minimumFractionDigits: 4, maximumFractionDigits: 8});
}

// Currency formatting utility
function formatCurrency(amount, showSign = false) {
    if (amount === null || amount === undefined) return '--';
    const sign = showSign && amount >= 0 ? '+' : '';
    const prefix = amount >= 0 ? '$' : '-$';
    return sign + prefix + Math.abs(amount).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Percentage formatting utility
function formatPercent(value, decimals = 1) {
    if (value === null || value === undefined) return '--';
    return value.toFixed(decimals) + '%';
}

// Relative time formatting
function formatRelativeTime(isoString) {
    if (!isoString) return 'Unknown';

    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    } catch (e) {
        return 'Unknown';
    }
}

// Generic API call wrapper with error handling
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.message || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API call failed: ${url}`, error);
        throw error;
    }
}

// Toast notification system
const Toast = {
    container: null,

    init() {
        if (this.container) return;

        this.container = document.createElement('div');
        this.container.className = 'fixed bottom-4 right-4 z-50 space-y-2';
        document.body.appendChild(this.container);
    },

    show(message, type = 'info', duration = 3000) {
        this.init();

        const colors = {
            success: 'bg-green-800 text-green-200',
            error: 'bg-red-800 text-red-200',
            warning: 'bg-yellow-800 text-yellow-200',
            info: 'bg-slate-700 text-white'
        };

        const toast = document.createElement('div');
        toast.className = `${colors[type]} px-4 py-2 rounded-lg shadow-lg animate-fade-in`;
        toast.textContent = message;

        this.container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('animate-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
    warning(message) { this.show(message, 'warning'); },
    info(message) { this.show(message, 'info'); }
};

// Add CSS animations for toasts
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes fadeOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(20px); }
    }
    .animate-fade-in { animation: fadeIn 0.3s ease-out; }
    .animate-fade-out { animation: fadeOut 0.3s ease-out; }
`;
document.head.appendChild(style);

// Debounce utility
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

// Storage utilities for persisting user preferences
const Storage = {
    get(key, defaultValue = null) {
        try {
            const value = localStorage.getItem('dashboard_' + key);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            return defaultValue;
        }
    },

    set(key, value) {
        try {
            localStorage.setItem('dashboard_' + key, JSON.stringify(value));
        } catch (e) {
            console.error('Failed to save to localStorage:', e);
        }
    },

    remove(key) {
        try {
            localStorage.removeItem('dashboard_' + key);
        } catch (e) {
            console.error('Failed to remove from localStorage:', e);
        }
    }
};

// Export for use in templates
window.Dashboard = {
    formatPrice,
    formatCurrency,
    formatPercent,
    formatRelativeTime,
    apiCall,
    Toast,
    debounce,
    Storage
};

console.log('Dashboard v2 initialized');
