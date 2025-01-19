// WebSocket connection handler
class WebSocketHandler {
    constructor() {
        this.connect();
        this.setupEventListeners();
    }

    connect() {
        const port = window.wsPort;
        if (!port) {
            console.error('WebSocket port not found in window.wsPort');
            return;
        }
        this.ws = new WebSocket(`ws://localhost:${port}`);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            document.getElementById('connection-status').className = 'badge bg-success';
            document.getElementById('connection-status').textContent = 'Connected';
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            document.getElementById('connection-status').className = 'badge bg-danger';
            document.getElementById('connection-status').textContent = 'Disconnected';
            // Attempt to reconnect after 5 seconds
            setTimeout(() => this.connect(), 5000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            document.getElementById('error-container').style.display = 'block';
            document.getElementById('error-message').textContent = 'Connection error. Retrying...';
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        };
    }

    setupEventListeners() {
        // Subscribe to all channels on connection
        this.ws.addEventListener('open', () => {
            this.ws.send(JSON.stringify({
                type: 'subscribe',
                channels: ['metrics', 'performance', 'system']
            }));
        });
    }

    handleMessage(data) {
        switch (data.type) {
            case 'metrics':
                this.updateMetrics(data.metrics);
                break;
            case 'performance':
                this.updatePerformance(data);
                break;
            case 'system':
                this.handleSystemMessage(data);
                break;
            case 'error':
                this.handleError(data);
                break;
        }
    }

    updateMetrics(metrics) {
        if (!metrics) {
            document.getElementById('data-status').className = 'badge bg-warning';
            document.getElementById('data-status').textContent = 'Waiting for data...';
            return;
        }

        // Update metrics display with proper loading states
        const elements = {
            'total-trades': metrics.total_trades,
            'trades-24h': metrics.trades_24h,
            'success-rate': metrics.success_rate !== undefined ? (metrics.success_rate * 100).toFixed(1) + '%' : '...',
            'total-profit': metrics.total_profit !== undefined ? '$' + metrics.total_profit.toFixed(2) : '...',
            'profit-24h': metrics.profit_24h !== undefined ? '$' + metrics.profit_24h.toFixed(2) : '...'
        };

        // Update each element, showing loading state if data is undefined
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value !== undefined ? value : '...';
            }
        });

        // Update DEX status table
        const dexTable = document.getElementById('dex-status');
        if (dexTable) {
            if (metrics.dex_status && metrics.dex_status.length > 0) {
                dexTable.innerHTML = metrics.dex_status.map(dex => `
                    <tr>
                        <td>${dex.name}</td>
                        <td><span class="badge ${dex.active ? 'bg-success' : 'bg-danger'}">${dex.active ? 'Active' : 'Inactive'}</span></td>
                        <td>$${dex.liquidity ? dex.liquidity.toLocaleString() : '...'}</td>
                        <td>$${dex.volume_24h ? dex.volume_24h.toLocaleString() : '...'}</td>
                    </tr>
                `).join('');
            } else {
                dexTable.innerHTML = '<tr><td colspan="4" class="text-center">Waiting for DEX data...</td></tr>';
            }
        }

        // Update status badge
        document.getElementById('data-status').className = 'badge bg-success';
        document.getElementById('data-status').textContent = 'Live';
    }

    updatePerformance(data) {
        if (!data) {
            return;
        }

        // Update charts only if there's valid data
        if (window.priceChart) {
            if (data.price_history && data.price_history.length > 0) {
                window.priceChart.updateSeries([{
                    data: data.price_history
                }]);
            } else {
                window.priceChart.updateSeries([{
                    data: []
                }]);
            }
        }

        if (window.profitChart) {
            if (data.profit_history && data.profit_history.length > 0) {
                window.profitChart.updateSeries([{
                    data: data.profit_history
                }]);
            } else {
                window.profitChart.updateSeries([{
                    data: []
                }]);
            }
        }

        if (window.volumeChart) {
            if (data.volume_history && data.volume_history.length > 0) {
                window.volumeChart.updateSeries([{
                    data: data.volume_history
                }]);
            } else {
                window.volumeChart.updateSeries([{
                    data: []
                }]);
            }
        }

        // Update opportunities table
        const opportunitiesTable = document.getElementById('opportunities');
        if (opportunitiesTable) {
            if (data.opportunities && data.opportunities.length > 0) {
                opportunitiesTable.innerHTML = data.opportunities.map(opp => `
                    <tr>
                        <td>${opp.token_pair}</td>
                        <td>$${opp.potential_profit ? opp.potential_profit.toFixed(2) : '...'}</td>
                        <td>$${opp.gas_cost ? opp.gas_cost.toFixed(2) : '...'}</td>
                        <td>$${opp.net_profit ? opp.net_profit.toFixed(2) : '...'}</td>
                        <td>${opp.price_impact ? (opp.price_impact * 100).toFixed(2) : '...'}%</td>
                        <td><span class="badge ${opp.executable ? 'bg-success' : 'bg-warning'}">${opp.executable ? 'Ready' : 'Pending'}</span></td>
                    </tr>
                `).join('');
            } else {
                opportunitiesTable.innerHTML = '<tr><td colspan="6" class="text-center">No active opportunities</td></tr>';
            }
        }
    }

    handleSystemMessage(data) {
        if (data.status === 'warning') {
            document.getElementById('warning-container').style.display = 'block';
            document.getElementById('warning-message').textContent = data.message;
        } else {
            document.getElementById('warning-container').style.display = 'none';
        }
    }

    handleError(data) {
        document.getElementById('error-container').style.display = 'block';
        document.getElementById('error-message').textContent = data.message;
    }
}

// Initialize WebSocket handler when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.wsHandler = new WebSocketHandler();
});
