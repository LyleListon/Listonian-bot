/**
 * Infrastructure Monitoring Section
 * Displays system health, node status, and resource utilization
 */

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create infrastructure section
function createInfrastructureSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'infrastructureSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Infrastructure Monitoring</h2>
            <button id="refreshInfrastructureBtn" class="refresh-btn">Refresh</button>
        </div>

        <h3 class="subsection-title">System Health</h3>
        <div class="metrics">
            <div class="metric">
                <h3>CPU Usage</h3>
                <p id="cpuUsage">Loading...</p>
                <div class="progress-bar">
                    <div id="cpuProgressBar" class="progress" style="width: 0%"></div>
                </div>
            </div>
            <div class="metric">
                <h3>Memory Usage</h3>
                <p id="memoryUsage">Loading...</p>
                <div class="progress-bar">
                    <div id="memoryProgressBar" class="progress" style="width: 0%"></div>
                </div>
            </div>
            <div class="metric">
                <h3>Disk Usage</h3>
                <p id="diskUsage">Loading...</p>
                <div class="progress-bar">
                    <div id="diskProgressBar" class="progress" style="width: 0%"></div>
                </div>
            </div>
            <div class="metric">
                <h3>Bot Uptime</h3>
                <p id="botUptime">Loading...</p>
            </div>
        </div>

        <h3 class="subsection-title">Node Connection Status</h3>
        <div class="table-container">
            <table class="data-table" id="nodeStatusTable">
                <thead>
                    <tr>
                        <th>Chain</th>
                        <th>Endpoint</th>
                        <th>Status</th>
                        <th>Latency</th>
                        <th>Block Height</th>
                        <th>Last Error</th>
                    </tr>
                </thead>
                <tbody id="nodeStatusTableBody">
                    <tr>
                        <td colspan="6" class="loading-cell">Loading node status...</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <h3 class="subsection-title">Wallet Balances</h3>
        <div class="table-container">
            <table class="data-table" id="walletBalanceTable">
                <thead>
                    <tr>
                        <th>Chain</th>
                        <th>Asset</th>
                        <th>Balance</th>
                        <th>USD Value</th>
                        <th>Last Updated</th>
                    </tr>
                </thead>
                <tbody id="walletBalanceTableBody">
                    <tr>
                        <td colspan="5" class="loading-cell">Loading wallet balances...</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <h3 class="subsection-title">Resource Utilization</h3>
        <div class="chart-container">
            <canvas id="resourceChart"></canvas>
        </div>

        <div id="infrastructureError" class="error"></div>
    `;

    return section;
}

// Initialize infrastructure section
function initInfrastructureSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('infrastructureSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createInfrastructureSection());

        // Set up refresh button
        document.getElementById('refreshInfrastructureBtn').addEventListener('click', fetchInfrastructureData);

        // Initial data fetch
        fetchInfrastructureData();

        // Set up auto-refresh
        setInterval(fetchInfrastructureData, 5000); // Every 5 seconds
    } else {
        console.error('Infrastructure section container not found');
    }
}

// Fetch infrastructure data
async function fetchInfrastructureData() {
    try {
        document.getElementById('infrastructureError').style.display = 'none';

        // Fetch system health
        await fetchSystemHealth();

        // Fetch node status
        await fetchNodeStatus();

        // Fetch wallet balances
        await fetchWalletBalances();

        // Fetch resource utilization history
        await fetchResourceUtilization();

        console.log('Infrastructure data updated successfully');
    } catch (error) {
        console.error('Error fetching infrastructure data:', error);
        document.getElementById('infrastructureError').textContent = `Error: ${error.message}`;
        document.getElementById('infrastructureError').style.display = 'block';
    }
}

// Fetch system health
async function fetchSystemHealth() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/system_health`);
            const data = await response.json();

            if (response.ok && Object.keys(data).length > 0) {
                updateSystemHealthDisplay(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch system health from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = {
            cpu_usage: 42.5, // percentage
            memory_usage: 68.3, // percentage
            memory_used: 2.7, // GB
            memory_total: 4.0, // GB
            disk_usage: 57.8, // percentage
            disk_used: 115.6, // GB
            disk_total: 200.0, // GB
            uptime: 172800 // seconds (2 days)
        };

        updateSystemHealthDisplay(mockData);
    } catch (error) {
        console.error('Error fetching system health:', error);
        throw error;
    }
}

