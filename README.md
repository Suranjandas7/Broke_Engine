# Broke Engine

A lightweight Flask-based wrapper for interacting with Zerodha Kite Connect (+ potentially other broker APIs in the future). The api provides endpoints for instrument caching, historical data retrieval, historical data caching, access token management with persistent SQLite storage, and Options Greeks calculation.

## Key highlights:

> Calculate Delta, Gamma, Theta, Vega, Rho, and Implied Volatility using Black-Scholes model. Auto-integrated into all option endpoints.

> Trade and analyze options (CE/PE) and futures (FUT) alongside stocks. Auto-detected, seamlessly integrated, with Open Interest fields ready for future enhancements.

> Cache years of 1-minute historical data locally for lightning-fast backtesting. Multi-format export with Apache Arrow (10-100x faster), Parquet (80-95% smaller), MessagePack, and CSV.

## Features

- **Zerodha Kite Connect Integration**: Full OAuth flow and API access
- **Options & Derivatives Support**: Full support for options (CE/PE) and futures (FUT) with auto-detection
- **Options Greeks Calculator**: Real-time calculation of Delta, Gamma, Theta, Vega, Rho, and Implied Volatility
- **Instrument Caching**: Local SQLite database for fast instrument lookups (stocks + options)
- **Historical Data API**: Fetch OHLC data for multiple instruments (stocks and options)
- **Historical Data Caching**: Cache 1-minute historical data locally with smart update mode
- **Multi-Format Export**: Export cached data in JSON, Arrow, Parquet, MessagePack, or CSV
- **High-Performance Queries**: Pandas-optimized database reads with composite indexes
- **Persistent Token Storage**: Access tokens stored in database
- **API Key Protection**: Secure endpoints with API key authentication
- **Rate Limiting**: Per-user request throttling (configurable, default 180 req/min)
- **Auto-Migration**: Database schema updates applied automatically on startup
- **Docker Support**: Production-ready containerization with data persistence
- **Lightweight**: Minimal dependencies, fast deployment

--

**Built with Flask + Zerodha Kite Connect**

Disclaimer: This software is not, in any form, connected to Zerodha or any of its business affiliates. It just uses the API and builds upon it. The user will be required to have a paid Kite API key and must manage it on their own, in order for this to work. The software is shipped as is under an open source license.

@2026 Suranjan Das
