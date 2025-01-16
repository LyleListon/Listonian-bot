// WebSocket connection handler
class WebSocketHandler {
    constructor() {
        this.connect();
        this.setupEventListeners();
    }

    connect() {
        const port = window.wsPort || 8771;
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
        // Update metrics display
        document.getElementById('total-trades').textContent = metrics.total_trades;
        document.getElementById('trades-24h').textContent = metrics.trades_24h;
        document.getElementById('success-rate').textContent = (metrics.success_rate * 100).toFixed(1) + '%';
        document.getElementById('total-profit').textContent = '$' + metrics.total_profit.toFixed(2);
        document.getElementById('profit-24h').textContent = '$' + metrics.profit_24h.toFixed(2);

        // Update DEX status table
        const dexTable = document.getElementById('dex-status');
        if (dexTable && metrics.dex_status) {
            dexTable.innerHTML = metrics.dex_status.map(dex => `
                <tr>
                    <td>${dex.name}</td>
                    <td><span class="badge ${dex.active ? 'bg-success' : 'bg-danger'}">${dex.active ? 'Active' : 'Inactive'}</span></td>
                    <td>$${dex.liquidity.toLocaleString()}</td>
                    <td>$${dex.volume_24h.toLocaleString()}</td>
                </tr>
            `).join('');
        }

        document.getElementById('data-status').className = 'badge bg-success';
        document.getElementById('data-status').textContent = 'Live';
    }

    updatePerformance(data) {
        // Update price chart
        if (window.priceChart && data.price_history) {
            window.priceChart.updateSeries([{
                data: data.price_history
            }]);
        }

        // Update profit chart
        if (window.profitChart && data.profit_history) {
            window.profitChart.updateSeries([{
                data: data.profit_history
            }]);
        }

        // Update volume chart
        if (window.volumeChart && data.volume_history) {
            window.volumeChart.updateSeries([{
                data: data.volume_history
            }]);
        }

        // Update opportunities table
        const opportunitiesTable = document.getElementById('opportunities');
        if (opportunitiesTable && data.opportunities) {
            opportunitiesTable.innerHTML = data.opportunities.map(opp => `
                <tr>
                    <td>${opp.token_pair}</td>
                    <td>$${opp.potential_profit.toFixed(2)}</td>
                    <td>$${opp.gas_cost.toFixed(2)}</td>
                    <td>$${opp.net_profit.toFixed(2)}</td>
                    <td>${(opp.price_impact * 100).toFixed(2)}%</td>
                    <td><span class="badge ${opp.executable ? 'bg-success' : 'bg-warning'}">${opp.executable ? 'Ready' : 'Pending'}</span></td>
                </tr>
            `).join('');
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
