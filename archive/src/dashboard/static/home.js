// Initialize charts
let profitChart = null;
let volumeChart = null;

function initializeCharts() {
    const profitCtx = document.getElementById('profit-chart').getContext('2d');
    const volumeCtx = document.getElementById('volume-chart').getContext('2d');

    // Common time scale options
    const timeScaleOptions = {
        type: 'time',
        time: {
            unit: 'hour',
            displayFormats: {
                hour: 'HH:mm'
            }
        },
        title: {
            display: true,
            text: 'Time'
        }
    };

    // Profit Chart
    profitChart = new Chart(profitCtx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Cumulative Profit',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: timeScaleOptions,
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Profit (USD)'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Profit History'
                }
            }
        }
    });

    // Volume Chart
    volumeChart = new Chart(volumeCtx, {
        type: 'bar',
        data: {
            datasets: [{
                label: 'Trade Volume',
                data: [],
                backgroundColor: 'rgb(54, 162, 235)',
                borderColor: 'rgb(54, 162, 235)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: timeScaleOptions,
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Trades'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Trade Volume'
                }
            }
        }
    });
}

// Update metrics
function updateMetrics(metrics) {
    document.getElementById('total-trades').textContent = metrics.total_trades || 0;
    document.getElementById('trades-24h').textContent = metrics.trades_24h || 0;
    document.getElementById('success-rate').textContent = `${(metrics.success_rate || 0).toFixed(1)}%`;
    document.getElementById('failed-trades').textContent = metrics.failed_trades || 0;
    document.getElementById('total-profit').textContent = `$${(metrics.total_profit || 0).toFixed(2)}`;
    document.getElementById('profit-24h').textContent = `$${(metrics.profit_24h || 0).toFixed(2)}`;
    document.getElementById('active-opportunities').textContent = metrics.active_opportunities || 0;
    document.getElementById('rejected-opportunities').textContent = metrics.rejected_opportunities || 0;
}

// Update trades list
function updateTrades(trade) {
    const container = document.getElementById('recent-trades');
    if (!container) return;

    const element = document.createElement('div');
    element.className = 'list-group-item';
    element.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h6 class="mb-0">${trade.path.join(' → ')}</h6>
                <small class="text-muted">${new Date(trade.timestamp).toLocaleString()}</small>
            </div>
            <span class="badge ${trade.profit >= 0 ? 'bg-success' : 'bg-danger'}">
                ${trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}%
            </span>
        </div>
    `;

    container.insertBefore(element, container.firstChild);
    if (container.children.length > 5) {
        container.removeChild(container.lastChild);
    }
}

// Update opportunities list
function updateOpportunities(opportunity) {
    const container = document.getElementById('current-opportunities');
    if (!container) return;

    const element = document.createElement('div');
    element.className = 'list-group-item';
    element.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h6 class="mb-0">${opportunity.path.join(' → ')}</h6>
                <small class="text-muted">Volume: $${opportunity.volume.toFixed(2)}</small>
            </div>
            <span class="badge bg-primary">+${opportunity.profit.toFixed(2)}%</span>
        </div>
    `;

    container.insertBefore(element, container.firstChild);
    if (container.children.length > 5) {
        container.removeChild(container.lastChild);
    }
}

// Show alert
function showAlert(alert) {
    const container = document.getElementById('alerts-container');
    if (!container) return;

    const element = document.createElement('div');
    element.className = `alert alert-${alert.type} alert-dismissible fade show`;
    element.innerHTML = `
        ${alert.message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    container.insertBefore(element, container.firstChild);
    setTimeout(() => element.remove(), 5000);
}

// Update chart data
function updateCharts(data) {
    if (!profitChart || !volumeChart) {
        initializeCharts();
    }

    // Update profit chart
    if (data.profit_history) {
        profitChart.data.datasets[0].data = data.profit_history.map(point => ({
            x: new Date(point[0]),
            y: point[1]
        }));
        profitChart.update();
    }

    // Update volume chart
    if (data.volume_history) {
        volumeChart.data.datasets[0].data = data.volume_history.map(point => ({
            x: new Date(point[0]),
            y: point[1]
        }));
        volumeChart.update();
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
});

// Export functions for use in common.js
window.updateMetrics = updateMetrics;
window.updateTrades = updateTrades;
window.updateOpportunities = updateOpportunities;
window.showAlert = showAlert;
window.updateCharts = updateCharts;
