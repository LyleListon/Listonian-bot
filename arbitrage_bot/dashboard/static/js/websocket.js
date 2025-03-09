bject has no attribute 'config'
2025-02-21 15:32:50,400 - arbitrage_bot.core.market_analyzer - ERROR - Error getting opportunities: 'BaseSwap' object has no attribute 'config'
2025-02-21 15:32:50,507 - arbitrage_bot.core.market_analyzer - ERROR - Error getting opportunities: 'BaseSwap' object has no attribute 'config'
2025-02-21 15:32:50,507 - arbitrage_bot.core.market_analyzer - ERROR - Error getting opportunities: 'BaseSwap' object has no attribute 'config'
2025-02-21 15:32:50,617 - arbitrage_bot.core.market_analyzer - ERROR - Error getting opportunities: 'BaseSwap' object has no attribute 'config'
2025-02-21 15:32:50,617 - arbitrage_bot.core.market_analyzer - ERROR - Error getting opportunities: 'BaseSwap' object has no attribute 'config'
2025-02-21 15:32:50,725 - arbitrage_bot.core.market_analyzer - ERROR - Error getting opportunities: 'BaseSwap' o// WebSocket client for dashboard
const socket = io({
    path: '/socket.io/'
});
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 5000;

// DOM elements
const connectionStatus = document.getElementById('connection-status');
const statusDot = connectionStatus ? connectionStatus.querySelector('.status-dot') : null;
const statusText = connectionStatus ? connectionStatus.querySelector('.status-text') : null;

// Charts
let priceChart = null;
let profitChart = null;
let volumeChart = null;

// Connection handling
socket.on('connect', () => {
    updateConnectionStatus('Connected', true);
    reconnectAttempts = 0;
});

socket.on('disconnect', () => {
    updateConnectionStatus('Disconnected', false);
    if (reconnectAttempts < maxReconnectAttempts) {
        setTimeout(() => {
            reconnectAttempts++;
            socket.connect();
        }, reconnectDelay);
    }
});

socket.on('connect_error', (error) => {
    updateConnectionStatus('Connection Error', false);
    console.error('Connection error:', error);
});

// New consolidated event handlers
socket.on('state_update', (data) => {
    // Update opportunities list
    if (data.opportunities) {
        updateOpportunities(data.opportunities);
    }

    // Update gas metrics
    if (data.gas) {
        updateGasMetrics(data.gas);
    }

    // Update network status
    if (data.network) {
        updateNetworkStatus(data.network);
    }
});

socket.on('metrics_update', (data) => {
    // Update analytics metrics
    if (data.analytics) {
        updateAnalytics(data.analytics);
    }

    // Update performance metrics
    if (data.performance) {
        updatePerformance(data.performance);
    }

    // Update DEX metrics
    if (data.dex_metrics) {
        updateDexStatus(data.dex_metrics);
    }
});

socket.on('market_update', (data) => {
    // Update market conditions
    if (data.market_conditions) {
        updateMarketConditions(data.market_conditions);
    }

    // Update competition metrics
    if (data.competition) {
        updateCompetition(data.competition);
    }

    // Update market analysis
    if (data.analysis) {
        updateMarketAnalysis(data.analysis);
    }
});

function updateConnectionStatus(message, connected) {
    if (statusDot && statusText) {
        statusDot.style.backgroundColor = connected ? '#4CAF50' : '#f44336';
        statusText.textContent = message;
    }
}

