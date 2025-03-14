// Dashboard UI management
class DashboardManager {
    constructor(wsManager) {
        this.wsManager = wsManager;
        this.setupHandlers();
        this.setupRefreshInterval();
    }

    setupHandlers() {
        // Market data updates
        this.wsManager.addHandler('market_update', (data) => {
            this.updateMarketData(data);
        });

        // Portfolio updates
        this.wsManager.addHandler('portfolio_update', (data) => {
            this.updatePortfolio(data);
        });

        // Memory updates
        this.wsManager.addHandler('memory_update', (data) => {
            this.updateMemoryStatus(data);
        });

        // Storage updates
        this.wsManager.addHandler('storage_update', (data) => {
            this.updateStorageStatus(data);
        });

        // Distribution updates
        this.wsManager.addHandler('distribution_update', (data) => {
            this.updateDistribution(data);
        });

        // Execution updates
        this.wsManager.addHandler('execution_update', (data) => {
            this.updateExecution(data);
        });

        // Gas updates
        this.wsManager.addHandler('gas_update', (data) => {
            this.updateGasData(data);
        });
    }

    setupRefreshInterval() {
        // Refresh data every 5 seconds
        setInterval(() => {
            this.wsManager.requestInitialData();
        }, 5000);
    }

    updateMarketData(data) {
        const activePaths = document.getElementById('active-paths');
        if (activePaths) {
            activePaths.textContent = data.active_paths || '0';
        }
    }

    updatePortfolio(data) {
        const totalProfit = document.getElementById('total-profit');
        const successRate = document.getElementById('success-rate');

        if (totalProfit) {
            totalProfit.textContent = this.formatEther(data.total_profit_wei || '0');
        }

        if (successRate) {
            successRate.textContent = this.formatPercentage(data.success_rate || 0);
        }
    }

    updateMemoryStatus(data) {
        const memoryStatus = document.getElementById('memory-status');
        if (memoryStatus) {
            memoryStatus.textContent = 'Connected';
            memoryStatus.style.color = 'var(--success-color)';
        }
    }

    updateStorageStatus(data) {
        const storageStatus = document.getElementById('storage-status');
        if (storageStatus) {
            storageStatus.textContent = 'Connected';
            storageStatus.style.color = 'var(--success-color)';
        }
    }

    updateDistribution(data) {
        // Update distribution metrics
    }

    updateExecution(data) {
        // Update execution metrics
    }

    updateGasData(data) {
        const gasPrice = document.getElementById('gas-price');
        if (gasPrice && data.gas_prices) {
            gasPrice.textContent = this.formatGwei(data.gas_prices.base_fee || '0');
        }
    }

    updateActivityFeed(activity) {
        const feed = document.getElementById('activity-feed');
        if (!feed) return;

        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.innerHTML = `
            <span class="timestamp">${this.formatTimestamp(activity.timestamp)}</span>
            <span class="type">${activity.type}</span>
            <span class="details">${activity.details}</span>
        `;

        feed.insertBefore(activityItem, feed.firstChild);

        // Keep only the last 50 activities
        while (feed.children.length > 50) {
            feed.removeChild(feed.lastChild);
        }
    }

    updateSystemStatus(status) {
        const web3Status = document.getElementById('web3-status');
        const flashbotsStatus = document.getElementById('flashbots-status');

        if (web3Status) {
            web3Status.textContent = status.web3_connected ? 'Connected' : 'Disconnected';
            web3Status.style.color = status.web3_connected ? 'var(--success-color)' : 'var(--danger-color)';
        }

        if (flashbotsStatus) {
            flashbotsStatus.textContent = status.flashbots_connected ? 'Connected' : 'Disconnected';
            flashbotsStatus.style.color = status.flashbots_connected ? 'var(--success-color)' : 'var(--danger-color)';
        }
    }

    // Utility functions
    formatEther(wei) {
        const ether = Number(wei) / 1e18;
        return `${ether.toFixed(4)} ETH`;
    }

    formatGwei(wei) {
        const gwei = Number(wei) / 1e9;
        return `${gwei.toFixed(2)} Gwei`;
    }

    formatPercentage(value) {
        return `${(value * 100).toFixed(2)}%`;
    }

    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleTimeString();
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new DashboardManager(wsManager);
});