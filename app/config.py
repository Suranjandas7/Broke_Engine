"""Application configuration."""

import os


class Config:
    """Application configuration class."""
    
    # Flask configuration - Used as JWT signing key
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.urandom(24))
    HOST = "0.0.0.0"
    PORT = 5010
    
    # Zerodha Kite Connect configuration
    KITE_API_KEY = os.getenv("zerodha_api")
    KITE_API_SECRET = os.getenv("zerodha_secret")
    
    # URL configuration
    REDIRECT_URL = f"http://{HOST}:{PORT}/login"
    LOGIN_URL = f"https://kite.zerodha.com/connect/login?api_key={KITE_API_KEY}"
    CONSOLE_URL = f"https://developers.kite.trade/apps/{KITE_API_KEY}"
    
    # Basic authentication configuration (for web routes)
    AUTH_USER = os.getenv("user")
    AUTH_PASSWORD = os.getenv("password")
    
    # JWT configuration
    JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))
    
    # Options Greeks calculation configuration
    RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.065"))  # Default 6.5% for India
    
    @classmethod
    def validate(cls):
        """Validate that required environment variables are set."""
        required_vars = {
            'KITE_API_KEY': cls.KITE_API_KEY,
            'KITE_API_SECRET': cls.KITE_API_SECRET,
            'AUTH_USER': cls.AUTH_USER,
            'AUTH_PASSWORD': cls.AUTH_PASSWORD
        }
        
        missing = [name for name, value in required_vars.items() if not value]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
