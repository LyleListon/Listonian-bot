// Format numbers with commas and fixed decimal places
function formatNumber(num, decimals = 2) {
    if (num === undefined || num === null) return '0.00';
    return Number(num).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// Get base URL for API requests
const getBaseUrl = () => {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    return `${protocol}//${hostname}${port ? `:${port}` : ''}`;
};

// WebSocket connection management
let ws = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 1000;
let lastUpdateTime = new Date();

// Connect to WebSocket
function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/metrics`;

    console.log(`Connecting to WebSocket at ${wsUrl}...`);
    document.getElementById('connection-status').textContent = 'Connecting...';
    document.getElementById('connection-status').className = 'text-sm text-yellow-400 mt-2';

    // Close existing connection if any
    if (ws && ws.readyState !== WebSocket.CLOSED) {
        console.log('Closing existing WebSocket connection before reconnecting...');
        ws.close();
    }

    // Create new WebSocket connection
    ws = new WebSocket(wsUrl);

    // Initialize WebSocket debugging if available
    if (window.wsDebug) {
        window.wsDebug.init(ws);
    }

    ws.onopen = () => {
        console.log('WebSocket connected successfully');
        document.getElementById('connection-status').textContent = 'Connected';
        document.getElementById('connection-status').className = 'text-sm text-green-400 mt-2';
        reconnectAttempts = 0;

        // Send initial message to confirm connection
        try {
            ws.send(JSON.stringify({ type: 'hello', client: 'dashboard', timestamp: new Date().toISOString() }));
        } catch (error) {
            console.error('Error sending initial message:', error);
        }
    };

    ws.onmessage = (event) => {
        try {
            console.log('Raw WebSocket message received:', event.data);
            const data = JSON.parse(event.data);
            console.log('Parsed WebSocket data:', data);

            // Update last update time
            lastUpdateTime = new Date();

            // Handle ping messages
            if (data.type === 'ping') {
                // Respond with pong
                try {
                    ws.send(JSON.stringify({
                        type: 'pong',
                        timestamp: new Date().toISOString(),
                        ping_timestamp: data.timestamp
                    }));
                } catch (error) {
                    console.error('Error sending pong response:', error);
                }
                return;
            }

            // Update UI with received data
            updateDashboard(data);

            // Flash the connection status to indicate activity
            const statusEl = document.getElementById('connection-status');
            statusEl.classList.add('animate-pulse');
            setTimeout(() => statusEl.classList.remove('animate-pulse'), 500);
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    };

    ws.onclose = (event) => {
        console.log(`WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`);
        document.getElementById('connection-status').textContent = 'Disconnected';
        document.getElementById('connection-status').className = 'text-sm text-red-400 mt-2';

        // Calculate time since last update
        const timeSinceUpdate = (new Date() - lastUpdateTime) / 1000;
        console.log(`Time since last update: ${timeSinceUpdate.toFixed(1)} seconds`);

        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const delay = reconnectDelay * reconnectAttempts;
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
            setTimeout(connectWebSocket, delay);
        } else {
            console.error('Maximum reconnection attempts reached. Please refresh the page.');
            document.getElementById('connection-status').textContent = 'Connection failed - please refresh';
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        document.getElementById('connection-status').textContent = 'Connection Error';
        document.getElementById('connection-status').className = 'text-sm text-red-400 mt-2';
    };
}

// Update dashboard with received data
function updateDashboard(data) {
    // Flash updated elements to indicate new data
    document.querySelectorAll('.metric-card').forEach(card => {
        card.classList.add('flash');
        setTimeout(() => card.classList.remove('flash'), 500);
    });

    // Update performance metrics
    if (data.metrics && data.metrics.metrics) {
        const metrics = data.metrics.metrics;
        document.getElementById('performance-metrics').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <p class="text-sm text-gray-600">Total Profit (ETH)</p>
                    <p class="text-lg font-semibold">${formatNumber(metrics.total_profit_eth || 0, 4)}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Success Rate</p>
                    <p class="text-lg font-semibold">${formatNumber((metrics.success_rate || 0) * 100)}%</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Gas Price (Gwei)</p>
                    <p class="text-lg font-semibold">${formatNumber(data.metrics.gas_price || 0)}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Total Trades</p>
                    <p class="text-lg font-semibold">${metrics.total_trades || 0}</p>
                </div>
            </div>
        `;
    }

    // Update opportunities
    if (data.opportunities) {
        document.getElementById('active-opportunities').innerHTML = data.opportunities.length > 0
            ? data.opportunities.map(opp => `
                <div class="mb-4 p-4 bg-gray-50 rounded">
                    <p class="font-semibold">${opp.token_pair || 'Unknown Pair'}</p>
                    <p class="text-sm text-gray-600">
                        ${opp.dex_1 || 'Unknown'} → ${opp.dex_2 || 'Unknown'}<br>
                        Potential Profit: ${formatNumber(opp.potential_profit || 0, 4)} ETH<br>
                        Confidence: ${formatNumber(opp.confidence || 0)}%
                    </p>
                </div>
            `).join('')
            : '<p class="text-gray-600">No active opportunities</p>';
    }

    // Update system status
    if (data.metrics && data.metrics.system) {
        const system = data.metrics.system;
        document.getElementById('system-status').innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center">
                    <div class="w-3 h-3 rounded-full ${system.cpu_usage < 80 ? 'bg-green-500' : 'bg-red-500'} mr-2"></div>
                    <span>System Status: ${system.cpu_usage < 80 ? 'Healthy' : 'High Load'}</span>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Memory Usage</p>
                    <p class="text-lg font-semibold">${formatNumber(system.memory_usage || 0)}%</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">CPU Usage</p>
                    <p class="text-lg font-semibold">${formatNumber(system.cpu_usage || 0)}%</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Disk Usage</p>
                    <p class="text-lg font-semibold">${formatNumber(system.disk_usage || 0)}%</p>
                </div>
            </div>
        `;
    }

    // Update recent trades
    if (data.trade_history) {
        document.getElementById('recent-trades').innerHTML = data.trade_history.length > 0
            ? `<div class="overflow-x-auto">
                <table class="min-w-full">
                    <thead>
                        <tr class="border-b">
                            <th class="text-left py-2">Time</th>
                            <th class="text-left py-2">Pair</th>
                            <th class="text-left py-2">Route</th>
                            <th class="text-right py-2">Profit</th>
                            <th class="text-right py-2">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.trade_history.map(trade => `
                            <tr class="border-b">
                                <td class="py-2">${new Date(trade.timestamp).toLocaleTimeString()}</td>
                                <td class="py-2">${trade.opportunity?.token_pair || 'Unknown'}</td>
                                <td class="py-2">${trade.opportunity?.dex_1 || 'Unknown'} → ${trade.opportunity?.dex_2 || 'Unknown'}</td>
                                <td class="text-right py-2">${formatNumber(trade.net_profit || 0, 4)} ETH</td>
                                <td class="text-right py-2">
                                    <span class="px-2 py-1 rounded ${trade.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                                        ${trade.success ? 'Success' : 'Failed'}
                                    </span>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`
            : '<p class="text-gray-600">No recent trades</p>';
    }

    // Update last update time
    const lastUpdate = new Date(data.timestamp || new Date());
    if (document.getElementById('lastUpdate')) {
        document.getElementById('lastUpdate').textContent = `Last Update: ${lastUpdate.toLocaleString()}`;
    }

    // Update system status indicator
    if (data.metrics && data.metrics.system && document.getElementById('systemStatus')) {
        const systemStatus = document.getElementById('systemStatus');
        const statusDot = systemStatus.querySelector('.rounded-full');
        const statusText = systemStatus.querySelector('span');
        if (statusDot && statusText) {
            const system = data.metrics.system;
            const isHealthy = system.cpu_usage < 80 && system.memory_usage < 80;

            statusDot.className = `w-3 h-3 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'} mr-2`;
            statusText.textContent = isHealthy ? 'System Healthy' : 'System Overloaded';
        }
    }

    // Update charts if they exist
    if (window.charts) {
        updateCharts(data);
    }
}

