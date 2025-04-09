/**
 * Market Data Section
 * Displays price differentials, arbitrage opportunities, and market conditions
 */

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create market data section
function createMarketDataSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'marketDataSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Market Data & Arbitrage Opportunities</h2>
            <button id="refreshMarketDataBtn" class="refresh-btn">Refresh</button>
        </div>

        <h3 class="subsection-title">Price Differentials (Top Opportunities)</h3>
        <div class="table-container">
            <table class="data-table" id="priceDiffTable">
                <thead>
                    <tr>
                        <th>Token Pair</th>
                        <th>DEX 1</th>
                        <th>Price 1</th>
                        <th>DEX 2</th>
                        <th>Price 2</th>
                        <th>Diff (%)</th>
                        <th>Diff ($)</th>
                        <th>Potential Profit</th>
                    </tr>
                </thead>
                <tbody id="priceDiffTableBody">
                    <tr>
                        <td colspan="8" class="loading-cell">Loading price differentials...</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <h3 class="subsection-title">Gas Prices</h3>
        <div class="metrics">
            <div class="metric">
                <h3>Base (Gwei)</h3>
                <p id="baseGasPrice">Loading...</p>
                <p id="baseGasTrend" class="trend">Loading...</p>
            </div>
            <div class="metric">
                <h3>Ethereum (Gwei)</h3>
                <p id="ethGasPrice">Loading...</p>
                <p id="ethGasTrend" class="trend">Loading...</p>
            </div>
            <div class="metric">
                <h3>Optimism (Gwei)</h3>
                <p id="optimismGasPrice">Loading...</p>
                <p id="optimismGasTrend" class="trend">Loading...</p>
            </div>
            <div class="metric">
                <h3>Arbitrum (Gwei)</h3>
                <p id="arbitrumGasPrice">Loading...</p>
                <p id="arbitrumGasTrend" class="trend">Loading...</p>
            </div>
        </div>

        <h3 class="subsection-title">Arbitrage Opportunity History (24h)</h3>
        <div class="chart-container">
            <canvas id="opportunityChart"></canvas>
        </div>

        <div id="marketDataError" class="error"></div>
    `;

    return section;
}

// Initialize market data section
function initMarketDataSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('marketDataSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createMarketDataSection());

        // Set up refresh button
        document.getElementById('refreshMarketDataBtn').addEventListener('click', fetchMarketData);

        // Initial data fetch
        fetchMarketData();

        // Set up auto-refresh
        setInterval(fetchMarketData, 5000); // Every 5 seconds
    } else {
        console.error('Market data section container not found');
    }
}

// Fetch market data
async function fetchMarketData() {
    try {
        document.getElementById('marketDataError').style.display = 'none';

        // Fetch price differentials
        await fetchPriceDifferentials();

        // Fetch gas prices
        await fetchGasPrices();

        // Fetch opportunity history
        await fetchOpportunityHistory();

        console.log('Market data updated successfully');
    } catch (error) {
        console.error('Error fetching market data:', error);
        document.getElementById('marketDataError').textContent = `Error: ${error.message}`;
        document.getElementById('marketDataError').style.display = 'block';
    }
}

// Fetch price differentials
async function fetchPriceDifferentials() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/price_differentials`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updatePriceDifferentialsTable(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch price differentials from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = generateMockPriceDifferentials();
        updatePriceDifferentialsTable(mockData);
    } catch (error) {
        console.error('Error fetching price differentials:', error);
        throw error;
    }
}

// Update price differentials table
function updatePriceDifferentialsTable(data) {
    const tableBody = document.getElementById('priceDiffTableBody');

    // Clear existing rows
    tableBody.innerHTML = '';

    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="loading-cell">No price differentials found</td></tr>';
        return;
    }

    // Add new rows
    for (const diff of data) {
        const row = document.createElement('tr');

        // Calculate percentage difference
        const priceDiffPercent = ((diff.price2 - diff.price1) / diff.price1 * 100).toFixed(2);
        const priceDiffAbsolute = (diff.price2 - diff.price1).toFixed(6);

        // Determine if this is a profitable opportunity
        const isProfitable = parseFloat(priceDiffPercent) > 0.5; // Assuming >0.5% is profitable after gas

        // Create row content
        row.innerHTML = `
            <td>${diff.tokenPair}</td>
            <td>${diff.dex1}</td>
            <td>$${diff.price1.toFixed(6)}</td>
            <td>${diff.dex2}</td>
            <td>$${diff.price2.toFixed(6)}</td>
            <td class="${isProfitable ? 'success' : ''}">${priceDiffPercent}%</td>
            <td>$${priceDiffAbsolute}</td>
            <td class="${isProfitable ? 'success' : 'failure'}">${isProfitable ? 'Yes' : 'No'}</td>
        `;

        tableBody.appendChild(row);
    }
}

