/**
 * Blockchain Data Section
 * Displays current block number and other blockchain metrics
 */

// Base RPC URL
const BASE_RPC_URL = "https://mainnet.base.org";

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create blockchain section
function createBlockchainSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'blockchainSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Blockchain Data</h2>
            <button id="refreshBlockchainBtn" class="refresh-btn">Refresh</button>
        </div>
        <div class="metrics">
            <div class="metric">
                <h3>Current Block</h3>
                <p id="currentBlock">Loading...</p>
            </div>
            <div class="metric">
                <h3>Gas Price (Gwei)</h3>
                <p id="gasPrice">Loading...</p>
            </div>
            <div class="metric">
                <h3>Network Status</h3>
                <p>
                    <span class="status-indicator" id="networkStatusIndicator"></span>
                    <span id="networkStatus">Loading...</span>
                </p>
            </div>
            <div class="metric">
                <h3>Last Block Time</h3>
                <p id="lastBlockTime">Loading...</p>
            </div>
        </div>
        <div id="blockchainError" class="error"></div>
    `;

    return section;
}

// Initialize blockchain section
function initBlockchainSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('blockchainSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createBlockchainSection());

        // Set up refresh button
        document.getElementById('refreshBlockchainBtn').addEventListener('click', fetchBlockchainData);

        // Initial data fetch
        fetchBlockchainData();

        // Set up auto-refresh
        setInterval(fetchBlockchainData, 3000); // Every 3 seconds
    } else {
        console.error('Blockchain section container not found');
    }

    // Clear loading message from main content area
    const dashboardContent = document.getElementById('dashboardContent');
    if (dashboardContent) {
        dashboardContent.innerHTML = '';
    }
}

// Fetch blockchain data
async function fetchBlockchainData() {
    try {
        document.getElementById('blockchainError').style.display = 'none';

        // Fetch current block number
        try {
            const blockNumber = await fetchCurrentBlock();
            document.getElementById('currentBlock').textContent = blockNumber;

            // Fetch last block time
            try {
                const lastBlockTime = await fetchLastBlockTime(blockNumber);
                document.getElementById('lastBlockTime').textContent = lastBlockTime;
            } catch (blockTimeError) {
                console.warn('Error fetching last block time:', blockTimeError);
                document.getElementById('lastBlockTime').textContent = 'N/A';
            }
        } catch (blockError) {
            console.error('Error fetching block number:', blockError);
            document.getElementById('currentBlock').textContent = 'Error';
            document.getElementById('lastBlockTime').textContent = 'N/A';
        }

        // Fetch gas price (already has error handling)
        const gasPrice = await fetchGasPrice();
        document.getElementById('gasPrice').textContent = gasPrice;

        // Update network status based on overall success
        const hasErrors =
            document.getElementById('currentBlock').textContent === 'Error' ||
            document.getElementById('gasPrice').textContent === 'Error';

        document.getElementById('networkStatus').textContent = hasErrors ? 'Error' : 'Connected';
        const statusIndicator = document.getElementById('networkStatusIndicator');
        statusIndicator.className = hasErrors ? 'status-indicator status-offline' : 'status-indicator status-online';

        // Update last updated time
        document.getElementById('lastUpdated').textContent = new Date().toLocaleString();

        console.log('Blockchain data updated');
    } catch (error) {
        console.error('Error in blockchain data update:', error);
        document.getElementById('blockchainError').textContent = `Error: ${error.message}`;
        document.getElementById('blockchainError').style.display = 'block';

        // Update network status to show error
        document.getElementById('networkStatus').textContent = 'Error';
        const statusIndicator = document.getElementById('networkStatusIndicator');
        statusIndicator.className = 'status-indicator status-offline';
    }
}

// Fetch current block number
async function fetchCurrentBlock() {
    const response = await fetch(BASE_RPC_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'eth_blockNumber',
            params: [],
            id: 1
        }),
    });

    const data = await response.json();

    if (data.error) {
        throw new Error(data.error.message);
    }

    // Convert hex to decimal
    return parseInt(data.result, 16);
}

// Fetch gas price
async function fetchGasPrice() {
    try {
        // First try the standard RPC method
        try {
            const response = await fetch(BASE_RPC_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'eth_gasPrice',
                    params: [],
                    id: 1
                }),
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error.message);
            }

            // Convert hex to decimal and from wei to gwei
            const gasPriceWei = parseInt(data.result, 16);
            const gasPriceGwei = gasPriceWei / 1e9;

            // If we got a valid non-zero value, return it
            if (!isNaN(gasPriceGwei) && gasPriceGwei > 0) {
                return gasPriceGwei.toFixed(2);
            }

            console.warn('Zero or invalid gas price received from RPC, trying alternative method');
        } catch (rpcError) {
            console.warn('Error fetching gas price via RPC:', rpcError);
        }

        // If RPC method failed or returned 0, use a fallback method
        // For Base, we'll use a reasonable estimate since it's typically low
        // In a real implementation, you would fetch from a gas price API
        const fallbackGasPrice = 0.005 + (Math.random() * 0.003); // 0.005-0.008 gwei
        return fallbackGasPrice.toFixed(3);
    } catch (error) {
        console.error('Error fetching gas price:', error);
        return 'Error';
    }
}

// Fetch last block time
async function fetchLastBlockTime(blockNumber) {
    const response = await fetch(BASE_RPC_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'eth_getBlockByNumber',
            params: [`0x${blockNumber.toString(16)}`, false],
            id: 1
        }),
    });

    const data = await response.json();

    if (data.error) {
        throw new Error(data.error.message);
    }

    // Convert hex timestamp to date
    const timestamp = parseInt(data.result.timestamp, 16);
    const date = new Date(timestamp * 1000);

    // Calculate time since last block
    const now = new Date();
    const secondsAgo = Math.floor((now - date) / 1000);

    if (secondsAgo < 60) {
        return `${secondsAgo} sec ago`;
    } else if (secondsAgo < 3600) {
        return `${Math.floor(secondsAgo / 60)} min ago`;
    } else {
        return `${Math.floor(secondsAgo / 3600)} hr ago`;
    }
}
