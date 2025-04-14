/**
 * Dashboard module
 * Handles dashboard-specific functionality
 */

/**
 * Load dashboard data from the API
 */
async function loadDashboardData() {
    try {
        // Load metrics
        const metricsResponse = await fetchAPI(API.metrics);
        if (metricsResponse.success) {
            state.metrics = metricsResponse.data;
        }
        
        // Load recent trades
        const tradesResponse = await fetchAPI(`${API.trades}?limit=5`);
        if (tradesResponse.success) {
            state.trades = tradesResponse.data.trades;
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

/**
 * Set up dashboard event listeners
 */
function setupDashboardEvents() {
    // No specific events for the dashboard page
}

/**
 * Update the dashboard UI with current data
 */
function updateDashboardUI() {
    // Update status indicator
    updateStatusIndicator();
    
    // Update metrics
    updateMetricsUI();
    
    // Update charts
    updateChartsUI();
    
    // Update recent trades table
    updateRecentTradesUI();
}

/**
 * Update metrics UI elements
 */
function updateMetricsUI() {
    // Trading metrics
    const tradingMetrics = state.metrics?.trading || {};
    
    if (document.getElementById('total-trades')) {
        document.getElementById('total-trades').textContent = tradingMetrics.total_trades || 0;
    }
    
    if (document.getElementById('success-rate')) {
        const successRate = tradingMetrics.success_rate || 0;
        document.getElementById('success-rate').textContent = formatPercentage(successRate);
    }
    
    if (document.getElementById('net-profit')) {
        const netProfit = tradingMetrics.net_profit_usd || 0;
        document.getElementById('net-profit').textContent = formatCurrency(netProfit);
    }
    
    // Performance metrics
    const performanceMetrics = state.metrics?.performance || {};
    
    if (document.getElementById('opportunities-found')) {
        document.getElementById('opportunities-found').textContent = performanceMetrics.opportunities_found || 0;
    }
    
    if (document.getElementById('execution-rate')) {
        const executionRate = performanceMetrics.execution_rate || 0;
        document.getElementById('execution-rate').textContent = formatPercentage(executionRate);
    }
    
    if (document.getElementById('avg-execution-time')) {
        const avgExecutionTime = performanceMetrics.average_execution_time_ms || 0;
        document.getElementById('avg-execution-time').textContent = `${avgExecutionTime}ms`;
    }
    
    // System metrics
    const systemMetrics = state.metrics?.system || {};
    
    if (document.getElementById('uptime')) {
        const uptime = systemMetrics.uptime || 0;
        document.getElementById('uptime').textContent = formatDuration(uptime);
    }
    
    if (document.getElementById('cpu-usage')) {
        const cpuUsage = systemMetrics.cpu_usage || 0;
        document.getElementById('cpu-usage').textContent = formatPercentage(cpuUsage);
    }
    
    if (document.getElementById('memory-usage')) {
        const memoryUsage = systemMetrics.memory_usage || 0;
        document.getElementById('memory-usage').textContent = `${Math.round(memoryUsage)}MB`;
    }
}

/**
 * Update charts UI elements
 */
function updateChartsUI() {
    // Create or update profit chart
    createProfitChart();
    
    // Create or update DEX chart
    createDexChart();
}

/**
 * Create or update the profit chart
 */
function createProfitChart() {
    const profitChartCanvas = document.getElementById('profit-chart');
    
    if (!profitChartCanvas) {
        return;
    }
    
    // Sample data for the chart
    // In a real implementation, this would come from the API
    const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const data = {
        labels: labels,
        datasets: [{
            label: 'Profit (USD)',
            data: [12, 19, 3, 5, 2, 3],
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };
    
    // Check if chart already exists
    if (state.charts.profitChart) {
        // Update existing chart
        state.charts.profitChart.data = data;
        state.charts.profitChart.update();
    } else {
        // Create new chart
        state.charts.profitChart = new Chart(profitChartCanvas, {
            type: 'line',
            data: data,
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
    }
}

/**
 * Create or update the DEX chart
 */
function createDexChart() {
    const dexChartCanvas = document.getElementById('dex-chart');
    
    if (!dexChartCanvas) {
        return;
    }
    
    // Sample data for the chart
    // In a real implementation, this would come from the API
    const data = {
        labels: ['Uniswap V3', 'PancakeSwap', 'SushiSwap', 'Curve', 'Balancer'],
        datasets: [{
            label: 'Opportunities',
            data: [12, 19, 3, 5, 2],
            backgroundColor: [
                'rgba(255, 99, 132, 0.2)',
                'rgba(54, 162, 235, 0.2)',
                'rgba(255, 206, 86, 0.2)',
                'rgba(75, 192, 192, 0.2)',
                'rgba(153, 102, 255, 0.2)'
            ],
            borderColor: [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)'
            ],
            borderWidth: 1
        }]
    };
    
    // Check if chart already exists
    if (state.charts.dexChart) {
        // Update existing chart
        state.charts.dexChart.data = data;
        state.charts.dexChart.update();
    } else {
        // Create new chart
        state.charts.dexChart = new Chart(dexChartCanvas, {
            type: 'pie',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

/**
 * Update recent trades table
 */
function updateRecentTradesUI() {
    const tableBody = document.getElementById('recent-trades-table');
    
    if (!tableBody) {
        return;
    }
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Check if there are trades
    if (!state.trades || state.trades.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5" class="text-center">No trades yet</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Add trades to table
    state.trades.forEach(trade => {
        const row = document.createElement('tr');
        
        // Create path string
        const path = trade.steps?.map(step => `${step.input_token} → ${step.output_token}`).join(' → ') || 'N/A';
        
        // Set row class based on status
        if (trade.status === 'success') {
            row.classList.add('table-success');
        } else if (trade.status === 'failed') {
            row.classList.add('table-danger');
        } else if (trade.status === 'pending') {
            row.classList.add('table-warning');
        }
        
        // Add cells
        row.innerHTML = `
            <td>${trade.id}</td>
            <td>${formatDate(trade.timestamp)}</td>
            <td>${path}</td>
            <td>${trade.status}</td>
            <td>${formatCurrency(trade.net_profit_usd || 0)}</td>
        `;
        
        tableBody.appendChild(row);
    });
}