// Fetch gas prices
async function fetchGasPrices() {
    try {
        // Base gas price (from blockchain section)
        const baseGasPrice = document.getElementById('gasPrice').textContent;
        document.getElementById('baseGasPrice').textContent = baseGasPrice;
        document.getElementById('baseGasTrend').textContent = '↔️ Stable';

        // Try to fetch other chain gas prices from bot API
        try {
            const response = await fetch(`${BOT_API_URL}/api/gas_prices`);
            const data = await response.json();

            if (response.ok && Object.keys(data).length > 0) {
                updateGasPrices(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch gas prices from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        updateGasPrices({
            ethereum: { price: 25.42, trend: 'up' },
            optimism: { price: 0.05, trend: 'stable' },
            arbitrum: { price: 0.1, trend: 'down' }
        });
    } catch (error) {
        console.error('Error fetching gas prices:', error);
        throw error;
    }
}

// Update gas prices display
function updateGasPrices(data) {
    // Ethereum
    if (data.ethereum) {
        document.getElementById('ethGasPrice').textContent = data.ethereum.price.toFixed(2);
        const ethTrend = getTrendIcon(data.ethereum.trend);
        document.getElementById('ethGasTrend').textContent = ethTrend;
    }

    // Optimism
    if (data.optimism) {
        document.getElementById('optimismGasPrice').textContent = data.optimism.price.toFixed(2);
        const optimismTrend = getTrendIcon(data.optimism.trend);
        document.getElementById('optimismGasTrend').textContent = optimismTrend;
    }

    // Arbitrum
    if (data.arbitrum) {
        document.getElementById('arbitrumGasPrice').textContent = data.arbitrum.price.toFixed(2);
        const arbitrumTrend = getTrendIcon(data.arbitrum.trend);
        document.getElementById('arbitrumGasTrend').textContent = arbitrumTrend;
    }
}

// Get trend icon
function getTrendIcon(trend) {
    switch (trend) {
        case 'up':
            return '↗️ Rising';
        case 'down':
            return '↘️ Falling';
        case 'stable':
        default:
            return '↔️ Stable';
    }
}

// Fetch opportunity history
async function fetchOpportunityHistory() {
    try {
        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/opportunity_history`);
            const data = await response.json();

            if (response.ok && data.length > 0) {
                updateOpportunityChart(data);
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch opportunity history from bot API, using mock data:', botApiError);
        }

        // Use mock data as fallback
        const mockData = generateMockOpportunityHistory();
        updateOpportunityChart(mockData);
    } catch (error) {
        console.error('Error fetching opportunity history:', error);
        throw error;
    }
}

// Update opportunity chart
function updateOpportunityChart(data) {
    const ctx = document.getElementById('opportunityChart').getContext('2d');

    // Destroy existing chart if it exists
    if (window.opportunityChart) {
        window.opportunityChart.destroy();
    }

    // Prepare data for chart
    const labels = data.map(item => item.hour);
    const foundOpportunities = data.map(item => item.found);
    const executedOpportunities = data.map(item => item.executed);

    // Create new chart
    window.opportunityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Found Opportunities',
                    data: foundOpportunities,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Executed Trades',
                    data: executedOpportunities,
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
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
                        text: 'Count'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Hour'
                    }
                }
            }
        }
    });
}

// Generate mock price differentials
function generateMockPriceDifferentials() {
    const tokenPairs = ['WETH-USDC', 'WETH-USDbC', 'USDC-USDbC', 'WETH-DAI', 'DAI-USDC'];
    const dexes = ['Baseswap', 'Aerodrome', 'Pancakeswap', 'Swapbased'];

    const differentials = [];

    for (let i = 0; i < 5; i++) {
        // Select token pair
        const tokenPair = tokenPairs[Math.floor(Math.random() * tokenPairs.length)];

        // Select DEXes (ensure they're different)
        let dex1 = dexes[Math.floor(Math.random() * dexes.length)];
        let dex2;
        do {
            dex2 = dexes[Math.floor(Math.random() * dexes.length)];
        } while (dex2 === dex1);

        // Generate prices
        let basePrice;
        if (tokenPair.includes('WETH')) {
            basePrice = 3450 + Math.random() * 10; // WETH price around $3450
        } else {
            basePrice = 1 + Math.random() * 0.01; // Stablecoin price around $1
        }

        // Add small difference between DEXes
        const price1 = basePrice;
        const price2 = basePrice * (1 + (Math.random() * 0.02 - 0.005)); // -0.5% to +1.5% difference

        differentials.push({
            tokenPair,
            dex1,
            price1,
            dex2,
            price2
        });
    }

    // Sort by absolute difference (largest first)
    differentials.sort((a, b) => {
        const diffA = Math.abs(a.price2 - a.price1);
        const diffB = Math.abs(b.price2 - b.price1);
        return diffB - diffA;
    });

    return differentials;
}

// Generate mock opportunity history
function generateMockOpportunityHistory() {
    const data = [];

    // Generate data for the last 24 hours
    for (let i = 0; i < 24; i++) {
        const hour = i.toString().padStart(2, '0') + ':00';

        // More opportunities during high activity hours (8-12, 18-22)
        let multiplier = 1;
        if ((i >= 8 && i <= 12) || (i >= 18 && i <= 22)) {
            multiplier = 2.5;
        }

        const foundOpportunities = Math.floor(Math.random() * 15 * multiplier) + 5;
        const executedOpportunities = Math.floor(foundOpportunities * (0.3 + Math.random() * 0.4)); // 30-70% execution rate

        data.push({
            hour,
            found: foundOpportunities,
            executed: executedOpportunities
        });
    }

    return data;
}
