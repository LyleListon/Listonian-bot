// Analytics page functionality
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const timeRange = document.getElementById('analytics-time-range');
    const customRange = document.getElementById('custom-range-inputs');
    const dateFrom = document.getElementById('analytics-date-from');
    const dateTo = document.getElementById('analytics-date-to');
    const performanceChart = document.getElementById('performance-chart');
    const gasAnalysisChart = document.getElementById('gas-analysis-chart');
    const topPairsChart = document.getElementById('top-pairs-chart');
    const dexPerformanceChart = document.getElementById('dex-performance-chart');
    const timeAnalysisChart = document.getElementById('time-analysis-chart');
    const riskAnalysisChart = document.getElementById('risk-analysis-chart');

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
        margin: { t: 30, l: 60, r: 30, b: 40 },
        xaxis: {
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.1)'
        },
        yaxis: {
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.1)'
        }
    };

    // Time range handling
    timeRange.addEventListener('change', () => {
        const value = timeRange.value;
        customRange.style.display = value === 'custom' ? 'block' : 'none';
        requestAnalyticsUpdate();
    });

    dateFrom.addEventListener('change', requestAnalyticsUpdate);
    dateTo.addEventListener('change', requestAnalyticsUpdate);

    function getTimeRange() {
        return {
            range: timeRange.value,
            from: dateFrom.value,
            to: dateTo.value
        };
    }

    function updateMetrics(data) {
        document.getElementById('total-volume').textContent = `$${formatNumber(data.total_volume)}`;
        document.getElementById('avg-daily-volume').textContent = `$${formatNumber(data.avg_daily_volume)}`;
        document.getElementById('total-gas').textContent = `$${formatNumber(data.total_gas)}`;
        document.getElementById('roi').textContent = `${(data.roi * 100).toFixed(2)}%`;
    }

    function updatePerformanceChart(data) {
        const traces = [
            {
                name: 'Profit',
                x: data.map(d => new Date(d.timestamp)),
                y: data.map(d => d.profit),
                type: 'scatter',
                mode: 'lines',
                line: { color: '#4CAF50' }
            },
            {
                name: 'Volume',
                x: data.map(d => new Date(d.timestamp)),
                y: data.map(d => d.volume),
                type: 'scatter',
                mode: 'lines',
                yaxis: 'y2',
                line: { color: '#2196F3' }
            }
        ];

        const layout = {
            ...chartLayout,
            title: 'Performance Over Time',
            yaxis: { title: 'Profit ($)' },
            yaxis2: {
                title: 'Volume ($)',
                overlaying: 'y',
                side: 'right'
            }
        };

        Plotly.newPlot(performanceChart, traces, layout);
    }

    function updateGasAnalysis(data) {
        const traces = [
            {
                x: data.map(d => new Date(d.timestamp)),
                y: data.map(d => d.gas_cost),
                type: 'scatter',
                mode: 'lines',
                name: 'Gas Cost',
                line: { color: '#FF9800' }
            },
            {
                x: data.map(d => new Date(d.timestamp)),
                y: data.map(d => d.gas_price),
                type: 'scatter',
                mode: 'lines',
                name: 'Gas Price',
                yaxis: 'y2',
                line: { color: '#E91E63' }
            }
        ];

        const layout = {
            ...chartLayout,
            title: 'Gas Cost Analysis',
            yaxis: { title: 'Gas Cost ($)' },
            yaxis2: {
                title: 'Gas Price (Gwei)',
                overlaying: 'y',
                side: 'right'
            }
        };

        Plotly.newPlot(gasAnalysisChart, traces, layout);
    }

    function updateTopPairs(data) {
        // Update chart
        const chartData = [{
            values: data.map(d => d.volume),
            labels: data.map(d => d.pair),
            type: 'pie',
            hole: 0.4,
            marker: {
                colors: ['#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#E91E63']
            }
        }];

        Plotly.newPlot(topPairsChart, chartData, {
            ...chartLayout,
            title: 'Top Trading Pairs by Volume'
        });

        // Update table
        const tbody = document.getElementById('top-pairs-list');
        tbody.innerHTML = data.map(pair => `
            <tr>
                <td>${pair.pair}</td>
                <td>$${formatNumber(pair.volume)}</td>
                <td>$${formatNumber(pair.profit)}</td>
                <td>${(pair.success_rate * 100).toFixed(1)}%</td>
            </tr>
        `).join('');
    }

    function updateDexPerformance(data) {
        // Update chart
        const traces = [
            {
                x: data.map(d => d.dex),
                y: data.map(d => d.volume),
                type: 'bar',
                name: 'Volume',
                marker: { color: '#4CAF50' }
            },
            {
                x: data.map(d => d.dex),
                y: data.map(d => d.profit),
                type: 'bar',
                name: 'Profit',
                marker: { color: '#2196F3' }
            }
        ];

        Plotly.newPlot(dexPerformanceChart, traces, {
            ...chartLayout,
            title: 'DEX Performance',
            barmode: 'group',
            xaxis: { title: 'DEX' },
            yaxis: { title: 'Amount ($)' }
        });

        // Update table
        const tbody = document.getElementById('dex-performance-list');
        tbody.innerHTML = data.map(dex => `
            <tr>
                <td>${dex.dex}</td>
                <td>$${formatNumber(dex.volume)}</td>
                <td>$${formatNumber(dex.profit)}</td>
                <td>${(dex.success_rate * 100).toFixed(1)}%</td>
            </tr>
        `).join('');
    }

    function updateTimeAnalysis(data) {
        const traces = [
            {
                x: data.map(d => d.hour),
                y: data.map(d => d.trades),
                type: 'scatter',
                mode: 'lines',
                name: 'Trades',
                line: { shape: 'spline', smoothing: 1.3 }
            }
        ];

        Plotly.newPlot(timeAnalysisChart, traces, {
            ...chartLayout,
            title: 'Trading Activity by Hour',
            xaxis: { title: 'Hour of Day', dtick: 2 },
            yaxis: { title: 'Number of Trades' }
        });

        // Update peak times list
        const peakTimesList = document.getElementById('peak-times-list');
        peakTimesList.innerHTML = data.peak_times.map(time => 
            `<li>${time.start} - ${time.end}: ${time.trades} trades, $${formatNumber(time.volume)} volume</li>`
        ).join('');
    }

    function updateRiskAnalysis(data) {
        const traces = [
            {
                x: data.map(d => d.risk_level),
                y: data.map(d => d.success_rate),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Success Rate',
                line: { color: '#4CAF50' }
            },
            {
                x: data.map(d => d.risk_level),
                y: data.map(d => d.avg_profit),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Avg Profit',
                yaxis: 'y2',
                line: { color: '#FF9800' }
            }
        ];

        Plotly.newPlot(riskAnalysisChart, traces, {
            ...chartLayout,
            title: 'Risk vs. Return Analysis',
            xaxis: { title: 'Risk Level' },
            yaxis: { title: 'Success Rate (%)' },
            yaxis2: {
                title: 'Average Profit ($)',
                overlaying: 'y',
                side: 'right'
            }
        });

        // Update risk metrics list
        const riskMetricsList = document.getElementById('risk-metrics-list');
        riskMetricsList.innerHTML = data.metrics.map(metric => 
            `<li>${metric.name}: ${metric.value}</li>`
        ).join('');
    }

    function updatePerformanceInsights(insights) {
        const container = document.getElementById('performance-insights');
        container.innerHTML = insights.map(insight => `
            <div class="insight-card ${insight.type}">
                <h4>${insight.title}</h4>
                <p>${insight.description}</p>
                ${insight.recommendation ? `<p class="recommendation">${insight.recommendation}</p>` : ''}
            </div>
        `).join('');
    }

    function requestAnalyticsUpdate() {
        socket.emit('analytics_request', getTimeRange());
    }

    // Socket.io event handlers
    socket.on('analytics_update', (data) => {
        updateMetrics(data.metrics);
        updatePerformanceChart(data.performance_data);
        updateGasAnalysis(data.gas_data);
        updateTopPairs(data.top_pairs);
        updateDexPerformance(data.dex_performance);
        updateTimeAnalysis(data.time_analysis);
        updateRiskAnalysis(data.risk_analysis);
        updatePerformanceInsights(data.insights);
    });

    function formatNumber(num) {
        if (num >= 1e9) {
            return `${(num / 1e9).toFixed(2)}B`;
        } else if (num >= 1e6) {
            return `${(num / 1e6).toFixed(2)}M`;
        } else if (num >= 1e3) {
            return `${(num / 1e3).toFixed(2)}K`;
        }
        return num.toFixed(2);
    }

    // Initial load
    requestAnalyticsUpdate();
});