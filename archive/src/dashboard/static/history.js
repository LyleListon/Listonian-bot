// History page functionality

// Store current page and page size
let currentPage = 1;
const pageSize = 10;

// Initialize date range picker
function initDateRange() {
    const rangeSelect = document.getElementById('date-range');
    const customRange = document.getElementById('custom-range');
    
    rangeSelect.addEventListener('change', () => {
        if (rangeSelect.value === 'custom') {
            customRange.style.display = 'block';
        } else {
            customRange.style.display = 'none';
            updateData();
        }
    });

    // Set default dates for custom range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);
    
    document.getElementById('start-date').value = startDate.toISOString().split('T')[0];
    document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
}

// Initialize filters
function initFilters() {
    // Token filter
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tokenSelect = document.getElementById('token-filter');
                const tokens = data.settings.tokens || [];
                tokenSelect.innerHTML = `
                    <option value="">All Tokens</option>
                    ${tokens.map(token => `<option value="${token}">${token}</option>`).join('')}
                `;
            }
        })
        .catch(error => console.error('Error loading tokens:', error));

    // DEX filter
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const dexSelect = document.getElementById('dex-filter');
                const dexes = data.settings.dexes || [];
                dexSelect.innerHTML = `
                    <option value="">All DEXes</option>
                    ${dexes.map(dex => `<option value="${dex}">${dex}</option>`).join('')}
                `;
            }
        })
        .catch(error => console.error('Error loading DEXes:', error));

    // Add filter event listeners
    document.querySelectorAll('.form-select, .form-control').forEach(element => {
        element.addEventListener('change', () => {
            currentPage = 1;
            updateData();
        });
    });

    // Export CSV button
    document.getElementById('export-csv').addEventListener('click', exportToCsv);
}

// Get current filter values
function getFilters() {
    const rangeSelect = document.getElementById('date-range');
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
        end_date: endDate.toISOString(),
        token: document.getElementById('token-filter').value,
        dex: document.getElementById('dex-filter').value,
        status: document.getElementById('status-filter').value,
        min_profit: parseFloat(document.getElementById('min-profit').value) || 0
    };
}

// Update performance metrics
async function updateMetrics() {
    try {
        const filters = getFilters();
        const response = await fetch(`/api/analytics/performance?${new URLSearchParams(filters)}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('total-volume').textContent = formatCurrency(data.metrics.total_volume);
            document.getElementById('avg-profit').textContent = formatPercentage(data.metrics.avg_profit);
            document.getElementById('best-profit').textContent = formatPercentage(data.metrics.best_profit);
            document.getElementById('total-gas').textContent = formatCurrency(data.metrics.total_gas);
        }
    } catch (error) {
        console.error('Error updating metrics:', error);
        showError('Failed to update metrics');
    }
}

// Update trade history table
async function updateTradeHistory() {
    try {
        const filters = getFilters();
        const response = await fetch(`/api/trades/filtered?${new URLSearchParams({
            ...filters,
            page: currentPage,
            page_size: pageSize
        })}`);
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.getElementById('trades-list');
            if (data.trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center">No trades found</td></tr>';
                return;
            }
            
            tbody.innerHTML = data.trades.map(trade => `
                <tr>
                    <td>${formatTimestamp(trade.timestamp)}</td>
                    <td>${trade.token_in}/${trade.token_out}</td>
                    <td>${trade.dex}</td>
                    <td>${trade.type}</td>
                    <td>${formatCurrency(trade.amount)}</td>
                    <td class="${trade.profit >= 0 ? 'text-success' : 'text-danger'}">
                        ${formatCurrency(trade.profit)}
                    </td>
                    <td>${formatCurrency(trade.gas_used)}</td>
                    <td>
                        <span class="badge bg-${trade.status === 'success' ? 'success' : 'danger'}">
                            ${trade.status}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="showTradeDetails(${trade.id})">
                            Details
                        </button>
                    </td>
                </tr>
            `).join('');

            // Update pagination
            updatePagination(data.total_pages);
        }
    } catch (error) {
        console.error('Error updating trade history:', error);
        showError('Failed to update trade history');
    }
}

// Update pagination controls
function updatePagination(totalPages) {
    const pagination = document.getElementById('pagination');
    let html = '';
    
    // Previous button
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Previous</a>
        </li>
    `;
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += '<li class="page-item disabled"><a class="page-link">...</a></li>';
        }
    }
    
    // Next button
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Next</a>
        </li>
    `;
    
    pagination.innerHTML = html;
}

// Change page
function changePage(page) {
    currentPage = page;
    updateTradeHistory();
}

// Show trade details modal
function showTradeDetails(id) {
    fetch(`/api/trades/${id}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const trade = data.trade;
                
                // Update modal content
                document.getElementById('modal-tx-hash').innerHTML = `
                    <a href="https://etherscan.io/tx/${trade.tx_hash}" target="_blank">
                        ${trade.tx_hash}
                    </a>
                `;
                document.getElementById('modal-block').textContent = trade.block_number;
                document.getElementById('modal-gas-price').textContent = `${formatNumber(trade.gas_price)} Gwei`;
                document.getElementById('modal-total-cost').textContent = formatCurrency(trade.total_cost);
                document.getElementById('modal-price-impact').textContent = formatPercentage(trade.price_impact);
                document.getElementById('modal-slippage').textContent = formatPercentage(trade.slippage);
                document.getElementById('modal-market-trend').textContent = trade.market_trend;
                document.getElementById('modal-volatility').textContent = formatPercentage(trade.volatility);
                
                // Update route diagram
                const routeContainer = document.getElementById('modal-route');
                routeContainer.innerHTML = trade.route.map((step, index) => `
                    <div class="d-flex align-items-center">
                        <div class="route-token">${step.token}</div>
                        ${index < trade.route.length - 1 ? `
                            <div class="route-arrow">
                                <i class="fas fa-arrow-right"></i>
                                <small class="d-block">${step.dex}</small>
                            </div>
                        ` : ''}
                    </div>
                `).join('');
                
                // Update Etherscan link
                document.getElementById('modal-etherscan').href = `https://etherscan.io/tx/${trade.tx_hash}`;
                
                // Show modal
                new bootstrap.Modal(document.getElementById('trade-modal')).show();
            }
        })
        .catch(error => {
            console.error('Error loading trade details:', error);
            showError('Failed to load trade details');
        });
}

// Export trades to CSV
function exportToCsv() {
    const filters = getFilters();
    const queryString = new URLSearchParams({
        ...filters,
        format: 'csv'
    }).toString();
    
    window.location.href = `/api/trades/export?${queryString}`;
}

// Update all data
function updateData() {
    updateMetrics();
    updateTradeHistory();
}

// Initialize history page
document.addEventListener('DOMContentLoaded', () => {
    initDateRange();
    initFilters();
    updateData();
    
    // Update data periodically
    setInterval(updateData, 30000); // Every 30 seconds
});
