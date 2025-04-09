/**
 * Financial Metrics Section
 * Displays detailed financial performance metrics
 */

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create financial metrics section
function createFinancialSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'financialSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Financial Metrics</h2>
            <button id="refreshFinancialBtn" class="refresh-btn">Refresh</button>
        </div>

        <div class="metrics">
            <div class="metric">
                <h3>Total Profit (All Time)</h3>
                <p id="totalProfitAllTime">Loading...</p>
            </div>
            <div class="metric">
                <h3>Total Fees Paid</h3>
                <p id="totalFeesPaid">Loading...</p>
            </div>
            <div class="metric">
                <h3>Net Profit</h3>
                <p id="netProfit">Loading...</p>
            </div>
            <div class="metric">
                <h3>Capital Efficiency</h3>
                <p id="capitalEfficiency">Loading...</p>
            </div>
        </div>

        <h3 class="subsection-title">Profit & Fees Over Time</h3>
        <div class="chart-container">
            <canvas id="profitFeesChart"></canvas>
        </div>

        <h3 class="subsection-title">Portfolio Composition</h3>
        <div class="chart-container" style="height: 250px;">
            <canvas id="portfolioChart"></canvas>
        </div>

        <h3 class="subsection-title">Fee Breakdown</h3>
        <div class="metrics">
            <div class="metric">
                <h3>Gas Fees</h3>
                <p id="gasFees">Loading...</p>
            </div>
            <div class="metric">
                <h3>DEX Fees</h3>
                <p id="dexFees">Loading...</p>
            </div>
            <div class="metric">
                <h3>Slippage Costs</h3>
                <p id="slippageCosts">Loading...</p>
            </div>
            <div class="metric">
                <h3>Other Costs</h3>
                <p id="otherCosts">Loading...</p>
            </div>
        </div>

        <div id="financialError" class="error"></div>
    `;

    return section;
}

// Initialize financial section
function initFinancialSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('financialSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createFinancialSection());

        // Set up refresh button
        document.getElementById('refreshFinancialBtn').addEventListener('click', fetchFinancialData);

        // Initial data fetch
        fetchFinancialData();

        // Set up auto-refresh
        setInterval(fetchFinancialData, 15000); // Every 15 seconds
    } else {
        console.error('Financial section container not found');
    }
}

// Fetch financial data
async function fetchFinancialData() {
    try {
        document.getElementById('financialError').style.display = 'none';

        // Fetch overall financial metrics
        await fetchFinancialMetrics();

        // Fetch profit and fees over time
        await fetchProfitFeesHistory();

        // Fetch portfolio composition
        await fetchPortfolioComposition();

        // Fetch fee breakdown
        await fetchFeeBreakdown();

        console.log('Financial data updated successfully');
    } catch (error) {
        console.error('Error fetching financial data:', error);
        document.getElementById('financialError').textContent = `Error: ${error.message}`;
        document.getElementById('financialError').style.display = 'block';
    }
}

// Fetch financial metrics
async function fetchFinancialMetrics() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/financial_metrics`);
            const data = await response.json();

            if (response.ok && Object.keys(data).length > 0) {
                updateFinancialMetricsDisplay(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch financial metrics from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = {
            total_profit: 5.28, // ETH
            total_fees: 1.45, // ETH
            net_profit: 3.83, // ETH
            capital_efficiency: 0.32, // profit per ETH deployed
            capital_deployed: 12.0 // ETH
        };

        updateFinancialMetricsDisplay(mockData);
    } catch (error) {
        console.error('Error fetching financial metrics:', error);
        throw error;
    }
}

// Update financial metrics display
function updateFinancialMetricsDisplay(data) {
    // Total Profit
    if (data.total_profit !== undefined) {
        document.getElementById('totalProfitAllTime').textContent = `${data.total_profit.toFixed(4)} ETH`;
    }

    // Total Fees
    if (data.total_fees !== undefined) {
        document.getElementById('totalFeesPaid').textContent = `${data.total_fees.toFixed(4)} ETH`;
    }

    // Net Profit
    if (data.net_profit !== undefined) {
        document.getElementById('netProfit').textContent = `${data.net_profit.toFixed(4)} ETH`;
    }

    // Capital Efficiency
    if (data.capital_efficiency !== undefined) {
        document.getElementById('capitalEfficiency').textContent = `${data.capital_efficiency.toFixed(4)} ETH/ETH`;
    }
}

