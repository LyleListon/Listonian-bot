// Dashboard functionality
document.addEventListener('DOMContentLoaded', () => {
    // Get shared socket instance
    const socket = window.dashboardSocket;
    if (!socket) {
        console.error('Socket.IO not initialized');
        return;
    }

    // Handle state updates (opportunities and gas)
    socket.on('state_update', (data) => {
        try {
            console.log('State update:', data);
            if (data.opportunities) {
                updateOpportunities(data);
            }
            if (data.gas) {
                updateGasMetrics(data.gas);
            }
        } catch (error) {
            console.error('Error handling state update:', error);
            showError('Failed to update state: ' + error.message);
        }
    });

    // Handle metrics updates
    socket.on('metrics_update', (data) => {
        try {
            console.log('Metrics update:', data);
            updateMetrics(data);
        } catch (error) {
            console.error('Error handling metrics update:', error);
            showError('Failed to update metrics: ' + error.message);
        }
    });

    // Handle market updates
    socket.on('market_update', (data) => {
        try {
            console.log('Market update:', data);
            updateMarketConditions(data);
        } catch (error) {
            console.error('Error handling market update:', error);
            showError('Failed to update market conditions: ' + error.message);
        }
    });

    function updateMetrics(data) {
        if (!data) return;

        // Update analytics metrics
        if (data.analytics) {
            const analytics = data.analytics;
            updateElement('total-profit', analytics.total_profit ? `$${analytics.total_profit.toFixed(2)}` : '$0.00');
            updateElement('success-rate', analytics.success_rate ? `${analytics.success_rate}%` : 'N/A');
        }

        // Update performance metrics
        if (data.performance) {
            const performance = data.performance;
            updateElement('active-opportunities', performance.active_opportunities ? performance.active_opportunities.length : 0);
            
            // Update profit chart if exists
            if (window.profitChart && performance.profit_history) {
                window.profitChart.data.labels = performance.profit_history.map(h => new Date(h.timestamp).toLocaleTimeString());
                window.profitChart.data.datasets[0].data = performance.profit_history.map(h => h.profit);
                window.profitChart.update();
            }
        }

        // Update DEX metrics
        if (data.dex_metrics) {
            updateDexMetrics(data.dex_metrics);
        }
    }

    function updateGasMetrics(gas) {
        if (!gas) return;

        updateElement('gas-used', `${gas.analysis.total_cost || 0} ETH`);

        // Update gas chart if exists
        if (window.gasChart) {
            const timestamp = new Date().toLocaleTimeString();
            window.gasChart.data.labels.push(timestamp);
            window.gasChart.data.datasets[0].data.push(gas.current_price);
            
            // Keep last 20 data points
            if (window.gasChart.data.labels.length > 20) {
                window.gasChart.data.labels.shift();
                window.gasChart.data.datasets[0].data.shift();
            }
            
            window.gasChart.update();
        }
    }

    function updateOpportunities(data) {
        if (!data || !data.opportunities) return;

        const container = document.getElementById('opportunities');
        if (!container) return;

        if (!Array.isArray(data.opportunities) || data.opportunities.length === 0) {
            container.innerHTML = '<p>No current opportunities</p>';
            return;
        }

        container.innerHTML = data.opportunities.map(opp => `
            <div class="opportunity">
                <div class="pair">${opp.token_in}/${opp.token_out}</div>
                <div class="dex">
                    <span class="badge bg-info">${opp.base_dex}</span>
                </div>
                <div class="prices">
                    Expected Out: ${parseFloat(opp.expected_out).toFixed(4)}
                    ${opp.profit_percentage ? `<div class="profit">+${opp.profit_percentage.toFixed(2)}%</div>` : ''}
                </div>
                ${opp.volume_24h ? `
                    <div class="volume">
                        24h Volume: $${formatNumber(opp.volume_24h)}
                    </div>
                ` : ''}
                ${opp.liquidity_score ? `
                    <div class="liquidity">
                        Liquidity: ${(opp.liquidity_score * 100).toFixed(1)}%
                    </div>
                ` : ''}
                ${opp.trend ? `
                    <div class="trend">
                        <span class="badge bg-${getTrendBadgeColor(opp.trend)}">
                            ${opp.trend}
                        </span>
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    function updateMarketConditions(data) {
        if (!data || !data.data) return;

        const container = document.getElementById('market-conditions');
        if (!container) return;

        const conditions = Object.entries(data.data).map(([token, condition]) => `
            <div class="market-condition">
                <div class="token">${token}</div>
                <div class="metrics">
                    <div>Price: $${parseFloat(condition.price).toFixed(4)}</div>
                    <div>Volume: $${formatNumber(condition.volume_24h)}</div>
                    <div>Liquidity: $${formatNumber(condition.liquidity)}</div>
                </div>
            </div>
        `).join('');

        container.innerHTML = conditions || '<p>No market data available</p>';
    }

    function updateDexMetrics(metrics) {
        const container = document.getElementById('dex-metrics');
        if (!container) return;

        container.innerHTML = Object.entries(metrics).map(([dex, data]) => `
            <div class="dex-metric">
                <div class="dex-name">${dex}</div>
                <div class="metrics">
                    <div>Volume: $${formatNumber(data.volume_24h)}</div>
                    <div>TVL: $${formatNumber(data.tvl)}</div>
                    ${data.success_rate ? `<div>Success Rate: ${data.success_rate}%</div>` : ''}
                </div>
            </div>
        `).join('');
    }

    function updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }

    function formatNumber(num) {
        if (num === undefined || num === null) return '0';
        return new Intl.NumberFormat('en-US', {
            maximumFractionDigits: 0
        }).format(num);
    }

    function getTrendBadgeColor(trend) {
        switch(trend.toLowerCase()) {
            case 'bullish':
                return 'success';
            case 'bearish':
                return 'danger';
            case 'neutral':
                return 'warning';
            default:
                return 'secondary';
        }
    }

    // Initialize charts after DOM is loaded
    // Initialize charts
    window.profitChart = new Chart(document.getElementById('profit-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Profit (USD)',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    window.gasChart = new Chart(document.getElementById('gas-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Gas Price (Gwei)',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});
