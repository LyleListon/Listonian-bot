/**
 * Trades module
 * Handles trades-specific functionality
 */

/**
 * Load trades data from the API
 */
async function loadTradesData() {
    try {
        // Get filter values
        const status = state.filters.trades.status;
        const page = state.pagination.trades.page;
        const limit = state.pagination.trades.limit;
        
        // Calculate offset
        const offset = (page - 1) * limit;
        
        // Build query string
        let queryString = `limit=${limit}&offset=${offset}`;
        if (status) {
            queryString += `&status=${status}`;
        }
        
        // Load trades
        const response = await fetchAPI(`${API.trades}?${queryString}`);
        
        if (response.success) {
            state.trades = response.data.trades;
            state.pagination.trades.total = response.data.total_count;
        }
    } catch (error) {
        console.error('Error loading trades data:', error);
    }
}

/**
 * Set up trades event listeners
 */
function setupTradesEvents() {
    // Set up filter button
    const applyFiltersButton = document.getElementById('apply-filters');
    if (applyFiltersButton) {
        applyFiltersButton.addEventListener('click', handleApplyFilters);
    }
    
    // Set up status filter select
    const statusFilterSelect = document.getElementById('status-filter');
    if (statusFilterSelect) {
        statusFilterSelect.value = state.filters.trades.status;
    }
    
    // Set up pagination buttons
    const prevPageButton = document.getElementById('prev-page');
    const nextPageButton = document.getElementById('next-page');
    
    if (prevPageButton) {
        prevPageButton.addEventListener('click', handlePrevPage);
    }
    
    if (nextPageButton) {
        nextPageButton.addEventListener('click', handleNextPage);
    }
}

/**
 * Handle apply filters button click
 */
async function handleApplyFilters() {
    // Get filter values
    const statusFilterSelect = document.getElementById('status-filter');
    
    if (statusFilterSelect) {
        // Update filters
        state.filters.trades.status = statusFilterSelect.value;
        
        // Reset pagination
        state.pagination.trades.page = 1;
        
        // Reload data
        await loadTradesData();
        
        // Update UI
        updateTradesUI();
    }
}

/**
 * Handle previous page button click
 */
async function handlePrevPage() {
    if (state.pagination.trades.page > 1) {
        state.pagination.trades.page--;
        
        // Reload data
        await loadTradesData();
        
        // Update UI
        updateTradesUI();
    }
}

/**
 * Handle next page button click
 */
async function handleNextPage() {
    const totalPages = Math.ceil(state.pagination.trades.total / state.pagination.trades.limit);
    
    if (state.pagination.trades.page < totalPages) {
        state.pagination.trades.page++;
        
        // Reload data
        await loadTradesData();
        
        // Update UI
        updateTradesUI();
    }
}

/**
 * Update the trades UI with current data
 */
function updateTradesUI() {
    // Update trades table
    updateTradesTable();
    
    // Update pagination
    updatePagination();
}

/**
 * Update trades table
 */
function updateTradesTable() {
    const tableBody = document.getElementById('trades-table');
    
    if (!tableBody) {
        return;
    }
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Check if there are trades
    if (!state.trades || state.trades.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="7" class="text-center">No trades found</td>';
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
        
        // Format transaction hash
        const txHash = trade.transaction_hash ? 
            `<a href="#" class="tx-link" data-hash="${trade.transaction_hash}">${trade.transaction_hash.substring(0, 10)}...</a>` : 
            'N/A';
        
        // Add cells
        row.innerHTML = `
            <td>${trade.id}</td>
            <td>${formatDate(trade.timestamp)}</td>
            <td>${trade.opportunity_id}</td>
            <td>${path}</td>
            <td>${trade.status}</td>
            <td>${formatCurrency(trade.net_profit_usd || 0)}</td>
            <td>${txHash}</td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add event listeners to transaction links
    const txLinks = tableBody.querySelectorAll('.tx-link');
    txLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const txHash = link.getAttribute('data-hash');
            openTransactionExplorer(txHash);
        });
    });
}

/**
 * Update pagination UI
 */
function updatePagination() {
    const prevPageButton = document.getElementById('prev-page');
    const nextPageButton = document.getElementById('next-page');
    const pageInfo = document.getElementById('page-info');
    
    if (!prevPageButton || !nextPageButton || !pageInfo) {
        return;
    }
    
    // Calculate total pages
    const totalPages = Math.ceil(state.pagination.trades.total / state.pagination.trades.limit);
    
    // Update page info
    pageInfo.textContent = `Page ${state.pagination.trades.page} of ${totalPages}`;
    
    // Update button states
    prevPageButton.disabled = state.pagination.trades.page <= 1;
    nextPageButton.disabled = state.pagination.trades.page >= totalPages;
}

/**
 * Open transaction explorer for a transaction hash
 * @param {string} txHash - The transaction hash
 */
function openTransactionExplorer(txHash) {
    // In a real implementation, this would open the appropriate blockchain explorer
    // For now, just show an alert
    alert(`Transaction Hash: ${txHash}\n\nIn a real implementation, this would open the blockchain explorer.`);
}