function updateOpportunities(opportunities) {
    const opportunitiesList = document.getElementById('opportunities-list');
    if (!opportunitiesList) return;

    if (!opportunities || !opportunities.length) {
        opportunitiesList.innerHTML = '<tr><td colspan="5" class="text-center">No active opportunities</td></tr>';
        return;
    }

    opportunitiesList.innerHTML = opportunities.map(opp => `
        <tr>
            <td>${opp.route.join(' → ')}</td>
            <td>$${opp.profit.toFixed(2)}</td>
            <td>$${opp.gas_cost.toFixed(2)}</td>
            <td>$${(opp.profit - opp.gas_cost).toFixed(2)}</td>
            <td>
                <span class="badge ${opp.status === 'active' ? 'badge-success' : 'badge-secondary'}">
                    ${opp.status}
                </span>
            </td>
        </tr>
    `).join('');

    // Update opportunity count
    const countElement = document.getElementById('active-opportunities');
    if (countElement) {
        countElement.textContent = opportunities.length;
    }
}

function updateGasMetrics(gas) {
    const gasMetrics = document.getElementById('gas-metrics');
    if (!gasMetrics) return;

    gasMetrics.innerHTML = `
        <div class="metric">
            <div class="label">Current Gas Price</div>
            <div class="value">${gas.current_price} GWEI</div>
        </div>
        <div class="metric">
            <div class="label">Optimal Gas Price</div>
            <div class="value">${gas.optimal_price} GWEI</div>
        </div>
        <div class="metric">
            <div class="label">Gas Analysis</div>
            <div class="value">${gas.analysis.recommendation}</div>
        </div>
    `;
}

function updateNetworkStatus(network) {
    const networkStatus = document.getElementById('network-status');
    if (!networkStatus) return;

    networkStatus.innerHTML = `
        <div class="metric">
            <div class="label">Block Number</div>
            <div class="value">${network.block.number}</div>
        </div>
        <div class="metric">
            <div class="label">Network Status</div>
            <div class="value ${network.status}">${network.status}</div>
        </div>
        <div class="metric">
            <div class="label">Last Block</div>
            <div class="value">${new Date(network.block.timestamp).toLocaleTimeString()}</div>
        </div>
    `;
}

function updateAnalytics(analytics) {
    // Update dashboard metrics
    if (analytics.total_trades !== undefined) {
        document.getElementById('total-trades').textContent = analytics.total_trades;
    }
    if (analytics.trades_24h !== undefined) {
        document.getElementById('trades-24h').textContent = analytics.trades_24h;
    }
    if (analytics.success_rate !== undefined) {
        document.getElementById('success-rate').textContent = `${(analytics.success_rate * 100).toFixed(1)}%`;
    }
    if (analytics.total_profit_usd !== undefined) {
        document.getElementById('total-profit').textContent = `$${analytics.total_profit_usd.toFixed(2)}`;
    }
    if (analytics.portfolio_change_24h !== undefined) {
        document.getElementById('profit-24h').textContent = `$${analytics.portfolio_change_24h.toFixed(2)}`;
    }
}

function updatePerformance(performance) {
    const performanceMetrics = document.getElementById('performance-metrics');
    if (!performanceMetrics) return;

    // Update performance metrics
    performanceMetrics.innerHTML = `
        <div class="metric">
            <div class="label">Success Rate</div>
            <div class="value">${(performance[0].success_rate * 100).toFixed(1)}%</div>
        </div>
        <div class="metric">
            <div class="label">Average Profit</div>
            <div class="value">$${formatNumber(performance[0].total_profit_usd / performance[0].total_trades)}</div>
        </div>
        <div class="metric">
            <div class="label">Portfolio Change</div>
            <div class="value ${performance[0].portfolio_change_24h >= 0 ? 'positive' : 'negative'}">
                ${formatNumber(performance[0].portfolio_change_24h)}%
            </div>
        </div>
    `;

    // Update performance charts if they exist
    if (performance[0].profit_history) {
        updateCharts(performance[0]);
    }
}

