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

// Update metrics
async function updateMetrics() {
    try {
        const baseUrl = getBaseUrl();
        console.log('Fetching metrics from', `${baseUrl}/api/metrics/current`);
        const response = await fetch(`${baseUrl}/api/metrics/current`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Log received data for debugging
        console.log('Received metrics data:', data);

        // Update performance metrics
        document.getElementById('performance-metrics').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <p class="text-sm text-gray-600">Total Profit (ETH)</p>
                    <p class="text-lg font-semibold">${formatNumber(data.metrics.total_profit_eth || 0, 4)}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Success Rate</p>
                    <p class="text-lg font-semibold">${formatNumber((data.metrics.success_rate || 0) * 100)}%</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Gas Price (Gwei)</p>
                    <p class="text-lg font-semibold">${formatNumber(data.gas_price || 0)}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Total Trades</p>
                    <p class="text-lg font-semibold">${data.metrics.total_trades || 0}</p>
                </div>
            </div>
        `;

        // Update opportunities
        document.getElementById('active-opportunities').innerHTML = data.opportunities && data.opportunities.length > 0
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

        // Update system status
        document.getElementById('system-status').innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center">
                    <div class="w-3 h-3 rounded-full ${data.system.cpu_usage < 80 ? 'bg-green-500' : 'bg-red-500'} mr-2"></div>
                    <span>System Status: ${data.system.cpu_usage < 80 ? 'Healthy' : 'High Load'}</span>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Memory Usage</p>
                    <p class="text-lg font-semibold">${formatNumber(data.system.memory_usage || 0)}%</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">CPU Usage</p>
                    <p class="text-lg font-semibold">${formatNumber(data.system.cpu_usage || 0)}%</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Disk Usage</p>
                    <p class="text-lg font-semibold">${formatNumber(data.system.disk_usage || 0)}%</p>
                </div>
            </div>
        `;

        // Update recent trades
        document.getElementById('recent-trades').innerHTML = data.trade_history && data.trade_history.length > 0
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

        // Update last update time
        const lastUpdate = new Date(data.timestamp);
        document.getElementById('lastUpdate').textContent = `Last Update: ${lastUpdate.toLocaleString()}`;

        // Update system status indicator
        const systemStatus = document.getElementById('systemStatus');
        if (systemStatus) {
            const statusDot = systemStatus.querySelector('.rounded-full');
            const statusText = systemStatus.querySelector('span');
            const isHealthy = data.system.cpu_usage < 80 && data.system.memory_usage < 80;
            
            statusDot.className = `w-3 h-3 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'} mr-2`;
            statusText.textContent = isHealthy ? 'System Healthy' : 'System Overloaded';
        }

    } catch (error) {
        console.error('Error updating metrics:', error);
        // Show error state in UI
        document.getElementById('performance-metrics').innerHTML = '<p class="text-red-600">Error loading metrics</p>';
        document.getElementById('active-opportunities').innerHTML = '<p class="text-red-600">Error loading opportunities</p>';
        document.getElementById('system-status').innerHTML = '<p class="text-red-600">Error loading system status</p>';
        document.getElementById('recent-trades').innerHTML = '<p class="text-red-600">Error loading trades</p>';
    }
}

// Update data every 5 seconds
setInterval(updateMetrics, 5000);

// Initial update when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    updateMetrics();
});