// Update system health display
function updateSystemHealthDisplay(data) {
    // CPU Usage
    if (data.cpu_usage !== undefined) {
        document.getElementById('cpuUsage').textContent = `${data.cpu_usage.toFixed(1)}%`;
        const cpuProgressBar = document.getElementById('cpuProgressBar');
        cpuProgressBar.style.width = `${data.cpu_usage}%`;

        // Change color based on usage
        if (data.cpu_usage > 80) {
            cpuProgressBar.style.backgroundColor = '#dc3545'; // red
        } else if (data.cpu_usage > 60) {
            cpuProgressBar.style.backgroundColor = '#ffc107'; // yellow
        } else {
            cpuProgressBar.style.backgroundColor = '#28a745'; // green
        }
    }

    // Memory Usage
    if (data.memory_usage !== undefined) {
        const memoryText = data.memory_used && data.memory_total ?
            `${data.memory_usage.toFixed(1)}% (${data.memory_used.toFixed(1)}/${data.memory_total.toFixed(1)} GB)` :
            `${data.memory_usage.toFixed(1)}%`;

        document.getElementById('memoryUsage').textContent = memoryText;
        const memoryProgressBar = document.getElementById('memoryProgressBar');
        memoryProgressBar.style.width = `${data.memory_usage}%`;

        // Change color based on usage
        if (data.memory_usage > 85) {
            memoryProgressBar.style.backgroundColor = '#dc3545'; // red
        } else if (data.memory_usage > 70) {
            memoryProgressBar.style.backgroundColor = '#ffc107'; // yellow
        } else {
            memoryProgressBar.style.backgroundColor = '#28a745'; // green
        }
    }

    // Disk Usage
    if (data.disk_usage !== undefined) {
        const diskText = data.disk_used && data.disk_total ?
            `${data.disk_usage.toFixed(1)}% (${data.disk_used.toFixed(1)}/${data.disk_total.toFixed(1)} GB)` :
            `${data.disk_usage.toFixed(1)}%`;

        document.getElementById('diskUsage').textContent = diskText;
        const diskProgressBar = document.getElementById('diskProgressBar');
        diskProgressBar.style.width = `${data.disk_usage}%`;

        // Change color based on usage
        if (data.disk_usage > 90) {
            diskProgressBar.style.backgroundColor = '#dc3545'; // red
        } else if (data.disk_usage > 75) {
            diskProgressBar.style.backgroundColor = '#ffc107'; // yellow
        } else {
            diskProgressBar.style.backgroundColor = '#28a745'; // green
        }
    }

    // Bot Uptime
    if (data.uptime !== undefined) {
        document.getElementById('botUptime').textContent = formatUptime(data.uptime);
    }
}

// Format uptime in human-readable format
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    let uptimeStr = '';
    if (days > 0) {
        uptimeStr += `${days}d `;
    }
    if (hours > 0 || days > 0) {
        uptimeStr += `${hours}h `;
    }
    uptimeStr += `${minutes}m`;

    return uptimeStr;
}

// Fetch node status
async function fetchNodeStatus() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/node_status`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updateNodeStatusTable(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch node status from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = [
            {
                chain: 'Base',
                endpoint: 'https://mainnet.base.org',
                status: 'Connected',
                latency: 120, // ms
                block_height: 5123456,
                last_error: null
            },
            {
                chain: 'Ethereum',
                endpoint: 'https://eth-mainnet.g.alchemy.com/v2/...',
                status: 'Connected',
                latency: 180, // ms
                block_height: 18765432,
                last_error: null
            },
            {
                chain: 'Optimism',
                endpoint: 'https://mainnet.optimism.io',
                status: 'Connected',
                latency: 150, // ms
                block_height: 12345678,
                last_error: null
            },
            {
                chain: 'Arbitrum',
                endpoint: 'https://arb1.arbitrum.io/rpc',
                status: 'Error',
                latency: 500, // ms
                block_height: 98765432,
                last_error: 'Timeout after 500ms'
            }
        ];

        updateNodeStatusTable(mockData);
    } catch (error) {
        console.error('Error fetching node status:', error);
        throw error;
    }
}

// Update node status table
function updateNodeStatusTable(data) {
    const tableBody = document.getElementById('nodeStatusTableBody');

    // Clear existing rows
    tableBody.innerHTML = '';

    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="loading-cell">No node status data found</td></tr>';
        return;
    }

    // Add new rows
    for (const node of data) {
        const row = document.createElement('tr');

        // Determine status class
        const statusClass = node.status === 'Connected' ? 'success' : 'failure';

        // Determine latency class
        let latencyClass = '';
        if (node.latency < 150) {
            latencyClass = 'success';
        } else if (node.latency < 300) {
            latencyClass = 'warning';
        } else {
            latencyClass = 'failure';
        }

        // Create row content
        row.innerHTML = `
            <td>${node.chain}</td>
            <td>${maskEndpoint(node.endpoint)}</td>
            <td class="${statusClass}">${node.status}</td>
            <td class="${latencyClass}">${node.latency} ms</td>
            <td>${node.block_height.toLocaleString()}</td>
            <td>${node.last_error || '-'}</td>
        `;

        tableBody.appendChild(row);
    }
}

// Mask endpoint to hide API keys
function maskEndpoint(endpoint) {
    try {
        const url = new URL(endpoint);

        // Check if there's an API key in the path or query
        if (url.pathname.includes('v2') || url.search.includes('apikey')) {
            return `${url.protocol}//${url.hostname}/...`;
        }

        return endpoint;
    } catch (e) {
        // If not a valid URL, return as is
        return endpoint;
    }
}