function updateDexStatus(dexMetrics) {
    const dexGrid = document.getElementById('dex-status');
    if (!dexGrid) return;

    dexGrid.innerHTML = '';
    Object.entries(dexMetrics).forEach(([name, metrics]) => {
        const dexCard = document.createElement('div');
        dexCard.className = 'dex-card';
        dexCard.innerHTML = `
            <h3>${name}</h3>
            <div class="dex-status ${metrics.active ? 'active' : 'inactive'}">
                ${metrics.active ? 'Active' : 'Inactive'}
            </div>
            <div class="dex-metrics">
                <div>Liquidity: $${formatNumber(metrics.liquidity)}</div>
                <div>24h Volume: $${formatNumber(metrics.volume_24h)}</div>
            </div>
        `;
        dexGrid.appendChild(dexCard);
    });
}

function updateMarketConditions(conditions) {
    const marketGrid = document.getElementById('market-conditions');
    if (!marketGrid) return;

    marketGrid.innerHTML = '';
    Object.entries(conditions).forEach(([token, condition]) => {
        const conditionCard = document.createElement('div');
        conditionCard.className = 'market-card';
        conditionCard.innerHTML = `
            <h3>${token}</h3>
            <div class="market-metrics">
                <div>Price: $${formatNumber(condition.price)}</div>
                <div>24h Volume: $${formatNumber(condition.volume_24h)}</div>
                <div>Trend: ${condition.trend.direction}</div>
                <div>Volatility: ${(condition.volatility_24h * 100).toFixed(2)}%</div>
            </div>
        `;
        marketGrid.appendChild(conditionCard);
    });

    // Update charts if they exist
    updateCharts(conditions);
}

function updateCompetition(competition) {
    const competitionMetrics = document.getElementById('competition-metrics');
    if (!competitionMetrics) return;

    competitionMetrics.innerHTML = `
        <div class="metric">
            <div class="label">Active Competitors</div>
            <div class="value">${competition.known_competitors}</div>
        </div>
        <div class="metric">
            <div class="label">Success Rate</div>
            <div class="value">${(competition.success_rate * 100).toFixed(1)}%</div>
        </div>
        <div class="metric">
            <div class="label">Block Reorgs</div>
            <div class="value">${competition.block_reorgs}</div>
        </div>
    `;
}

function updateMarketAnalysis(analysis) {
    const marketAnalysis = document.getElementById('market-analysis');
    if (!marketAnalysis) return;

    marketAnalysis.innerHTML = `
        <div class="metric">
            <div class="label">Market State</div>
            <div class="value">${analysis.market_state}</div>
        </div>
        <div class="metric">
            <div class="label">Competition Rate</div>
            <div class="value">${(analysis.competition.rate * 100).toFixed(1)}%</div>
        </div>
        <div class="metric">
            <div class="label">Network Congestion</div>
            <div class="value">${(analysis.network.congestion * 100).toFixed(1)}%</div>
        </div>
    `;
}

function updateCharts(data) {
    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#e0e0e0' },
        showlegend: false,
        margin: { t: 20, l: 50, r: 20, b: 30 },
        xaxis: {
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.1)',
            tickformat: '%H:%M:%S'
        },
        yaxis: {
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.1)'
        }
    };

    // Update price chart if it exists
    const priceChartElement = document.getElementById('price-chart');
    if (priceChartElement && data.WETH) {
        const priceData = [{
            x: [new Date()],
            y: [data.WETH.price],
            type: 'scatter',
            mode: 'lines',
            line: { color: '#4CAF50' }
        }];
        
        if (!priceChart) {
            priceChart = Plotly.newPlot('price-chart', priceData, layout);
        } else {
            Plotly.extendTraces('price-chart', { x: [[new Date()]], y: [[data.WETH.price]] }, [0]);
        }
    }
}

function formatNumber(num) {
    if (num >= 1e9) {
        return `${(num / 1e9).toFixed(2)}B`;
    } else if (num >= 1e6) {
        return `${(num / 1e6).toFixed(2)}M`;
    } else if (num >= 1e3) {
        return `${(num / 1e3).toFixed(2)}K`;
    }
    return num.toFixed(2);
}

// Initialize connection
socket.connect();
