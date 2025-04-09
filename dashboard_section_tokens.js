/**
 * Token Prices Section
 * Displays current prices and 24h changes for key tokens
 */

// Token addresses on Base
const TOKEN_ADDRESSES = {
    WETH: '0x4200000000000000000000000000000000000006',
    USDC: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    USDbC: '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
    DAI: '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb'
};

// Coingecko API for token prices
const COINGECKO_API_URL = 'https://api.coingecko.com/api/v3';
const COINGECKO_IDS = {
    WETH: 'ethereum',
    USDC: 'usd-coin',
    USDbC: 'usd-coin', // Using USDC as proxy for USDbC
    DAI: 'dai'
};

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create tokens section
function createTokensSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'tokensSection';

    section.innerHTML = `
        <div class="card-header">
            <h2>Token Prices</h2>
            <button id="refreshTokensBtn" class="refresh-btn">Refresh</button>
        </div>
        <div class="metrics">
            <div class="metric">
                <h3>WETH</h3>
                <p id="wethPrice">Loading...</p>
                <p id="wethChange" style="font-size: 14px;">Loading...</p>
            </div>
            <div class="metric">
                <h3>USDC</h3>
                <p id="usdcPrice">Loading...</p>
                <p id="usdcChange" style="font-size: 14px;">Loading...</p>
            </div>
            <div class="metric">
                <h3>USDbC</h3>
                <p id="usdbcPrice">Loading...</p>
                <p id="usdbcChange" style="font-size: 14px;">Loading...</p>
            </div>
            <div class="metric">
                <h3>DAI</h3>
                <p id="daiPrice">Loading...</p>
                <p id="daiChange" style="font-size: 14px;">Loading...</p>
            </div>
        </div>
        <div id="tokensError" class="error"></div>
    `;

    return section;
}

// Initialize tokens section
function initTokensSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('tokensSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createTokensSection());

        // Set up refresh button
        document.getElementById('refreshTokensBtn').addEventListener('click', fetchTokenPrices);

        // Initial data fetch
        fetchTokenPrices();

        // Set up auto-refresh
        setInterval(fetchTokenPrices, 5000); // Every 5 seconds
    } else {
        console.error('Tokens section container not found');
    }
}

// Fetch token prices
async function fetchTokenPrices() {
    try {
        document.getElementById('tokensError').style.display = 'none';

        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/token_prices`);
            const data = await response.json();

            if (response.ok && Object.keys(data).length > 0) {
                // Process data from bot API
                for (const [token, tokenData] of Object.entries(data)) {
                    const tokenId = token.toLowerCase();
                    updateTokenPrice(tokenId, {
                        usd: tokenData.price || 0,
                        usd_24h_change: tokenData.change_24h || 0
                    });
                }

                console.log('Token prices updated from bot API');
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch token prices from bot API, falling back to Coingecko:', botApiError);
        }

        // Fallback to Coingecko
        const tokenIds = Object.values(COINGECKO_IDS).join(',');
        const response = await fetch(`${COINGECKO_API_URL}/simple/price?ids=${tokenIds}&vs_currencies=usd&include_24hr_change=true`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error('Failed to fetch token prices');
        }

        // Update WETH
        updateTokenPrice('weth', data[COINGECKO_IDS.WETH]);

        // Update USDC
        updateTokenPrice('usdc', data[COINGECKO_IDS.USDC]);

        // Update USDbC (using USDC as proxy)
        updateTokenPrice('usdbc', data[COINGECKO_IDS.USDbC]);

        // Update DAI
        updateTokenPrice('dai', data[COINGECKO_IDS.DAI]);

        console.log('Token prices updated from Coingecko');
    } catch (error) {
        console.error('Error fetching token prices:', error);
        document.getElementById('tokensError').textContent = `Error: ${error.message}`;
        document.getElementById('tokensError').style.display = 'block';
    }
}

// Update token price display
function updateTokenPrice(tokenId, priceData) {
    if (!priceData) {
        return;
    }

    const price = priceData.usd;
    const change = priceData.usd_24h_change;

    // Update price
    document.getElementById(`${tokenId}Price`).textContent = `$${price.toFixed(2)}`;

    // Update change
    const changeElement = document.getElementById(`${tokenId}Change`);
    const changeText = change >= 0 ? `+${change.toFixed(2)}%` : `${change.toFixed(2)}%`;
    const changeColor = change >= 0 ? 'green' : 'red';

    changeElement.textContent = changeText;
    changeElement.style.color = changeColor;
}
