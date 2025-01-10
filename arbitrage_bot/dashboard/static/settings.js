// Settings page functionality

// Initialize token modal
const addTokenModal = new bootstrap.Modal(document.getElementById('add-token-modal'));

// Load current settings
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();
        
        if (data.success) {
            // Update trading settings form
            document.getElementById('min-profit').value = data.settings.min_profit;
            document.getElementById('max-trade-size').value = data.settings.max_trade_size;
            document.getElementById('max-slippage').value = data.settings.max_slippage;
            document.getElementById('gas-buffer').value = data.settings.gas_buffer;
            document.getElementById('min-liquidity').value = data.settings.min_liquidity;
            document.getElementById('update-interval').value = data.settings.update_interval;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        showError('Failed to load settings');
    }
}

// Save trading settings
async function saveSettings(event) {
    event.preventDefault();
    
    try {
        const settings = {
            min_profit: parseFloat(document.getElementById('min-profit').value),
            max_trade_size: parseFloat(document.getElementById('max-trade-size').value),
            max_slippage: parseFloat(document.getElementById('max-slippage').value),
            gas_buffer: parseInt(document.getElementById('gas-buffer').value),
            min_liquidity: parseFloat(document.getElementById('min-liquidity').value),
            update_interval: parseInt(document.getElementById('update-interval').value)
        };
        
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        if (data.success) {
            showSuccess('Settings saved successfully');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showError('Failed to save settings');
    }
}

// Load token list
async function loadTokens() {
    try {
        const response = await fetch('/api/tokens');
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.getElementById('token-list');
            if (data.tokens.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">No tokens configured</td></tr>';
                return;
            }
            
            tbody.innerHTML = data.tokens.map(token => `
                <tr>
                    <td>${token.symbol}</td>
                    <td>
                        <a href="https://etherscan.io/token/${token.address}" target="_blank">
                            ${token.address}
                        </a>
                    </td>
                    <td>${token.decimals}</td>
                    <td>
                        <span class="badge bg-${token.approved ? 'success' : 'warning'}">
                            ${token.approved ? 'Approved' : 'Not Approved'}
                        </span>
                    </td>
                    <td>
                        ${token.approved ? `
                            <button class="btn btn-sm btn-danger" onclick="removeToken('${token.address}')">
                                Remove
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-primary" onclick="approveToken('${token.address}')">
                                Approve
                            </button>
                        `}
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading tokens:', error);
        showError('Failed to load tokens');
    }
}

// Add new token
async function addToken(event) {
    event.preventDefault();
    
    try {
        const address = document.getElementById('token-address').value;
        const response = await fetch('/api/tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ address })
        });
        
        const data = await response.json();
        if (data.success) {
            addTokenModal.hide();
            await loadTokens();
            showSuccess('Token added successfully');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error adding token:', error);
        showError('Failed to add token');
    }
}

// Remove token
async function removeToken(address) {
    if (!confirm('Are you sure you want to remove this token?')) return;
    
    try {
        const response = await fetch(`/api/tokens/${address}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            await loadTokens();
            showSuccess('Token removed successfully');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error removing token:', error);
        showError('Failed to remove token');
    }
}

// Approve token
async function approveToken(address) {
    try {
        const response = await fetch(`/api/tokens/${address}/approve`, {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            await loadTokens();
            showSuccess('Token approved successfully');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error approving token:', error);
        showError('Failed to approve token');
    }
}

// Update system status
async function updateSystemStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.success) {
            // Update connection statuses
            ['web3', 'trading', 'price-feed', 'db'].forEach(service => {
                const element = document.getElementById(`${service}-status`);
                const status = data.status[service];
                element.className = `badge bg-${status ? 'success' : 'danger'}`;
                element.textContent = status ? 'Connected' : 'Disconnected';
            });
            
            // Update network info
            document.getElementById('network-name').textContent = data.status.network;
            document.getElementById('gas-price').textContent = `${formatNumber(data.status.gas_price)} Gwei`;
            document.getElementById('block-number').textContent = formatNumber(data.status.block_number);
            document.getElementById('sync-status').textContent = data.status.syncing ? 'Syncing...' : 'Synced';
            
            // Update system resources
            ['cpu', 'memory', 'disk'].forEach(resource => {
                const usage = data.status[`${resource}_usage`];
                document.getElementById(`${resource}-usage`).textContent = `${usage}%`;
                document.getElementById(`${resource}-progress`).style.width = `${usage}%`;
                document.getElementById(`${resource}-progress`).className = 
                    `progress-bar ${usage > 80 ? 'bg-danger' : usage > 60 ? 'bg-warning' : 'bg-success'}`;
            });
        }
    } catch (error) {
        console.error('Error updating system status:', error);
        showError('Failed to update system status');
    }
}

// Show success message
function showSuccess(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').insertBefore(alert, document.querySelector('.container').firstChild);
    
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Initialize settings page
document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadSettings();
    loadTokens();
    updateSystemStatus();
    
    // Add event listeners
    document.getElementById('trading-settings').addEventListener('submit', saveSettings);
    document.getElementById('add-token-form').addEventListener('submit', addToken);
    
    // Auto-load token info when address is entered
    document.getElementById('token-address').addEventListener('input', async (event) => {
        const address = event.target.value;
        if (address.length === 42) { // Valid Ethereum address length
            try {
                const response = await fetch(`/api/tokens/${address}/info`);
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('token-symbol').value = data.token.symbol;
                    document.getElementById('token-decimals').value = data.token.decimals;
                }
            } catch (error) {
                console.error('Error loading token info:', error);
            }
        }
    });
    
    // Update system status periodically
    setInterval(updateSystemStatus, 5000); // Every 5 seconds
});
