/**
 * Settings module
 * Handles settings-specific functionality
 */

/**
 * Load config data from the API
 */
async function loadConfigData() {
    try {
        // Load config
        const response = await fetchAPI(API.config);
        
        if (response.success) {
            state.config = response.data;
        }
    } catch (error) {
        console.error('Error loading config data:', error);
    }
}

/**
 * Set up settings event listeners
 */
function setupSettingsEvents() {
    // Set up dashboard settings form
    const dashboardSettingsForm = document.getElementById('dashboard-settings-form');
    if (dashboardSettingsForm) {
        dashboardSettingsForm.addEventListener('submit', handleDashboardSettingsSubmit);
    }
    
    // Set up trading settings form
    const tradingSettingsForm = document.getElementById('trading-settings-form');
    if (tradingSettingsForm) {
        tradingSettingsForm.addEventListener('submit', handleTradingSettingsSubmit);
    }
    
    // Set up theme select
    const themeSelect = document.getElementById('theme');
    if (themeSelect) {
        themeSelect.addEventListener('change', handleThemeChange);
    }
}

/**
 * Handle dashboard settings form submit
 * @param {Event} event - The form submit event
 */
async function handleDashboardSettingsSubmit(event) {
    event.preventDefault();
    
    // Get form values
    const themeSelect = document.getElementById('theme');
    const refreshIntervalInput = document.getElementById('refresh-interval');
    const maxTradesDisplayInput = document.getElementById('max-trades-display');
    const enableNotificationsCheckbox = document.getElementById('enable-notifications');
    
    if (!themeSelect || !refreshIntervalInput || !maxTradesDisplayInput || !enableNotificationsCheckbox) {
        return;
    }
    
    // Create settings object
    const settings = {
        theme: themeSelect.value,
        refresh_interval: parseInt(refreshIntervalInput.value) * 1000, // Convert to milliseconds
        max_trades_display: parseInt(maxTradesDisplayInput.value),
        enable_notifications: enableNotificationsCheckbox.checked
    };
    
    try {
        // Save settings
        const response = await fetchAPI(API.settings, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.success) {
            // Update state
            state.theme = settings.theme;
            state.refreshInterval = settings.refresh_interval;
            
            // Apply theme
            applyTheme(state.theme);
            
            // Restart auto-refresh
            startAutoRefresh();
            
            // Save to localStorage
            localStorage.setItem('theme', state.theme);
            localStorage.setItem('refreshInterval', state.refreshInterval);
            
            alert('Dashboard settings saved successfully');
        } else {
            alert(`Error saving dashboard settings: ${response.error}`);
        }
    } catch (error) {
        console.error('Error saving dashboard settings:', error);
        alert(`Error saving dashboard settings: ${error.message}`);
    }
}

/**
 * Handle trading settings form submit
 * @param {Event} event - The form submit event
 */
async function handleTradingSettingsSubmit(event) {
    event.preventDefault();
    
    // Get form values
    const tradingEnabledCheckbox = document.getElementById('trading-enabled');
    const minProfitThresholdInput = document.getElementById('min-profit-threshold');
    const maxSlippageInput = document.getElementById('max-slippage');
    const gasPriceMultiplierInput = document.getElementById('gas-price-multiplier');
    const maxTradeAmountInput = document.getElementById('max-trade-amount');
    
    if (!tradingEnabledCheckbox || !minProfitThresholdInput || !maxSlippageInput || 
        !gasPriceMultiplierInput || !maxTradeAmountInput) {
        return;
    }
    
    // Create settings object
    const settings = {
        trading: {
            trading_enabled: tradingEnabledCheckbox.checked,
            min_profit_threshold: parseFloat(minProfitThresholdInput.value),
            max_slippage: parseFloat(maxSlippageInput.value),
            gas_price_multiplier: parseFloat(gasPriceMultiplierInput.value),
            max_trade_amount: parseFloat(maxTradeAmountInput.value)
        }
    };
    
    try {
        // Save settings
        const response = await fetchAPI(API.config, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.success) {
            alert('Trading settings saved successfully');
        } else {
            alert(`Error saving trading settings: ${response.error}`);
        }
    } catch (error) {
        console.error('Error saving trading settings:', error);
        alert(`Error saving trading settings: ${error.message}`);
    }
}

/**
 * Handle theme change
 * @param {Event} event - The change event
 */
function handleThemeChange(event) {
    const theme = event.target.value;
    applyTheme(theme);
}

/**
 * Update the settings UI with current data
 */
function updateSettingsUI() {
    // Update dashboard settings
    updateDashboardSettingsUI();
    
    // Update trading settings
    updateTradingSettingsUI();
}

/**
 * Update dashboard settings UI
 */
function updateDashboardSettingsUI() {
    // Get dashboard settings elements
    const themeSelect = document.getElementById('theme');
    const refreshIntervalInput = document.getElementById('refresh-interval');
    const maxTradesDisplayInput = document.getElementById('max-trades-display');
    const enableNotificationsCheckbox = document.getElementById('enable-notifications');
    
    if (!themeSelect || !refreshIntervalInput || !maxTradesDisplayInput || !enableNotificationsCheckbox) {
        return;
    }
    
    // Set values
    themeSelect.value = state.theme;
    refreshIntervalInput.value = state.refreshInterval / 1000; // Convert from milliseconds
    
    // Get dashboard settings from config
    const dashboardSettings = state.config?.dashboard || {};
    
    maxTradesDisplayInput.value = dashboardSettings.max_trades_display || 100;
    enableNotificationsCheckbox.checked = dashboardSettings.enable_notifications !== false;
}

/**
 * Update trading settings UI
 */
function updateTradingSettingsUI() {
    // Get trading settings elements
    const tradingEnabledCheckbox = document.getElementById('trading-enabled');
    const minProfitThresholdInput = document.getElementById('min-profit-threshold');
    const maxSlippageInput = document.getElementById('max-slippage');
    const gasPriceMultiplierInput = document.getElementById('gas-price-multiplier');
    const maxTradeAmountInput = document.getElementById('max-trade-amount');
    
    if (!tradingEnabledCheckbox || !minProfitThresholdInput || !maxSlippageInput || 
        !gasPriceMultiplierInput || !maxTradeAmountInput) {
        return;
    }
    
    // Get trading settings from config
    const tradingSettings = state.config?.trading || {};
    
    // Set values
    tradingEnabledCheckbox.checked = tradingSettings.trading_enabled === true;
    minProfitThresholdInput.value = tradingSettings.min_profit_threshold || 0.5;
    maxSlippageInput.value = tradingSettings.max_slippage || 1.0;
    gasPriceMultiplierInput.value = tradingSettings.gas_price_multiplier || 1.1;
    maxTradeAmountInput.value = tradingSettings.max_trade_amount || 1.0;
}