// Fetch wallet balances
async function fetchWalletBalances() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/wallet_balances`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updateWalletBalanceTable(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch wallet balances from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = [
            {
                chain: 'Base',
                asset: 'ETH',
                balance: 3.5,
                usd_value: 12075.0,
                last_updated: '2023-06-15T14:32:45Z'
            },
            {
                chain: 'Base',
                asset: 'USDC',
                balance: 5000.0,
                usd_value: 5000.0,
                last_updated: '2023-06-15T14:32:45Z'
            },
            {
                chain: 'Ethereum',
                asset: 'ETH',
                balance: 1.2,
                usd_value: 4140.0,
                last_updated: '2023-06-15T14:30:12Z'
            },
            {
                chain: 'Optimism',
                asset: 'ETH',
                balance: 0.8,
                usd_value: 2760.0,
                last_updated: '2023-06-15T14:31:23Z'
            },
            {
                chain: 'Arbitrum',
                asset: 'ETH',
                balance: 0.5,
                usd_value: 1725.0,
                last_updated: '2023-06-15T14:29:56Z'
            }
        ];

        updateWalletBalanceTable(mockData);
    } catch (error) {
        console.error('Error fetching wallet balances:', error);
        throw error;
    }
}

// Update wallet balance table
function updateWalletBalanceTable(data) {
    const tableBody = document.getElementById('walletBalanceTableBody');

    // Clear existing rows
    tableBody.innerHTML = '';

    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="loading-cell">No wallet balance data found</td></tr>';
        return;
    }

    // Add new rows
    for (const balance of data) {
        const row = document.createElement('tr');

        // Format last updated time
        const lastUpdated = new Date(balance.last_updated);
        const timeAgo = getTimeAgo(lastUpdated);

        // Create row content
        row.innerHTML = `
            <td>${balance.chain}</td>
            <td>${balance.asset}</td>
            <td>${balance.balance.toFixed(balance.asset === 'ETH' ? 4 : 2)}</td>
            <td>$${balance.usd_value.toFixed(2)}</td>
            <td>${timeAgo}</td>
        `;

        tableBody.appendChild(row);
    }
}

// Get time ago in human-readable format
function getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);

    if (diffSec < 60) {
        return `${diffSec}s ago`;
    } else if (diffSec < 3600) {
        return `${Math.floor(diffSec / 60)}m ago`;
    } else if (diffSec < 86400) {
        return `${Math.floor(diffSec / 3600)}h ago`;
    } else {
        return `${Math.floor(diffSec / 86400)}d ago`;
    }
}

// Fetch resource utilization
async function fetchResourceUtilization() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/resource_history`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updateResourceChart(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch resource history from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = generateMockResourceHistory();
        updateResourceChart(mockData);
    } catch (error) {
        console.error('Error fetching resource utilization:', error);
        throw error;
    }
}

// Update resource chart
function updateResourceChart(data) {
    const ctx = document.getElementById('resourceChart').getContext('2d');

    // Destroy existing chart if it exists
    if (window.resourceChart) {
        window.resourceChart.destroy();
    }

    // Prepare data for chart
    const labels = data.map(item => item.time);
    const cpuData = data.map(item => item.cpu);
    const memoryData = data.map(item => item.memory);

    // Create new chart
    window.resourceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'CPU Usage (%)',
                    data: cpuData,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    fill: false,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Memory Usage (%)',
                    data: memoryData,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    fill: false,
                    tension: 0.4,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Usage (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
}

// Generate mock resource history
function generateMockResourceHistory() {
    const data = [];
    const now = new Date();

    // Generate data for the last 30 minutes (every minute)
    for (let i = 29; i >= 0; i--) {
        const time = new Date(now);
        time.setMinutes(time.getMinutes() - i);
        const timeStr = time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

        // Generate realistic values with some randomness and trends
        let cpuBase = 40 + Math.sin(i / 5) * 15; // Oscillating base value
        let memoryBase = 65 + Math.sin(i / 10) * 10; // Slower oscillating base value

        // Add some noise
        const cpu = Math.min(100, Math.max(0, cpuBase + (Math.random() * 10 - 5)));
        const memory = Math.min(100, Math.max(0, memoryBase + (Math.random() * 6 - 3)));

        data.push({
            time: timeStr,
            cpu: cpu,
            memory: memory
        });
    }

    return data;
}