// Update charts with new data
function updateCharts(data) {
    // Make sure charts are initialized
    if (!window.charts) return;

    try {
        // Update profit chart
        if (data.metrics && data.metrics.metrics && data.metrics.metrics.profit_trend && window.charts.profitChart) {
            const profitTrend = data.metrics.metrics.profit_trend;
            window.charts.profitChart.data.labels = profitTrend.map(p => {
                const date = new Date(p.timestamp);
                return date.getHours().toString().padStart(2, '0') + ':' +
                       date.getMinutes().toString().padStart(2, '0');
            });
            window.charts.profitChart.data.datasets[0].data = profitTrend.map(p => p.profit);
            window.charts.profitChart.update('none');
        }

        // Update price chart
        if (data.market_data && data.market_data.prices && window.charts.priceChart) {
            const prices = data.market_data.prices;
            const timestamp = new Date().toLocaleTimeString();

            window.charts.priceChart.data.labels.shift();
            window.charts.priceChart.data.labels.push(timestamp);

            window.charts.priceChart.data.datasets[0].data.shift();
            window.charts.priceChart.data.datasets[0].data.push(prices.baseswap_v3 || 0);

            window.charts.priceChart.data.datasets[1].data.shift();
            window.charts.priceChart.data.datasets[1].data.push(prices.aerodrome_v3 || 0);

            window.charts.priceChart.update('none');
        }

        // Update liquidity chart
        if (data.market_data && data.market_data.liquidity && window.charts.liquidityChart) {
            const liquidity = data.market_data.liquidity;

            window.charts.liquidityChart.data.datasets[0].data = [
                (liquidity.baseswap_v3 || 0) / 1e18,
                (liquidity.aerodrome_v3 || 0) / 1e18
            ];

            window.charts.liquidityChart.update('none');

            if (document.getElementById('liquidity-update')) {
                document.getElementById('liquidity-update').textContent =
                    'Last updated: ' + new Date().toLocaleString();
            }
        }
    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');

    // Add update frequency display if it doesn't exist
    if (!document.getElementById('update-frequency-container')) {
        const container = document.createElement('div');
        container.id = 'update-frequency-container';
        container.className = 'text-xs text-gray-500 mt-1';
        container.innerHTML = 'Update frequency: <span id="update-frequency">0.00 updates/sec</span>';

        const statusElement = document.getElementById('connection-status');
        if (statusElement && statusElement.parentNode) {
            statusElement.parentNode.appendChild(container);
        }
    }

    // Connect to WebSockets for real-time updates
    connectWebSockets();

    // Also fetch initial data via HTTP as a fallback
    fetchInitialData();

    // Set up periodic check for stale data
    setInterval(checkDataFreshness, 5000);
});

