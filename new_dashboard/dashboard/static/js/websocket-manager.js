/**
 * WebSocket Manager
 * Handles WebSocket connections with automatic reconnection and event handling
 */

class WebSocketManager {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || window.location.origin;
        this.endpoints = options.endpoints || {
            metrics: '/ws/metrics',
            system: '/ws/system',
            trades: '/ws/trades',
            market: '/ws/market'
        };
        this.reconnectInterval = options.reconnectInterval || 3000;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
        
        this.connections = {};
        this.listeners = {};
        this.reconnectAttempts = {};
        this.reconnectTimers = {};
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.disconnect = this.disconnect.bind(this);
        this.reconnect = this.reconnect.bind(this);
        this.send = this.send.bind(this);
        this.on = this.on.bind(this);
        this.off = this.off.bind(this);
        
        // Initialize debug mode
        this.debug = options.debug || false;
    }
    
    /**
     * Connect to a WebSocket endpoint
     * @param {string} endpoint - The endpoint name or full URL
     * @returns {WebSocket} The WebSocket connection
     */
    connect(endpoint) {
        // Determine the full URL
        const url = endpoint.startsWith('ws') ? endpoint : 
            `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${this.endpoints[endpoint] || endpoint}`;
        
        if (this.debug) console.log(`[WebSocketManager] Connecting to ${url}`);
        
        // Create WebSocket connection
        const ws = new WebSocket(url);
        
        // Store connection
        const key = this.getEndpointKey(endpoint);
        this.connections[key] = ws;
        this.reconnectAttempts[key] = 0;
        
        // Set up event handlers
        ws.onopen = (event) => {
            if (this.debug) console.log(`[WebSocketManager] Connected to ${url}`);
            this.reconnectAttempts[key] = 0;
            this.triggerListeners(key, 'open', event);
            
            // Send initial message to confirm connection
            this.send(endpoint, { type: 'hello', client: 'dashboard', timestamp: new Date().toISOString() });
        };
        
        ws.onmessage = (event) => {
            if (this.debug) console.log(`[WebSocketManager] Message from ${url}:`, event.data);
            try {
                const data = JSON.parse(event.data);
                this.triggerListeners(key, 'message', data);
                
                // Also trigger specific event type if available
                if (data.type) {
                    this.triggerListeners(key, data.type, data);
                }
            } catch (error) {
                console.error(`[WebSocketManager] Error parsing message from ${url}:`, error);
                this.triggerListeners(key, 'error', { error, originalEvent: event });
            }
        };
        
        ws.onerror = (error) => {
            console.error(`[WebSocketManager] Error with connection to ${url}:`, error);
            this.triggerListeners(key, 'error', error);
        };
        
        ws.onclose = (event) => {
            if (this.debug) console.log(`[WebSocketManager] Connection to ${url} closed:`, event);
            this.triggerListeners(key, 'close', event);
            
            // Attempt to reconnect
            if (!event.wasClean) {
                this.scheduleReconnect(endpoint);
            }
        };
        
        return ws;
    }
    
    /**
     * Disconnect from a WebSocket endpoint
     * @param {string} endpoint - The endpoint name or full URL
     */
    disconnect(endpoint) {
        const key = this.getEndpointKey(endpoint);
        const ws = this.connections[key];
        
        if (ws) {
            if (this.debug) console.log(`[WebSocketManager] Disconnecting from ${endpoint}`);
            
            // Clear any reconnect timers
            if (this.reconnectTimers[key]) {
                clearTimeout(this.reconnectTimers[key]);
                delete this.reconnectTimers[key];
            }
            
            // Close the connection
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close();
            }
            
            delete this.connections[key];
        }
    }
    
    /**
     * Schedule a reconnection attempt
     * @param {string} endpoint - The endpoint name or full URL
     */
    scheduleReconnect(endpoint) {
        const key = this.getEndpointKey(endpoint);
        
        // Increment reconnect attempts
        this.reconnectAttempts[key] = (this.reconnectAttempts[key] || 0) + 1;
        
        // Check if we've exceeded max attempts
        if (this.reconnectAttempts[key] > this.maxReconnectAttempts) {
            console.error(`[WebSocketManager] Max reconnect attempts (${this.maxReconnectAttempts}) exceeded for ${endpoint}`);
            this.triggerListeners(key, 'reconnect_failed', { attempts: this.reconnectAttempts[key] });
            return;
        }
        
        // Calculate backoff time (exponential backoff with jitter)
        const baseDelay = this.reconnectInterval;
        const exponentialDelay = baseDelay * Math.pow(1.5, this.reconnectAttempts[key] - 1);
        const jitter = Math.random() * 0.5 + 0.75; // Random between 0.75 and 1.25
        const delay = Math.min(exponentialDelay * jitter, 30000); // Cap at 30 seconds
        
        if (this.debug) console.log(`[WebSocketManager] Scheduling reconnect to ${endpoint} in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts[key]})`);
        
        // Schedule reconnect
        this.reconnectTimers[key] = setTimeout(() => {
            this.reconnect(endpoint);
        }, delay);
        
        // Trigger event
        this.triggerListeners(key, 'reconnect_scheduled', { 
            attempt: this.reconnectAttempts[key],
            delay: delay
        });
    }
    
    /**
     * Reconnect to a WebSocket endpoint
     * @param {string} endpoint - The endpoint name or full URL
     */
    reconnect(endpoint) {
        const key = this.getEndpointKey(endpoint);
        
        // Disconnect if still connected
        if (this.connections[key]) {
            this.disconnect(endpoint);
        }
        
        // Trigger event
        this.triggerListeners(key, 'reconnecting', { attempt: this.reconnectAttempts[key] });
        
        // Connect again
        this.connect(endpoint);
    }
    
    /**
     * Send data to a WebSocket endpoint
     * @param {string} endpoint - The endpoint name or full URL
     * @param {object} data - The data to send
     * @returns {boolean} Whether the data was sent successfully
     */
    send(endpoint, data) {
        const key = this.getEndpointKey(endpoint);
        const ws = this.connections[key];
        
        if (ws && ws.readyState === WebSocket.OPEN) {
            try {
                const message = typeof data === 'string' ? data : JSON.stringify(data);
                ws.send(message);
                return true;
            } catch (error) {
                console.error(`[WebSocketManager] Error sending data to ${endpoint}:`, error);
                return false;
            }
        } else {
            if (this.debug) console.warn(`[WebSocketManager] Cannot send to ${endpoint}: not connected`);
            return false;
        }
    }
    
    /**
     * Register an event listener
     * @param {string} endpoint - The endpoint name or full URL
     * @param {string} event - The event name
     * @param {function} callback - The callback function
     */
    on(endpoint, event, callback) {
        const key = this.getEndpointKey(endpoint);
        
        if (!this.listeners[key]) {
            this.listeners[key] = {};
        }
        
        if (!this.listeners[key][event]) {
            this.listeners[key][event] = [];
        }
        
        this.listeners[key][event].push(callback);
    }
    
    /**
     * Remove an event listener
     * @param {string} endpoint - The endpoint name or full URL
     * @param {string} event - The event name
     * @param {function} callback - The callback function to remove
     */
    off(endpoint, event, callback) {
        const key = this.getEndpointKey(endpoint);
        
        if (this.listeners[key] && this.listeners[key][event]) {
            this.listeners[key][event] = this.listeners[key][event].filter(cb => cb !== callback);
        }
    }
    
    /**
     * Trigger event listeners
     * @param {string} key - The endpoint key
     * @param {string} event - The event name
     * @param {*} data - The event data
     */
    triggerListeners(key, event, data) {
        if (this.listeners[key] && this.listeners[key][event]) {
            this.listeners[key][event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[WebSocketManager] Error in ${event} listener for ${key}:`, error);
                }
            });
        }
        
        // Also trigger global listeners
        if (this.listeners['global'] && this.listeners['global'][event]) {
            this.listeners['global'][event].forEach(callback => {
                try {
                    callback({ endpoint: key, data });
                } catch (error) {
                    console.error(`[WebSocketManager] Error in global ${event} listener:`, error);
                }
            });
        }
    }
    
    /**
     * Get a standardized key for an endpoint
     * @param {string} endpoint - The endpoint name or full URL
     * @returns {string} The standardized key
     */
    getEndpointKey(endpoint) {
        if (endpoint === 'global') return 'global';
        return this.endpoints[endpoint] || endpoint;
    }
    
    /**
     * Get the connection status for an endpoint
     * @param {string} endpoint - The endpoint name or full URL
     * @returns {string} The connection status
     */
    getStatus(endpoint) {
        const key = this.getEndpointKey(endpoint);
        const ws = this.connections[key];
        
        if (!ws) return 'disconnected';
        
        switch (ws.readyState) {
            case WebSocket.CONNECTING: return 'connecting';
            case WebSocket.OPEN: return 'connected';
            case WebSocket.CLOSING: return 'closing';
            case WebSocket.CLOSED: return 'closed';
            default: return 'unknown';
        }
    }
    
    /**
     * Connect to all configured endpoints
     */
    connectAll() {
        Object.keys(this.endpoints).forEach(endpoint => {
            this.connect(endpoint);
        });
    }
    
    /**
     * Disconnect from all endpoints
     */
    disconnectAll() {
        Object.keys(this.connections).forEach(key => {
            const endpoint = Object.keys(this.endpoints).find(e => this.endpoints[e] === key) || key;
            this.disconnect(endpoint);
        });
    }
}

// Create global instance
window.wsManager = new WebSocketManager({ debug: true });

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketManager;
}
