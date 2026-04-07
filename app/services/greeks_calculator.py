"""High-level service for calculating Options Greeks."""

import logging
from typing import Dict, Optional
from datetime import datetime

from app.config import Config
from app.database.instruments import get_instrument_by_key
from app.services.kite_client import get_kite_client
from app.services.greeks import (
    calculate_time_to_expiry,
    extract_underlying_symbol,
    get_moneyness,
    calculate_intrinsic_value,
    validate_inputs,
    calculate_all_greeks,
    calculate_iv_with_fallback,
    black_scholes_price
)

logger = logging.getLogger(__name__)


def calculate_option_greeks(
    tradingsymbol: str,
    exchange: str,
    option_price: Optional[float] = None,
    spot_price: Optional[float] = None,
    risk_free_rate: Optional[float] = None
) -> Optional[Dict]:
    """
    Calculate Greeks for an option contract.
    
    This is the main entry point for Greeks calculation across all endpoints.
    
    Args:
        tradingsymbol: Trading symbol (e.g., "HDFCAMC26MAR2880CE")
        exchange: Exchange (e.g., "NFO")
        option_price: Market price of option (fetched from API if not provided)
        spot_price: Spot price of underlying (fetched from API if not provided)
        risk_free_rate: Risk-free rate (uses Config default if not provided)
        
    Returns:
        Dictionary containing Greeks data or None if calculation fails:
        {
            "greeks": {
                "delta": float,
                "gamma": float,
                "theta": float,
                "vega": float,
                "rho": float
            },
            "implied_volatility": float,
            "theoretical_price": float,
            "intrinsic_value": float,
            "time_value": float,
            "moneyness": str,
            "underlying_symbol": str,
            "underlying_price": float,
            "days_to_expiry": int,
            "time_to_expiry_years": float
        }
        
    Note:
        - Returns None for non-option instruments (stocks)
        - Returns None if option has expired
        - Returns None if calculation fails
    """
    try:
        # Get instrument metadata
        instrument = get_instrument_by_key(tradingsymbol, exchange)
        if not instrument:
            logger.warning(f"Instrument not found: {tradingsymbol}:{exchange}")
            return None
        
        # Check if it's an option
        instrument_type = instrument.get('instrument_type', '')
        if instrument_type not in ['CE', 'PE']:
            # Not an option, skip Greeks
            return None
        
        # Get expiry and check if expired
        expiry_str = instrument.get('expiry', '')
        if not expiry_str or expiry_str == '':
            logger.warning(f"No expiry date for option: {tradingsymbol}")
            return None
        
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            if expiry_date < datetime.now():
                logger.info(f"Option expired: {tradingsymbol}")
                return None
        except ValueError:
            logger.error(f"Invalid expiry format: {expiry_str}")
            return None
        
        # Get strike price
        strike = instrument.get('strike', 0)
        if not strike or strike <= 0:
            logger.warning(f"Invalid strike price for {tradingsymbol}: {strike}")
            return None
        
        # Get risk-free rate
        if risk_free_rate is None:
            risk_free_rate = Config.RISK_FREE_RATE
        
        # Get Kite client
        kite = get_kite_client()
        
        # Get option price if not provided
        if option_price is None:
            try:
                token = instrument['instrument_token']
                quote = kite.quote([f"{exchange}:{tradingsymbol}"])
                option_data = quote.get(f"{exchange}:{tradingsymbol}", {})
                option_price = option_data.get('last_price', 0)
                
                if not option_price or option_price <= 0:
                    logger.warning(f"Invalid option price from API: {option_price}")
                    return None
            except Exception as e:
                logger.error(f"Failed to fetch option price: {e}")
                return None
        
        # Get underlying spot price if not provided
        if spot_price is None:
            try:
                underlying_symbol = extract_underlying_symbol(tradingsymbol, exchange)
                if not underlying_symbol:
                    logger.warning(f"Could not extract underlying from: {tradingsymbol}")
                    return None
                
                # Try to find underlying instrument
                # NSE equity is most common
                underlying_instrument = get_instrument_by_key(underlying_symbol, "NSE")
                if not underlying_instrument:
                    # Try NFO (for indices like NIFTY, BANKNIFTY)
                    underlying_instrument = get_instrument_by_key(underlying_symbol, "NFO")
                
                if not underlying_instrument:
                    logger.warning(f"Underlying instrument not found: {underlying_symbol}")
                    return None
                
                # Fetch spot price from API
                underlying_token = underlying_instrument['instrument_token']
                underlying_exchange = underlying_instrument['exchange']
                quote = kite.quote([f"{underlying_exchange}:{underlying_symbol}"])
                underlying_data = quote.get(f"{underlying_exchange}:{underlying_symbol}", {})
                spot_price = underlying_data.get('last_price', 0)
                
                if not spot_price or spot_price <= 0:
                    logger.warning(f"Invalid spot price from API: {spot_price}")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to fetch spot price: {e}")
                return None
        else:
            # If spot_price is provided, still get the underlying symbol
            underlying_symbol = extract_underlying_symbol(tradingsymbol, exchange)
        
        # Calculate time to expiry
        time_to_expiry = calculate_time_to_expiry(expiry_str)
        days_to_expiry = int(time_to_expiry * 365)
        
        # Validate inputs
        is_valid, error_msg = validate_inputs(
            S=spot_price,
            K=strike,
            T=time_to_expiry,
            r=risk_free_rate,
            sigma=None,  # Will be calculated
            option_price=option_price
        )
        
        if not is_valid:
            logger.error(f"Invalid inputs for Greeks calculation: {error_msg}")
            return None
        
        # Calculate Implied Volatility
        iv = calculate_iv_with_fallback(
            option_price=option_price,
            S=spot_price,
            K=strike,
            T=time_to_expiry,
            r=risk_free_rate,
            option_type=instrument_type
        )
        
        if iv is None:
            logger.warning(f"Failed to calculate IV for {tradingsymbol}")
            return None
        
        # Calculate all Greeks using the IV
        greeks = calculate_all_greeks(
            S=spot_price,
            K=strike,
            T=time_to_expiry,
            r=risk_free_rate,
            sigma=iv,
            option_type=instrument_type
        )
        
        # Calculate theoretical price
        theoretical_price = black_scholes_price(
            S=spot_price,
            K=strike,
            T=time_to_expiry,
            r=risk_free_rate,
            sigma=iv,
            option_type=instrument_type
        )
        
        # Calculate intrinsic and time value
        intrinsic = calculate_intrinsic_value(spot_price, strike, instrument_type)
        time_value = option_price - intrinsic
        
        # Get moneyness
        moneyness = get_moneyness(spot_price, strike, instrument_type)
        
        # Return complete Greeks data
        return {
            "greeks": {
                "delta": round(greeks['delta'], 4),
                "gamma": round(greeks['gamma'], 6),
                "theta": round(greeks['theta'], 2),
                "vega": round(greeks['vega'], 2),
                "rho": round(greeks['rho'], 2)
            },
            "implied_volatility": round(iv, 4),
            "theoretical_price": round(theoretical_price, 2),
            "intrinsic_value": round(intrinsic, 2),
            "time_value": round(time_value, 2),
            "moneyness": moneyness,
            "underlying_symbol": underlying_symbol,
            "underlying_price": round(spot_price, 2),
            "days_to_expiry": days_to_expiry,
            "time_to_expiry_years": round(time_to_expiry, 6)
        }
        
    except Exception as e:
        logger.error(f"Error calculating Greeks for {tradingsymbol}: {e}", exc_info=True)
        return None


