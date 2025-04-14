"""Performance tests for configuration loading."""

import time
import statistics
import pytest

from arbitrage_bot.common.config.config_loader import load_config


@pytest.mark.performance
def test_config_loading_performance():
    """Test the performance of configuration loading."""
    # Number of times to run the test
    num_runs = 10
    
    # Measure the time taken to load the configuration
    times = []
    for _ in range(num_runs):
        start_time = time.time()
        config = load_config("test")
        end_time = time.time()
        times.append(end_time - start_time)
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    max_time = max(times)
    min_time = min(times)
    
    # Print statistics
    print(f"Config loading performance:")
    print(f"  Average time: {avg_time:.6f} seconds")
    print(f"  Maximum time: {max_time:.6f} seconds")
    print(f"  Minimum time: {min_time:.6f} seconds")
    
    # Assert that the average time is below a threshold
    assert avg_time < 0.1, f"Average config loading time ({avg_time:.6f}s) exceeds threshold (0.1s)"
