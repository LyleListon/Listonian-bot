/**
 * Recent Trades Section
 * Displays recent trades executed by the bot
 */

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create trades section
function createTradesSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'tradesSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Recent Trades</h2>
            <button id="refreshTradesBtn" class="refresh-btn">Refresh</button>
        </div>
        <div id="tradesLoading" class="loading">Loading trades...</div>
        <table id="tradesTable" class="trades" style="display: none;">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Token Pair</th>
                    <th>DEX 1</th>
                    <th>DEX 2</th>
                    <th>Amount</th>
                    <th>Profit</th>
                    <th>Gas Cost</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="tradesTableBody">
            </tbody>
        </table>
        <div id="tradesError" class="error"></div>
    `;

    return section;
}

// Initialize trades section
function initTradesSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('tradesSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createTradesSection());

        // Set up refresh button
        document.getElementById('refreshTradesBtn').addEventListener('click', fetchTradesData);

        // Initial data fetch
        fetchTradesData();

        // Set up auto-refresh
        setInterval(fetchTradesData, 5000); // Every 5 seconds
    } else {
        console.error('Trades section container not found');
    }
}

// Fetch trades data
async function fetchTradesData() {
    try {
        console.log('Fetching trades data from API...');
        document.getElementById('tradesError').style.display = 'none';
        document.getElementById('tradesLoading').style.display = 'block';
        document.getElementById('tradesTable').style.display = 'none';

        // Fetch from bot API
        console.log(`Fetching from ${BOT_API_URL}/api/trades`);
        const response = await fetch(`${BOT_API_URL}/api/trades`);
        console.log('API response status:', response.status);

        const data = await response.json();
        console.log('API response data:', data);

        if (response.ok) {
            // Update UI with real trades data
            console.log('Updating table with data');
            updateTradesTable(data);
            console.log('Trades data updated from bot API');
        } else {
            throw new Error(`API returned status: ${response.status}`);
        }
    } catch (error) {
        console.error('Error fetching trades data:', error);
        document.getElementById('tradesError').textContent = `Error: ${error.message}`;
        document.getElementById('tradesError').style.display = 'block';
        document.getElementById('tradesLoading').style.display = 'none';
    }
}

// No longer needed - using real data only

// Update trades table
function updateTradesTable(trades) {
    const tableBody = document.getElementById('tradesTableBody');
    const tradesTable = document.getElementById('tradesTable');
    const tradesLoading = document.getElementById('tradesLoading');

    // Clear existing rows
    tableBody.innerHTML = '';

    // Handle case where API returns an array directly or nested in an object
    let tradesArray = Array.isArray(trades) ? trades : (trades.trades || []);

    if (!tradesArray || tradesArray.length === 0) {
        tradesLoading.textContent = 'No trades found';
        tradesTable.style.display = 'none';
        tradesLoading.style.display = 'block';
        return;
    }

    // Add new rows
    for (const trade of tradesArray) {
        const row = document.createElement('tr');

        // Extract trade data
        const tradeTime = new Date(trade.timestamp);
        const timeFormatted = tradeTime.toLocaleString();

        // Extract token pair and DEXes
        let tokenPair, dex1, dex2;

        if (trade.opportunity) {
            // Format with opportunity object
            tokenPair = trade.opportunity.token_pair || 'Unknown';
            dex1 = trade.opportunity.dex_1 || 'Unknown';
            dex2 = trade.opportunity.dex_2 || 'Unknown';
        } else {
            // Direct format
            tokenPair = trade.token_pair || 'Unknown';
            dex1 = trade.dex_1 || 'Unknown';
            dex2 = trade.dex_2 || 'Unknown';
        }

        // Extract other fields
        const amount = trade.amount || 0;
        const profit = trade.profit || 0;
        const gasCost = trade.gas_cost || 0;
        const success = trade.success !== undefined ? trade.success : true;

        // Create row content
        row.innerHTML = `
            <td>${timeFormatted}</td>
            <td>${tokenPair}</td>
            <td>${dex1}</td>
            <td>${dex2}</td>
            <td>${typeof amount === 'number' ? amount.toFixed(2) : amount} ETH</td>
            <td>${typeof profit === 'number' ? profit.toFixed(4) : profit} ETH</td>
            <td>${typeof gasCost === 'number' ? gasCost.toFixed(4) : gasCost} ETH</td>
            <td class="${success ? 'success' : 'failure'}">${success ? 'Success' : 'Failed'}</td>
        `;

        tableBody.appendChild(row);
    }

    // Show table, hide loading
    tradesTable.style.display = 'table';
    tradesLoading.style.display = 'none';

    // Log success
    console.log(`Successfully displayed ${tradesArray.length} trades`);
}
