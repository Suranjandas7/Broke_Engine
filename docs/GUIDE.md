## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Docker Deployment](#docker-deployment)
- [Development](#development)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
cd broke_engine

# Configure environment variables in docker-compose.yml
# Then build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export KITE_API_KEY="your_api_key"
export KITE_API_SECRET="your_api_secret"
export AUTH_USER="admin"
export AUTH_PASSWORD="your_password"
export JWT_SECRET_KEY="your_secret_key_for_jwt"

# Run the application
python main.py
```

The server will start on `http://0.0.0.0:5010`

## Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Zerodha Kite Connect API credentials ([Get them here](https://developers.kite.trade/))

### Local Setup

1. **Clone the repository**
   ```bash
   cd /path/to/broke_engine
   ```

2. **Create virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** (see [Configuration](#configuration))

5. **Run the application**
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables

The application requires the following environment variables:

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `KITE_API_KEY` | Zerodha Kite API key | Yes | `your_kite_api_key` |
| `KITE_API_SECRET` | Zerodha Kite API secret | Yes | `your_kite_api_secret` |
| `AUTH_USER` | Basic auth username for web UI | Yes | `admin` |
| `AUTH_PASSWORD` | Basic auth password for web UI | Yes | `secure_password` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | Recommended | `your_jwt_secret` |
| `JWT_EXPIRATION_DAYS` | JWT token validity in days (default: 7) | No | `7` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per user per minute (default: 180) | No | `180` |
| `RISK_FREE_RATE` | Risk-free rate for Greeks calculation (default: 0.065) | No | `0.065` |

### Setting Environment Variables

**For Docker:**
Edit the `docker-compose.yml` file:
```yaml
environment:
  - KITE_API_KEY=your_api_key
  - KITE_API_SECRET=your_secret
  - AUTH_USER=admin
  - AUTH_PASSWORD=secure_password
  - JWT_SECRET_KEY=your_jwt_secret
```

**For Local Development:**
```bash
# Linux/Mac
export KITE_API_KEY="your_api_key"
export KITE_API_SECRET="your_secret"
export AUTH_USER="admin"
export AUTH_PASSWORD="secure_password"
export JWT_SECRET_KEY="your_jwt_secret"

# Windows CMD
set KITE_API_KEY=your_api_key
set KITE_API_SECRET=your_secret
set AUTH_USER=admin
set AUTH_PASSWORD=secure_password
set JWT_SECRET_KEY=your_jwt_secret

# Windows PowerShell
$env:KITE_API_KEY="your_api_key"
$env:KITE_API_SECRET="your_secret"
$env:AUTH_USER="admin"
$env:AUTH_PASSWORD="secure_password"
$env:JWT_SECRET_KEY="your_jwt_secret"
```

### Configuration Class

Configuration is managed in `app/config.py`:
- Server runs on `0.0.0.0:5010` by default
- OAuth redirect URL: `http://HOST:PORT/login`
- All required variables are validated on startup

## API Documentation

### Authentication

#### JWT Token Authentication (Primary Method)

Most API endpoints require JWT Bearer token authentication:

**Step 1: Get a JWT Token**
```bash
curl -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "your_auth_user", "password": "your_auth_password"}'

# Response: {"status": "success", "token": "eyJhbGciOiJIUzI1NiIs..."}
```

**Step 2: Use the Token in Requests**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/ltp?tickers=SBIN:NSE"
```

#### Basic Authentication (Web UI)

The web UI (`/` and `/cache_instruments`) requires HTTP Basic Authentication using the `AUTH_USER` and `AUTH_PASSWORD` environment variables.

### Rate Limiting

All authenticated API endpoints are protected by rate limiting to prevent abuse. The rate limit is applied per user (based on JWT token) using in-memory storage.

**Default Configuration:**
- **Limit**: 180 requests per minute per user
- **Storage**: In-memory (no Redis required)
- **Key**: Username extracted from JWT token
- **Fallback**: IP address if no valid token

**Configuration via Environment Variable:**
```yaml
# docker-compose.yml
environment:
  - RATE_LIMIT_PER_MINUTE=180  # Adjust as needed
```

**Rate Limit Response:**
When the limit is exceeded, the API returns HTTP 429 (Too Many Requests) with a retry-after header.

```json
{
  "error": "Rate limit exceeded: 180 per 1 minute"
}
```

**Exempt Endpoints:**
The following endpoints are exempt from rate limiting:
- `/` - Home page
- `/login` - OAuth callback
- `/auth/token` - Token generation
- `/cache_instruments` - Instrument caching
- Static files

### Endpoints

#### Authentication & Web UI

##### `GET /`
Home page with Kite Connect login link.
- **Auth**: Basic Auth (username/password)
- **Returns**: HTML page with login button

##### `GET /login`
OAuth callback handler for Kite Connect.
- **Auth**: None (OAuth callback)
- **Query Params**: `request_token` (provided by Kite)
- **Returns**: HTML page with access token

##### `GET /testing`
Test endpoint for historical data (development only).
- **Auth**: Basic Auth
- **Returns**: Sample historical data

---

#### Instrument Management

##### `GET /cache_instruments`
Cache all instruments from Kite API into local SQLite database.
- **Auth**: Basic Auth (username/password)
- **Returns**:
  ```json
  {
    "status": "success",
    "message": "Cached 70000 instruments in SQLite database",
    "total_instruments": 70000,
    "database_path": "/app/data/instruments.db"
  }
  ```

##### `GET /get_instrument`
Retrieve instrument details by trading symbol.
- **Auth**: JWT Bearer Token
- **Query Params**:
  - `tradingsymbol` (required) - e.g., `SBIN`, `NIFTY`
  - `exchange` (optional) - e.g., `NSE`, `BSE`
- **Returns**:
  ```json
  {
    "status": "success",
    "data": {
      "instrument_token": 779521,
      "exchange_token": 3045,
      "tradingsymbol": "SBIN",
      "exchange": "NSE",
      "name": "STATE BANK OF INDIA",
      "last_price": 0,
      "expiry": "",
      "strike": 0,
      "tick_size": 0.05,
      "lot_size": 1,
      "instrument_type": "EQ",
      "segment": "NSE"
    }
  }
  ```

##### `GET /cache_status`
Get status of the instruments cache.
- **Auth**: JWT Bearer Token
- **Returns**:
  ```json
  {
    "status": "success",
    "cache_exists": true,
    "total_instruments": 70000,
    "database_path": "/app/data/instruments.db",
    "database_size_bytes": 15728640,
    "database_size_mb": 15.0
  }
  ```

##### `GET /clear_cache`
Clear the instruments cache (deletes database file).
- **Auth**: JWT Bearer Token
- **Returns**:
  ```json
  {
    "status": "success",
    "message": "Cache cleared successfully"
  }
  ```

---

#### Options & Derivatives Support

**Broke Engine fully supports options and futures contracts** from NFO (National Futures & Options) and other derivative exchanges. Options are automatically detected and handled seamlessly alongside stocks.

##### How Options Work in Broke Engine

**Auto-Detection:**
- The system automatically detects options/futures based on `instrument_type` in the instruments database
- Option types: `CE` (Call European), `PE` (Put European), `FUT` (Futures)
- No special parameters needed - just use the trading symbol

**Trading Symbol Format for Options:**
Options in the instruments database follow this format:
```
SYMBOL + YY + MMM + STRIKE + TYPE
```

Examples:
- `HDFCAMC26MAR2880CE` - HDFC AMC March 2026 2880 Call Option
- `NIFTY26APR24000PE` - NIFTY April 2026 24000 Put Option
- `BANKNIFTY26MAR51000CE` - Bank NIFTY March 2026 51000 Call Option

**Open Interest (OI) Fields:**
Options data includes three additional fields:
- `oi` - Open Interest (number of outstanding contracts)
- `oi_day_high` - Highest OI during the day
- `oi_day_low` - Lowest OI during the day

**⚠️ Important Limitation:**
Kite's `historical_data` API **does not provide historical Open Interest (OI) data**. Therefore:
- OI fields will be `0` in historical data responses
- This applies to `/historical_data`, `/fetch_history`, and `/get_history` endpoints
- Real-time OI data would require WebSocket streaming (future enhancement)

##### Using Options with API Endpoints

**Example 1: Fetch Option LTP**
```bash
# Get current price of HDFC AMC March 2880 Call Option
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/ltp?tickers=HDFCAMC26MAR2880CE:NFO"
```

**Example 2: Fetch Option Historical Data**
```bash
# Get historical data for an option (real-time, no caching)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/historical_data?tickers=HDFCAMC26MAR2880CE:NFO&from=2026-03-01%2009:15:00&to=2026-03-20%2015:30:00&interval=15minute"
```

**Example 3: Cache Option Historical Data**
```bash
# Cache 1-minute data for an option (for backtesting)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/fetch_history?ticker=HDFCAMC26MAR2880CE:NFO&from_year=2026&to_year=2026"

# Export cached option data
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/get_history?ticker=HDFCAMC26MAR2880CE:NFO&from_year=2026&to_year=2026&format=json"
```

**Example 4: Mixed Stock and Option Query**
```bash
# Get LTP for both stocks and options in one call
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/ltp?tickers=SBIN:NSE,HDFCAMC26MAR2880CE:NFO,RELIANCE:NSE"
```

##### Response Format for Options

**Stock Response (SBIN:NSE):**
```json
{
  "status": "success",
  "ticker": "SBIN",
  "exchange": "NSE",
  "instrument_type": "EQ",
  "data": [
    {
      "date": "2024-01-02 09:15:00",
      "open": 575.5,
      "high": 576.0,
      "low": 575.0,
      "close": 575.8,
      "volume": 125000,
      "oi": 0,
      "oi_day_high": 0,
      "oi_day_low": 0
    }
  ]
}
```

**Option Response (HDFCAMC26MAR2880CE:NFO):**
```json
{
  "status": "success",
  "ticker": "HDFCAMC26MAR2880CE",
  "exchange": "NFO",
  "instrument_type": "CE",
  "data": [
    {
      "date": "2026-03-01 09:15:00",
      "open": 125.5,
      "high": 128.0,
      "low": 124.0,
      "close": 127.3,
      "volume": 9000,
      "oi": 0,
      "oi_day_high": 0,
      "oi_day_low": 0
    }
  ]
}
```

**Note:** OI fields are 0 due to Kite API limitations. The `instrument_type` field helps identify whether the data is for a stock (`EQ`) or option (`CE`/`PE`/`FUT`).

##### Finding Option Symbols

**Method 1: Query by Trading Symbol**
```bash
# Search for all HDFC AMC options
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/get_instrument?tradingsymbol=HDFCAMC26MAR2880CE&exchange=NFO"
```

**Method 2: Check Instruments Database**
```python
import sqlite3
conn = sqlite3.connect('data/instruments.db')
cursor = conn.cursor()

# Find all options for HDFCAMC expiring in March 2026
cursor.execute("""
    SELECT tradingsymbol, strike, instrument_type, expiry, lot_size
    FROM instruments
    WHERE tradingsymbol LIKE 'HDFCAMC26MAR%'
    AND exchange = 'NFO'
    ORDER BY strike
""")

for row in cursor.fetchall():
    print(row)
```

**Method 3: Zerodha Kite Platform**
- Visit [kite.zerodha.com](https://kite.zerodha.com)
- Search for the underlying symbol (e.g., "HDFCAMC")
- Click on "Options Chain" to see all available strikes and expiries
- Use the trading symbol format from the platform

##### Key Differences: Stocks vs Options

| Feature | Stocks (EQ) | Options (CE/PE/FUT) |
|---------|-------------|---------------------|
| **Exchange** | NSE, BSE | NFO, MCX |
| **Trading Symbol** | Simple (e.g., `SBIN`) | Complex (e.g., `HDFCAMC26MAR2880CE`) |
| **Expiry Date** | N/A | Yes (monthly/weekly) |
| **Strike Price** | N/A | Yes (e.g., 2880) |
| **Lot Size** | 1 | Varies (e.g., 300 for HDFCAMC) |
| **OI Fields** | Always 0 | 0 (API limitation, but structure ready) |
| **Instrument Type** | `EQ` | `CE`, `PE`, `FUT` |

---

### 📊 Options Greeks Calculator

**Broke Engine includes a comprehensive Black-Scholes options pricing and Greeks calculation engine!** Calculate Delta, Gamma, Theta, Vega, Rho, and Implied Volatility for any option contract.

#### Greeks API Endpoints

##### 1. Dedicated Greeks Endpoint

Calculate Greeks for a single option:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/greeks?ticker=NIFTY26MAR24000CE:NFO"
```

**Response:**
```json
{
  "status": "success",
  "ticker": "HDFCAMC26MAR2880CE",
  "exchange": "NFO",
  "option_type": "CE",
  "strike": 2880.0,
  "expiry": "2026-03-26",
  "lot_size": 300,
  "underlying_symbol": "HDFCAMC",
  "underlying_price": 2950.50,
  "option_price": 125.50,
  "days_to_expiry": 6,
  "time_to_expiry_years": 0.0164,
  "risk_free_rate": 0.065,
  "greeks": {
    "delta": 0.6543,
    "gamma": 0.0124,
    "theta": -15.50,
    "vega": 125.30,
    "rho": 8.50
  },
  "implied_volatility": 0.285,
  "theoretical_price": 125.45,
  "intrinsic_value": 70.50,
  "time_value": 55.00,
  "moneyness": "ITM"
}
```

**Optional Parameters:**
- `risk_free_rate`: Override default risk-free rate (e.g., `0.07` for 7%)

##### 2. Batch Greeks Calculation

Calculate Greeks for multiple options in one request:

```bash
curl -X POST http://localhost:5010/greeks/batch \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": [
      "HDFCAMC26MAR2880CE:NFO",
      "HDFCAMC26MAR2900CE:NFO",
      "NIFTY26APR24000PE:NFO"
    ],
    "risk_free_rate": 0.065
  }'
```

**Response:**
```json
{
  "status": "success",
  "count": 3,
  "results": [
    {
      "ticker": "HDFCAMC26MAR2880CE",
      "greeks": { ... },
      ...
    },
    ...
  ],
  "errors": []
}
```

##### 3. Auto-Greeks in Existing Endpoints

Greeks are **automatically calculated** for options when using these endpoints:

**GET /ltp** - Get LTP with Greeks:
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/ltp?tickers=HDFCAMC26MAR2880CE:NFO&greeks=true"
```

Response includes both LTP and Greeks:
```json
{
  "status": "success",
  "results": {
    "HDFCAMC26MAR2880CE:NFO": {
      "ltp": 125.50,
      "strike": 2880.0,
      "expiry": "2026-03-26",
      "greeks": {
        "delta": 0.6543,
        "gamma": 0.0124,
        "theta": -15.50,
        "vega": 125.30,
        "rho": 8.50,
        "implied_volatility": 0.285,
        "underlying_price": 2950.50,
        "moneyness": "ITM",
        "days_to_expiry": 6
      }
    }
  }
}
```

**GET /historical_data** - Historical data with Greeks:
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/historical_data?tickers=HDFCAMC26MAR2880CE:NFO&from=2026-03-15%2009:15:00&to=2026-03-20%2015:30:00&interval=15minute&greeks=true"
```

Greeks calculated using the **latest candle's close price**:
```json
{
  "status": "success",
  "results": {
    "HDFCAMC26MAR2880CE:NFO": {
      "data": [ ... historical candles ... ],
      "latest_price": 125.50,
      "greeks": { ... }
    }
  }
}
```

**GET /get_history** - Cached data with Greeks:
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5010/get_history?ticker=HDFCAMC26MAR2880CE:NFO&from_year=2026&to_year=2026&format=json&greeks=true"
```

Greeks included in metadata (calculated from latest record):
```json
{
  "status": "success",
  "ticker": "HDFCAMC26MAR2880CE",
  "instrument_type": "CE",
  "strike": 2880.0,
  "expiry": "2026-03-26",
  "latest_close": 125.50,
  "greeks": { ... },
  "data": [ ... ]
}
```

**Disable Greeks:** Add `greeks=false` to any endpoint to skip Greeks calculation for faster response.

#### How It Works

**1. Black-Scholes Model:**
- Uses the classic Black-Scholes formula for European options (NSE options are European-style)
- Calculates theoretical option price based on spot, strike, time, volatility, and interest rate

**2. Implied Volatility Solver:**
- Uses Newton-Raphson iterative method to find IV
- Fallback to bisection method if Newton-Raphson fails
- Handles edge cases (deep ITM/OTM, near expiry)

**3. Data Sources:**
- **Option price**: Fetched from Kite API in real-time
- **Underlying spot price**: Auto-detected and fetched from Kite API
- **Strike & Expiry**: From instruments database
- **Risk-free rate**: Configurable (default 6.5% for India)

**4. Auto-Detection:**
- System automatically detects option symbols and extracts underlying
- Example: `HDFCAMC26MAR2880CE` → underlying is `HDFCAMC`
- Fetches both option and underlying prices automatically

#### Configuration

Set risk-free rate via environment variable:

```bash
export RISK_FREE_RATE=0.065  # 6.5% (India T-Bill rate)
```

Or in `docker-compose.yml`:
```yaml
environment:
  - RISK_FREE_RATE=0.065
```

#### Greeks Interpretation Guide

##### Delta (Δ) - Direction Indicator
```
Call Delta: 0.65 
→ If underlying moves up ₹1, option price increases by ~₹0.65
→ 65% probability of expiring ITM
→ Position delta: If you buy 1 lot (300 contracts), you're effectively long 195 shares (300 × 0.65)

Put Delta: -0.35
→ If underlying moves up ₹1, option price decreases by ~₹0.35
→ 35% probability of expiring ITM
```

##### Gamma (Γ) - Delta Acceleration
```
Gamma: 0.0124
→ If underlying moves up ₹1, Delta increases by 0.0124
→ High gamma near ATM at expiry = rapid Delta changes
→ Gamma risk = position becomes more/less directional quickly
```

##### Theta (Θ) - Time is Money
```
Theta: -15.50
→ Option loses ₹15.50 in value per day (all else equal)
→ Negative for option buyers (time decay hurts)
→ Positive for option sellers (time decay helps)
→ Accelerates as expiry approaches
```

##### Vega (ν) - Volatility Sensitivity
```
Vega: 125.30
→ If IV increases by 1% (e.g., 28% → 29%), option price increases by ₹1.25
→ High vega = sensitive to volatility changes
→ Important during earnings, events, market stress
```

##### Rho (ρ) - Interest Rate Effect
```
Rho: 8.50
→ If interest rate increases by 1% (e.g., 6.5% → 7.5%), option price increases by ₹0.085
→ Usually least important Greek for short-term options
→ More relevant for LEAP options
```

##### Implied Volatility (IV)
```
IV: 0.285 (28.5%)
→ Market expects underlying to move ±28.5% annually
→ High IV = expensive options, expect big moves
→ Low IV = cheap options, market calm
→ Compare with historical volatility (HV) for relative value
```

##### Moneyness
```
ITM (In-The-Money): Strike < Spot (calls) or Strike > Spot (puts)
→ Has intrinsic value, higher delta

ATM (At-The-Money): Strike ≈ Spot
→ Maximum time value, highest gamma

OTM (Out-of-The-Money): Strike > Spot (calls) or Strike < Spot (puts)
→ Only time value, lower delta
```

#### Example Use Cases

##### Use Case 1: Option Strategy Analysis
```bash
# Analyze a bull call spread
GET /greeks/batch
{
  "tickers": [
    "NIFTY26MAR24000CE:NFO",  # Long call
    "NIFTY26MAR24500CE:NFO"   # Short call
  ]
}

# Calculate net Greeks:
# Net Delta = 0.65 - 0.35 = 0.30 (moderately bullish)
# Net Theta = -20 + 15 = -5 (time decay manageable)
# Net Vega = 150 - 100 = 50 (IV increase helps slightly)
```

##### Use Case 2: Delta Hedging
```bash
# You're short 1 lot (50 contracts) NIFTY 24000 CE
# Delta = -0.65 per contract
# Position Delta = 50 × -0.65 × 50 (lot size) = -1,625

# To hedge, buy 1,625 shares of NIFTY futures
# Or adjust dynamically as gamma changes
```

##### Use Case 3: Volatility Trading
```bash
# Find options with high vega for volatility plays
GET /greeks?ticker=BANKNIFTY26MAR51000CE:NFO

# If vega is 200 and you expect IV to increase from 20% to 25%:
# Expected profit = 5% × 200 = ₹1,000 per contract
```

##### Use Case 4: Time Decay Analysis
```bash
# Compare theta across strikes
GET /greeks/batch
{
  "tickers": [
    "NIFTY26MAR23800CE:NFO",  # ITM
    "NIFTY26MAR24000CE:NFO",  # ATM
    "NIFTY26MAR24200CE:NFO"   # OTM
  ]
}

# ATM options typically have highest theta (fastest decay)
```

#### Limitations & Notes

1. **European Options Only**: Uses Black-Scholes model (NSE options are European-style)
2. **No Dividend Yield**: Currently set to 0 (can be enhanced)
3. **Real-time Prices**: Fetches live prices from Kite API for accuracy
4. **Expired Options**: Returns error for expired contracts
5. **Convergence**: Deep ITM/OTM options may occasionally fail IV calculation
6. **Rate Limit**: Respects Kite API rate limits (3 req/sec)

#### Performance

- **Single Greeks**: ~200-500ms (includes 2 API calls: option + underlying)
- **Batch Greeks** (10 options): ~2-3 seconds
- **Auto-Greeks in /ltp**: Adds ~300ms per option ticker
- **Cached Greeks**: Instant (if prices already fetched)

#### Technical Details

**Algorithm:**
- Black-Scholes closed-form solution for pricing
- Newton-Raphson method for IV calculation (converges in 5-10 iterations)
- Bisection method fallback for robustness
- scipy.stats.norm for cumulative distribution function

**Dependencies:**
- `numpy>=1.24.0` - Array operations
- `scipy>=1.10.0` - Statistical functions

---

#### Market Data (Real-time Fetch)

##### `GET /ltp`
Fetch last traded price (LTP) for one or more instruments in real-time.
- **Auth**: JWT Bearer Token
- **Query Params**:
  - `tickers` (required) - Comma-separated list in format `SYMBOL:EXCHANGE`
- **Important Notes**:
  - Requires instruments cache to be populated (call `/cache_instruments` first)
  - Returns current LTP for each ticker
  - Fast real-time price quotes
- **Example**:
  ```bash
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/ltp?tickers=SBIN:NSE,RELIANCE:NSE"
  ```
- **Returns**:
  ```json
  {
    "status": "success",
    "results": {
      "SBIN:NSE": {
        "instrument_token": 779521,
        "tradingsymbol": "SBIN",
        "exchange": "NSE",
        "ltp": 726.35
      },
      "RELIANCE:NSE": {
        "instrument_token": 738561,
        "tradingsymbol": "RELIANCE",
        "exchange": "NSE",
        "ltp": 1255.95
      }
    },
    "errors": {}
  }
  ```

##### `GET /historical_data`
Fetch historical OHLC data directly from Kite API for one or more instruments (no caching).
- **Auth**: JWT Bearer Token
- **Query Params**:
  - `tickers` (required) - Comma-separated list in format `SYMBOL:EXCHANGE`
  - `from` (required) - Start date-time (format: `YYYY-MM-DD HH:MM:SS`)
  - `to` (required) - End date-time (format: `YYYY-MM-DD HH:MM:SS`)
  - `interval` (optional) - Candle interval: `minute`, `3minute`, `5minute`, `10minute`, `15minute`, `30minute`, `60minute`, `day` (default: `day`)
- **Important Notes**:
  - **Date Format**: All datetime values in the response use ISO 8601 format (`YYYY-MM-DD HH:MM:SS`) for easy parsing
  - **Historical Data Limits**: Intraday intervals (minute, 15minute, etc.) are typically available for the last 60-200 days only. For older data, use `day` interval
  - **Multiple Tickers**: Supports fetching data for multiple instruments in a single request
- **Example**:
  ```bash
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/historical_data?tickers=SBIN:NSE,RELIANCE:NSE&from=2026-03-20%2009:15:00&to=2026-03-20%2015:30:00&interval=15minute"
  ```
- **Returns**:
  ```json
  {
    "status": "success",
    "from": "2026-03-20 09:15:00",
    "to": "2026-03-20 15:30:00",
    "interval": "15minute",
    "results": {
      "SBIN:NSE": {
        "instrument_token": 779521,
        "tradingsymbol": "SBIN",
        "exchange": "NSE",
        "data": [
          {
            "date": "2026-03-20 09:15:00",
            "open": 725.5,
            "high": 727.0,
            "low": 724.8,
            "close": 726.3,
            "volume": 125000
          },
          {
            "date": "2026-03-20 09:30:00",
            "open": 726.3,
            "high": 728.5,
            "low": 726.0,
            "close": 727.8,
            "volume": 98000
          }
        ]
      },
      "RELIANCE:NSE": {
        "instrument_token": 738561,
        "tradingsymbol": "RELIANCE",
        "exchange": "NSE",
        "data": [
          {
            "date": "2026-03-20 09:15:00",
            "open": 1251.85,
            "high": 1255.95,
            "low": 1250.05,
            "close": 1255.95,
            "volume": 934207
          }
        ]
      }
    },
    "errors": {}
  }
  ```
- **Data Format Benefits**:
  - **ISO 8601 Standard**: `YYYY-MM-DD HH:MM:SS` format is universally recognized
  - **Easy Parsing**: Compatible with pandas (`pd.to_datetime()`), JavaScript (`Date.parse()`), SQL databases
  - **Machine Readable**: No timezone suffixes or complex string parsing needed
  - **Sortable**: String comparison works for chronological ordering

---

#### Historical Data Caching (1-Minute Data)

The caching system allows you to store years of 1-minute historical data locally for fast access and analysis. Perfect for backtesting and data analysis without hitting API rate limits.

##### `GET /fetch_history`
Fetch and cache 1-minute historical data for a ticker across a year range (multi-year support).

- **Auth**: JWT Bearer Token
- **Query Params**:
  - `ticker` (required) - Format: `SYMBOL:EXCHANGE` (e.g., `SBIN:NSE`)
  - `from_year` (required) - Start year (2015 onwards)
  - `to_year` (required) - End year (max: current year)
- **Limits**:
  - **Maximum 5 years per request** - For larger ranges, split into multiple requests
  - **Atomic operation** - If any year fails, entire request fails (no partial caching)
- **Features**:
  - **Multi-year Fetching**: Fetch multiple years in one request (e.g., 2023-2025)
  - **Smart Caching**: Only fetches new data since last cached timestamp (update mode per year)
  - **Auto-chunking**: Splits each year into 60-day chunks (Kite API limit for 1-minute data)
  - **Rate Limiting**: Built-in 0.35s delay between requests (respects 3 req/sec limit)
  - **Current Year**: Auto-cutoff at yesterday's market close (never fetches incomplete "today")
  - **Per-ticker Tables**: Each ticker stored in separate table for optimal performance
- **Performance**:
  - ~6-8 seconds per year (first fetch)
  - ~1-3 seconds for daily updates (current year)
  - ~90,000 records per year (~4.5 MB)
  - Multi-year: Total time = sum of all years
- **Examples**:
  ```bash
  # Single year
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/fetch_history?ticker=SBIN:NSE&from_year=2024&to_year=2024"
  
  # Multi-year (3 years)
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/fetch_history?ticker=SBIN:NSE&from_year=2023&to_year=2025"
  ```
- **Returns** (multi-year response):
  ```json
  {
    "status": "success",
    "message": "Successfully processed 3 year(s) for SBIN:NSE",
    "ticker": "SBIN:NSE",
    "from_year": 2023,
    "to_year": 2025,
    "total_records_added": 269250,
    "years": {
      "2023": {
        "records_added": 89750,
        "last_timestamp": "2023-12-31 15:30:00",
        "already_cached": false
      },
      "2024": {
        "records_added": 0,
        "last_timestamp": null,
        "already_cached": true
      },
      "2025": {
        "records_added": 89500,
        "last_timestamp": "2025-03-20 15:30:00",
        "already_cached": false
      }
    }
  }
  ```
- **Error Response** (exceeding 5-year limit):
  ```json
  {
    "status": "error",
    "message": "Invalid request parameters",
    "errors": [
      {
        "type": "value_error",
        "loc": ["to_year"],
        "msg": "Maximum 5 years per request. Please split into multiple requests."
      }
    ]
  }
  ```

##### `GET /get_history`
Export cached historical data in multiple formats (supports both year-based and date-based queries).

- **Auth**: JWT Bearer Token
- **Query Params (Option 1 - Year Range)**:
  - `ticker` (required) - Format: `SYMBOL:EXCHANGE`
  - `from_year` (required) - Start year (inclusive)
  - `to_year` (required) - End year (inclusive)
  - `format` (optional) - Export format: `json` (default), `arrow`, `parquet`, `msgpack`, `csv`
  - **Validation**: Returns error if any year in range is not fully cached
- **Query Params (Option 2 - Date Range)**:
  - `ticker` (required) - Format: `SYMBOL:EXCHANGE`
  - `from_date` (required) - Start datetime (format: `YYYY-MM-DD HH:MM:SS`)
  - `to_date` (required) - End datetime (format: `YYYY-MM-DD HH:MM:SS`)
  - `format` (optional) - Export format: `json` (default), `arrow`, `parquet`, `msgpack`, `csv`
  - **Validation**: Returns error if NO data exists in the specified range

- **Export Formats**:
  | Format | Size vs JSON | Speed vs JSON | Best For | Content-Type |
  |--------|--------------|---------------|----------|--------------|
  | `json` | 100% (baseline) | 1x (baseline) | Default, browser compatibility | `application/json` |
  | `csv` | 40-60% smaller | 2-3x faster | Excel, pandas, universal tools | `text/csv` |
  | `msgpack` | 30-50% smaller | 2-5x faster | Binary JSON, broad compatibility | `application/msgpack` |
  | `parquet` | 80-95% smaller | 5-10x faster | Analytics, archival, max compression | `application/vnd.apache.parquet` |
  | `arrow` | 50-70% smaller | **10-100x faster** | API-to-API, zero-copy reads, **best performance** | `application/vnd.apache.arrow.file` |

- **Performance**: 
  - JSON: <1 second for single year, ~1-2 seconds for 5+ years
  - Arrow/Parquet: ~0.1-0.5 seconds for any size (10-100x faster parsing)
  - Database queries optimized with pandas read_sql and composite indexes

- **Examples**:
  ```bash
  # Year-based query (single year, JSON - default)
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/get_history?ticker=SBIN:NSE&from_year=2024&to_year=2024"
  
  # Year-based query (multiple years, Arrow format - fastest)
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/get_history?ticker=SBIN:NSE&from_year=2023&to_year=2025&format=arrow" \
    -o sbin_2023_2025.arrow
  
  # Year-based query (Parquet format - best compression)
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/get_history?ticker=SBIN:NSE&from_year=2023&to_year=2025&format=parquet" \
    -o sbin_2023_2025.parquet
  
  # Date-based query (CSV format - Excel compatible)
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/get_history?ticker=SBIN:NSE&from_date=2024-01-15%2009:15:00&to_date=2024-06-30%2015:30:00&format=csv" \
    -o sbin_h1_2024.csv
  
  # Date-based query (MessagePack format)
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/get_history?ticker=SBIN:NSE&from_date=2024-03-20%2009:15:00&to_date=2024-03-20%2015:30:00&format=msgpack" \
    -o sbin_intraday.msgpack
  ```

- **Client Usage Examples**:
  
  **Python (Arrow - Fastest)**:
  ```python
  import requests
  import pyarrow.feather as feather
  from io import BytesIO
  
  # Get JWT token first
  auth_response = requests.post('http://localhost:5010/auth/token',
      json={'username': 'admin', 'password': 'your_password'})
  token = auth_response.json()['token']
  headers = {'Authorization': f'Bearer {token}'}
  
  response = requests.get('http://localhost:5010/get_history', params={
      'ticker': 'SBIN:NSE',
      'from_year': 2023,
      'to_year': 2025,
      'format': 'arrow'
  }, headers=headers)
  
  # Zero-copy read into pandas DataFrame (10-100x faster than JSON)
  df = feather.read_feather(BytesIO(response.content))
  print(df.head())
  # Metadata available in df.attrs
  ```
  
  **Python (Parquet - Best Compression)**:
  ```python
  import pandas as pd
  from io import BytesIO
  
  response = requests.get('http://localhost:5010/get_history', params={
      'ticker': 'SBIN:NSE',
      'from_year': 2023,
      'to_year': 2025,
      'format': 'parquet'
  }, headers=headers)
  
  df = pd.read_parquet(BytesIO(response.content))
  ```
  
  **Python (CSV)**:
  ```python
  import pandas as pd
  from io import StringIO
  
  response = requests.get('http://localhost:5010/get_history', params={
      'ticker': 'SBIN:NSE',
      'from_year': 2024,
      'to_year': 2024,
      'format': 'csv'
  }, headers=headers)
  
  df = pd.read_csv(StringIO(response.text), comment='#')
  ```
  
  **Python (MessagePack)**:
  ```python
  import msgpack
  
  response = requests.get('http://localhost:5010/get_history', params={
      'ticker': 'SBIN:NSE',
      'from_year': 2024,
      'to_year': 2024,
      'format': 'msgpack'
  }, headers=headers)
  
  data = msgpack.unpackb(response.content)
  print(data['ticker'], data['record_count'])
  df = pd.DataFrame(data['data'])
  ```

- **Returns (JSON format - Year-based)**:
  ```json
  {
    "status": "success",
    "ticker": "SBIN",
    "exchange": "NSE",
    "from_year": 2023,
    "to_year": 2025,
    "record_count": 269250,
    "data": [
      {
        "date": "2023-01-02 09:15:00",
        "open": 575.5,
        "high": 576.0,
        "low": 575.0,
        "close": 575.8,
        "volume": 125000
      },
      {
        "date": "2023-01-02 09:16:00",
        "open": 575.8,
        "high": 577.2,
        "low": 575.5,
        "close": 576.9,
        "volume": 98000
      }
    ]
  }
  ```
- **Returns (Date-based)**:
  ```json
  {
    "status": "success",
    "ticker": "SBIN",
    "exchange": "NSE",
    "from_date": "2024-01-15 09:15:00",
    "to_date": "2024-06-30 15:30:00",
    "record_count": 45000,
    "data": [
      {
        "date": "2024-01-15 09:15:00",
        "open": 575.5,
        "high": 576.0,
        "low": 575.0,
        "close": 575.8,
        "volume": 125000
      }
    ]
  }
  ```
- **Error Response** (missing years):
  ```json
  {
    "status": "error",
    "message": "Missing cached data for years: [2023, 2025]. Please fetch these years first using /fetch_history.",
    "missing_years": [2023, 2025],
    "ticker": "SBIN:NSE"
  }
  ```
- **Error Response** (no data in date range):
  ```json
  {
    "status": "error",
    "message": "No cached data found for SBIN:NSE between 2024-01-15 09:15:00 and 2024-06-30 15:30:00. Please fetch this date range first using /fetch_history."
  }
  ```

##### `GET /history_cache_status`
Get statistics about cached historical data.

- **Auth**: JWT Bearer Token
- **Example**:
  ```bash
  curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    "http://localhost:5010/history_cache_status"
  ```
- **Returns**:
  ```json
  {
    "status": "success",
    "statistics": {
      "total_tickers": 5,
      "total_years_cached": 12,
      "total_records": 1078500,
      "database_size_mb": 54.3
    },
    "cached_tickers": [
      {
        "ticker": "SBIN",
        "exchange": "NSE",
        "years": "2023,2024,2025",
        "total_records": 269250
      },
      {
        "ticker": "RELIANCE",
        "exchange": "NSE",
        "years": "2024,2025",
        "total_records": 179500
      }
    ]
  }
  ```

---

#### Token Management

##### `POST /auth/token`
Generate a JWT token for API authentication.
- **Auth**: None (uses credentials in body)
- **Body** (JSON):
  ```json
  {
    "username": "your_auth_user",
    "password": "your_auth_password"
  }
  ```
- **Returns**:
  ```json
  {
    "status": "success",
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
  ```

##### `GET /set_access_token`
Set the Zerodha access token programmatically.
- **Auth**: JWT Bearer Token
- **Query Params**:
  - `access_token` (required) - Zerodha access token
- **Returns**:
  ```json
  {
    "status": "success",
    "message": "Access token saved successfully"
  }
  ```

##### `GET /get_token_status`
Check if access token is configured.
- **Auth**: JWT Bearer Token
- **Returns**:
  ```json
  {
    "status": "success",
    "token_exists": true,
    "token_preview": "***h3k2",
    "message": "Access token is configured"
  }
  ```

##### `GET /clear_token`
Clear the stored access token (forces re-authentication).
- **Auth**: JWT Bearer Token
- **Returns**:
  ```json
  {
    "status": "success",
    "message": "Access token cleared successfully"
  }
  ```

---

### When to Use Which Endpoint?

| Use Case | Endpoint | Why? |
|----------|----------|------|
| **Quick price check** | `/ltp` | Fastest way to get current price, minimal data transfer |
| **Portfolio monitoring** | `/ltp` | Get real-time LTP for multiple stocks in one call |
| **Quick intraday data check** | `/historical_data` | Fast, no caching needed, works immediately |
| **Backtesting strategies** | `/fetch_history` + `/get_history` | Cache once, query forever, no API rate limits |
| **Daily trading signals** | `/historical_data` | Real-time data, always up to date |
| **Data analysis (years of data)** | `/fetch_history` + `/get_history` | Blazing fast queries, offline access |
| **Multiple timeframe analysis** | `/get_history` | Get 1-min data, resample to any timeframe |
| **One-time analysis** | `/historical_data` | No need to cache |
| **Repeated queries** | `/fetch_history` + `/get_history` | Cache once, save API calls |
| **Current day data** | `/historical_data` or `/ltp` | Live data not yet cached |
| **Historical data (yesterday+)** | `/get_history` | Instant access from cache |
| **Specific date range** | `/get_history` (date params) | Query exact dates (e.g., Jan-Jun 2024) |
| **Multi-year datasets** | `/fetch_history` (multi-year) | Fetch 2-5 years in one request |

**Rule of Thumb**: 
- Use `/ltp` for **current price only** (fastest, minimal data)
- Use `/historical_data` for **real-time, one-time, or quick queries**
- Use `/fetch_history` + `/get_history` for **repeated access, backtesting, or large datasets**

---

### Historical Data Caching Workflow

Here's a typical workflow for using the historical data caching feature:

```bash
# Step 0: Get a JWT token first
TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')

# Step 1: Cache instruments (if not already done) - requires Basic Auth
curl -u admin:your_password "http://localhost:5010/cache_instruments"

# Step 2: Fetch historical data for multiple years (now in ONE request!)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/fetch_history?ticker=SBIN:NSE&from_year=2023&to_year=2025"

# Step 3: Check cache status
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/history_cache_status"

# Step 4: Export data for analysis (year-based)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/get_history?ticker=SBIN:NSE&from_year=2023&to_year=2025" > sbin_data.json

# Step 5: Export specific date range (date-based query)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/get_history?ticker=SBIN:NSE&from_date=2024-01-15%2009:15:00&to_date=2024-06-30%2015:30:00" > sbin_h1_2024.json

# Step 6: Daily updates (for current year)
# Run this daily to keep current year data up to date
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/fetch_history?ticker=SBIN:NSE&from_year=2026&to_year=2026"
```

**Performance Comparison:**

| Operation | Without Cache | With Cache | Speedup |
|-----------|--------------|------------|---------|
| **Fetch 1 year of 1-min data** | N/A (API limits) | 6-8 seconds | First time |
| **Query 1 year of data** | 7+ API calls (~3s) | <1 second | **3x faster** |
| **Query 5 years of data** | 35+ API calls (~15s) | 1-2 seconds | **10x faster** |
| **Daily update (current year)** | Full year refetch | 1-3 seconds | **Minimal** |
| **Analyze same data 10 times** | 10 × API calls | 10 × cache queries | **No API usage!** |

**Storage Cost**: ~4.5 MB per ticker-year (1 year SBIN = ~90,000 records = 4.5 MB)

---

### Usage Examples

#### Python - Real-time LTP (Last Traded Price)

```python
import requests

# First, get a JWT token
auth_response = requests.post(
    'http://localhost:5010/auth/token',
    json={'username': 'admin', 'password': 'your_password'}
)
token = auth_response.json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Fetch current prices for multiple stocks
response = requests.get(
    'http://localhost:5010/ltp',
    params={'tickers': 'SBIN:NSE,RELIANCE:NSE,TCS:NSE'},
    headers=headers
)

data = response.json()

# Print current prices
for ticker, info in data['results'].items():
    print(f"{ticker}: ₹{info['ltp']}")

# Output:
# SBIN:NSE: ₹726.35
# RELIANCE:NSE: ₹1255.95
# TCS:NSE: ₹3421.50
```

#### Python - Historical Data Analysis with Pandas

```python
import requests
import pandas as pd

# Get JWT token
auth_response = requests.post(
    'http://localhost:5010/auth/token',
    json={'username': 'admin', 'password': 'your_password'}
)
token = auth_response.json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Fetch and cache historical data (multi-year in one request!)
response = requests.get(
    'http://localhost:5010/fetch_history',
    params={
        'ticker': 'SBIN:NSE',
        'from_year': 2023,
        'to_year': 2025
    },
    headers=headers
)
print(response.json())

# Export cached data (year-based query)
response = requests.get(
    'http://localhost:5010/get_history',
    params={
        'ticker': 'SBIN:NSE',
        'from_year': 2023,
        'to_year': 2025
    },
    headers=headers
)

data = response.json()

# Convert to pandas DataFrame
df = pd.DataFrame(data['data'])
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

print(f"Loaded {len(df)} records")
print(df.head())

# Export specific date range (date-based query)
response = requests.get(
    'http://localhost:5010/get_history',
    params={
        'ticker': 'SBIN:NSE',
        'from_date': '2024-01-15 09:15:00',
        'to_date': '2024-06-30 15:30:00'
    },
    headers=headers
)

df_h1 = pd.DataFrame(response.json()['data'])
df_h1['date'] = pd.to_datetime(df_h1['date'])
df_h1.set_index('date', inplace=True)

print(f"Loaded H1 2024: {len(df_h1)} records")

# Resample to different timeframes
df_15min = df.resample('15T').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
})

# Calculate technical indicators
df['sma_20'] = df['close'].rolling(window=20).mean()
df['sma_50'] = df['close'].rolling(window=50).mean()

# Backtesting-ready data!
print(df.tail())
```

#### Python - Real-time Data Fetch (No Caching)

```python
import requests
import pandas as pd

# Get JWT token
auth_response = requests.post(
    'http://localhost:5010/auth/token',
    json={'username': 'admin', 'password': 'your_password'}
)
token = auth_response.json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Fetch historical data
response = requests.get(
    'http://localhost:5010/historical_data',
    params={
        'tickers': 'SBIN:NSE,RELIANCE:NSE',
        'from': '2026-03-20 09:15:00',
        'to': '2026-03-20 15:30:00',
        'interval': '15minute'
    },
    headers=headers
)

data = response.json()

# Convert to pandas DataFrame
for ticker, info in data['results'].items():
    df = pd.DataFrame(info['data'])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    print(f"\n{ticker}:")
    print(df.head())
```

#### JavaScript/TypeScript

```javascript
// Get JWT token first
const authResponse = await fetch('http://localhost:5010/auth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'your_password' })
});
const { token } = await authResponse.json();

const response = await fetch(
  'http://localhost:5010/historical_data?' + 
  new URLSearchParams({
    tickers: 'SBIN:NSE,RELIANCE:NSE',
    from: '2026-03-20 09:15:00',
    to: '2026-03-20 15:30:00',
    interval: '15minute'
  }),
  {
    headers: { 'Authorization': `Bearer ${token}` }
  }
);

const data = await response.json();

// Parse dates
for (const [ticker, info] of Object.entries(data.results)) {
  info.data.forEach(candle => {
    candle.date = new Date(candle.date);
  });
  console.log(`${ticker}:`, info.data);
}
```

#### cURL

```bash
# Get JWT token
TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')

# Use the token for API requests
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/historical_data?tickers=SBIN:NSE,RELIANCE:NSE&from=2026-03-20%2009:15:00&to=2026-03-20%2015:30:00&interval=15minute"
```

---

### Error Responses

All endpoints return consistent error responses:
```json
{
  "status": "error",
  "message": "Detailed error message"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad request (missing parameters)
- `401` - Unauthorized (invalid API key or auth)
- `404` - Not found (instrument/token not found)
- `500` - Internal server error

## Docker Deployment

### Building the Image

```bash
docker-compose build
```

### Running the Container

```bash
# Start in background
docker-compose up -d

# Start with logs
docker-compose up

# Stop the container
docker-compose down
```

### Data Persistence

The application uses Docker volumes to persist data:
- **Volume Mount**: `./data:/app/data`
- **Database Location**: `./data/instruments.db` (on host)

This ensures:
- Database survives container restarts
- Easy backup and migration
- Data persists across image updates

### Logs

View container logs:
```bash
# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs app
```

## Development

### Project Structure

```
broke_engine/
├── app/
│   ├── __init__.py           # Application factory
│   ├── config.py             # Configuration management
│   ├── error_handlers.py     # Global error handlers
│   ├── utils.py              # Utility functions
│   ├── database/             # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py     # SQLite connection management
│   │   ├── instruments.py    # Instrument cache operations
│   │   ├── auth_tokens.py    # Token storage operations
│   │   └── historical_data.py # Historical data caching (NEW)
│   ├── middleware/           # Request middleware
│   │   ├── __init__.py
│   │   ├── auth.py           # Basic auth middleware
│   │   └── api_key.py        # API key validation
│   ├── models/               # Pydantic models
│   │   ├── requests.py       # Request validation models
│   │   └── responses.py      # Response models
│   ├── routes/               # API endpoints
│   │   ├── __init__.py
│   │   ├── auth_routes.py    # Authentication & web UI
│   │   ├── instrument_routes.py  # Instrument management
│   │   ├── market_routes.py  # Market data (real-time)
│   │   ├── token_routes.py   # Token management
│   │   └── history_routes.py # Historical data caching (NEW)
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── kite_client.py    # Kite Connect client
│   │   └── historical_fetcher.py # Historical data fetcher (NEW)
│   └── templates/            # HTML templates
│       ├── index.html
│       └── login_success.html
├── data/                     # SQLite database storage
│   └── instruments.db        # Auto-created on first run
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container definition
├── docker-compose.yml        # Container orchestration
├── .dockerignore             # Docker build exclusions
└── README.md                 # This file
```

**Storage Estimates:**
- 1 ticker-year of 1-minute data: ~90,000 records ≈ 4.5 MB
- 10 tickers × 5 years: ~4.5M records ≈ 225 MB
- Database file is single SQLite file with all data

## Troubleshooting

### Database Error: "Cannot find database"

**Problem**: Application fails with database-related errors in Docker.

**Solution**: This was fixed in recent updates. If you still encounter this:
1. Ensure the `data/` directory exists: `mkdir -p data`
2. Rebuild the Docker image: `docker-compose build`
3. Check volume permissions: `ls -la data/`
4. Verify docker-compose.yml has volume mount: `- ./data:/app/data`

### Port Already in Use

**Problem**: Port 5010 is already in use.

**Solution**:
```bash
# Find process using port 5010
lsof -i :5010  # Linux/Mac
netstat -ano | findstr :5010  # Windows

# Kill the process or change port in docker-compose.yml
ports:
  - "5011:5010"  # Map to different host port
```

### Access Token Expires

**Problem**: API calls fail with authentication error.

**Solution**:
1. Access tokens expire daily
2. Re-login via browser: `http://localhost:5010/`
3. Or set token programmatically using JWT:
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')
   
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:5010/set_access_token?access_token=NEW_TOKEN"
   ```

### Instruments Cache Empty

**Problem**: `/get_instrument` or `/fetch_history` returns "cache is empty" error.

**Solution**:
```bash
# Populate the instruments cache (requires Basic Auth)
curl -u admin:your_password "http://localhost:5010/cache_instruments"

# Verify cache status (requires JWT)
TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')

curl -H "Authorization: Bearer $TOKEN" "http://localhost:5010/cache_status"
```

### Historical Data Fetch Fails

**Problem**: `/fetch_history` fails with errors.

**Solution**:
1. **"Ticker not found in cache"**: Run `/cache_instruments` first
2. **"Invalid year"**: Year must be between 2015 and current year
3. **"Invalid ticker format"**: Use format `SYMBOL:EXCHANGE` (e.g., `SBIN:NSE`)
4. **Rate limit errors**: Built-in delays should prevent this, but wait 10 seconds and retry
5. **"No access token"**: Login via web UI or use `/set_access_token`

### Missing Years Error

**Problem**: `/get_history` returns "Missing cached data for years" error.

**Solution**:
```bash
# Get JWT token
TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')

# Fetch the missing years (now multi-year support!)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/fetch_history?ticker=SBIN:NSE&from_year=2023&to_year=2024"

# Then export
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/get_history?ticker=SBIN:NSE&from_year=2023&to_year=2024"
```

### Options-Related Issues

**Problem**: Option data shows OI (Open Interest) as 0.

**Solution**: This is expected behavior. Kite's `historical_data` API does not provide historical OI data. The OI fields (`oi`, `oi_day_high`, `oi_day_low`) are included in the response structure but will always be 0 for historical data. Real-time OI would require WebSocket streaming (future enhancement).

**Problem**: Can't find the option symbol.

**Solution**:
1. Options follow the format: `SYMBOL + YY + MMM + STRIKE + TYPE` (e.g., `HDFCAMC26MAR2880CE`)
2. Query the instruments database to find available options:
   ```bash
   # Refresh cache first (requires Basic Auth)
   curl -u admin:your_password "http://localhost:5010/cache_instruments"
   ```
3. Or check Zerodha Kite's option chain for the underlying symbol

**Problem**: Option expired - no data available.

**Solution**: Options have expiry dates. Check the expiry date in the instruments database. If the option has expired and you're trying to fetch current data, you'll need to find the current month's option contract.

### Invalid API Credentials

**Problem**: "Invalid or missing credentials" or 401 Unauthorized on requests.

**Solution**:
1. Check environment variables are set correctly (`AUTH_USER`, `AUTH_PASSWORD`, `JWT_SECRET_KEY`)
2. For API endpoints, get a JWT token first:
   ```bash
   curl -X POST http://localhost:5010/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username": "your_auth_user", "password": "your_auth_password"}'
   ```
3. Include `Authorization: Bearer YOUR_TOKEN` header in all API requests
4. For web UI endpoints (`/`, `/cache_instruments`), use Basic Auth with `AUTH_USER`/`AUTH_PASSWORD`

### Docker Container Won't Start

**Problem**: Container exits immediately.

**Solution**:
```bash
# Check logs
docker-compose logs

# Verify environment variables
docker-compose config

# Rebuild image
docker-compose build --no-cache
docker-compose up
```

### Performance Issues

**Problem**: Slow API responses.

**Solution**:
1. Ensure instruments are cached locally (not fetching from API each time)
2. Check database indexes exist: `sqlite3 data/instruments.db ".schema"`
3. Increase Gunicorn workers in Dockerfile: `--workers 4`
4. Use specific exchange in `/get_instrument?exchange=NSE` to avoid multiple matches

## Dependencies

The application uses minimal dependencies for optimal performance:

```
Flask==3.1.3          # Web framework
gunicorn==25.0.1      # Production WSGI server
pydantic==2.10.6      # Data validation
kiteconnect==5.0.1    # Zerodha Kite Connect SDK
```

All other required packages (requests, werkzeug, etc.) are installed as sub-dependencies.

## License

This project is for educational and development purposes. Ensure compliance with Zerodha's [API usage policies](https://kite.trade/docs/connect/v3/).

## Support

For issues related to:
- **Kite Connect API**: [Zerodha Developer Forum](https://kite.trade/forum/)
- **This Application**: Open an issue in the repository

## Changelog

### Recent Updates

- **Options & Derivatives Support** (LATEST): Full support for options and futures contracts
  - **Auto-detection**: System automatically detects options (CE/PE/FUT) from instrument_type
  - **OI fields**: Added Open Interest columns (oi, oi_day_high, oi_day_low) to database schema
  - **Auto-migration**: Existing historical data tables automatically updated with OI columns on startup
  - **Seamless integration**: Options work exactly like stocks - no API changes needed
  - **Response metadata**: Includes instrument_type in responses to identify stocks vs options
  - **Note**: Historical OI data is 0 (Kite API limitation), but structure is ready for future enhancements
  - **Supports**: NFO options (CE/PE), NFO futures (FUT), and all derivative exchanges
- **LTP Endpoint**: Added `/ltp` endpoint for fast real-time price quotes
  - Fetch last traded price for multiple instruments in one request
  - Returns simple LTP value for each ticker
  - Perfect for quick price checks and monitoring
  - Supports both stocks and options
- **Date Format Enhancement**: Historical data endpoints now return standardized ISO 8601 datetime format
  - Format: `YYYY-MM-DD HH:MM:SS` for universal compatibility
  - Applied to `/historical_data` endpoint response
  - Easy parsing in Python, JavaScript, SQL, and other tools
- **Multi-Year & Date Range Support**: Enhanced historical data caching with powerful new features
  - **Multi-year fetching**: Fetch 2-5 years in one `/fetch_history` request (e.g., 2023-2025)
  - **Date-based queries**: Query specific date ranges in `/get_history` (e.g., 2024-01-15 to 2024-06-30)
  - **Atomic operations**: Multi-year fetches are all-or-nothing (if any year fails, none are cached)
  - **5-year limit per request**: Prevents timeouts, split larger ranges into multiple requests
  - **Flexible exports**: Choose year-based or date-based queries depending on your needs
- **Historical Data Caching**: Cache years of 1-minute data locally with smart update mode
  - Per-ticker storage tables for optimal performance
  - Auto-chunking for Kite API 60-day limit
  - Rate limiting (0.35s delays) respects API limits
  - Update mode only fetches new data since last timestamp
  - Current year auto-cutoff at yesterday's market close
  - Three endpoints: `/fetch_history`, `/get_history`, `/history_cache_status`
  - Perfect for backtesting and data analysis
- **Date Format Standardization**: Historical data now returns dates in ISO 8601 format (`YYYY-MM-DD HH:MM:SS`) for better compatibility with data analysis tools
- **API Response Improvement**: Consistent datetime formatting across all endpoints for easier programmatic consumption
- **Database Fix**: Fixed "cannot find database" error in Docker
- **Data Persistence**: Added volume mounts for SQLite database
- **Dependencies**: Trimmed requirements.txt from 65 to 4 packages
- **Docker Optimization**: Improved Dockerfile with proper permissions
- **Documentation**: Comprehensive README with all features documented

---

## Quick Reference

### All API Endpoints

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Auth** | `/` | GET | Home page with Kite login |
| **Auth** | `/login` | GET | OAuth callback handler |
| **Instruments** | `/cache_instruments` | GET | Cache all instruments from Kite API |
| **Instruments** | `/get_instrument` | GET | Query cached instrument by symbol |
| **Instruments** | `/cache_status` | GET | Check instruments cache status |
| **Instruments** | `/clear_cache` | GET | Clear instruments cache |
| **Market Data** | `/ltp` | GET | Fetch real-time last traded price (LTP) |
| **Market Data** | `/historical_data` | GET | Fetch real-time OHLC data (no cache) |
| **History Cache** | `/fetch_history` | GET | Cache 1-minute data for ticker/year range (multi-year) |
| **History Cache** | `/get_history` | GET | Export cached data (year or date range) |
| **History Cache** | `/history_cache_status` | GET | View cache statistics |
| **Tokens** | `/set_access_token` | GET | Set Zerodha access token |
| **Tokens** | `/get_token_status` | GET | Check token status |
| **Tokens** | `/clear_token` | GET | Clear access token |

### Common Commands

All API endpoints require JWT Bearer token authentication:

```bash
# Step 0: Get JWT Token (required for all API calls)
TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')

# Initial Setup (cache instruments - requires Basic Auth)
curl -u admin:your_password "http://localhost:5010/cache_instruments"

# Get Real-time Prices (LTP)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/ltp?tickers=SBIN:NSE,RELIANCE:NSE"

# Fetch & Cache Historical Data (multi-year)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/fetch_history?ticker=SBIN:NSE&from_year=2023&to_year=2025"

# Export Cached Data (year-based)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/get_history?ticker=SBIN:NSE&from_year=2023&to_year=2025"

# Export Cached Data (date-based)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/get_history?ticker=SBIN:NSE&from_date=2024-01-15%2009:15:00&to_date=2024-06-30%2015:30:00"

# Get Real-time OHLC Data
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/historical_data?tickers=SBIN:NSE&from=2026-03-20%2009:15:00&to=2026-03-20%2015:30:00&interval=15minute"

# Check Cache Status
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/history_cache_status"
```

### Data Format Standards

All datetime values follow **ISO 8601** format: `YYYY-MM-DD HH:MM:SS`

**Example**: `2024-03-20 09:15:00`

This format is:
- ✅ Pandas compatible: `pd.to_datetime(df['date'])`
- ✅ JavaScript compatible: `new Date('2024-03-20 09:15:00')`
- ✅ SQL compatible: Direct insert/query
- ✅ Sortable: String comparison works chronologically

---

