"""Greeks calculations for options using Black-Scholes model."""

import numpy as np
from scipy.stats import norm
from typing import Dict, Literal

from .black_scholes import calculate_d1_d2


def calculate_delta(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["CE", "PE"]
) -> float:
    """
    Calculate Delta: rate of change of option price with respect to underlying price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility
        option_type: "CE" for call, "PE" for put
        
    Returns:
        Delta value
        - Call: 0 to 1
        - Put: -1 to 0
        
    Interpretation:
        Delta of 0.65 means option price changes by ₹0.65 for every ₹1 change in underlying.
    """
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    
    if option_type == "CE":
        return norm.cdf(d1)
    else:  # PE
        return norm.cdf(d1) - 1


def calculate_gamma(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float
) -> float:
    """
    Calculate Gamma: rate of change of Delta with respect to underlying price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility
        
    Returns:
        Gamma value (same for calls and puts)
        
    Interpretation:
        Gamma of 0.012 means Delta changes by 0.012 for every ₹1 change in underlying.
        High gamma = Delta changes rapidly (risky near expiry for ATM options)
    """
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    return gamma


def calculate_theta(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["CE", "PE"]
) -> float:
    """
    Calculate Theta: rate of change of option price with respect to time (time decay).
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility
        option_type: "CE" for call, "PE" for put
        
    Returns:
        Theta value per year (divide by 365 for daily theta)
        
    Interpretation:
        Theta of -15.50 means option loses ₹15.50 in value per day.
        Always negative for long options (time decay works against you).
    """
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
    
    # Common term for both call and put
    term1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
    
    if option_type == "CE":
        # Call theta
        term2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
        theta = term1 + term2
    else:  # PE
        # Put theta
        term2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
        theta = term1 + term2
    
    # Convert from per year to per day
    theta_per_day = theta / 365.0
    
    return theta_per_day


def calculate_vega(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float
) -> float:
    """
    Calculate Vega: rate of change of option price with respect to volatility.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility
        
    Returns:
        Vega value (same for calls and puts)
        
    Interpretation:
        Vega of 125.30 means option price increases by ₹1.25 for 1% increase in IV.
        (Note: Vega is typically expressed per 1% change in volatility)
    """
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    
    vega = S * norm.pdf(d1) * np.sqrt(T)
    
    # Convert to per 1% change in volatility (divide by 100)
    vega_per_percent = vega / 100.0
    
    return vega_per_percent


def calculate_rho(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["CE", "PE"]
) -> float:
    """
    Calculate Rho: rate of change of option price with respect to interest rate.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility
        option_type: "CE" for call, "PE" for put
        
    Returns:
        Rho value
        
    Interpretation:
        Rho of 8.50 means option price increases by ₹0.085 for 1% increase in interest rate.
        (Note: Rho is typically expressed per 1% change in rate)
    """
    _, d2 = calculate_d1_d2(S, K, T, r, sigma)
    
    if option_type == "CE":
        # Call rho
        rho = K * T * np.exp(-r * T) * norm.cdf(d2)
    else:  # PE
        # Put rho
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
    
    # Convert to per 1% change in rate (divide by 100)
    rho_per_percent = rho / 100.0
    
    return rho_per_percent


def calculate_all_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: Literal["CE", "PE"]
) -> Dict[str, float]:
    """
    Calculate all Greeks at once for efficiency.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility
        option_type: "CE" for call, "PE" for put
        
    Returns:
        Dictionary containing all Greeks:
        {
            "delta": float,
            "gamma": float,
            "theta": float,
            "vega": float,
            "rho": float
        }
    """
    return {
        "delta": calculate_delta(S, K, T, r, sigma, option_type),
        "gamma": calculate_gamma(S, K, T, r, sigma),
        "theta": calculate_theta(S, K, T, r, sigma, option_type),
        "vega": calculate_vega(S, K, T, r, sigma),
        "rho": calculate_rho(S, K, T, r, sigma, option_type)
    }
