// WebSocket connection management
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second delay
        this.handlers = new Map();
        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket connection established');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.requestInitialData();
        };

        this.socket.onclose = () => {
            console.log('WebSocket connection closed');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type && this.handlers.has(data.type)) {
                    this.handlers.get(data.type)(data.data);
                }
            } catch (error) {
                console.error('Error processing message:', error);
            }
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
                console.log(`Attempting to reconnect (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})...`);
                this.connect();
                this.reconnectAttempts++;
                this.reconnectDelay *= 2; // Exponential backoff
            }, this.reconnectDelay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    requestInitialData() {
        this.send('request_update', { type: 'market_data' });
        this.send('request_update', { type: 'portfolio' });
        this.send('request_update', { type: 'memory' });
        this.send('request_update', { type: 'storage' });
        this.send('request_update', { type: 'distribution' });
        this.send('request_update', { type: 'execution' });
        this.send('request_update', { type: 'gas' });
    }

    send(type, data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type, data }));
        }
    }

    addHandler(type, handler) {
        this.handlers.set(type, handler);
    }
}

// Create WebSocket manager instance
const wsManager = new WebSocketManager();