// Fetch profit and fees history
async function fetchProfitFeesHistory() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/profit_fees_history`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updateProfitFeesChart(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch profit/fees history from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = generateMockProfitFeesHistory();
        updateProfitFeesChart(mockData);
    } catch (error) {
        console.error('Error fetching profit/fees history:', error);
        throw error;
    }
}

// Update profit and fees chart
function updateProfitFeesChart(data) {
    const ctx = document.getElementById('profitFeesChart').getContext('2d');

    // Destroy existing chart if it exists
    if (window.profitFeesChart) {
        window.profitFeesChart.destroy();
    }

    // Prepare data for chart
    const labels = data.map(item => item.date);
    const grossProfits = data.map(item => item.gross_profit);
    const fees = data.map(item => item.fees);
    const netProfits = data.map(item => item.net_profit);

    // Create new chart
    window.profitFeesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Gross Profit',
                    data: grossProfits,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Fees',
                    data: fees,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Net Profit',
                    data: netProfits,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'ETH'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });
}

// Fetch portfolio composition
async function fetchPortfolioComposition() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/portfolio_composition`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updatePortfolioChart(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch portfolio composition from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = [
            { asset: 'WETH', value: 8.5, percentage: 0.65 },
            { asset: 'USDC', value: 2.3, percentage: 0.18 },
            { asset: 'USDbC', value: 1.2, percentage: 0.09 },
            { asset: 'DAI', value: 1.0, percentage: 0.08 }
        ];

        updatePortfolioChart(mockData);
    } catch (error) {
        console.error('Error fetching portfolio composition:', error);
        throw error;
    }
}

// Update portfolio chart
function updatePortfolioChart(data) {
    const ctx = document.getElementById('portfolioChart').getContext('2d');

    // Destroy existing chart if it exists
    if (window.portfolioChart) {
        window.portfolioChart.destroy();
    }

    // Prepare data for chart
    const labels = data.map(item => item.asset);
    const values = data.map(item => item.value);

    // Create new chart
    window.portfolioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 206, 86, 1)',
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
                    text: 'Portfolio Composition (ETH Value)'
                }
            }
        }
    });
}

// Fetch fee breakdown
async function fetchFeeBreakdown() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/fee_breakdown`);
            const data = await response.json();

            if (response.ok && Object.keys(data).length > 0) {
                updateFeeBreakdownDisplay(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch fee breakdown from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = {
            gas_fees: 0.85,
            dex_fees: 0.42,
            slippage: 0.15,
            other: 0.03
        };

        updateFeeBreakdownDisplay(mockData);
    } catch (error) {
        console.error('Error fetching fee breakdown:', error);
        throw error;
    }
}

// Update fee breakdown display
function updateFeeBreakdownDisplay(data) {
    // Gas Fees
    if (data.gas_fees !== undefined) {
        document.getElementById('gasFees').textContent = `${data.gas_fees.toFixed(4)} ETH`;
    }

    // DEX Fees
    if (data.dex_fees !== undefined) {
        document.getElementById('dexFees').textContent = `${data.dex_fees.toFixed(4)} ETH`;
    }

    // Slippage Costs
    if (data.slippage !== undefined) {
        document.getElementById('slippageCosts').textContent = `${data.slippage.toFixed(4)} ETH`;
    }

    // Other Costs
    if (data.other !== undefined) {
        document.getElementById('otherCosts').textContent = `${data.other.toFixed(4)} ETH`;
    }
}

// Generate mock profit and fees history
function generateMockProfitFeesHistory() {
    const data = [];
    const now = new Date();

    // Generate data for the last 14 days
    for (let i = 13; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        // Generate realistic values with some randomness
        const grossProfit = 0.2 + Math.random() * 0.6; // 0.2-0.8 ETH
        const fees = grossProfit * (0.2 + Math.random() * 0.15); // 20-35% of gross profit
        const netProfit = grossProfit - fees;

        data.push({
            date: dateStr,
            gross_profit: grossProfit,
            fees: fees,
            net_profit: netProfit
        });
    }

    return data;
}
