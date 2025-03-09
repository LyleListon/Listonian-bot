// Common JavaScript functions for dashboard

// WebSocket connection
const wsPort = window.wsConfig ? window.wsConfig.port : 8771; // Default to dashboard WebSocket port
const debug = true; // Enable logging for debugging
const maxRetries = 10;
const baseDelay = 1000;
const maxDelay = 30000;

function log(...args) {
    console.log('[WebSocket]', ...args);
}

let ws = null;
let reconnectAttempts = 0;
let reconnectTimeout = null;
let isConnecting = false;

async function initWebSocket() {
    if (isConnecting) {
        log('Connection attempt already in progress');
        return;
    }

    isConnecting = true;
    log('Initializing WebSocket connection...');

    try {
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }

        if (ws) {
            log('Closing existing connection...');
            ws.close();
            ws = null;
        }

        const url = `ws://localhost:${wsPort}`;
        log(`Creating WebSocket connection to ${url}`);
        
        // Create new WebSocket with explicit protocols
        ws = new WebSocket(url, ['websocket']);
        log('WebSocket instance created');

        // Set binary type to arraybuffer for better compatibility
        ws.binaryType = 'arraybuffer';
        
        ws.onopen = function() {
            log('WebSocket connection opened');
            updateConnectionStatus('Connected');
            reconnectAttempts = 0;
            isConnecting = false;

            // Send a ping message to test the connection
            try {
                ws.send(JSON.stringify({ type: 'ping' }));
            } catch (e) {
                log('Error sending ping:', e);
            }
        };
        
        ws.onclose = function(event) {
            log(`WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}`);
            updateConnectionStatus('Disconnected');
            isConnecting = false;
            
            if (reconnectAttempts < maxRetries) {
                reconnectAttempts++;
                const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts - 1), maxDelay);
                log(`Scheduling reconnection attempt ${reconnectAttempts} in ${delay/1000} seconds...`);
                reconnectTimeout = setTimeout(initWebSocket, delay);
            } else {
                log('Max reconnection attempts reached');
                updateConnectionStatus('Failed');
                // Reset and try again after maxDelay
                reconnectAttempts = 0;
                reconnectTimeout = setTimeout(initWebSocket, maxDelay);
            }
        };
        
        ws.onerror = function(error) {
            console.error('[WebSocket] Error:', error);
            log('WebSocket error occurred');
            updateConnectionStatus('Error');
            isConnecting = false;
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
            ws = null;
        };
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                log('Received message:', data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('[WebSocket] Error parsing message:', error);
                log('Raw message:', event.data);
            }
        };
    } catch (error) {
        console.error('[WebSocket] Error initializing:', error);
        log('Error details:', error.message);
        updateConnectionStatus('Error');
    }
}

function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.textContent = `Status: ${status}`;
        // Remove all existing status classes
        statusElement.classList.remove('connected', 'disconnected', 'error');
        // Add appropriate status class
        statusElement.classList.add(status.toLowerCase());
        
        // Update status indicator classes
        statusElement.classList.remove('status-connected', 'status-disconnected', 'status-error');
        statusElement.classList.add(`status-${status.toLowerCase()}`);
        
        // Update alert type
        statusElement.classList.remove('alert-info', 'alert-success', 'alert-danger', 'alert-warning');
        switch (status.toLowerCase()) {
            case 'connected':
                statusElement.classList.add('alert-success');
                break;
            case 'disconnected':
                statusElement.classList.add('alert-danger');
                break;
            case 'error':
                statusElement.classList.add('alert-warning');
                break;
            default:
                statusElement.classList.add('alert-info');
        }
    }
}

function handleWebSocketMessage(data) {
    // Handle different types of updates
    switch (data.type) {
        case 'portfolio':
            updatePortfolio(data);
            break;
        case 'opportunity':
            if (window.updateOpportunities) {
                window.updateOpportunities(data.opportunity);
            }
            break;
        case 'trade':
            if (window.updateTrades) {
                window.updateTrades(data.trade);
            }
            break;
        case 'alert':
            if (window.showAlert) {
                window.showAlert(data.alert);
            }
            break;
        case 'metrics':
            if (window.updateMetrics) {
                window.updateMetrics(data.metrics);
            }
            break;
        case 'performance':
            if (window.updateCharts) {
                window.updateCharts(data);
            }
            break;
    }
}

