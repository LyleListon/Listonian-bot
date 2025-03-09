// Trade history page functionality
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const dateRange = document.getElementById('date-range');
    const customDateRange = document.getElementById('custom-date-range');
    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    const statusFilter = document.getElementById('status-filter');
    const tradesList = document.getElementById('trades-list');
    const prevPage = document.getElementById('prev-page');
    const nextPage = document.getElementById('next-page');
    const pageInfo = document.getElementById('page-info');
    const volumeChart = document.getElementById('volume-history-chart');
    const profitDistChart = document.getElementById('profit-distribution-chart');

    // Pagination state
    let currentPage = 1;
    let totalPages = 1;
    const itemsPerPage = 20;

    // Chart configurations
    const chartLayout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#e0e0e0' },
        showlegend: true,
        legend: {
            x: 0,
            y: 1.1,
            orientation: 'h'
        },
        margin: { t: 20, l: 50, r: 20, b: 30 },
        xaxis: {
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.1)'
        },
        yaxis: {
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.1)'
        }
    };

    // Filter state
    let filters = {
        dateRange: '24h',
        dateFrom: null,
        dateTo: null,
        status: 'all'
    };

    // Event listeners
    dateRange.addEventListener('change', handleDateRangeChange);
    dateFrom.addEventListener('change', updateFilters);
    dateTo.addEventListener('change', updateFilters);
    statusFilter.addEventListener('change', updateFilters);
    prevPage.addEventListener('click', () => changePage(-1));
    nextPage.addEventListener('click', () => changePage(1));

    function handleDateRangeChange() {
        const value = dateRange.value;
        filters.dateRange = value;
        customDateRange.style.display = value === 'custom' ? 'block' : 'none';
        updateFilters();
    }

    function updateFilters() {
        filters = {
            dateRange: dateRange.value,
            dateFrom: dateFrom.value,
            dateTo: dateTo.value,
            status: statusFilter.value
        };
        currentPage = 1;
        requestHistoryUpdate();
    }

    function changePage(delta) {
        const newPage = currentPage + delta;
        if (newPage >= 1 && newPage <= totalPages) {
            currentPage = newPage;
            requestHistoryUpdate();
        }
    }

    function updatePagination(total) {
        totalPages = Math.ceil(total / itemsPerPage);
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        prevPage.disabled = currentPage === 1;
        nextPage.disabled = currentPage === totalPages;
    }

    function updateVolumeChart(data) {
        const chartData = [{
            x: data.map(d => new Date(d.timestamp)),
            y: data.map(d => d.volume),
            type: 'bar',
            name: 'Volume',
            marker: { color: '#4CAF50' }
        }];

        Plotly.newPlot(volumeChart, chartData, {
            ...chartLayout,
            title: 'Trade Volume Over Time',
            yaxis: { title: 'Volume ($)' }
        });
    }

    function updateProfitDistChart(data) {
        const profits = data.map(d => d.profit);
        const trace = {
            x: profits,
            type: 'histogram',
            nbinsx: 30,
            marker: {
                color: '#2196F3'
            }
        };

        Plotly.newPlot(profitDistChart, [trace], {
            ...chartLayout,
            title: 'Profit Distribution',
            xaxis: { title: 'Profit ($)' },
            yaxis: { title: 'Frequency' }
        });
    }

    function updateTradesList(trades) {
        tradesList.innerHTML = '';
        trades.forEach(trade => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(trade.timestamp).toLocaleString()}</td>
                <td>${trade.token_pair}</td>
                <td>${trade.dex_route}</td>
                <td>$${trade.amount.toFixed(2)}</td>
                <td>$${trade.profit.toFixed(2)}</td>
                <td>$${trade.gas_cost.toFixed(2)}</td>
                <td>$${trade.net_profit.toFixed(2)}</td>
                <td><span class="status-badge ${trade.status.toLowerCase()}">${trade.status}</span></td>
            `;
            tradesList.appendChild(row);
        });
    }

    function updateMetrics(metrics) {
        document.getElementById('history-total-trades').textContent = metrics.total_trades;
        document.getElementById('history-success-rate').textContent = `${(metrics.success_rate * 100).toFixed(1)}%`;
        document.getElementById('history-total-profit').textContent = `$${metrics.total_profit.toFixed(2)}`;
        document.getElementById('history-avg-profit').textContent = `$${metrics.avg_profit.toFixed(2)}`;
    }

    function requestHistoryUpdate() {
        socket.emit('history_request', {
            filters,
            page: currentPage,
            items_per_page: itemsPerPage
        });
    }

    // Socket.io event handlers
    socket.on('history_update', (data) => {
        updateTradesList(data.trades);
        updatePagination(data.total_trades);
        updateMetrics(data.metrics);
        updateVolumeChart(data.volume_data);
        updateProfitDistChart(data.trades);
    });

    // Initial load
    requestHistoryUpdate();
});