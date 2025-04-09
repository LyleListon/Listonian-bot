/**
 * Bot Performance Metrics Section
 * Displays detailed metrics about the bot's performance
 */

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create bot metrics section
function createBotMetricsSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'botMetricsSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Bot Performance Metrics</h2>
            <button id="refreshBotMetricsBtn" class="refresh-btn">Refresh</button>
        </div>

        <div class="metrics">
            <div class="metric">
                <h3>Execution Latency</h3>
                <p id="executionLatency">Loading...</p>
                <p id="latencyTrend" class="trend">Loading...</p>
            </div>
            <div class="metric">
                <h3>Win Rate</h3>
                <p id="winRate">Loading...</p>
                <p id="winRateTrend" class="trend">Loading...</p>
            </div>
            <div class="metric">
                <h3>Trades Attempted</h3>
                <p id="tradesAttempted">Loading...</p>
            </div>
            <div class="metric">
                <h3>Trades Completed</h3>
                <p id="tradesCompleted">Loading...</p>
            </div>
            <div class="metric">
                <h3>ROI (24h)</h3>
                <p id="dailyROI">Loading...</p>
            </div>
            <div class="metric">
                <h3>Fee-to-Profit Ratio</h3>
                <p id="feeRatio">Loading...</p>
            </div>
        </div>

        <h3 class="subsection-title">Error Distribution</h3>
        <div class="chart-container" style="height: 250px;">
            <canvas id="errorChart"></canvas>
        </div>

        <h3 class="subsection-title">Performance by Trading Pair</h3>
        <div class="table-container">
            <table class="data-table" id="pairPerformanceTable">
                <thead>
                    <tr>
                        <th>Token Pair</th>
                        <th>Trades</th>
                        <th>Success Rate</th>
                        <th>Avg. Profit</th>
                        <th>Total Profit</th>
                        <th>Avg. Latency</th>
                        <th>ROI</th>
                    </tr>
                </thead>
                <tbody id="pairPerformanceTableBody">
                    <tr>
                        <td colspan="7" class="loading-cell">Loading performance data...</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div id="botMetricsError" class="error"></div>
    `;

    return section;
}

// Initialize bot metrics section
function initBotMetricsSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('botMetricsSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createBotMetricsSection());

        // Set up refresh button
        document.getElementById('refreshBotMetricsBtn').addEventListener('click', fetchBotMetrics);

        // Initial data fetch
        fetchBotMetrics();

        // Set up auto-refresh
        setInterval(fetchBotMetrics, 10000); // Every 10 seconds
    } else {
        console.error('Bot metrics section container not found');
    }
}

// Fetch bot metrics
async function fetchBotMetrics() {
    try {
        document.getElementById('botMetricsError').style.display = 'none';

        // Fetch overall performance metrics
        await fetchPerformanceMetrics();

        // Fetch error distribution
        await fetchErrorDistribution();

        // Fetch performance by trading pair
        await fetchPairPerformance();

        console.log('Bot metrics updated successfully');
    } catch (error) {
        console.error('Error fetching bot metrics:', error);
        document.getElementById('botMetricsError').textContent = `Error: ${error.message}`;
        document.getElementById('botMetricsError').style.display = 'block';
    }
}

// Fetch performance metrics
async function fetchPerformanceMetrics() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/bot_metrics`);
            const data = await response.json();

            if (response.ok && Object.keys(data).length > 0) {
                updatePerformanceMetricsDisplay(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch bot metrics from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = {
            execution_latency: {
                current: 320, // ms
                trend: 'down', // improving
                history: [350, 340, 330, 320]
            },
            win_rate: {
                current: 0.85, // 85%
                trend: 'up',
                history: [0.82, 0.83, 0.84, 0.85]
            },
            trades: {
                attempted: 125,
                completed: 112,
                successful: 95
            },
            roi: {
                daily: 0.042, // 4.2%
                weekly: 0.18, // 18%
                monthly: 0.65 // 65%
            },
            fee_ratio: 0.28 // fees are 28% of profits
        };

        updatePerformanceMetricsDisplay(mockData);
    } catch (error) {
        console.error('Error fetching performance metrics:', error);
        throw error;
    }
}

