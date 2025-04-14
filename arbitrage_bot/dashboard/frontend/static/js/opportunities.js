/**
 * Opportunities module
 * Handles opportunities-specific functionality
 */

/**
 * Load opportunities data from the API
 */
async function loadOpportunitiesData() {
    try {
        // Get filter values
        const minProfit = state.filters.opportunities.minProfit;
        const maxRisk = state.filters.opportunities.maxRisk;
        const page = state.pagination.opportunities.page;
        const limit = state.pagination.opportunities.limit;
        
        // Calculate offset
        const offset = (page - 1) * limit;
        
        // Load opportunities
        const response = await fetchAPI(
            `${API.opportunities}?min_profit=${minProfit}&max_risk=${maxRisk}&limit=${limit}&offset=${offset}`
        );
        
        if (response.success) {
            state.opportunities = response.data.opportunities;
            state.pagination.opportunities.total = response.data.total_count;
        }
    } catch (error) {
        console.error('Error loading opportunities data:', error);
    }
}

/**
 * Set up opportunities event listeners
 */
function setupOpportunitiesEvents() {
    // Set up filter button
    const applyFiltersButton = document.getElementById('apply-filters');
    if (applyFiltersButton) {
        applyFiltersButton.addEventListener('click', handleApplyFilters);
    }
    
    // Set up min profit input
    const minProfitInput = document.getElementById('min-profit');
    if (minProfitInput) {
        minProfitInput.value = state.filters.opportunities.minProfit;
    }
    
    // Set up max risk select
    const maxRiskSelect = document.getElementById('max-risk');
    if (maxRiskSelect) {
        maxRiskSelect.value = state.filters.opportunities.maxRisk;
    }
}

/**
 * Handle apply filters button click
 */
async function handleApplyFilters() {
    // Get filter values
    const minProfitInput = document.getElementById('min-profit');
    const maxRiskSelect = document.getElementById('max-risk');
    
    if (minProfitInput && maxRiskSelect) {
        // Update filters
        state.filters.opportunities.minProfit = parseFloat(minProfitInput.value);
        state.filters.opportunities.maxRisk = parseInt(maxRiskSelect.value);
        
        // Reset pagination
        state.pagination.opportunities.page = 1;
        
        // Reload data
        await loadOpportunitiesData();
        
        // Update UI
        updateOpportunitiesUI();
    }
}

/**
 * Handle execute opportunity button click
 * @param {string} opportunityId - The opportunity ID
 */
async function handleExecuteOpportunity(opportunityId) {
    try {
        // Show confirmation dialog
        if (!confirm('Are you sure you want to execute this opportunity?')) {
            return;
        }
        
        // Execute opportunity
        const response = await fetchAPI(`${API.trades}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                opportunity_id: opportunityId
            })
        });
        
        if (response.success) {
            alert(`Trade executed successfully. Trade ID: ${response.data.id}`);
            
            // Reload data
            await loadOpportunitiesData();
            
            // Update UI
            updateOpportunitiesUI();
        } else {
            alert(`Error executing trade: ${response.error}`);
        }
    } catch (error) {
        console.error('Error executing opportunity:', error);
        alert(`Error executing opportunity: ${error.message}`);
    }
}

/**
 * Update the opportunities UI with current data
 */
function updateOpportunitiesUI() {
    // Update opportunities table
    updateOpportunitiesTable();
}

/**
 * Update opportunities table
 */
function updateOpportunitiesTable() {
    const tableBody = document.getElementById('opportunities-table');
    
    if (!tableBody) {
        return;
    }
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Check if there are opportunities
    if (!state.opportunities || state.opportunities.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="7" class="text-center">No opportunities found</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Add opportunities to table
    state.opportunities.forEach(opportunity => {
        const row = document.createElement('tr');
        
        // Create path string
        const path = opportunity.path?.map(edge => `${edge.from_token} → ${edge.to_token}`).join(' → ') || 'N/A';
        
        // Set row class based on risk score
        if (opportunity.risk_score <= 2) {
            row.classList.add('table-success');
        } else if (opportunity.risk_score <= 4) {
            row.classList.add('table-warning');
        } else {
            row.classList.add('table-danger');
        }
        
        // Add cells
        row.innerHTML = `
            <td>${opportunity.id}</td>
            <td>${path}</td>
            <td>${opportunity.input_token}</td>
            <td>${opportunity.input_amount}</td>
            <td>${formatPercentage(opportunity.expected_profit_percentage)} (${formatCurrency(opportunity.expected_profit_usd)})</td>
            <td>${opportunity.risk_score}/5</td>
            <td>
                <button class="btn btn-sm btn-primary execute-btn" data-id="${opportunity.id}">Execute</button>
                <button class="btn btn-sm btn-secondary details-btn" data-id="${opportunity.id}">Details</button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add event listeners to buttons
    const executeButtons = tableBody.querySelectorAll('.execute-btn');
    executeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const opportunityId = button.getAttribute('data-id');
            handleExecuteOpportunity(opportunityId);
        });
    });
    
    const detailsButtons = tableBody.querySelectorAll('.details-btn');
    detailsButtons.forEach(button => {
        button.addEventListener('click', () => {
            const opportunityId = button.getAttribute('data-id');
            showOpportunityDetails(opportunityId);
        });
    });
}

/**
 * Show opportunity details
 * @param {string} opportunityId - The opportunity ID
 */
function showOpportunityDetails(opportunityId) {
    // Find opportunity
    const opportunity = state.opportunities.find(opp => opp.id === opportunityId);
    
    if (!opportunity) {
        alert('Opportunity not found');
        return;
    }
    
    // Create details HTML
    let detailsHtml = `
        <h3>Opportunity Details</h3>
        <p><strong>ID:</strong> ${opportunity.id}</p>
        <p><strong>Input Token:</strong> ${opportunity.input_token}</p>
        <p><strong>Input Amount:</strong> ${opportunity.input_amount}</p>
        <p><strong>Expected Profit:</strong> ${formatPercentage(opportunity.expected_profit_percentage)} (${formatCurrency(opportunity.expected_profit_usd)})</p>
        <p><strong>Estimated Gas Cost:</strong> ${formatCurrency(opportunity.estimated_gas_cost_usd)}</p>
        <p><strong>Net Profit:</strong> ${formatCurrency(opportunity.net_profit_usd)}</p>
        <p><strong>Risk Score:</strong> ${opportunity.risk_score}/5</p>
        <p><strong>Timestamp:</strong> ${formatDate(opportunity.timestamp)}</p>
        
        <h4>Path</h4>
        <table class="table table-sm">
            <thead>
                <tr>
                    <th>From</th>
                    <th>To</th>
                    <th>DEX</th>
                    <th>Price</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Add path details
    opportunity.path?.forEach(edge => {
        detailsHtml += `
            <tr>
                <td>${edge.from_token}</td>
                <td>${edge.to_token}</td>
                <td>${edge.dex}</td>
                <td>${edge.price}</td>
            </tr>
        `;
    });
    
    detailsHtml += `
            </tbody>
        </table>
    `;
    
    // Show details in an alert (in a real app, this would be a modal)
    alert(detailsHtml);
}
