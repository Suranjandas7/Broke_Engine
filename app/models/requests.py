"""Request validation models using Pydantic."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_ticker_format(ticker: str) -> str:
    """Validate ticker format is SYMBOL:EXCHANGE."""
    if ':' not in ticker:
        raise ValueError("Ticker must be in format SYMBOL:EXCHANGE (e.g., SBIN:NSE)")
    parts = ticker.split(':')
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Invalid ticker format. Use SYMBOL:EXCHANGE")
    return ticker


class HistoricalDataRequest(BaseModel):
    """Historical data request validation model."""
    
    tickers: str = Field(..., description="Comma-separated list of tickers in format SYMBOL:EXCHANGE")
    from_date: str = Field(..., alias='from', description="Start date-time (YYYY-MM-DD HH:MM:SS)")
    to_date: str = Field(..., alias='to', description="End date-time (YYYY-MM-DD HH:MM:SS)")
    interval: str = Field(default='day', description="Candle interval")
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v):
        """Validate interval is a supported value."""
        valid_intervals = [
            'minute', '3minute', '5minute', '10minute', '15minute',
            '30minute', '60minute', 'day', 'week', 'month'
        ]
        if v not in valid_intervals:
            raise ValueError(f"Interval must be one of: {', '.join(valid_intervals)}")
        return v


class InstrumentSearchRequest(BaseModel):
    """Instrument search request validation model."""
    
    tradingsymbol: str = Field(..., description="Trading symbol to search for")
    exchange: Optional[str] = Field(default=None, description="Optional exchange filter")


class TokenSetRequest(BaseModel):
    """Access token set request validation model."""
    
    access_token: str = Field(..., description="Zerodha access token")


class FetchHistoryRequest(BaseModel):
    """Fetch history request validation model."""
    
    ticker: str = Field(..., description="Ticker in format SYMBOL:EXCHANGE (e.g., SBIN:NSE)")
    from_year: int = Field(..., description="Start year (e.g., 2023)")
    to_year: int = Field(..., description="End year (e.g., 2025)")
    
    @field_validator('from_year')
    @classmethod
    def validate_from_year(cls, v):
        """Validate from_year is within reasonable range."""
        from datetime import datetime
        current_year = datetime.now().year
        if v < 2015 or v > current_year:
            raise ValueError(f"from_year must be between 2015 and {current_year}")
        return v
    
    @field_validator('to_year')
    @classmethod
    def validate_to_year(cls, v, info):
        """Validate to_year and enforce 5-year limit."""
        from datetime import datetime
        from_year = info.data.get('from_year')
        current_year = datetime.now().year
        
        if v > current_year:
            raise ValueError(f"to_year cannot be greater than current year ({current_year})")
        
        if from_year and v < from_year:
            raise ValueError("to_year must be greater than or equal to from_year")
        
        # 5-year limit
        if from_year and (v - from_year + 1) > 5:
            raise ValueError("Maximum 5 years per request. Please split into multiple requests.")
        
        return v
    
    @field_validator('ticker')
    @classmethod
    def validate_ticker_format(cls, v):
        """Validate ticker format."""
        return _validate_ticker_format(v)


class GetHistoryRequest(BaseModel):
    """Get history request validation model."""
    
    ticker: str = Field(..., description="Ticker in format SYMBOL:EXCHANGE")
    
    # Year-based parameters (mutually exclusive with date-based)
    from_year: Optional[int] = Field(default=None, description="Start year (inclusive)")
    to_year: Optional[int] = Field(default=None, description="End year (inclusive)")
    
    # Date-based parameters (mutually exclusive with year-based)
    from_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD HH:MM:SS)")
    to_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD HH:MM:SS)")
    
    # Export format parameter
    format: str = Field(
        default='json',
        description="Export format: json, arrow, parquet, msgpack, csv",
        pattern=r'^(json|arrow|parquet|msgpack|csv)$'
    )
    
    @field_validator('ticker')
    @classmethod
    def validate_ticker_format(cls, v):
        """Validate ticker format."""
        return _validate_ticker_format(v)
    
    @model_validator(mode='after')
    def validate_date_or_year_params(self):
        """Ensure either year params OR date params are provided, not both."""
        from datetime import datetime
        
        has_year_params = self.from_year is not None and self.to_year is not None
        has_date_params = self.from_date is not None and self.to_date is not None
        
        # Must provide one set of parameters
        if not has_year_params and not has_date_params:
            raise ValueError("Must provide either (from_year + to_year) OR (from_date + to_date)")
        
        # Cannot mix both
        if has_year_params and has_date_params:
            raise ValueError("Cannot mix year and date parameters. Use one or the other.")
        
        # Validate date format if provided
        if has_date_params:
            try:
                from_dt = datetime.strptime(self.from_date, '%Y-%m-%d %H:%M:%S')
                to_dt = datetime.strptime(self.to_date, '%Y-%m-%d %H:%M:%S')
                
                if to_dt < from_dt:
                    raise ValueError("to_date must be after from_date")
                    
            except ValueError as e:
                if "does not match format" in str(e):
                    raise ValueError("Date format must be YYYY-MM-DD HH:MM:SS")
                raise
        
        # Validate year range if provided
        if has_year_params:
            current_year = datetime.now().year
            
            if self.from_year < 2015 or self.from_year > current_year:
                raise ValueError(f"from_year must be between 2015 and {current_year}")
            
            if self.to_year > current_year:
                raise ValueError(f"to_year cannot be greater than current year ({current_year}")
            
            if self.to_year < self.from_year:
                raise ValueError("to_year must be greater than or equal to from_year")
        
        return self