def is_option_instrument(instrument_type: str) -> bool:
    """
    Check if instrument is an option (CE or PE).
    
    Args:
        instrument_type: Instrument type from database
        
    Returns:
        True if option (CE/PE), False otherwise
    """
    return instrument_type in ['CE', 'PE']


def format_greeks_response(greeks_data: Dict) -> Dict:
    """
    Format greeks_data into a flattened response dictionary.
    
    Args:
        greeks_data: Dictionary returned by calculate_option_greeks()
        
    Returns:
        Flattened dictionary with greeks at top level
    """
    return {
        'delta': greeks_data['greeks']['delta'],
        'gamma': greeks_data['greeks']['gamma'],
        'theta': greeks_data['greeks']['theta'],
        'vega': greeks_data['greeks']['vega'],
        'rho': greeks_data['greeks']['rho'],
        'implied_volatility': greeks_data['implied_volatility'],
        'theoretical_price': greeks_data['theoretical_price'],
        'intrinsic_value': greeks_data['intrinsic_value'],
        'time_value': greeks_data['time_value'],
        'moneyness': greeks_data['moneyness'],
        'underlying_symbol': greeks_data['underlying_symbol'],
        'underlying_price': greeks_data['underlying_price'],
        'days_to_expiry': greeks_data['days_to_expiry']
    }
