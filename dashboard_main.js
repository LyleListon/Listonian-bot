/**
 * Main Dashboard Script
 * Initializes all dashboard sections and handles global functionality
 */

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing dashboard...');

    // Set up debug section
    setupDebugSection();

    // Clear loading message
    const dashboardContent = document.getElementById('dashboardContent');
    dashboardContent.innerHTML = '';

    try {
        // Initialize core sections first
        console.log('Initializing blockchain section...');
        initBlockchainSection();

        console.log('Initializing tokens section...');
        initTokensSection();

        console.log('Initializing DEX section...');
        initDexesSection();

        console.log('Initializing performance section...');
        initPerformanceSection();

        console.log('Initializing trades section...');
        initTradesSection();

        // Initialize new sections
        console.log('Initializing market data section...');
        if (typeof initMarketDataSection === 'function') {
            initMarketDataSection();
        } else {
            console.error('initMarketDataSection is not defined');
        }

        console.log('Initializing bot metrics section...');
        if (typeof initBotMetricsSection === 'function') {
            initBotMetricsSection();
        } else {
            console.error('initBotMetricsSection is not defined');
        }

        console.log('Initializing financial section...');
        if (typeof initFinancialSection === 'function') {
            initFinancialSection();
        } else {
            console.error('initFinancialSection is not defined');
        }

        console.log('Initializing infrastructure section...');
        if (typeof initInfrastructureSection === 'function') {
            initInfrastructureSection();
        } else {
            console.error('initInfrastructureSection is not defined');
        }
    } catch (error) {
        console.error('Error initializing dashboard sections:', error);
    }

    // Set up global refresh button
    document.getElementById('refreshAllBtn').addEventListener('click', refreshAllSections);

    // Update last updated time
    document.getElementById('lastUpdated').textContent = new Date().toLocaleString();

    // Set up auto-refresh for the entire dashboard
    setInterval(refreshAllSections, 15000); // Refresh everything every 15 seconds

    console.log('Dashboard initialized successfully');
});

// Refresh all sections
function refreshAllSections() {
    console.log('Refreshing all sections...');

    try {
        // Trigger refresh for core sections
        if (typeof fetchBlockchainData === 'function') fetchBlockchainData();
        if (typeof fetchTokenPrices === 'function') fetchTokenPrices();
        if (typeof fetchDexStatistics === 'function') fetchDexStatistics();
        if (typeof fetchPerformanceData === 'function') fetchPerformanceData();
        if (typeof fetchTradesData === 'function') fetchTradesData();

        // Trigger refresh for new sections
        if (typeof fetchMarketData === 'function') fetchMarketData();
        if (typeof fetchBotMetrics === 'function') fetchBotMetrics();
        if (typeof fetchFinancialData === 'function') fetchFinancialData();
        if (typeof fetchInfrastructureData === 'function') fetchInfrastructureData();
    } catch (error) {
        console.error('Error refreshing dashboard sections:', error);
    }

    // Update last updated time
    document.getElementById('lastUpdated').textContent = new Date().toLocaleString();
}

// Set up debug section
function setupDebugSection() {
    const debugInfo = document.getElementById('debugInfo');
    const testApiBtn = document.getElementById('testApiBtn');

    // Display initial debug info
    updateDebugInfo();

    // Set up test API button
    testApiBtn.addEventListener('click', async function() {
        debugInfo.textContent = 'Testing API connection...';

        try {
            const response = await fetch('http://localhost:8081/api/trades');
            const data = await response.json();

            debugInfo.textContent = `API Connection: Success\nStatus: ${response.status}\nData: ${JSON.stringify(data).substring(0, 200)}...`;
        } catch (error) {
            debugInfo.textContent = `API Connection: Failed\nError: ${error.message}`;
        }
    });
}

// Update debug info
function updateDebugInfo() {
    const debugInfo = document.getElementById('debugInfo');

    // Get browser info
    const browserInfo = `Browser: ${navigator.userAgent}`;

    // Get API URL
    const apiUrl = 'http://localhost:8081';

    // Display debug info
    debugInfo.textContent = `${browserInfo}\nAPI URL: ${apiUrl}\nDashboard Version: 1.0.0\nLast Updated: ${new Date().toLocaleString()}`;
}
