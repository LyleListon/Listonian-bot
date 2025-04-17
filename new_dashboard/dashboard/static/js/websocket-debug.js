/**
 * WebSocket Debug Tool
 * 
 * This script helps diagnose WebSocket connection issues by providing
 * detailed logging and connection status information.
 */

// Configuration
const wsDebugConfig = {
    logToConsole: true,
    logToUI: true,
    maxLogEntries: 100,
    pingInterval: 30000, // 30 seconds
};

// State
let wsDebugState = {
    connectionAttempts: 0,
    lastMessageTime: null,
    logs: [],
    pingTimer: null,
    connectionStatus: 'disconnected',
};

// Create debug UI
function createDebugUI() {
    // Check if debug UI already exists
    if (document.getElementById('ws-debug-panel')) {
        return;
    }
    
    // Create debug panel
    const debugPanel = document.createElement('div');
    debugPanel.id = 'ws-debug-panel';
    debugPanel.className = 'fixed bottom-0 right-0 bg-gray-900 text-white p-4 w-96 max-h-96 overflow-auto shadow-lg rounded-tl-lg z-50';
    debugPanel.style.display = 'none';
    
    // Add header
    debugPanel.innerHTML = `
        <div class="flex justify-between items-center mb-2">
            <h3 class="text-lg font-semibold">WebSocket Debug</h3>
            <div>
                <button id="ws-debug-clear" class="px-2 py-1 bg-red-600 text-white text-xs rounded mr-2">Clear</button>
                <button id="ws-debug-close" class="px-2 py-1 bg-gray-600 text-white text-xs rounded">Close</button>
            </div>
        </div>
        <div class="mb-2">
            <div class="flex justify-between">
                <span>Status:</span>
                <span id="ws-debug-status" class="font-mono">Disconnected</span>
            </div>
            <div class="flex justify-between">
                <span>Last Message:</span>
                <span id="ws-debug-last-msg" class="font-mono">Never</span>
            </div>
            <div class="flex justify-between">
                <span>Connection Attempts:</span>
                <span id="ws-debug-attempts" class="font-mono">0</span>
            </div>
        </div>
        <div id="ws-debug-log" class="font-mono text-xs bg-gray-800 p-2 rounded h-40 overflow-y-auto"></div>
    `;
    
    // Add to document
    document.body.appendChild(debugPanel);
    
    // Add event listeners
    document.getElementById('ws-debug-clear').addEventListener('click', () => {
        wsDebugState.logs = [];
        updateDebugUI();
    });
    
    document.getElementById('ws-debug-close').addEventListener('click', () => {
        debugPanel.style.display = 'none';
    });
    
    // Add keyboard shortcut (Ctrl+Shift+D) to toggle debug panel
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.key === 'D') {
            toggleDebugPanel();
            e.preventDefault();
        }
    });
}

