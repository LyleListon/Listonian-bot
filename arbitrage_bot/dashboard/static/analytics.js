// Analytics page functionality

// Chart instances
let profitChart = null;
let tokenDistributionChart = null;
let dexVolumeChart = null;
let gasAnalysisChart = null;

// Initialize charts
function initCharts() {
    // Cumulative Profit Chart
    const profitCtx = document.getElementById('profit-chart').getContext('2d');
    profitChart = new Chart(profitCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Cumulative Profit',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => formatCurrency(value)
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => formatCurrency(context.raw)
                    }
                }
            }
        }
    });

    // Token Distribution Chart
    const tokenCtx = document.getElementById('token-distribution').getContext('2d');
    tokenDistributionChart = new Chart(tokenCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)',
                    'rgb(255, 206, 86)',
                    'rgb(75, 192, 192)',
                    'rgb(153, 102, 255)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${formatCurrency(value)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });

    // DEX Volume Chart
    const dexCtx = document.getElementById('dex-volume').getContext('2d');
    dexVolumeChart = new Chart(dexCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Volume',
                data: [],
                backgroundColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => formatCurrency(value)
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => formatCurrency(context.raw)
                    }
                }
            }
        }
    });

    // Gas Analysis Chart
    const gasCtx = document.getElementById('gas-analysis').getContext('2d');
    gasAnalysisChart = new Chart(gasCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Gas Cost',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                yAxisID: 'y1'
            }, {
                label: 'Gas Price',
                data: [],
                borderColor: 'rgb(255, 159, 64)',
                yAxisID: 'y2'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    ticks: {
                        callback: (value) => formatCurrency(value)
                    }
                },
                y2: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    ticks: {
                        callback: (value) => `${value} Gwei`
                    }
                }
            }
        }
    });
}

// Get current time range
function getTimeRange() {
    const rangeSelect = document.getElementById('time-range');
    let startDate, endDate;
    
    if (rangeSelect.value === 'custom') {
        startDate = document.getElementById('start-date').value;
        endDate = document.getElementById('end-date').value;
    } else {
        endDate = new Date();
        startDate = new Date();
        
        switch(rangeSelect.value) {
            case '24h':
                startDate.setHours(startDate.getHours() - 24);
                break;
            case '7d':
                startDate.setDate(startDate.getDate() - 7);
                break;
            case '30d':
                startDate.setDate(startDate.getDate() - 30);
                break;
        }
    }

    return {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
    };
}

// Update performance metrics
async function updateMetrics() {
    try {
        const timeRange = getTimeRange();
        const response = await fetch(`/api/analytics/performance?${new URLSearchParams(timeRange)}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('total-profit').textContent = formatCurrency(data.metrics.total_profit);
            document.getElementById('roi').textContent = formatPercentage(data.metrics.roi);
            document.getElementById('win-rate').textContent = formatPercentage(data.metrics.win_rate);
            document.getElementById('avg-trade').textContent = formatCurrency(data.metrics.avg_trade);
        }
    } catch (error) {
        console.error('Error updating metrics:', error);
        showError('Failed to update metrics');
    }
}

// Update charts
async function updateCharts() {
    try {
        const timeRange = getTimeRange();
        const response = await fetch(`/api/analytics/charts?${new URLSearchParams(timeRange)}`);
        const data = await response.json();
        
        if (data.success) {
            // Update profit chart
            profitChart.data.labels = data.profit_history.map(p => formatTimestamp(p.timestamp));
            profitChart.data.datasets[0].data = data.profit_history.map(p => p.cumulative_profit);
            profitChart.update();
            
            // Update token distribution chart
            tokenDistributionChart.data.labels = data.token_distribution.map(t => t.token);
            tokenDistributionChart.data.datasets[0].data = data.token_distribution.map(t => t.volume);
            tokenDistributionChart.update();
            
            // Update DEX volume chart
            dexVolumeChart.data.labels = data.dex_volume.map(d => d.dex);
            dexVolumeChart.data.datasets[0].data = data.dex_volume.map(d => d.volume);
            dexVolumeChart.update();
            
            // Update gas analysis chart
            gasAnalysisChart.data.labels = data.gas_history.map(g => formatTimestamp(g.timestamp));
            gasAnalysisChart.data.datasets[0].data = data.gas_history.map(g => g.gas_cost);
            gasAnalysisChart.data.datasets[1].data = data.gas_history.map(g => g.gas_price);
            gasAnalysisChart.update();
        }
    } catch (error) {
        console.error('Error updating charts:', error);
        showError('Failed to update charts');
    }
}

// Update performance analysis tables
async function updateAnalysisTables() {
    try {
        const timeRange = getTimeRange();
        const response = await fetch(`/api/analytics/analysis?${new URLSearchParams(timeRange)}`);
        const data = await response.json();
        
        if (data.success) {
            // Update time analysis table
            const timeBody = document.getElementById('time-analysis');
            timeBody.innerHTML = data.time_analysis.map(period => `
                <tr>
                    <td>${period.period}</td>
                    <td>${formatNumber(period.trades)}</td>
                    <td>${formatPercentage(period.success_rate)}</td>
                    <td>${formatCurrency(period.avg_profit)}</td>
                </tr>
            `).join('');
            
            // Update token analysis table
            const tokenBody = document.getElementById('token-analysis');
            tokenBody.innerHTML = data.token_analysis.map(token => `
                <tr>
                    <td>${token.token}</td>
                    <td>${formatCurrency(token.volume)}</td>
                    <td>${formatPercentage(token.success_rate)}</td>
                    <td>${formatCurrency(token.total_profit)}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error updating analysis tables:', error);
        showError('Failed to update analysis');
    }
}

// Update all data
function updateData() {
    updateMetrics();
    updateCharts();
    updateAnalysisTables();
}

// Initialize analytics page
document.addEventListener('DOMContentLoaded', () => {
    // Initialize time range picker
    const rangeSelect = document.getElementById('time-range');
    const customRange = document.getElementById('custom-range');
    
    rangeSelect.addEventListener('change', () => {
        if (rangeSelect.value === 'custom') {
            customRange.style.display = 'block';
        } else {
            customRange.style.display = 'none';
            updateData();
        }
    });

    // Initialize update button
    document.getElementById('update-analytics').addEventListener('click', updateData);

    // Initialize charts and load data
    initCharts();
    updateData();
    
    // Update data periodically
    setInterval(updateData, 60000); // Every minute
});
