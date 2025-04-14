"""Helper functions for the arbitrage bot."""

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID.
    
    Args:
        prefix: A prefix to add to the ID.
        
    Returns:
        A unique ID.
    """
    return f"{prefix}{uuid.uuid4()}"


def timestamp_now() -> int:
    """Get the current timestamp in seconds.
    
    Returns:
        The current timestamp in seconds.
    """
    return int(time.time())


def format_amount(amount: Union[int, float], decimals: int = 18) -> str:
    """Format an amount with the specified number of decimals.
    
    Args:
        amount: The amount to format.
        decimals: The number of decimals to use.
        
    Returns:
        The formatted amount as a string.
    """
    return f"{amount:.{decimals}f}"


def calculate_percentage(value: float, total: float) -> float:
    """Calculate a percentage.
    
    Args:
        value: The value.
        total: The total.
        
    Returns:
        The percentage.
    """
    if total == 0:
        return 0.0
    return (value / total) * 100.0


def calculate_price_impact(
    input_amount: float, output_amount: float, input_price: float
) -> float:
    """Calculate the price impact of a trade.
    
    Args:
        input_amount: The input amount.
        output_amount: The output amount.
        input_price: The price of the input token in terms of the output token.
        
    Returns:
        The price impact as a percentage.
    """
    expected_output = input_amount * input_price
    if expected_output == 0:
        return 0.0
    
    impact = (expected_output - output_amount) / expected_output
    return impact * 100.0


def calculate_profit(
    input_amount: float,
    output_amount: float,
    gas_cost: float = 0.0,
    flash_loan_fee: float = 0.0,
) -> float:
    """Calculate the profit from a trade.
    
    Args:
        input_amount: The input amount.
        output_amount: The output amount.
        gas_cost: The gas cost in the same unit as input_amount.
        flash_loan_fee: The flash loan fee in the same unit as input_amount.
        
    Returns:
        The profit.
    """
    return output_amount - input_amount - gas_cost - flash_loan_fee


def calculate_roi(
    input_amount: float,
    output_amount: float,
    gas_cost: float = 0.0,
    flash_loan_fee: float = 0.0,
) -> float:
    """Calculate the ROI from a trade.
    
    Args:
        input_amount: The input amount.
        output_amount: The output amount.
        gas_cost: The gas cost in the same unit as input_amount.
        flash_loan_fee: The flash loan fee in the same unit as input_amount.
        
    Returns:
        The ROI as a percentage.
    """
    profit = calculate_profit(input_amount, output_amount, gas_cost, flash_loan_fee)
    if input_amount == 0:
        return 0.0
    
    return (profit / input_amount) * 100.0


def hash_dict(data: Dict[str, Any]) -> str:
    """Create a hash of a dictionary.
    
    Args:
        data: The dictionary to hash.
        
    Returns:
        The hash as a hexadecimal string.
    """
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks.
    
    Args:
        items: The list to split.
        chunk_size: The size of each chunk.
        
    Returns:
        A list of chunks.
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def retry(
    func: callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """Retry a function with exponential backoff.
    
    Args:
        func: The function to retry.
        max_attempts: The maximum number of attempts.
        delay: The initial delay between attempts.
        backoff: The backoff multiplier.
        exceptions: The exceptions to catch.
        
    Returns:
        The result of the function.
        
    Raises:
        The last exception if all attempts fail.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            return func()
        except exceptions as e:
            attempt += 1
            if attempt == max_attempts:
                raise e
            
            sleep_time = delay * (backoff ** (attempt - 1))
            time.sleep(sleep_time)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers.
    
    Args:
        numerator: The numerator.
        denominator: The denominator.
        default: The default value to return if the denominator is zero.
        
    Returns:
        The result of the division, or the default value if the denominator is zero.
    """
    if denominator == 0:
        return default
    return numerator / denominator
