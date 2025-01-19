// Dashboard functionality
const errorMessage = document.getElementById('error-message');

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

async function updateMetrics() {
    try {
        const response = await fetch('/api/metrics');
        if (!response.ok) throw new Error('Failed to fetch metrics');

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        // Update metrics if elements exist
        const elements = {
            'total-trades': data.total_trades,
            'success-rate': data.success_rate ? `${data.success_rate}%` : 'N/A',
            'total-profit': data.total_profit ? `${data.total_profit.toFixed(4)} ETH` : '0.0000 ETH',
            'active-opportunities': data.length || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
    } catch (error) {
        console.error('Error updating metrics:', error);
        showError('Failed to update metrics: ' + error.message);
    }
}

async function updateOpportunities() {
    try {
        const response = await fetch('/api/opportunities');
        if (!response.ok) throw new Error('Failed to fetch');

        const opportunities = await response.json();
        if (opportunities.error) throw new Error(opportunities.error);

        const container = document.getElementById('opportunities');
        if (!container) return;

        if (!Array.isArray(opportunities) || opportunities.length === 0) {
            container.innerHTML = '<p>No current opportunities</p>';
            return;
        }

        container.innerHTML = opportunities.map(opp => `
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
    } catch (error) {
        console.error('Error updating opportunities:', error);
        showError('Failed to update opportunities: ' + error.message);
    }
}

function formatNumber(num) {
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

// Update every 5 seconds
setInterval(() => {
    updateMetrics();
    updateOpportunities();
}, 5000);

// Initial update
updateMetrics();
updateOpportunities();
