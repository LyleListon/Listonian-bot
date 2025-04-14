/**
 * Arbitrage Bot Dashboard
 * Main application script
 */

// Global state
const state = {
    currentPage: 'dashboard',
    theme: 'dark',
    refreshInterval: 5000,
    refreshTimer: null,
    opportunities: [],
    trades: [],
    metrics: {},
    config: {},
    status: 'unknown',
    pagination: {
        trades: {
            page: 1,
            limit: 10,
            total: 0
        },
        opportunities: {
            page: 1,
            limit: 10,
            total: 0
        }
    },
    filters: {
        opportunities: {
            minProfit: 0.5,
            maxRisk: 3
        },
        trades: {
            status: ''
        }
    },
    charts: {}
};

// API endpoints
const API = {
    status: '/api/v1/status',
    metrics: '/api/v1/metrics',
    opportunities: '/api/v1/opportunities',
    trades: '/api/v1/trades',
    config: '/api/v1/config',
    settings: '/api/v1/settings'
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

/**
 * Initialize the application
 */
async function initApp() {
    // Set up navigation
    setupNavigation();

    // Load initial data
    await loadInitialData();

    // Set up auto-refresh
    startAutoRefresh();

    // Apply theme
    applyTheme(state.theme);

    // Load the current page
    loadPage(state.currentPage);
}

/**
 * Set up navigation event listeners
 */
function setupNavigation() {
    const navLinks = document.querySelectorAll('#sidebar .nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            // Get the page from the href attribute
            const href = link.getAttribute('href');
            const page = href.substring(1); // Remove the # character

            // Update active link
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Load the page
            loadPage(page);
        });
    });
}

/**
 * Load initial data from the API
 */
async function loadInitialData() {
    try {
        // Show loading indicator
        document.getElementById('loading').style.display = 'flex';

        // Load status
        const statusResponse = await fetchAPI(API.status);
        if (statusResponse.success) {
            state.status = statusResponse.data.status;

            // Load theme from localStorage or use default
            state.theme = localStorage.getItem('theme') || 'dark';

            // Load refresh interval from localStorage or use default
            state.refreshInterval = parseInt(localStorage.getItem('refreshInterval')) || 5000;
        }

        // Hide loading indicator
        document.getElementById('loading').style.display = 'none';
    } catch (error) {
        console.error('Error loading initial data:', error);
        // Hide loading indicator
        document.getElementById('loading').style.display = 'none';
    }
}

/**
 * Start auto-refresh timer
 */
function startAutoRefresh() {
    // Clear existing timer
    if (state.refreshTimer) {
        clearInterval(state.refreshTimer);
    }

    // Start new timer
    state.refreshTimer = setInterval(() => {
        refreshCurrentPage();
    }, state.refreshInterval);
}

/**
 * Refresh the current page data
 */
async function refreshCurrentPage() {
    try {
        // Refresh status
        const statusResponse = await fetchAPI(API.status);
        if (statusResponse.success) {
            state.status = statusResponse.data.status;
            updateStatusIndicator();
        }

        // Refresh page-specific data
        switch (state.currentPage) {
            case 'dashboard':
                await loadDashboardData();
                updateDashboardUI();
                break;
            case 'opportunities':
                await loadOpportunitiesData();
                updateOpportunitiesUI();
                break;
            case 'trades':
                await loadTradesData();
                updateTradesUI();
                break;
            case 'settings':
                await loadConfigData();
                updateSettingsUI();
                break;
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
    }
}

/**
 * Load a page by name
 * @param {string} page - The page name to load
 */
async function loadPage(page) {
    // Update current page
    state.currentPage = page;

    // Get the content element
    const contentElement = document.getElementById('content');

    // Get the template
    const template = document.getElementById(`${page}-template`);

    if (!template) {
        console.error(`Template not found for page: ${page}`);
        return;
    }

    // Clone the template content
    const content = template.content.cloneNode(true);

    // Clear the content element
    contentElement.innerHTML = '';

    // Append the new content
    contentElement.appendChild(content);

    // Load page-specific data and set up event listeners
    switch (page) {
        case 'dashboard':
            await loadDashboardData();
            setupDashboardEvents();
            updateDashboardUI();
            break;
        case 'opportunities':
            await loadOpportunitiesData();
            setupOpportunitiesEvents();
            updateOpportunitiesUI();
            break;
        case 'trades':
            await loadTradesData();
            setupTradesEvents();
            updateTradesUI();
            break;
        case 'settings':
            await loadConfigData();
            setupSettingsEvents();
            updateSettingsUI();
            break;
    }
}

/**
 * Apply theme to the document
 * @param {string} theme - The theme name ('light' or 'dark')
 */
function applyTheme(theme) {
    if (theme === 'dark') {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.remove('dark-theme');
    }

    // Save theme preference
    localStorage.setItem('theme', theme);
}

/**
 * Update the status indicator
 */
function updateStatusIndicator() {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');

    if (!statusDot || !statusText) {
        return;
    }

    // Update status dot
    statusDot.className = 'status-dot';
    if (state.status === 'running') {
        statusDot.classList.add('running');
    } else if (state.status === 'stopped') {
        statusDot.classList.add('stopped');
    } else {
        statusDot.classList.add('warning');
    }

    // Update status text
    statusText.textContent = `Status: ${state.status.charAt(0).toUpperCase() + state.status.slice(1)}`;
}

/**
 * Fetch data from the API
 * @param {string} endpoint - The API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} - The API response
 */
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, options);

        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        throw error;
    }
}

/**
 * Format a timestamp as a readable date string
 * @param {number} timestamp - The timestamp in seconds
 * @returns {string} - Formatted date string
 */
function formatDate(timestamp) {
    if (!timestamp) return 'N/A';

    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

/**
 * Format a number as currency
 * @param {number} value - The value to format
 * @returns {string} - Formatted currency string
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

/**
 * Format a number as percentage
 * @param {number} value - The value to format
 * @returns {string} - Formatted percentage string
 */
function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

/**
 * Format seconds as a readable duration
 * @param {number} seconds - The duration in seconds
 * @returns {string} - Formatted duration string
 */
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    return `${hours}h ${minutes}m ${secs}s`;
}

// Load this file first, then we'll load the page-specific modules
loadModules();

/**
 * Load additional JavaScript modules
 */
function loadModules() {
    // Load dashboard module
    loadScript('js/dashboard.js');

    // Load opportunities module
    loadScript('js/opportunities.js');

    // Load trades module
    loadScript('js/trades.js');

    // Load settings module
    loadScript('js/settings.js');
}

/**
 * Load a JavaScript file dynamically
 * @param {string} src - The script source URL
 * @returns {Promise} - Promise that resolves when the script is loaded
 */
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}
