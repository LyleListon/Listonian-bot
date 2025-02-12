// WebSocket connection handler
class WebSocketHandler {
    constructor() {
        this.maxReconnectAttempts = 5;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000; // Start with 1 second
        this.connect();
    }

    connect() {
        const port = parseInt(window.wsPort) || 8772;
        this.ws = new WebSocket(`ws://localhost:${port}`);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            document.getElementById('connection-status').className = 'badge bg-success';
            document.getElementById('connection-status').textContent = 'Connected';
            
            // Reset reconnection parameters on successful connection
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            // Send initial request for data
            this.ws.send(JSON.stringify({
                type: 'subscribe',
                channels: ['metrics', 'performance', 'system']
            }));
            
            // Start heartbeat
            this.startHeartbeat();
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            document.getElementById('connection-status').className = 'badge bg-danger';
            document.getElementById('connection-status').textContent = 'Disconnected';
            
            // Clear heartbeat
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
            }
            
            // Attempt to reconnect with exponential backoff
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                this.reconnectDelay *= 2; // Exponential backoff
                console.log(`Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                setTimeout(() => this.connect(), this.reconnectDelay);
            } else {
                console.error('Max reconnection attempts reached');
                document.getElementById('error-container').style.display = 'block';
                document.getElementById('error-message').textContent = 'Connection failed. Please refresh the page.';
            }
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

    startHeartbeat() {
        // Send heartbeat every 30 seconds
        this.heartbeatInterval = setInterval(() => {
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'ping',
                    timestamp: Date.now()
                }));
            }
        }, 30000);
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
            case 'pong':
                // Handle pong response if needed
                break;
        }
    }

    updateMetrics(metrics) {
        if (!metrics) return;

        // Update basic metrics
        const elements = {
            'total-trades': metrics.total_trades || 0,
            'trades-24h': metrics.trades_24h || 0,
            'success-rate': ((metrics.success_rate || 0) * 100).toFixed(1) + '%',
            'total-profit': '$' + (metrics.total_profit || 0).toFixed(2),
            'profit-24h': '$' + (metrics.profit_24h || 0).toFixed(2)
        };

        for (const [id, value] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        }

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
        if (!data) return;

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
