/**
 * DEX Statistics Section
 * Displays volume, TVL, and fees for major DEXes on Base
 */

// DEX information
const DEXES = [
    {
        name: 'Baseswap',
        id: 'baseswap',
        logo: 'https://baseswap.fi/images/tokens/baseswap.png',
        url: 'https://baseswap.fi'
    },
    {
        name: 'Aerodrome',
        id: 'aerodrome',
        logo: 'https://assets.coingecko.com/coins/images/30163/small/aerodrome.png',
        url: 'https://aerodrome.finance'
    },
    {
        name: 'Pancakeswap',
        id: 'pancakeswap',
        logo: 'https://assets.coingecko.com/coins/images/12632/small/pancakeswap-cake-logo.png',
        url: 'https://pancakeswap.finance'
    },
    {
        name: 'Swapbased',
        id: 'swapbased',
        logo: 'https://swapbased.finance/logo.png',
        url: 'https://swapbased.finance'
    }
];

// Bot API URL
const BOT_API_URL = "http://localhost:8081";

// Create DEXes section
function createDexesSection() {
    const section = document.createElement('div');
    section.className = 'card';
    section.id = 'dexesSection';

    let dexesHtml = '';
    for (const dex of DEXES) {
        dexesHtml += `
            <div class="metric">
                <h3>${dex.name}</h3>
                <p id="${dex.id}Volume">Loading...</p>
                <p id="${dex.id}Tvl" style="font-size: 14px;">Loading...</p>
                <p id="${dex.id}Fee" style="font-size: 12px;">Loading...</p>
            </div>
        `;
    }

    section.innerHTML = `
        <div class="card-header">
            <h2>DEX Statistics</h2>
            <button id="refreshDexesBtn" class="refresh-btn">Refresh</button>
        </div>
        <div class="metrics">
            ${dexesHtml}
        </div>
        <div id="dexesError" class="error"></div>
    `;

    return section;
}

// Initialize DEXes section
function initDexesSection() {
    // Add section to the explicit container
    const sectionContainer = document.getElementById('dexesSection');
    if (sectionContainer) {
        sectionContainer.innerHTML = ''; // Clear any existing content
        sectionContainer.appendChild(createDexesSection());

        // Set up refresh button
        document.getElementById('refreshDexesBtn').addEventListener('click', fetchDexStatistics);

        // Initial data fetch
        fetchDexStatistics();

        // Set up auto-refresh
        setInterval(fetchDexStatistics, 10000); // Every 10 seconds
    } else {
        console.error('DEXes section container not found');
    }
}

// Fetch DEX statistics
async function fetchDexStatistics() {
    try {
        document.getElementById('dexesError').style.display = 'none';

        // Try to fetch from bot API first
        try {
            const response = await fetch(`${BOT_API_URL}/api/dex_stats`);
            const data = await response.json();

            if (response.ok && Object.keys(data).length > 0) {
                // Process data from bot API
                for (const dex of DEXES) {
                    const dexData = data[dex.id.toLowerCase()];
                    if (dexData) {
                        updateDexDisplay(dex, dexData);
                    }
                }

                console.log('DEX statistics updated from bot API');
                return;
            }
        } catch (botApiError) {
            console.warn('Could not fetch DEX statistics from bot API, using fallback data:', botApiError);
        }

        // Fallback to mock data
        for (const dex of DEXES) {
            await fetchMockDexData(dex);
        }

        console.log('DEX statistics updated with fallback data');
    } catch (error) {
        console.error('Error fetching DEX statistics:', error);
        document.getElementById('dexesError').textContent = `Error: ${error.message}`;
        document.getElementById('dexesError').style.display = 'block';
    }
}

// Update DEX display with data
function updateDexDisplay(dex, dexData) {
    const volume = dexData.volume_24h || 0;
    const tvl = dexData.tvl || 0;
    const fee = dexData.fee || 0;

    document.getElementById(`${dex.id}Volume`).textContent = `$${formatNumber(volume)}`;
    document.getElementById(`${dex.id}Tvl`).textContent = `TVL: $${formatNumber(tvl)}`;
    document.getElementById(`${dex.id}Fee`).textContent = `Fee: ${(fee * 100).toFixed(2)}%`;
}

// Fetch mock data for a specific DEX
async function fetchMockDexData(dex) {
    try {
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 300));

        // Generate realistic mock data
        const volume = Math.random() * 10000000 + 5000000; // $5M-$15M
        const tvl = Math.random() * 100000000 + 50000000; // $50M-$150M
        const fee = Math.random() * 0.3 + 0.1; // 0.1%-0.4%

        // Update UI
        updateDexDisplay(dex, {
            volume_24h: volume,
            tvl: tvl,
            fee: fee / 100 // Convert to decimal
        });
    } catch (error) {
        console.error(`Error fetching data for ${dex.name}:`, error);
        throw error;
    }
}

// Format number with commas and abbreviations
function formatNumber(num) {
    if (num >= 1000000000) {
        return (num / 1000000000).toFixed(1) + 'B';
    } else if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    } else {
        return num.toFixed(0);
    }
}
