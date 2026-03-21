"""Response data models using Pydantic."""

from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class InstrumentData(BaseModel):
    """Instrument data model."""
    
    instrument_token: int
    exchange_token: int
    tradingsymbol: str
    exchange: str
    name: str
    last_price: float
    expiry: str
    strike: float
    tick_size: float
    lot_size: int
    instrument_type: str
    segment: str


class ApiResponse(BaseModel):
    """Standard API response wrapper."""
    
    status: str = Field(..., description="Response status: 'success' or 'error'")
    message: Optional[str] = Field(default=None, description="Optional message")
    data: Optional[Any] = Field(default=None, description="Response data payload")
    errors: Optional[Dict[str, str]] = Field(default=None, description="Error details")


class HistoricalCandle(BaseModel):
    """Historical OHLCV candle data model."""
    
    date: str = Field(..., description="Timestamp in YYYY-MM-DD HH:MM:SS format")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: int = Field(..., description="Volume")


class HistoricalDataResponse(BaseModel):
    """Historical data export response model."""
    
    status: str = Field(default="success", description="Response status")
    ticker: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    from_year: int = Field(..., description="Start year")
    to_year: int = Field(..., description="End year")
    record_count: int = Field(..., description="Total number of records")
    data: list = Field(..., description="Array of OHLCV candle data")
