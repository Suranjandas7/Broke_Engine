"""Utility functions for Greeks calculations."""

import re
from datetime import datetime, timedelta
from typing import Tuple, Optional


def calculate_time_to_expiry(expiry_date: str) -> float:
    """
    Calculate time to expiry in years.
    
    Args:
        expiry_date: Expiry date in YYYY-MM-DD format
        
    Returns:
        Time to expiry in years (fraction)
        
    Note:
        - Minimum time is 1 hour (0.000114 years) to avoid division by zero
        - Uses 365 days per year convention
    """
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
    now = datetime.now()
    
    # Calculate time difference
    time_diff = expiry - now
    
    # Convert to years
    days_to_expiry = time_diff.total_seconds() / (24 * 3600)
    years_to_expiry = days_to_expiry / 365.0
    
    # Set minimum to 1 hour to avoid issues near expiry
    min_time = 1.0 / (365.0 * 24.0)  # 1 hour in years
    
    return max(years_to_expiry, min_time)


def extract_underlying_symbol(tradingsymbol: str, exchange: str) -> Optional[str]:
    """
    Extract underlying symbol from option trading symbol.
    
    Args:
        tradingsymbol: Trading symbol (e.g., "HDFCAMC26MAR2880CE")
        exchange: Exchange (e.g., "NFO")
        
    Returns:
        Underlying symbol (e.g., "HDFCAMC") or None if not an option
        
    Examples:
        HDFCAMC26MAR2880CE -> HDFCAMC
        NIFTY26APR24000PE -> NIFTY
        BANKNIFTY26MAR52000CE -> BANKNIFTY
    """
    if exchange != "NFO":
        return None
    
    # Pattern: {UNDERLYING}{YYMMMDDSTRIKE}{CE|PE}
    # Extract everything before the expiry date pattern
    # Expiry format: YYMMMDD or YYMDD (e.g., 26MAR, 26MAR30)
    
    # Match pattern: letters followed by digits and month abbreviation
    pattern = r'^([A-Z]+?)(\d{2}[A-Z]{3})'
    match = re.match(pattern, tradingsymbol)
    
    if match:
        return match.group(1)
    
    return None


def get_moneyness(spot_price: float, strike: float, option_type: str) -> str:
    """
    Determine if option is ITM, ATM, or OTM.
    
    Args:
        spot_price: Current price of underlying
        strike: Strike price
        option_type: "CE" for call, "PE" for put
        
    Returns:
        "ITM", "ATM", or "OTM"
    """
    threshold = 0.005  # 0.5% threshold for ATM
    
    ratio = spot_price / strike
    
    if abs(ratio - 1.0) < threshold:
        return "ATM"
    
    if option_type == "CE":
        return "ITM" if spot_price > strike else "OTM"
    else:  # PE
        return "ITM" if spot_price < strike else "OTM"


def calculate_intrinsic_value(spot_price: float, strike: float, option_type: str) -> float:
    """
    Calculate intrinsic value of an option.
    
    Args:
        spot_price: Current price of underlying
        strike: Strike price
        option_type: "CE" for call, "PE" for put
        
    Returns:
        Intrinsic value (always >= 0)
    """
    if option_type == "CE":
        return max(spot_price - strike, 0.0)
    else:  # PE
        return max(strike - spot_price, 0.0)


def validate_inputs(S: float, K: float, T: float, r: float, sigma: float, option_price: float = None) -> Tuple[bool, Optional[str]]:
    """
    Validate inputs for Greeks calculation.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry
        r: Risk-free rate
        sigma: Volatility
        option_price: Option price (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if S <= 0:
        return False, "Spot price must be positive"
    
    if K <= 0:
        return False, "Strike price must be positive"
    
    if T <= 0:
        return False, "Time to expiry must be positive"
    
    if r < 0 or r > 1:
        return False, "Risk-free rate must be between 0 and 1"
    
    if sigma is not None and (sigma <= 0 or sigma > 5):
        return False, "Volatility must be between 0 and 5"
    
    if option_price is not None and option_price < 0:
        return False, "Option price cannot be negative"
    
    return True, None