function updatePortfolio(data) {
    const portfolio = data.portfolio;
    if (!portfolio) return;
    
    // Update total value
    const totalValueElement = document.getElementById('total-value');
    if (totalValueElement) {
        totalValueElement.textContent = `$${portfolio.total_value.toFixed(2)}`;
    }
    
    // Update token balances
    const balancesContainer = document.getElementById('token-balances');
    if (balancesContainer && portfolio.tokens) {
        balancesContainer.innerHTML = '';
        Object.entries(portfolio.tokens).forEach(([token, data]) => {
            const tokenElement = document.createElement('div');
            tokenElement.className = 'token-balance';
            tokenElement.innerHTML = `
                <span class="token-name">${token}</span>
                <span class="token-amount">${data.amount.toFixed(4)}</span>
                <span class="token-value">$${data.value.toFixed(2)}</span>
            `;
            balancesContainer.appendChild(tokenElement);
        });
    }
}

function updateOpportunities(data) {
    const opportunities = data.opportunities;
    if (!opportunities) return;
    
    const container = document.getElementById('opportunities-list');
    if (!container) return;
    
    container.innerHTML = '';
    opportunities.forEach(opp => {
        const element = document.createElement('div');
        element.className = 'opportunity';
        element.innerHTML = `
            <div class="opp-header">
                <span class="opp-path">${opp.path.join(' → ')}</span>
                <span class="opp-profit">+${opp.profit.toFixed(2)}%</span>
            </div>
            <div class="opp-details">
                <span>Volume: $${opp.volume.toFixed(2)}</span>
                <span>Gas: ${opp.gas} gwei</span>
            </div>
        `;
        container.appendChild(element);
    });
}

function updateTrades(data) {
    const trades = data.trades;
    if (!trades) return;
    
    const container = document.getElementById('trades-list');
    if (!container) return;
    
    trades.forEach(trade => {
        const element = document.createElement('div');
        element.className = 'trade';
        element.innerHTML = `
            <div class="trade-header">
                <span class="trade-time">${new Date(trade.timestamp).toLocaleString()}</span>
                <span class="trade-profit ${trade.profit >= 0 ? 'positive' : 'negative'}">
                    ${trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}%
                </span>
            </div>
            <div class="trade-path">${trade.path.join(' → ')}</div>
            <div class="trade-details">
                <span>Volume: $${trade.volume.toFixed(2)}</span>
                <span>Gas Used: ${trade.gas_used} gwei</span>
            </div>
        `;
        container.insertBefore(element, container.firstChild);
    });
}

function showAlert(data) {
    const alert = data.alert;
    if (!alert) return;
    
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const element = document.createElement('div');
    element.className = `alert alert-${alert.type}`;
    element.innerHTML = `
        <span class="alert-time">${new Date(alert.timestamp).toLocaleString()}</span>
        <span class="alert-message">${alert.message}</span>
    `;
    
    alertsContainer.insertBefore(element, alertsContainer.firstChild);
    
    // Remove old alerts if there are too many
    while (alertsContainer.children.length > 50) {
        alertsContainer.removeChild(alertsContainer.lastChild);
    }
}

function updateMetrics(data) {
    const metrics = data.metrics;
    if (!metrics) return;
    
    // Update success rate
    const successRateElement = document.getElementById('success-rate');
    if (successRateElement && metrics.success_rate !== undefined) {
        successRateElement.textContent = `${metrics.success_rate.toFixed(1)}%`;
    }
    
    // Update average profit
    const avgProfitElement = document.getElementById('avg-profit');
    if (avgProfitElement && metrics.avg_profit !== undefined) {
        avgProfitElement.textContent = `${metrics.avg_profit.toFixed(2)}%`;
    }
    
    // Update gas metrics
    const gasMetricsElement = document.getElementById('gas-metrics');
    if (gasMetricsElement && metrics.gas) {
        gasMetricsElement.innerHTML = `
            <div>Average Gas: ${metrics.gas.average.toFixed(1)} gwei</div>
            <div>Min Gas: ${metrics.gas.min.toFixed(1)} gwei</div>
            <div>Max Gas: ${metrics.gas.max.toFixed(1)} gwei</div>
        `;
    }
}

// Initialize WebSocket connection when page loads
document.addEventListener('DOMContentLoaded', initWebSocket);
