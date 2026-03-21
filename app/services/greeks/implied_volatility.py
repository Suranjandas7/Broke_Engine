"""Implied Volatility calculation using Newton-Raphson method."""

import numpy as np
from typing import Optional, Literal

from .black_scholes import black_scholes_price
from .greeks import calculate_vega


def calculate_implied_volatility(
    option_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: Literal["CE", "PE"],
    initial_guess: float = 0.3,
    max_iterations: int = 100,
    tolerance: float = 0.0001
) -> Optional[float]:
    """
    Calculate Implied Volatility using Newton-Raphson iterative method.
    
    The IV is the volatility value that makes the Black-Scholes price equal
    to the market price of the option.
    
    Args:
        option_price: Market price of the option
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        option_type: "CE" for call, "PE" for put
        initial_guess: Starting volatility estimate (default 0.3 = 30%)
        max_iterations: Maximum Newton-Raphson iterations
        tolerance: Convergence tolerance
        
    Returns:
        Implied volatility (as decimal, e.g., 0.285 = 28.5%) or None if failed
        
    Algorithm:
        1. Start with initial volatility guess
        2. Calculate BS price with current volatility
        3. If price difference < tolerance, we're done
        4. Otherwise, adjust volatility: σ_new = σ_old - (BS_price - market_price) / vega
        5. Repeat until convergence or max iterations
        
    Note:
        - Returns None if convergence fails
        - Deep ITM/OTM options may have convergence issues
        - Options near expiry may be unstable
    """
    # Handle edge case: option price too low
    if option_price < 0.01:
        return 0.01  # Minimum IV of 1%
    
    # Calculate intrinsic value
    if option_type == "CE":
        intrinsic_value = max(S - K, 0)
    else:  # PE
        intrinsic_value = max(K - S, 0)
    
    # If option price <= intrinsic value, IV is very low
    if option_price <= intrinsic_value:
        return 0.01
    
    # Bound sigma between reasonable values
    min_sigma = 0.001  # 0.1%
    max_sigma = 5.0    # 500%
    
    sigma = initial_guess
    
    for i in range(max_iterations):
        # Ensure sigma is within bounds
        sigma = max(min_sigma, min(sigma, max_sigma))
        
        try:
            # Calculate BS price with current sigma
            bs_price = black_scholes_price(S, K, T, r, sigma, option_type)
            
            # Check convergence
            price_diff = bs_price - option_price
            
            if abs(price_diff) < tolerance:
                return sigma
            
            # Calculate vega (sensitivity to volatility)
            vega = calculate_vega(S, K, T, r, sigma)
            
            # Avoid division by very small vega
            if abs(vega) < 1e-6:
                return None
            
            # Newton-Raphson update
            # We need vega in absolute terms (not per 1%), so multiply by 100
            vega_absolute = vega * 100
            sigma = sigma - price_diff / vega_absolute
            
        except (ValueError, ZeroDivisionError, OverflowError):
            # Numerical issues, try adjusting sigma
            if i < max_iterations // 2:
                sigma = initial_guess * (0.5 + np.random.random())
            else:
                return None
    
    # Failed to converge
    return None


def calculate_implied_volatility_bisection(
    option_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: Literal["CE", "PE"],
    max_iterations: int = 50,
    tolerance: float = 0.0001
) -> Optional[float]:
    """
    Calculate Implied Volatility using bisection method (more robust fallback).
    
    This method is slower but more reliable when Newton-Raphson fails.
    
    Args:
        option_price: Market price of the option
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        option_type: "CE" for call, "PE" for put
        max_iterations: Maximum iterations
        tolerance: Convergence tolerance
        
    Returns:
        Implied volatility or None if failed
    """
    # Set bounds
    sigma_low = 0.001
    sigma_high = 5.0
    
    for i in range(max_iterations):
        sigma_mid = (sigma_low + sigma_high) / 2.0
        
        try:
            bs_price = black_scholes_price(S, K, T, r, sigma_mid, option_type)
            price_diff = bs_price - option_price
            
            if abs(price_diff) < tolerance:
                return sigma_mid
            
            # Adjust bounds
            if price_diff > 0:
                sigma_high = sigma_mid
            else:
                sigma_low = sigma_mid
                
        except (ValueError, ZeroDivisionError, OverflowError):
            return None
    
    # Return best estimate
    return (sigma_low + sigma_high) / 2.0


def calculate_iv_with_fallback(
    option_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: Literal["CE", "PE"]
) -> Optional[float]:
    """
    Calculate IV with fallback to bisection method if Newton-Raphson fails.
    
    Args:
        option_price: Market price of the option
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        option_type: "CE" for call, "PE" for put
        
    Returns:
        Implied volatility or None if both methods fail
    """
    # Try Newton-Raphson first (faster)
    iv = calculate_implied_volatility(option_price, S, K, T, r, option_type)
    
    if iv is not None:
        return iv
    
    # Fallback to bisection (more robust)
    return calculate_implied_volatility_bisection(option_price, S, K, T, r, option_type)