// Fetch initial data via HTTP API
async function fetchInitialData() {
    try {
        const baseUrl = getBaseUrl();
        console.log('Fetching initial metrics from', `${baseUrl}/api/metrics/current`);
        const response = await fetch(`${baseUrl}/api/metrics/current`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        // Log received data for debugging
        console.log('Received initial metrics data:', data);

        // Update UI with initial data
        updateDashboard(data);

        // Also fetch other data
        fetchSystemData();
        fetchTradesData();
        fetchMarketData();
    } catch (error) {
        console.error('Error fetching initial data:', error);
    }
}

// Fetch system data
async function fetchSystemData() {
    try {
        const baseUrl = getBaseUrl();
        const response = await fetch(`${baseUrl}/api/system/status`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        dashboardState.system = data;
        updateSystemDisplay(data);
    } catch (error) {
        console.error('Error fetching system data:', error);
    }
}

// Fetch trades data
async function fetchTradesData() {
    try {
        const baseUrl = getBaseUrl();
        const response = await fetch(`${baseUrl}/api/metrics/trades`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        dashboardState.trades = data.trades || [];
        updateTradesDisplay(dashboardState.trades);
    } catch (error) {
        console.error('Error fetching trades data:', error);
    }
}

// Fetch market data
async function fetchMarketData() {
    try {
        const baseUrl = getBaseUrl();
        const response = await fetch(`${baseUrl}/api/metrics/market`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        dashboardState.market = data;
        updateMarketDisplay(data);
    } catch (error) {
        console.error('Error fetching market data:', error);
    }
}

// Check if data is fresh
function checkDataFreshness() {
    if (!dashboardState.lastUpdate) return;

    const now = Date.now();
    const lastUpdate = new Date(dashboardState.lastUpdate).getTime();
    const timeSinceUpdate = now - lastUpdate;

    // If no updates in 10 seconds, show warning
    if (timeSinceUpdate > 10000) {
        document.getElementById('connection-status').textContent = 'Stale Data';
        document.getElementById('connection-status').className = 'text-sm text-yellow-500 mt-2';

        // If no updates in 30 seconds, try to reconnect
        if (timeSinceUpdate > 30000) {
            console.warn('Data is stale (30+ seconds old). Reconnecting WebSockets...');
            window.wsManager.disconnectAll();
            setTimeout(() => window.wsManager.connectAll(), 1000);
        }
    }
}

// Cleanup when page is unloaded
window.addEventListener('beforeunload', () => {
    console.log('Closing all WebSocket connections...');
    window.wsManager.disconnectAll();
});
