"""Black-Scholes pricing model for European options."""

import numpy as np
from scipy.stats import norm
from typing import Literal


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["CE", "PE"]
) -> float:
    """
    Calculate option price using Black-Scholes formula.
    
    Args:
        S: Spot price of underlying
        K: Strike price
        T: Time to expiry in years
        r: Risk-free interest rate (annualized)
        sigma: Volatility (annualized)
        option_type: "CE" for call, "PE" for put
        
    Returns:
        Theoretical option price
        
    Raises:
        ValueError: If input parameters are invalid
        
    Formula:
        C = S*N(d1) - K*e^(-r*T)*N(d2)  [Call]
        P = K*e^(-r*T)*N(-d2) - S*N(-d1)  [Put]
        
        where:
        d1 = [ln(S/K) + (r + σ²/2)*T] / (σ*√T)
        d2 = d1 - σ*√T
        N(x) = Cumulative standard normal distribution
    """
    # Validate inputs to prevent division by zero and mathematical errors
    if S <= 0:
        raise ValueError(f"Spot price must be positive, got S={S}")
    if K <= 0:
        raise ValueError(f"Strike price must be positive, got K={K}")
    if T <= 0:
        raise ValueError(f"Time to expiry must be positive, got T={T}")
    if sigma <= 0:
        raise ValueError(f"Volatility must be positive, got sigma={sigma}")
    
    # Calculate d1 and d2
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == "CE":
        # Call option price
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # PE
        # Put option price
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price


def calculate_d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple:
    """
    Calculate d1 and d2 for Black-Scholes formula.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry
        r: Risk-free rate
        sigma: Volatility
        
    Returns:
        Tuple of (d1, d2)
        
    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs to prevent division by zero and mathematical errors
    if S <= 0:
        raise ValueError(f"Spot price must be positive, got S={S}")
    if K <= 0:
        raise ValueError(f"Strike price must be positive, got K={K}")
    if T <= 0:
        raise ValueError(f"Time to expiry must be positive, got T={T}")
    if sigma <= 0:
        raise ValueError(f"Volatility must be positive, got sigma={sigma}")
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    return d1, d2
