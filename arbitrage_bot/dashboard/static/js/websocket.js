// WebSocket connection handler
class WebSocketHandler {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // Start with 2 seconds
        this.isConnecting = false;
        this.callbacks = {
            onMetrics: [],
            onPerformance: [],
            onError: []
        };
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.reconnect = this.reconnect.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
    }
    
    async connect() {
        if (this.isConnecting) return;
        this.isConnecting = true;
        
        try {
            const port = parseInt(window.WEBSOCKET_PORT);
            if (!port) {
                console.error('WebSocket port not configured');
                this.isConnecting = false;
                this.reconnect();
                return;
            }
            const wsUrl = `ws://${window.location.hostname}:${port}`;
            console.debug(`Connecting to WebSocket at ${wsUrl}`);
            
            this.socket = new WebSocket(wsUrl);
            console.debug('WebSocket instance created');
            
            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.reconnectDelay = 2000;
                this.isConnecting = false;
                
                // Start heartbeat
                this.startHeartbeat();
                
                // Send initial request for data
                this.socket.send(JSON.stringify({
                    type: 'subscribe',
                    channels: ['metrics', 'performance']
                }));
            };
            
            this.socket.onmessage = this.handleMessage;
            
            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.callbacks.onError.forEach(cb => cb(error));
            };
            
            this.socket.onclose = () => {
                console.log('WebSocket closed');
                this.stopHeartbeat();
                this.isConnecting = false;
                this.reconnect();
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.isConnecting = false;
            this.reconnect();
        }
    }
    
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Send ping every 30 seconds
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        this.reconnectDelay *= 1.5; // Exponential backoff
        
        console.log(`Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(this.connect, this.reconnectDelay);
    }
    
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'metrics':
                    this.callbacks.onMetrics.forEach(cb => cb(data.metrics));
                    this.updateDashboard(data.metrics);
                    break;
                    
                case 'performance':
                    this.callbacks.onPerformance.forEach(cb => cb(data));
                    this.updateCharts(data);
                    break;
                    
                case 'pong':
                    // Heartbeat response received
                    break;
                    
                default:
                    console.log('Unknown message type:', data.type);
            }
        } catch (error) {
            console.error('Error handling message:', error);
        }
    }
    
    updateDashboard(metrics) {
        // Update metrics display
        document.getElementById('total-trades')?.textContent = metrics.total_trades;
        document.getElementById('trades-24h')?.textContent = metrics.trades_24h;
        document.getElementById('success-rate')?.textContent = `${(metrics.success_rate * 100).toFixed(1)}%`;
        document.getElementById('total-profit')?.textContent = `$${metrics.total_profit.toFixed(2)}`;
        document.getElementById('profit-24h')?.textContent = `$${metrics.profit_24h.toFixed(2)}`;
        document.getElementById('active-opportunities')?.textContent = metrics.active_opportunities;
    }
    
    updateCharts(data) {
        // Update profit history chart
        if (window.profitChart && data.profit_history) {
            window.profitChart.updateSeries([{
                data: data.profit_history
            }]);
        }
        
        // Update volume history chart
        if (window.volumeChart && data.volume_history) {
            window.volumeChart.updateSeries([{
                data: data.volume_history
            }]);
        }
    }
    
    // Callback registration methods
    onMetrics(callback) {
        this.callbacks.onMetrics.push(callback);
    }
    
    onPerformance(callback) {
        this.callbacks.onPerformance.push(callback);
    }
    
    onError(callback) {
        this.callbacks.onError.push(callback);
    }
}

// Create and export WebSocket handler instance
window.wsHandler = new WebSocketHandler();

// Connect when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.wsHandler.connect();
});
