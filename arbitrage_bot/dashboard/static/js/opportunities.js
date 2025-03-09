// Opportunities page functionality
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const minProfitInput = document.getElementById('min-profit');
    const dexFilter = document.getElementById('dex-filter');
    const pairFilter = document.getElementById('pair-filter');
    const opportunitiesList = document.getElementById('opportunities-list');
    const distributionChart = document.getElementById('opportunity-distribution-chart');
    const profitPotentialChart = document.getElementById('profit-potential-chart');

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
        minProfit: 0,
        dex: 'all',
        pair: 'all'
    };

    // Available DEXs and pairs (will be populated from data)
    let availableDexs = new Set();
    let availablePairs = new Set();

    // Event listeners for filters
    minProfitInput.addEventListener('change', updateFilters);
    dexFilter.addEventListener('change', updateFilters);
    pairFilter.addEventListener('change', updateFilters);

    function updateFilters() {
        filters = {
            minProfit: parseFloat(minProfitInput.value) || 0,
            dex: dexFilter.value,
            pair: pairFilter.value
        };
        applyFilters();
    }

    function applyFilters() {
        const opportunities = Array.from(opportunitiesList.children);
        opportunities.forEach(opp => {
            const profit = parseFloat(opp.querySelector('[data-profit]').dataset.profit);
            const dex = opp.querySelector('[data-dex]').dataset.dex;
            const pair = opp.querySelector('[data-pair]').dataset.pair;

            const visible = 
                profit >= filters.minProfit &&
                (filters.dex === 'all' || dex === filters.dex) &&
                (filters.pair === 'all' || pair === filters.pair);

            opp.style.display = visible ? 'block' : 'none';
        });
    }

    function updateDistributionChart(data) {
        const dexCounts = {};
        data.forEach(opp => {
            dexCounts[opp.dex] = (dexCounts[opp.dex] || 0) + 1;
        });

        const chartData = [{
            values: Object.values(dexCounts),
            labels: Object.keys(dexCounts),
            type: 'pie',
            hole: 0.4,
            marker: {
                colors: ['#4CAF50', '#2196F3', '#9C27B0', '#FFC107', '#FF5722']
            }
        }];

        Plotly.newPlot(distributionChart, chartData, {
            ...chartLayout,
            title: 'Opportunities by DEX'
        });
    }

    function updateProfitPotentialChart(data) {
        const profitRanges = {
            '0-1': 0,
            '1-5': 0,
            '5-10': 0,
            '10-50': 0,
            '50+': 0
        };

        data.forEach(opp => {
            const profit = opp.potential_profit;
            if (profit < 1) profitRanges['0-1']++;
            else if (profit < 5) profitRanges['1-5']++;
            else if (profit < 10) profitRanges['5-10']++;
            else if (profit < 50) profitRanges['10-50']++;
            else profitRanges['50+']++;
        });

        const chartData = [{
            x: Object.keys(profitRanges),
            y: Object.values(profitRanges),
            type: 'bar',
            marker: {
                color: '#4CAF50'
            }
        }];

        Plotly.newPlot(profitPotentialChart, chartData, {
            ...chartLayout,
            title: 'Profit Distribution ($)',
            xaxis: {
                title: 'Profit Range ($)'
            },
            yaxis: {
                title: 'Number of Opportunities'
            }
        });
    }

    // Socket.io event handlers
    socket.on('opportunities_update', (data) => {
        // Update available DEXs and pairs
        data.opportunities.forEach(opp => {
            availableDexs.add(opp.dex);
            availablePairs.add(opp.token_pair);
        });

        // Update filter dropdowns if needed
        if (dexFilter.children.length === 1) {
            Array.from(availableDexs).forEach(dex => {
                const option = document.createElement('option');
                option.value = dex;
                option.textContent = dex;
                dexFilter.appendChild(option);
            });
        }

        if (pairFilter.children.length === 1) {
            Array.from(availablePairs).forEach(pair => {
                const option = document.createElement('option');
                option.value = pair;
                option.textContent = pair;
                pairFilter.appendChild(option);
            });
        }

        // Update opportunities list
        updateOpportunitiesList(data.opportunities);

        // Update charts
        updateDistributionChart(data.opportunities);
        updateProfitPotentialChart(data.opportunities);
    });

    function updateOpportunitiesList(opportunities) {
        opportunitiesList.innerHTML = '';
        opportunities.forEach(opp => {
            const oppCard = document.createElement('div');
            oppCard.className = `opportunity-card ${opp.executable ? 'executable' : ''}`;
            oppCard.innerHTML = `
                <h3 data-pair="${opp.token_pair}">${opp.token_pair}</h3>
                <div class="opportunity-metrics">
                    <div data-profit="${opp.potential_profit}">Potential Profit: $${opp.potential_profit.toFixed(2)}</div>
                    <div>Gas Cost: $${opp.gas_cost.toFixed(2)}</div>
                    <div>Net Profit: $${opp.net_profit.toFixed(2)}</div>
                    <div>Price Impact: ${(opp.price_impact * 100).toFixed(2)}%</div>
                    <div data-dex="${opp.dex}">DEX: ${opp.dex}</div>
                </div>
            `;
            opportunitiesList.appendChild(oppCard);
        });

        applyFilters();
    }
});