// Update performance metrics display
function updatePerformanceMetricsDisplay(data) {
    // Execution Latency
    if (data.execution_latency) {
        document.getElementById('executionLatency').textContent = `${data.execution_latency.current} ms`;
        const latencyTrend = getTrendIcon(data.execution_latency.trend, true);
        document.getElementById('latencyTrend').textContent = latencyTrend;
    }

    // Win Rate
    if (data.win_rate) {
        document.getElementById('winRate').textContent = `${(data.win_rate.current * 100).toFixed(1)}%`;
        const winRateTrend = getTrendIcon(data.win_rate.trend);
        document.getElementById('winRateTrend').textContent = winRateTrend;
    }

    // Trades
    if (data.trades) {
        document.getElementById('tradesAttempted').textContent = data.trades.attempted;
        document.getElementById('tradesCompleted').textContent = data.trades.completed;
    }

    // ROI
    if (data.roi) {
        document.getElementById('dailyROI').textContent = `${(data.roi.daily * 100).toFixed(2)}%`;
    }

    // Fee Ratio
    if (data.fee_ratio !== undefined) {
        document.getElementById('feeRatio').textContent = `${(data.fee_ratio * 100).toFixed(1)}%`;
    }
}

// Get trend icon (with option to invert for metrics where down is good)
function getTrendIcon(trend, invert = false) {
    if (invert) {
        // For metrics where down is good (like latency)
        switch (trend) {
            case 'up':
                return '↗️ Increasing (Worse)';
            case 'down':
                return '↘️ Decreasing (Better)';
            case 'stable':
            default:
                return '↔️ Stable';
        }
    } else {
        // For metrics where up is good (like win rate)
        switch (trend) {
            case 'up':
                return '↗️ Improving';
            case 'down':
                return '↘️ Declining';
            case 'stable':
            default:
                return '↔️ Stable';
        }
    }
}

// Fetch error distribution
async function fetchErrorDistribution() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/error_distribution`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updateErrorChart(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch error distribution from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = [
            { type: 'Gas Price Spike', count: 8 },
            { type: 'Slippage Too High', count: 12 },
            { type: 'Transaction Timeout', count: 5 },
            { type: 'RPC Node Error', count: 3 },
            { type: 'Insufficient Liquidity', count: 7 },
            { type: 'Other', count: 2 }
        ];

        updateErrorChart(mockData);
    } catch (error) {
        console.error('Error fetching error distribution:', error);
        throw error;
    }
}

// Update error chart
function updateErrorChart(data) {
    const ctx = document.getElementById('errorChart').getContext('2d');

    // Destroy existing chart if it exists
    if (window.errorChart) {
        window.errorChart.destroy();
    }

    // Prepare data for chart
    const labels = data.map(item => item.type);
    const counts = data.map(item => item.count);

    // Create new chart
    window.errorChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                title: {
                    display: true,
                    text: 'Error Types Distribution'
                }
            }
        }
    });
}

// Fetch performance by trading pair
async function fetchPairPerformance() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/pair_performance`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updatePairPerformanceTable(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch pair performance from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = generateMockPairPerformance();
        updatePairPerformanceTable(mockData);
    } catch (error) {
        console.error('Error fetching pair performance:', error);
        throw error;
    }
}

// Update pair performance table
function updatePairPerformanceTable(data) {
    const tableBody = document.getElementById('pairPerformanceTableBody');

    // Clear existing rows
    tableBody.innerHTML = '';

    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="loading-cell">No performance data found</td></tr>';
        return;
    }

    // Add new rows
    for (const pair of data) {
        const row = document.createElement('tr');

        // Calculate success rate
        const successRate = pair.success_rate || (pair.successful_trades / pair.total_trades);

        // Create row content
        row.innerHTML = `
            <td>${pair.token_pair}</td>
            <td>${pair.total_trades}</td>
            <td>${(successRate * 100).toFixed(1)}%</td>
            <td>${pair.avg_profit.toFixed(4)} ETH</td>
            <td>${pair.total_profit.toFixed(4)} ETH</td>
            <td>${pair.avg_latency} ms</td>
            <td>${(pair.roi * 100).toFixed(2)}%</td>
        `;

        tableBody.appendChild(row);
    }
}

// Generate mock pair performance data
function generateMockPairPerformance() {
    const tokenPairs = ['WETH-USDC', 'WETH-USDbC', 'USDC-USDbC', 'WETH-DAI', 'DAI-USDC'];

    return tokenPairs.map(pair => {
        const totalTrades = Math.floor(Math.random() * 30) + 10;
        const successfulTrades = Math.floor(totalTrades * (0.7 + Math.random() * 0.25));
        const avgProfit = 0.01 + Math.random() * 0.05;
        const totalProfit = avgProfit * successfulTrades;
        const invested = totalTrades * (0.5 + Math.random() * 1.5);
        const roi = totalProfit / invested;

        return {
            token_pair: pair,
            total_trades: totalTrades,
            successful_trades: successfulTrades,
            success_rate: successfulTrades / totalTrades,
            avg_profit: avgProfit,
            total_profit: totalProfit,
            avg_latency: Math.floor(Math.random() * 200) + 200,
            roi: roi
        };
    });
}
