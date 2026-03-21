"""
Options Greeks calculation module.

This module provides Black-Scholes pricing and Greeks calculations for European options.

Main functions:
- calculate_option_greeks(): Calculate all Greeks for an option
- calculate_implied_volatility(): Calculate IV from market price

Greeks calculated:
- Delta: Price sensitivity to underlying
- Gamma: Delta sensitivity to underlying
- Theta: Time decay per day
- Vega: IV sensitivity
- Rho: Interest rate sensitivity
"""

from .black_scholes import black_scholes_price, calculate_d1_d2
from .greeks import (
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    calculate_rho,
    calculate_all_greeks
)
from .implied_volatility import (
    calculate_implied_volatility,
    calculate_implied_volatility_bisection,
    calculate_iv_with_fallback
)
from .utils import (
    calculate_time_to_expiry,
    extract_underlying_symbol,
    get_moneyness,
    calculate_intrinsic_value,
    validate_inputs
)

__all__ = [
    # Black-Scholes
    'black_scholes_price',
    'calculate_d1_d2',
    
    # Greeks
    'calculate_delta',
    'calculate_gamma',
    'calculate_theta',
    'calculate_vega',
    'calculate_rho',
    'calculate_all_greeks',
    
    # Implied Volatility
    'calculate_implied_volatility',
    'calculate_implied_volatility_bisection',
    'calculate_iv_with_fallback',
    
    # Utils
    'calculate_time_to_expiry',
    'extract_underlying_symbol',
    'get_moneyness',
    'calculate_intrinsic_value',
    'validate_inputs'
]
