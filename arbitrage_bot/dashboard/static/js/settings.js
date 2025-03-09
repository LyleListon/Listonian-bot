// Settings page functionality
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements - Trading Settings
    const tradingForm = document.getElementById('trading-settings-form');
    const minProfit = document.getElementById('min-profit');
    const maxSlippage = document.getElementById('max-slippage');
    const gasLimit = document.getElementById('gas-limit');
    const tradeSize = document.getElementById('trade-size');

    // DOM elements - Risk Management
    const riskForm = document.getElementById('risk-settings-form');
    const dailyLimit = document.getElementById('daily-limit');
    const maxExposure = document.getElementById('max-exposure');
    const stopLoss = document.getElementById('stop-loss');

    // DOM elements - DEX Settings
    const dexForm = document.getElementById('dex-settings-form');
    const dexList = document.getElementById('dex-list');
    const minLiquidity = document.getElementById('min-liquidity');

    // DOM elements - Notification Settings
    const notificationForm = document.getElementById('notification-settings-form');
    const tradeNotifications = document.querySelector('input[name="trade_notifications"]');
    const errorNotifications = document.querySelector('input[name="error_notifications"]');
    const profitNotifications = document.querySelector('input[name="profit_notifications"]');
    const notificationEmail = document.getElementById('notification-email');

    // DOM elements - Advanced Settings
    const advancedForm = document.getElementById('advanced-settings-form');
    const concurrentTrades = document.getElementById('concurrent-trades');
    const retryAttempts = document.getElementById('retry-attempts');
    const autoGasAdjustment = document.querySelector('input[name="auto_gas_adjustment"]');
    const debugMode = document.querySelector('input[name="debug_mode"]');

    // Buttons
    const saveButton = document.getElementById('save-settings');
    const resetButton = document.getElementById('reset-settings');

    // Form validation
    function validateSettings() {
        const errors = [];

        // Trading Settings validation
        if (minProfit.value < 0) errors.push('Minimum profit must be non-negative');
        if (maxSlippage.value < 0 || maxSlippage.value > 100) errors.push('Slippage must be between 0 and 100');
        if (gasLimit.value < 0) errors.push('Gas limit must be non-negative');
        if (tradeSize.value < 0) errors.push('Trade size must be non-negative');

        // Risk Management validation
        if (dailyLimit.value < 0) errors.push('Daily limit must be non-negative');
        if (maxExposure.value < 0 || maxExposure.value > 100) errors.push('Max exposure must be between 0 and 100');
        if (stopLoss.value < 0 || stopLoss.value > 100) errors.push('Stop loss must be between 0 and 100');

        // DEX Settings validation
        if (minLiquidity.value < 0) errors.push('Minimum liquidity must be non-negative');

        // Advanced Settings validation
        if (concurrentTrades.value < 1) errors.push('Must allow at least 1 concurrent trade');
        if (retryAttempts.value < 0) errors.push('Retry attempts must be non-negative');

        return errors;
    }

    // Save settings
    saveButton.addEventListener('click', async () => {
        const errors = validateSettings();
        if (errors.length > 0) {
            alert('Validation errors:\n' + errors.join('\n'));
            return;
        }

        const settings = {
            trading: {
                min_profit: parseFloat(minProfit.value),
                max_slippage: parseFloat(maxSlippage.value),
                gas_limit: parseInt(gasLimit.value),
                trade_size: parseFloat(tradeSize.value)
            },
            risk: {
                daily_limit: parseFloat(dailyLimit.value),
                max_exposure: parseFloat(maxExposure.value),
                stop_loss: parseFloat(stopLoss.value)
            },
            dex: {
                enabled_dexs: Array.from(dexList.querySelectorAll('input[type="checkbox"]:checked'))
                    .map(cb => cb.value),
                min_liquidity: parseFloat(minLiquidity.value)
            },
            notifications: {
                trade_notifications: tradeNotifications.checked,
                error_notifications: errorNotifications.checked,
                profit_notifications: profitNotifications.checked,
                notification_email: notificationEmail.value
            },
            advanced: {
                concurrent_trades: parseInt(concurrentTrades.value),
                retry_attempts: parseInt(retryAttempts.value),
                auto_gas_adjustment: autoGasAdjustment.checked,
                debug_mode: debugMode.checked
            }
        };

        try {
            socket.emit('save_settings', settings);
            showNotification('Settings saved successfully', 'success');
        } catch (error) {
            showNotification('Error saving settings: ' + error.message, 'error');
        }
    });

    // Reset settings
    resetButton.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all settings to default values?')) {
            socket.emit('reset_settings');
        }
    });

    // Update DEX list
    function updateDexList(dexs) {
        dexList.innerHTML = dexs.map(dex => `
            <div class="dex-option">
                <label>
                    <input type="checkbox" value="${dex.id}" ${dex.enabled ? 'checked' : ''}>
                    ${dex.name}
                </label>
                <div class="dex-info">
                    <span>Volume: $${formatNumber(dex.volume_24h)}</span>
                    <span>Liquidity: $${formatNumber(dex.liquidity)}</span>
                </div>
            </div>
        `).join('');
    }

    // Notification display
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    // Format numbers for display
    function formatNumber(num) {
        if (num >= 1e9) {
            return `${(num / 1e9).toFixed(2)}B`;
        } else if (num >= 1e6) {
            return `${(num / 1e6).toFixed(2)}M`;
        } else if (num >= 1e3) {
            return `${(num / 1e3).toFixed(2)}K`;
        }
        return num.toFixed(2);
    }

    // Socket.io event handlers
    socket.on('settings_update', (data) => {
        // Update Trading Settings
        minProfit.value = data.trading.min_profit;
        maxSlippage.value = data.trading.max_slippage;
        gasLimit.value = data.trading.gas_limit;
        tradeSize.value = data.trading.trade_size;

        // Update Risk Management
        dailyLimit.value = data.risk.daily_limit;
        maxExposure.value = data.risk.max_exposure;
        stopLoss.value = data.risk.stop_loss;

        // Update DEX Settings
        updateDexList(data.dex.available_dexs);
        minLiquidity.value = data.dex.min_liquidity;

        // Update Notification Settings
        tradeNotifications.checked = data.notifications.trade_notifications;
        errorNotifications.checked = data.notifications.error_notifications;
        profitNotifications.checked = data.notifications.profit_notifications;
        notificationEmail.value = data.notifications.notification_email;

        // Update Advanced Settings
        concurrentTrades.value = data.advanced.concurrent_trades;
        retryAttempts.value = data.advanced.retry_attempts;
        autoGasAdjustment.checked = data.advanced.auto_gas_adjustment;
        debugMode.checked = data.advanced.debug_mode;
    });

    socket.on('settings_saved', () => {
        showNotification('Settings saved successfully', 'success');
    });

    socket.on('settings_error', (error) => {
        showNotification('Error: ' + error, 'error');
    });

    // Request initial settings
    socket.emit('get_settings');
});