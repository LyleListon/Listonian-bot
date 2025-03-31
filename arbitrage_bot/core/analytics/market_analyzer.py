"""
Market Analyzer Module

Provides sophisticated market analysis for the arbitrage system.
"""

import logging
import asyncio
import math
from typing import Dict, Any, Optional, List, Tuple, Set
from decimal import Decimal
from datetime import datetime, timedelta
import json
import os
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    Analyzes market trends and conditions.
    
    Features:
    - Market trend detection
    - Correlation analysis between tokens
    - Volatility forecasting
    - Liquidity depth analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the market analyzer.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()
        
        # Storage for market data
        self._price_history = {}  # token_address -> list of price points
        self._liquidity_history = {}  # token_address -> list of liquidity points
        self._volume_history = {}  # token_address -> list of volume points
        
        # Storage paths
        self.storage_dir = self.config.get('storage_dir', 'analytics')
        self.market_data_file = os.path.join(self.storage_dir, 'market_data.json')
        
        # Analysis settings
        self.trend_detection_window = int(self.config.get('trend_detection_window', 24))  # hours
        self.volatility_window = int(self.config.get('volatility_window', 7))  # days
        self.correlation_window = int(self.config.get('correlation_window', 30))  # days
        
        # Cache settings
        self.cache_ttl = int(self.config.get('cache_ttl', 300))  # 5 minutes
        self._last_cache_update = 0
        self._cached_analysis = {}
        
    async def initialize(self) -> bool:
        """
        Initialize the market analyzer.
        
        Returns:
            True if initialization successful
        """
        try:
            # Create storage directory if it doesn't exist
            os.makedirs(self.storage_dir, exist_ok=True)
            
            # Load historical data if available
            await self._load_historical_data()
            
            self.initialized = True
            logger.info("Market analyzer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize market analyzer: {e}")
            return False
    
    async def _load_historical_data(self) -> None:
        """Load historical market data from storage."""
        try:
            if os.path.exists(self.market_data_file):
                async with self.lock:
                    with open(self.market_data_file, 'r') as f:
                        data = json.load(f)
                    
                    # Process price history
                    if 'price_history' in data:
                        for token, history in data['price_history'].items():
                            # Convert string timestamps to datetime objects
                            for entry in history:
                                if 'timestamp' in entry:
                                    entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                            self._price_history[token] = history
                    
                    # Process liquidity history
                    if 'liquidity_history' in data:
                        for token, history in data['liquidity_history'].items():
                            # Convert string timestamps to datetime objects
                            for entry in history:
                                if 'timestamp' in entry:
                                    entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                            self._liquidity_history[token] = history
                    
                    # Process volume history
                    if 'volume_history' in data:
                        for token, history in data['volume_history'].items():
                            # Convert string timestamps to datetime objects
                            for entry in history:
                                if 'timestamp' in entry:
                                    entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                            self._volume_history[token] = history
                    
                    logger.info(f"Loaded market data for {len(self._price_history)} tokens")
            else:
                logger.info("No historical market data found")
        except Exception as e:
            logger.error(f"Error loading historical market data: {e}")
    
    async def _save_historical_data(self) -> None:
        """Save historical market data to storage."""
        try:
            async with self.lock:
                # Prepare data for serialization
                data = {
                    'price_history': {},
                    'liquidity_history': {},
                    'volume_history': {}
                }
                
                # Process price history
                for token, history in self._price_history.items():
                    serialized_history = []
                    for entry in history:
                        entry_copy = entry.copy()
                        if isinstance(entry_copy.get('timestamp'), datetime):
                            entry_copy['timestamp'] = entry_copy['timestamp'].isoformat()
                        serialized_history.append(entry_copy)
                    data['price_history'][token] = serialized_history
                
                # Process liquidity history
                for token, history in self._liquidity_history.items():
                    serialized_history = []
                    for entry in history:
                        entry_copy = entry.copy()
                        if isinstance(entry_copy.get('timestamp'), datetime):
                            entry_copy['timestamp'] = entry_copy['timestamp'].isoformat()
                        serialized_history.append(entry_copy)
                    data['liquidity_history'][token] = serialized_history
                
                # Process volume history
                for token, history in self._volume_history.items():
                    serialized_history = []
                    for entry in history:
                        entry_copy = entry.copy()
                        if isinstance(entry_copy.get('timestamp'), datetime):
                            entry_copy['timestamp'] = entry_copy['timestamp'].isoformat()
                        serialized_history.append(entry_copy)
                    data['volume_history'][token] = serialized_history
                
                with open(self.market_data_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Saved market data for {len(self._price_history)} tokens")
        except Exception as e:
            logger.error(f"Error saving historical market data: {e}")
    
    async def track_price(self, token_address: str, price_data: Dict[str, Any]) -> None:
        """
        Track a new price point for a token.
        
        Args:
            token_address: Token address (checksummed)
            price_data: Dictionary containing price data with at least:
                - price: Current price
                - timestamp: Price timestamp (optional, defaults to now)
                - source: Price data source (e.g., "uniswap", "chainlink")
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
        
        # Ensure required fields are present
        if 'price' not in price_data:
            raise ValueError("Missing required field: price")
        
        # Add timestamp if not present
        if 'timestamp' not in price_data:
            price_data['timestamp'] = datetime.utcnow()
        
        async with self.lock:
            # Initialize price history for token if not exists
            if token_address not in self._price_history:
                self._price_history[token_address] = []
            
            # Add price data
            self._price_history[token_address].append(price_data)
            
            # Sort by timestamp
            self._price_history[token_address].sort(key=lambda x: x.get('timestamp', datetime.min))
            
            # Limit history size (keep last 90 days)
            cutoff = datetime.utcnow() - timedelta(days=90)
            self._price_history[token_address] = [
                entry for entry in self._price_history[token_address]
                if entry.get('timestamp', datetime.utcnow()) >= cutoff
            ]
            
            # Invalidate cache
            self._cached_analysis = {}
            
            # Save to storage
            await self._save_historical_data()
    
    async def track_liquidity(self, token_address: str, liquidity_data: Dict[str, Any]) -> None:
        """
        Track a new liquidity point for a token.
        
        Args:
            token_address: Token address (checksummed)
            liquidity_data: Dictionary containing liquidity data with at least:
                - liquidity: Current liquidity
                - timestamp: Liquidity timestamp (optional, defaults to now)
                - dex: DEX name
                - pool_address: Pool address (optional)
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
        
        # Ensure required fields are present
        if 'liquidity' not in liquidity_data:
            raise ValueError("Missing required field: liquidity")
        
        # Add timestamp if not present
        if 'timestamp' not in liquidity_data:
            liquidity_data['timestamp'] = datetime.utcnow()
        
        async with self.lock:
            # Initialize liquidity history for token if not exists
            if token_address not in self._liquidity_history:
                self._liquidity_history[token_address] = []
            
            # Add liquidity data
            self._liquidity_history[token_address].append(liquidity_data)
            
            # Sort by timestamp
            self._liquidity_history[token_address].sort(key=lambda x: x.get('timestamp', datetime.min))
            
            # Limit history size (keep last 90 days)
            cutoff = datetime.utcnow() - timedelta(days=90)
            self._liquidity_history[token_address] = [
                entry for entry in self._liquidity_history[token_address]
                if entry.get('timestamp', datetime.utcnow()) >= cutoff
            ]
            
            # Invalidate cache
            self._cached_analysis = {}
            
            # Save to storage
            await self._save_historical_data()
    
    async def track_volume(self, token_address: str, volume_data: Dict[str, Any]) -> None:
        """
        Track a new volume point for a token.
        
        Args:
            token_address: Token address (checksummed)
            volume_data: Dictionary containing volume data with at least:
                - volume: Trading volume
                - timestamp: Volume timestamp (optional, defaults to now)
                - dex: DEX name
                - period: Time period (e.g., "1h", "24h")
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
        
        # Ensure required fields are present
        if 'volume' not in volume_data:
            raise ValueError("Missing required field: volume")
        
        # Add timestamp if not present
        if 'timestamp' not in volume_data:
            volume_data['timestamp'] = datetime.utcnow()
        
        async with self.lock:
            # Initialize volume history for token if not exists
            if token_address not in self._volume_history:
                self._volume_history[token_address] = []
            
            # Add volume data
            self._volume_history[token_address].append(volume_data)
            
            # Sort by timestamp
            self._volume_history[token_address].sort(key=lambda x: x.get('timestamp', datetime.min))
            
            # Limit history size (keep last 90 days)
            cutoff = datetime.utcnow() - timedelta(days=90)
            self._volume_history[token_address] = [
                entry for entry in self._volume_history[token_address]
                if entry.get('timestamp', datetime.utcnow()) >= cutoff
            ]
            
            # Invalidate cache
            self._cached_analysis = {}
            
            # Save to storage
            await self._save_historical_data()
    
    async def detect_market_trend(self, token_address: str, timeframe: str = "24h") -> Dict[str, Any]:
        """
        Detect market trend for a specific token.
        
        Args:
            token_address: Token address (checksummed)
            timeframe: Time frame for trend detection ("1h", "4h", "12h", "24h", "7d", "30d")
            
        Returns:
            Dictionary with trend analysis
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
        
        # Check if token exists
        if token_address not in self._price_history:
            return {
                'token_address': token_address,
                'timeframe': timeframe,
                'trend': 'unknown',
                'confidence': 0,
                'price_change': 0,
                'volatility': 0,
                'support_levels': [],
                'resistance_levels': []
            }
        
        # Check cache
        cache_key = f"trend_{token_address}_{timeframe}"
        if cache_key in self._cached_analysis:
            current_time = asyncio.get_event_loop().time()
            if current_time - self._last_cache_update < self.cache_ttl:
                return self._cached_analysis[cache_key]
        
        async with self.lock:
            # Filter data by timeframe
            filtered_data = await self._filter_price_by_timeframe(token_address, timeframe)
            
            if not filtered_data or len(filtered_data) < 2:
                return {
                    'token_address': token_address,
                    'timeframe': timeframe,
                    'trend': 'unknown',
                    'confidence': 0,
                    'price_change': 0,
                    'volatility': 0,
                    'support_levels': [],
                    'resistance_levels': []
                }
            
            # Calculate price change
            first_price = float(filtered_data[0].get('price', 0))
            last_price = float(filtered_data[-1].get('price', 0))
            
            if first_price <= 0:
                price_change = 0
            else:
                price_change = (last_price - first_price) / first_price * 100
            
            # Calculate volatility
            prices = [float(entry.get('price', 0)) for entry in filtered_data]
            volatility = np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0
            
            # Determine trend
            trend, confidence = await self._determine_trend(filtered_data)
            
            # Find support and resistance levels
            support_levels, resistance_levels = await self._find_support_resistance(filtered_data)
            
            # Prepare result
            result = {
                'token_address': token_address,
                'timeframe': timeframe,
                'trend': trend,
                'confidence': confidence,
                'price_change': price_change,
                'volatility': volatility,
                'support_levels': support_levels,
                'resistance_levels': resistance_levels,
                'current_price': last_price,
                'price_data': {
                    'timestamps': [entry.get('timestamp').isoformat() for entry in filtered_data],
                    'prices': [float(entry.get('price', 0)) for entry in filtered_data]
                }
            }
            
            # Update cache
            self._cached_analysis[cache_key] = result
            self._last_cache_update = asyncio.get_event_loop().time()
            
            return result
    
    async def _filter_price_by_timeframe(self, token_address: str, timeframe: str) -> List[Dict[str, Any]]:
        """Filter price data by timeframe."""
        if token_address not in self._price_history:
            return []
        
        now = datetime.utcnow()
        
        if timeframe == "1h":
            start_time = now - timedelta(hours=1)
        elif timeframe == "4h":
            start_time = now - timedelta(hours=4)
        elif timeframe == "12h":
            start_time = now - timedelta(hours=12)
        elif timeframe == "24h":
            start_time = now - timedelta(hours=24)
        elif timeframe == "7d":
            start_time = now - timedelta(days=7)
        elif timeframe == "30d":
            start_time = now - timedelta(days=30)
        else:
            raise ValueError(f"Invalid timeframe: {timeframe}")
        
        return [
            entry for entry in self._price_history[token_address]
            if entry.get('timestamp', now) >= start_time
        ]
    
    async def _determine_trend(self, price_data: List[Dict[str, Any]]) -> Tuple[str, float]:
        """
        Determine trend from price data.
        
        Returns:
            Tuple of (trend, confidence)
            trend: "bullish", "bearish", "sideways", or "unknown"
            confidence: 0.0 to 1.0
        """
        if not price_data or len(price_data) < 2:
            return "unknown", 0.0
        
        # Extract prices
        prices = [float(entry.get('price', 0)) for entry in price_data]
        
        # Calculate simple moving average
        window_size = min(len(prices) // 4, 24) or 1  # Use 1/4 of data points or 24, whichever is smaller
        sma = []
        
        for i in range(len(prices) - window_size + 1):
            window = prices[i:i+window_size]
            sma.append(sum(window) / window_size)
        
        if not sma or len(sma) < 2:
            return "unknown", 0.0
        
        # Calculate trend based on SMA slope
        sma_change = (sma[-1] - sma[0]) / sma[0] if sma[0] > 0 else 0
        
        # Calculate price volatility
        volatility = np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0
        
        # Determine trend
        if sma_change > 0.02:  # 2% increase
            trend = "bullish"
            confidence = min(abs(sma_change) * 5, 1.0)  # Scale confidence
        elif sma_change < -0.02:  # 2% decrease
            trend = "bearish"
            confidence = min(abs(sma_change) * 5, 1.0)  # Scale confidence
        else:
            trend = "sideways"
            confidence = 1.0 - min(volatility * 10, 0.9)  # Higher volatility = lower confidence
        
        return trend, confidence
    
    async def _find_support_resistance(self, price_data: List[Dict[str, Any]]) -> Tuple[List[float], List[float]]:
        """Find support and resistance levels."""
        if not price_data or len(price_data) < 10:
            return [], []
        
        # Extract prices
        prices = [float(entry.get('price', 0)) for entry in price_data]
        
        # Find local minima and maxima
        min_points = []
        max_points = []
        
        for i in range(1, len(prices) - 1):
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                min_points.append(prices[i])
            elif prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                max_points.append(prices[i])
        
        # Cluster similar levels
        support_levels = await self._cluster_price_levels(min_points)
        resistance_levels = await self._cluster_price_levels(max_points)
        
        return support_levels, resistance_levels
    
    async def _cluster_price_levels(self, price_points: List[float]) -> List[float]:
        """Cluster similar price levels."""
        if not price_points:
            return []
        
        # Sort price points
        sorted_points = sorted(price_points)
        
        # Calculate average price
        avg_price = sum(sorted_points) / len(sorted_points)
        
        # Define clustering threshold (0.5% of average price)
        threshold = avg_price * 0.005
        
        # Cluster similar price levels
        clusters = []
        current_cluster = [sorted_points[0]]
        
        for i in range(1, len(sorted_points)):
            if sorted_points[i] - sorted_points[i-1] <= threshold:
                # Add to current cluster
                current_cluster.append(sorted_points[i])
            else:
                # Start a new cluster
                clusters.append(current_cluster)
                current_cluster = [sorted_points[i]]
        
        # Add the last cluster
        if current_cluster:
            clusters.append(current_cluster)
        
        # Calculate average price for each cluster
        return [sum(cluster) / len(cluster) for cluster in clusters]
    
    async def analyze_token_correlation(self, token_addresses: List[str], timeframe: str = "7d") -> Dict[str, Any]:
        """
        Analyze correlation between tokens.
        
        Args:
            token_addresses: List of token addresses (checksummed)
            timeframe: Time frame for analysis ("24h", "7d", "30d")
            
        Returns:
            Dictionary with correlation analysis
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
        
        # Check if tokens exist
        existing_tokens = [addr for addr in token_addresses if addr in self._price_history]
        
        if not existing_tokens or len(existing_tokens) < 2:
            return {
                'timeframe': timeframe,
                'token_count': len(existing_tokens),
                'correlation_matrix': {},
                'highly_correlated_pairs': [],
                'inversely_correlated_pairs': []
            }
        
        # Check cache
        token_key = '_'.join(sorted(existing_tokens))
        cache_key = f"correlation_{token_key}_{timeframe}"
        if cache_key in self._cached_analysis:
            current_time = asyncio.get_event_loop().time()
            if current_time - self._last_cache_update < self.cache_ttl:
                return self._cached_analysis[cache_key]
        
        async with self.lock:
            # Get price data for each token
            token_prices = {}
            common_timestamps = set()
            first_token = True
            
            for token in existing_tokens:
                # Filter data by timeframe
                filtered_data = await self._filter_price_by_timeframe(token, timeframe)
                
                if not filtered_data:
                    continue
                
                # Extract timestamps and prices
                timestamps = [entry.get('timestamp') for entry in filtered_data]
                prices = [float(entry.get('price', 0)) for entry in filtered_data]
                
                token_prices[token] = {
                    'timestamps': timestamps,
                    'prices': prices
                }
                
                # Track common timestamps
                token_timestamps = set(timestamps)
                if first_token:
                    common_timestamps = token_timestamps
                    first_token = False
                else:
                    common_timestamps &= token_timestamps
            
            if not common_timestamps or len(token_prices) < 2:
                return {
                    'timeframe': timeframe,
                    'token_count': len(token_prices),
                    'correlation_matrix': {},
                    'highly_correlated_pairs': [],
                    'inversely_correlated_pairs': []
                }
            
            # Convert common timestamps to list and sort
            common_timestamps_list = sorted(list(common_timestamps))
            
            # Create aligned price series
            aligned_prices = {}
            for token, data in token_prices.items():
                # Create a mapping of timestamp to price
                ts_to_price = {ts: price for ts, price in zip(data['timestamps'], data['prices'])}
                
                # Extract prices for common timestamps
                aligned_prices[token] = [ts_to_price.get(ts, 0) for ts in common_timestamps_list]
            
            # Calculate correlation matrix
            correlation_matrix = {}
            for token1 in aligned_prices:
                correlation_matrix[token1] = {}
                for token2 in aligned_prices:
                    if token1 == token2:
                        correlation_matrix[token1][token2] = 1.0
                    else:
                        # Calculate correlation coefficient
                        prices1 = aligned_prices[token1]
                        prices2 = aligned_prices[token2]
                        
                        if len(prices1) < 2 or len(prices2) < 2:
                            correlation_matrix[token1][token2] = 0.0
                            continue
                        
                        correlation = np.corrcoef(prices1, prices2)[0, 1]
                        correlation_matrix[token1][token2] = correlation
            
            # Find highly correlated and inversely correlated pairs
            highly_correlated = []
            inversely_correlated = []
            
            for token1 in correlation_matrix:
                for token2 in correlation_matrix[token1]:
                    if token1 >= token2:  # Avoid duplicates
                        continue
                    
                    correlation = correlation_matrix[token1][token2]
                    
                    if correlation >= 0.7:
                        highly_correlated.append({
                            'token1': token1,
                            'token2': token2,
                            'correlation': correlation
                        })
                    elif correlation <= -0.7:
                        inversely_correlated.append({
                            'token1': token1,
                            'token2': token2,
                            'correlation': correlation
                        })
            
            # Sort by absolute correlation (descending)
            highly_correlated.sort(key=lambda x: x['correlation'], reverse=True)
            inversely_correlated.sort(key=lambda x: x['correlation'])
            
            # Prepare result
            result = {
                'timeframe': timeframe,
                'token_count': len(token_prices),
                'correlation_matrix': correlation_matrix,
                'highly_correlated_pairs': highly_correlated,
                'inversely_correlated_pairs': inversely_correlated,
                'timestamp_count': len(common_timestamps_list)
            }
            
            # Update cache
            self._cached_analysis[cache_key] = result
            self._last_cache_update = asyncio.get_event_loop().time()
            
            return result
    
    async def forecast_volatility(self, token_address: str, timeframe: str = "24h") -> Dict[str, Any]:
        """
        Forecast volatility for a specific token.
        
        Args:
            token_address: Token address (checksummed)
            timeframe: Time frame for forecasting ("24h", "7d", "30d")
            
        Returns:
            Dictionary with volatility forecast
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
        
        # Check if token exists
        if token_address not in self._price_history:
            return {
                'token_address': token_address,
                'timeframe': timeframe,
                'historical_volatility': 0,
                'forecasted_volatility': 0,
                'confidence': 0,
                'volatility_trend': 'unknown'
            }
        
        # Check cache
        cache_key = f"volatility_{token_address}_{timeframe}"
        if cache_key in self._cached_analysis:
            current_time = asyncio.get_event_loop().time()
            if current_time - self._last_cache_update < self.cache_ttl:
                return self._cached_analysis[cache_key]
        
        async with self.lock:
            # Filter data by timeframe
            filtered_data = await self._filter_price_by_timeframe(token_address, timeframe)
            
            if not filtered_data or len(filtered_data) < 5:
                return {
                    'token_address': token_address,
                    'timeframe': timeframe,
                    'historical_volatility': 0,
                    'forecasted_volatility': 0,
                    'confidence': 0,
                    'volatility_trend': 'unknown'
                }
            
            # Calculate historical volatility
            prices = [float(entry.get('price', 0)) for entry in filtered_data]
            returns = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
            
            historical_volatility = np.std(returns) * np.sqrt(365)  # Annualized
            
            # Forecast volatility using EWMA (Exponentially Weighted Moving Average)
            lambda_param = 0.94  # Standard EWMA parameter
            
            # Initialize with historical volatility
            forecasted_volatility = historical_volatility
            
            # Apply EWMA
            for i in range(len(returns) - 1, 0, -1):
                forecasted_volatility = np.sqrt(lambda_param * forecasted_volatility**2 + 
                                              (1 - lambda_param) * returns[i]**2)
            
            # Determine volatility trend
            if len(returns) >= 10:
                early_vol = np.std(returns[:len(returns)//2]) * np.sqrt(365)
                late_vol = np.std(returns[len(returns)//2:]) * np.sqrt(365)
                
                if late_vol > early_vol * 1.2:
                    volatility_trend = "increasing"
                elif late_vol < early_vol * 0.8:
                    volatility_trend = "decreasing"
                else:
                    volatility_trend = "stable"
            else:
                volatility_trend = "unknown"
            
            # Calculate confidence based on data points
            confidence = min(len(returns) / 30, 1.0)  # More data points = higher confidence
            
            # Prepare result
            result = {
                'token_address': token_address,
                'timeframe': timeframe,
                'historical_volatility': historical_volatility,
                'forecasted_volatility': forecasted_volatility,
                'confidence': confidence,
                'volatility_trend': volatility_trend,
                'data_points': len(returns)
            }
            
            # Update cache
            self._cached_analysis[cache_key] = result
            self._last_cache_update = asyncio.get_event_loop().time()
            
            return result
    
    async def analyze_liquidity_depth(self, token_address: str, 
                                     dex_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze liquidity depth for a specific token across DEXes.
        
        Args:
            token_address: Token address (checksummed)
            dex_list: Optional list of DEXes to include (if None, includes all)
            
        Returns:
            Dictionary with liquidity analysis
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")
        
        # Check if token exists
