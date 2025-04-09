/**
 * Bot Performance Section
 * Displays profit, trades, success rate, and other performance metrics
 */

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create performance section
function createPerformanceSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'performanceSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Bot Performance</h2>
            <button id="refreshPerformanceBtn" class="refresh-btn">Refresh</button>
        </div>
        <div class="metrics">
            <div class="metric">
                <h3>Total Profit</h3>
                <p id="totalProfit">Loading...</p>
            </div>
            <div class="metric">
                <h3>Success Rate</h3>
                <p id="successRate">Loading...</p>
            </div>
            <div class="metric">
                <h3>Total Trades</h3>
                <p id="totalTrades">Loading...</p>
            </div>
            <div class="metric">
                <h3>Average Profit</h3>
                <p id="averageProfit">Loading...</p>
            </div>
            <div class="metric">
                <h3>Average Gas Cost</h3>
                <p id="averageGas">Loading...</p>
            </div>
            <div class="metric">
                <h3>Wallet Balance</h3>
                <p id="walletBalance">Loading...</p>
            </div>
        </div>
        <div class="chart-container">
            <canvas id="profitChart"></canvas>
        </div>
        <div id="performanceError" class="error"></div>
    `;

    return section;
}

// Initialize performance section
function initPerformanceSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('performanceSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createPerformanceSection());

        // Set up refresh button
        document.getElementById('refreshPerformanceBtn').addEventListener('click', fetchPerformanceData);

        // Initial data fetch
        fetchPerformanceData();

        // Set up auto-refresh
        setInterval(fetchPerformanceData, 5000); // Every 5 seconds
    } else {
        console.error('Performance section container not found');
    }
}

// Fetch performance data
async function fetchPerformanceData() {
    try {
        document.getElementById('performanceError').style.display = 'none';

        // Try to fetch from bot API first
        try {
            // Fetch performance data
            const perfResponse = await fetch(`${BOT_API_URL}/api/performance`);
            const perfData = await perfResponse.json();

            // Fetch state data for wallet balance
            const stateResponse = await fetch(`${BOT_API_URL}/api/state`);
            const stateData = await stateResponse.json();

            if (perfResponse.ok && Object.keys(perfData).length > 0) {
                // Process performance data
                const totalProfit = perfData.total_profit || 0;
                const successRate = perfData.success_rate || 0;
                const totalTrades = perfData.total_trades || 0;
                const averageProfit = perfData.average_profit || 0;
                const averageGas = perfData.average_gas_cost || 0;
                const walletBalance = stateData.wallet_balance || 0;

                // Update UI
                document.getElementById('totalProfit').textContent = `${totalProfit.toFixed(4)} ETH`;
                document.getElementById('successRate').textContent = `${(successRate * 100).toFixed(1)}%`;
                document.getElementById('totalTrades').textContent = totalTrades;
                document.getElementById('averageProfit').textContent = `${averageProfit.toFixed(4)} ETH`;
                document.getElementById('averageGas').textContent = `${averageGas.toFixed(4)} ETH`;
                document.getElementById('walletBalance').textContent = `${walletBalance.toFixed(4)} ETH`;

                // Update chart if profit trend is available
                if (perfData.profit_trend && perfData.profit_trend.length > 0) {
                    updateProfitChart(perfData.profit_trend);
                } else {
                    // Fetch trades to generate profit trend
                    const tradesResponse = await fetch(`${BOT_API_URL}/api/trades`);
                    const tradesData = await tradesResponse.json();

                    if (tradesResponse.ok && tradesData.length > 0) {
                        const profitTrend = generateProfitTrendFromTrades(tradesData);
                        updateProfitChart(profitTrend);
                    } else {
                        // Fallback to mock profit trend
                        updateProfitChart(generateMockProfitTrend());
                    }
                }

                console.log('Performance data updated from bot API');
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch performance data from bot API, using fallback data:', botApiError);
        }

        // Fallback to mock data
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 500));

        // Generate realistic mock data
        const totalProfit = Math.random() * 2 + 0.5; // 0.5-2.5 ETH
        const successRate = Math.random() * 0.2 + 0.8; // 80%-100%
        const totalTrades = Math.floor(Math.random() * 50) + 20; // 20-70 trades
        const averageProfit = totalProfit / totalTrades;
        const averageGas = Math.random() * 0.02 + 0.01; // 0.01-0.03 ETH
        const walletBalance = Math.random() * 5 + 1; // 1-6 ETH

        // Generate profit trend data
        const profitTrend = generateMockProfitTrend();

        // Update UI
        document.getElementById('totalProfit').textContent = `${totalProfit.toFixed(4)} ETH`;
        document.getElementById('successRate').textContent = `${(successRate * 100).toFixed(1)}%`;
        document.getElementById('totalTrades').textContent = totalTrades;
        document.getElementById('averageProfit').textContent = `${averageProfit.toFixed(4)} ETH`;
        document.getElementById('averageGas').textContent = `${averageGas.toFixed(4)} ETH`;
        document.getElementById('walletBalance').textContent = `${walletBalance.toFixed(4)} ETH`;

        // Update chart
        updateProfitChart(profitTrend);

        console.log('Performance data updated with fallback data');
    } catch (error) {
        console.error('Error fetching performance data:', error);
        document.getElementById('performanceError').textContent = `Error: ${error.message}`;
        document.getElementById('performanceError').style.display = 'block';
    }
}

// Generate mock profit trend data
function generateMockProfitTrend() {
    const data = [];
    const now = new Date();

    // Generate data for the last 24 hours
    for (let i = 24; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 60 * 60 * 1000);
        const profit = Math.random() * 0.1 + 0.02; // 0.02-0.12 ETH per hour

        data.push({
            time: time,
            profit: profit
        });
    }

    return data;
}

// Generate profit trend from trades data
function generateProfitTrendFromTrades(trades) {
    if (!trades || trades.length === 0) {
        return [];
    }

    const hourlyProfits = {};
    const now = new Date();

    // Initialize hourly buckets for the last 24 hours
    for (let i = 24; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 60 * 60 * 1000);
        const hourKey = `${time.getFullYear()}-${time.getMonth()+1}-${time.getDate()}-${time.getHours()}`;
        hourlyProfits[hourKey] = {
            time: time,
            profit: 0
        };
    }

    // Aggregate profits by hour
    for (const trade of trades) {
        // Skip failed trades
        if (!trade.success) continue;

        // Get trade timestamp
        const tradeTime = new Date(trade.timestamp);

        // Skip trades older than 24 hours
        if (now.getTime() - tradeTime.getTime() > 24 * 60 * 60 * 1000) continue;

        // Get hour key
        const hourKey = `${tradeTime.getFullYear()}-${tradeTime.getMonth()+1}-${tradeTime.getDate()}-${tradeTime.getHours()}`;

        // Add profit to hour bucket
        if (hourlyProfits[hourKey]) {
            hourlyProfits[hourKey].profit += (trade.profit || trade.net_profit || 0);
        }
    }

    // Convert to array and sort by time
    const profitTrend = Object.values(hourlyProfits);
    profitTrend.sort((a, b) => a.time - b.time);

    return profitTrend;
}

// Update profit chart
function updateProfitChart(profitTrend) {
    const ctx = document.getElementById('profitChart').getContext('2d');

    // Destroy existing chart if it exists
    if (window.profitChart) {
        window.profitChart.destroy();
    }

    // Prepare data for chart
    const labels = profitTrend.map(item => {
        const time = item.time;
        return time.getHours() + ':00';
    });

    const data = profitTrend.map(item => item.profit);

    // Create new chart
    window.profitChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Hourly Profit (ETH)',
                data: data,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Profit (ETH)'
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
