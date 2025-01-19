// Opportunities page functionality

// Store current opportunities data
let currentOpportunities = [];
let rejectedOpportunities = [];

// Initialize opportunity modal
const opportunityModal = new bootstrap.Modal(document.getElementById('opportunity-modal'));

// Initialize filters
function initFilters() {
    // Token pair filter
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tokenSelect = document.getElementById('token-filter');
                const pairs = data.settings.token_pairs || [];
                tokenSelect.innerHTML = `
                    <option value="">All Pairs</option>
                    ${pairs.map(pair => `<option value="${pair}">${pair}</option>`).join('')}
                `;
            }
        })
        .catch(error => console.error('Error loading token pairs:', error));

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
        element.addEventListener('change', applyFilters);
    });
}

// Apply filters to opportunities
function applyFilters() {
    const tokenFilter = document.getElementById('token-filter').value;
    const minProfit = parseFloat(document.getElementById('min-profit').value) || 0;
    const dexFilter = document.getElementById('dex-filter').value;
    const statusFilter = document.getElementById('status-filter').value;

    // Filter opportunities
    const filteredOpportunities = currentOpportunities.filter(opp => {
        const tokenMatch = !tokenFilter || `${opp.token_in}/${opp.token_out}` === tokenFilter;
        const profitMatch = opp.profit_percentage >= minProfit;
        const dexMatch = !dexFilter || opp.dex === dexFilter;
        const statusMatch = !statusFilter || (statusFilter === 'active' && !opp.rejected) || 
                          (statusFilter === 'rejected' && opp.rejected);
        return tokenMatch && profitMatch && dexMatch && statusMatch;
    });

    // Update opportunities list
    updateOpportunitiesList(filteredOpportunities);
}

// Update opportunities list
function updateOpportunitiesList(opportunities) {
    const container = document.getElementById('opportunities-list');
    
    if (opportunities.length === 0) {
        container.innerHTML = '<div class="text-center">No opportunities found</div>';
        return;
    }

    container.innerHTML = opportunities.map(opp => `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h5 class="card-title mb-1">${opp.token_in}/${opp.token_out}</h5>
                        <span class="badge bg-secondary">${opp.dex}</span>
                        ${opp.trend ? `
                            <span class="badge bg-${getTrendBadgeColor(opp.trend)}">
                                ${opp.trend}
                            </span>
                        ` : ''}
                    </div>
                    <div class="text-end">
                        <h5 class="text-success mb-1">+${formatPercentage(opp.profit_percentage)}</h5>
                        <small class="text-muted">Expected: ${formatCurrency(opp.expected_out)}</small>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="row">
                        <div class="col-md-4">
                            <small class="text-muted">Volume (24h):</small>
                            <br>
                            $${formatNumber(opp.volume_24h || 0)}
                        </div>
                        <div class="col-md-4">
                            <small class="text-muted">Liquidity:</small>
                            <br>
                            ${formatPercentage(opp.liquidity_score * 100)}
                        </div>
                        <div class="col-md-4">
                            <small class="text-muted">Gas Cost:</small>
                            <br>
                            ${formatCurrency(opp.estimated_gas_cost)}
                        </div>
                    </div>
                </div>
                <button class="btn btn-sm btn-primary mt-2" onclick="showOpportunityDetails(${opp.id})">
                    View Details
                </button>
            </div>
        </div>
    `).join('');
}