// Toggle debug panel visibility
function toggleDebugPanel() {
    const panel = document.getElementById('ws-debug-panel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
}

// Update debug UI with current state
function updateDebugUI() {
    if (!wsDebugConfig.logToUI) return;
    
    const statusEl = document.getElementById('ws-debug-status');
    const lastMsgEl = document.getElementById('ws-debug-last-msg');
    const attemptsEl = document.getElementById('ws-debug-attempts');
    const logEl = document.getElementById('ws-debug-log');
    
    if (statusEl) {
        statusEl.textContent = wsDebugState.connectionStatus;
        statusEl.className = 
            wsDebugState.connectionStatus === 'connected' ? 'font-mono text-green-400' :
            wsDebugState.connectionStatus === 'connecting' ? 'font-mono text-yellow-400' :
            'font-mono text-red-400';
    }
    
    if (lastMsgEl) {
        lastMsgEl.textContent = wsDebugState.lastMessageTime 
            ? new Date(wsDebugState.lastMessageTime).toLocaleTimeString()
            : 'Never';
    }
    
    if (attemptsEl) {
        attemptsEl.textContent = wsDebugState.connectionAttempts;
    }
    
    if (logEl) {
        logEl.innerHTML = wsDebugState.logs.map(log => {
            const time = new Date(log.time).toLocaleTimeString();
            const levelClass = 
                log.level === 'error' ? 'text-red-400' :
                log.level === 'warn' ? 'text-yellow-400' :
                log.level === 'info' ? 'text-blue-400' :
                'text-gray-400';
            
            return `<div class="mb-1">
                <span class="text-gray-500">[${time}]</span>
                <span class="${levelClass}">[${log.level.toUpperCase()}]</span>
                <span>${log.message}</span>
            </div>`;
        }).join('');
        
        // Scroll to bottom
        logEl.scrollTop = logEl.scrollHeight;
    }
}

// Log a message
function wsDebugLog(level, message) {
    // Add to logs
    wsDebugState.logs.unshift({
        time: new Date(),
        level,
        message
    });
    
    // Trim logs if needed
    if (wsDebugState.logs.length > wsDebugConfig.maxLogEntries) {
        wsDebugState.logs = wsDebugState.logs.slice(0, wsDebugConfig.maxLogEntries);
    }
    
    // Log to console if enabled
    if (wsDebugConfig.logToConsole) {
        const method = level === 'error' ? 'error' : 
                      level === 'warn' ? 'warn' : 
                      level === 'info' ? 'info' : 'log';
        console[method](`[WebSocket] ${message}`);
    }
    
    // Update UI if enabled
    if (wsDebugConfig.logToUI) {
        updateDebugUI();
    }
}

// Initialize WebSocket debugging
function initWebSocketDebug(ws) {
    if (!ws) {
        wsDebugLog('error', 'Cannot initialize debugging: WebSocket is null');
        return;
    }
    
    // Create debug UI
    createDebugUI();
    
    // Reset state
    wsDebugState.connectionAttempts++;
    wsDebugState.connectionStatus = 'connecting';
    
    // Log connection attempt
    wsDebugLog('info', `Connection attempt #${wsDebugState.connectionAttempts}`);
    
    // Add event listeners
    ws.addEventListener('open', () => {
        wsDebugState.connectionStatus = 'connected';
        wsDebugLog('info', 'Connection established');
        
        // Start ping timer
        startPingTimer(ws);
    });
    
    ws.addEventListener('message', (event) => {
        wsDebugState.lastMessageTime = new Date();
        
        try {
            const data = JSON.parse(event.data);
            wsDebugLog('debug', `Received: ${JSON.stringify(data).substring(0, 100)}...`);
        } catch (error) {
            wsDebugLog('warn', `Received non-JSON message: ${event.data.substring(0, 100)}...`);
        }
    });
    
    ws.addEventListener('close', (event) => {
        wsDebugState.connectionStatus = 'disconnected';
        wsDebugLog('warn', `Connection closed: Code ${event.code}, Reason: ${event.reason || 'None'}`);
        
        // Stop ping timer
        stopPingTimer();
    });
    
    ws.addEventListener('error', (error) => {
        wsDebugState.connectionStatus = 'error';
        wsDebugLog('error', `Connection error: ${error.message || 'Unknown error'}`);
    });
    
    // Update UI
    updateDebugUI();
    
    return ws;
}

// Start ping timer
function startPingTimer(ws) {
    // Stop existing timer if any
    stopPingTimer();
    
    // Start new timer
    wsDebugState.pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
            // Send ping
            try {
                ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }));
                wsDebugLog('debug', 'Ping sent');
            } catch (error) {
                wsDebugLog('error', `Failed to send ping: ${error.message}`);
            }
        } else {
            wsDebugLog('warn', `Cannot send ping: WebSocket state is ${ws.readyState}`);
            stopPingTimer();
        }
    }, wsDebugConfig.pingInterval);
}

// Stop ping timer
function stopPingTimer() {
    if (wsDebugState.pingTimer) {
        clearInterval(wsDebugState.pingTimer);
        wsDebugState.pingTimer = null;
    }
}

// Export functions
window.wsDebug = {
    init: initWebSocketDebug,
    log: wsDebugLog,
    toggle: toggleDebugPanel,
    getState: () => ({ ...wsDebugState }),
    getConfig: () => ({ ...wsDebugConfig }),
    setConfig: (config) => {
        wsDebugConfig = { ...wsDebugConfig, ...config };
    }
};