// Update market overview
function updateMarketOverview() {
    // Update active pairs
    const activePairs = [...new Set(currentOpportunities.map(opp => `${opp.token_in}/${opp.token_out}`))];
    const pairsContainer = document.getElementById('active-pairs');
    pairsContainer.innerHTML = activePairs.map(pair => 
        `<span class="badge bg-primary me-1">${pair}</span>`
    ).join('');

    // Update top DEXes
    const dexCounts = currentOpportunities.reduce((acc, opp) => {
        acc[opp.dex] = (acc[opp.dex] || 0) + 1;
        return acc;
    }, {});
    const topDexes = Object.entries(dexCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5);
    
    const dexContainer = document.getElementById('top-dexes');
    dexContainer.innerHTML = topDexes.map(([dex, count]) => `
        <div class="d-flex justify-content-between mb-1">
            <span>${dex}</span>
            <span class="badge bg-secondary">${count}</span>
        </div>
    `).join('');

    // Update market conditions
    const conditions = document.getElementById('market-conditions');
    conditions.innerHTML = `
        <div class="d-flex justify-content-between mb-1">
            <span>Volatility</span>
            <span class="badge bg-${getVolatilityBadgeColor(currentOpportunities)}">
                ${calculateVolatility(currentOpportunities)}
            </span>
        </div>
        <div class="d-flex justify-content-between mb-1">
            <span>Opportunity Count</span>
            <span class="badge bg-primary">${currentOpportunities.length}</span>
        </div>
        <div class="d-flex justify-content-between">
            <span>Avg. Profit</span>
            <span class="badge bg-success">
                ${formatPercentage(calculateAverageProfit(currentOpportunities))}
            </span>
        </div>
    `;
}

// Show opportunity details
function showOpportunityDetails(id) {
    const opportunity = currentOpportunities.find(opp => opp.id === id);
    if (!opportunity) return;

    // Update modal content
    document.getElementById('modal-pair').textContent = `${opportunity.token_in}/${opportunity.token_out}`;
    document.getElementById('modal-dex').textContent = opportunity.dex;
    document.getElementById('modal-profit').textContent = formatPercentage(opportunity.profit_percentage);
    document.getElementById('modal-gas').textContent = formatCurrency(opportunity.estimated_gas_cost);
    document.getElementById('modal-liquidity').textContent = formatPercentage(opportunity.liquidity_score * 100);
    document.getElementById('modal-volume').textContent = `$${formatNumber(opportunity.volume_24h || 0)}`;
    document.getElementById('modal-impact').textContent = formatPercentage(opportunity.price_impact || 0);
    document.getElementById('modal-trend').textContent = opportunity.trend || 'N/A';

    // Update risk analysis
    const risks = [];
    if (opportunity.liquidity_score < 0.5) risks.push('Low liquidity');
    if (opportunity.price_impact > 1) risks.push('High price impact');
    if (opportunity.volume_24h < 100000) risks.push('Low volume');

    document.getElementById('modal-risks').innerHTML = risks.length > 0 
        ? risks.map(risk => `<div class="alert alert-warning mb-1">${risk}</div>`).join('')
        : '<div class="alert alert-success">No significant risks detected</div>';

    opportunityModal.show();
}

// Update rejected opportunities table
function updateRejectedList() {
    const tbody = document.getElementById('rejected-list');
    
    if (rejectedOpportunities.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No rejected opportunities</td></tr>';
        return;
    }

    tbody.innerHTML = rejectedOpportunities.map(opp => `
        <tr>
            <td>${formatTimestamp(opp.timestamp)}</td>
            <td>${opp.token_in}/${opp.token_out}</td>
            <td>${opp.dex}</td>
            <td>${formatPercentage(opp.profit_percentage)}</td>
            <td>
                <span class="badge bg-warning">
                    ${opp.rejection_reason}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="showOpportunityDetails(${opp.id})">
                    Details
                </button>
            </td>
        </tr>
    `).join('');
}

// Fetch and update opportunities
async function fetchOpportunities() {
    try {
        // Fetch active opportunities
        const activeResponse = await fetch('/api/opportunities');
        const activeData = await activeResponse.json();
        
        if (activeData.success) {
            currentOpportunities = activeData.opportunities;
            applyFilters();
            updateMarketOverview();
        }

        // Fetch rejected opportunities
        const rejectedResponse = await fetch('/api/opportunities/rejected');
        const rejectedData = await rejectedResponse.json();
        
        if (rejectedData.success) {
            rejectedOpportunities = rejectedData.rejected;
            updateRejectedList();
        }
    } catch (error) {
        console.error('Error fetching opportunities:', error);
        showError('Failed to fetch opportunities');
    }
}

// Handle price updates
window.addEventListener('prices', (event) => {
    fetchOpportunities();
});

// Initialize opportunities page
document.addEventListener('DOMContentLoaded', () => {
    initFilters();
    fetchOpportunities();
    
    // Update data periodically
    setInterval(fetchOpportunities, 10000); // Every 10 seconds
});
