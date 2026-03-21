# Broke Engine API Documentation

## Overview

The Broke Engine is a Flask-based API that provides access to historical market data and instrument information from Zerodha Kite Connect. It uses SQLite for efficient caching of instrument data.

## Authentication

### API Key Authentication
All endpoints (except `/` and `/login`) require API key authentication via query parameter:
- Parameter: `apikey`
- Value: Your configured API key

### Zerodha Access Token
Endpoints that fetch data from Zerodha (like `/historical_data` and `/cache_instruments`) 
require a valid Zerodha Kite Connect access token to be configured on the server.

**Two methods to configure the access token:**

1. **Browser Login (Interactive)**: Visit the root endpoint `/` and complete the Zerodha OAuth flow
2. **API Method (Programmatic)**: Call `/set_access_token?apikey=YOUR_KEY&access_token=YOUR_TOKEN`

**Token Persistence**: The access token is stored persistently in the database and survives 
server restarts. Zerodha tokens expire daily, so you must renew them every 24 hours.

Basic authentication is required for the index (`/`) and testing (`/testing`) endpoints.

---

## Endpoints

### 1. Cache Management

#### `/cache_instruments` - Populate Instruments Cache

Fetches all available instruments from Kite API and stores them in SQLite database.

**Method:** `GET`

**Query Parameters:**
- `apikey` (required): Your API key

**Response:**
```json
{
  "status": "success",
  "message": "Cached 200000 instruments in SQLite database",
  "total_instruments": 200000,
  "database_path": "/path/to/instruments.db"
}
```

**Notes:**
- This should be called periodically (e.g., daily) to keep instrument data fresh
- The database is persisted to disk and survives app restarts
- Memory-efficient: Uses ~18-28 MB vs ~50-90 MB for in-memory dict

---

#### `/cache_status` - Get Cache Status

Returns information about the current state of the instruments cache.

**Method:** `GET`

**Query Parameters:**
- `apikey` (required): Your API key

**Response:**
```json
{
  "status": "success",
  "cache_exists": true,
  "total_instruments": 200000,
  "database_path": "/path/to/instruments.db",
  "database_size_bytes": 25600000,
  "database_size_mb": 24.41
}
```

---

#### `/clear_cache` - Clear Instruments Cache

Deletes the SQLite database file to clear the cache.

**Method:** `GET`

**Query Parameters:**
- `apikey` (required): Your API key

**Response:**
```json
{
  "status": "success",
  "message": "Cache cleared successfully"
}
```

---

### 2. Token Management

#### `/set_access_token` - Set Zerodha Access Token

Configure the Zerodha access token programmatically for API access.

**Method:** `GET`

**Query Parameters:**
- `apikey` (required): Your API key
- `access_token` (required): Valid Zerodha Kite Connect access token

**Example Request:**
```
GET /set_access_token?apikey=your_api_key&access_token=your_zerodha_token
```

**Response:**
```json
{
  "status": "success",
  "message": "Access token saved successfully"
}
```

**Notes:**
- Zerodha access tokens expire daily (24 hours after generation)
- You must renew the token every day either via browser login or this endpoint
- The token is stored persistently and survives server restarts

---

#### `/get_token_status` - Check Token Status

Check if an access token is configured on the server.

**Method:** `GET`

**Query Parameters:**
- `apikey` (required): Your API key

**Response (Token Exists):**
```json
{
  "status": "success",
  "token_exists": true,
  "token_preview": "***x7Ks",
  "message": "Access token is configured"
}
```

**Response (No Token):**
```json
{
  "status": "success",
  "token_exists": false,
  "message": "No access token found. Please login via browser or call /set_access_token"
}
```

---

#### `/clear_token` - Clear Access Token

Remove the stored access token (useful for forcing re-authentication).

**Method:** `GET`

**Query Parameters:**
- `apikey` (required): Your API key

**Response:**
```json
{
  "status": "success",
  "message": "Access token cleared successfully"
}
```

---

### 3. Instrument Lookup

#### `/get_instrument` - Get Instrument Details

Retrieve instrument details by trading symbol and optional exchange.

**Method:** `GET`

**Query Parameters:**
- `apikey` (required): Your API key
- `tradingsymbol` (required): Trading symbol (e.g., "RELIANCE", "SBIN")
- `exchange` (optional): Exchange name (e.g., "NSE", "BSE")

**Example Request:**
```
GET /get_instrument?apikey=your_api_key&tradingsymbol=RELIANCE&exchange=NSE
```

**Response (Single Match):**
```json
{
  "status": "success",
  "data": {
    "instrument_token": 738561,
    "exchange_token": 2884,
    "tradingsymbol": "RELIANCE",
    "exchange": "NSE",
    "name": "RELIANCE INDUSTRIES LTD",
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

**Response (Multiple Matches - No Exchange Specified):**
```json
{
  "status": "success",
  "message": "Found 2 instruments with tradingsymbol RELIANCE",
  "data": [
    {
      "instrument_token": 738561,
      "tradingsymbol": "RELIANCE",
      "exchange": "NSE",
      ...
    },
    {
      "instrument_token": 123456,
      "tradingsymbol": "RELIANCE",
      "exchange": "BSE",
      ...
    }
  ]
}
```

---

### 4. Historical Data

#### `/historical_data` - Fetch Historical OHLCV Data

Fetch historical OHLCV (Open, High, Low, Close, Volume) data for one or more instruments.

**Method:** `GET`

### Query Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `apikey` | Yes | API key for authentication | `your_api_key_here` |
| `tickers` | Yes | Comma-separated list of tickers in format `TRADINGSYMBOL:EXCHANGE` | `SBIN:NSE,RELIANCE:NSE` |
| `from` | Yes | Start date-time (format: `YYYY-MM-DD HH:MM:SS`) | `2025-03-16+09:15:00` |
| `to` | Yes | End date-time (format: `YYYY-MM-DD HH:MM:SS`) | `2025-03-16+15:30:00` |
| `interval` | No | Candle interval (default: `day`) | `5minute` |

#### Supported Intervals
- `minute` - 1 minute
- `day` - 1 day
- `3minute` - 3 minutes
- `5minute` - 5 minutes
- `10minute` - 10 minutes
- `15minute` - 15 minutes
- `30minute` - 30 minutes
- `60minute` - 60 minutes
- `day` - daily 

### Example Request

```
GET /historical_data?apikey=your_api_key&tickers=RELIANCE:NSE&from=2025-03-16+09:15:00&to=2025-04-16+15:30:00&interval=day
```

### Example Request (Multiple Tickers)

```
GET /historical_data?apikey=your_api_key&tickers=RELIANCE:NSE,SBIN:NSE,TCS:NSE&from=2025-03-16+09:15:00&to=2025-04-16+15:30:00&interval=day
```

### Response Format

#### Success Response

```json
{
  "status": "success",
  "from": "2025-03-16 09:15:00",
  "to": "2025-04-16 15:30:00",
  "interval": "day",
  "results": {
    "RELIANCE:NSE": {
      "instrument_token": 738561,
      "tradingsymbol": "RELIANCE",
      "exchange": "NSE",
      "data": [
        {
          "date": "Sun, 16 Mar 2025 18:30:00 GMT",
          "open": 1242.15,
          "high": 1257.4,
          "low": 1233.1,
          "close": 1238.85,
          "volume": 16640952
        },
        {
          "date": "Mon, 17 Mar 2025 18:30:00 GMT",
          "open": 1244.7,
          "high": 1248.35,
          "low": 1235,
          "close": 1238.8,
          "volume": 15745877
        }
      ]
    }
  }
}
```

#### Partial Success Response (with errors)

If some tickers succeed and others fail:

```json
{
  "status": "success",
  "from": "2025-03-16 09:15:00",
  "to": "2025-04-16 15:30:00",
  "interval": "day",
  "results": {
    "RELIANCE:NSE": {
      "instrument_token": 738561,
      "tradingsymbol": "RELIANCE",
      "exchange": "NSE",
      "data": [...]
    }
  },
  "errors": {
    "INVALID:NSE": "Instrument not found in cache"
  }
}
```

#### Error Response

```json
{
  "status": "error",
  "message": "tickers parameter is required (format: \"TRADINGSYMBOL:EXCHANGE,TRADINGSYMBOL:EXCHANGE\")"
}
```

### Error Codes

| HTTP Code | Description |
|-----------|-------------|
| 200 | Success - data returned for at least one ticker |
| 400 | Bad Request - missing or invalid parameters |
| 401 | Unauthorized - invalid or missing API key |
| 404 | Not Found - instruments cache not initialized |
| 500 | Internal Server Error - server-side error |

### Prerequisites

Before using this endpoint, you must:

1. Call `/cache_instruments?apikey=your_api_key` to populate the instruments cache
2. Ensure you have configured a valid Zerodha access token via:
   - Browser login at `/` (interactive OAuth flow), OR
   - API call to `/set_access_token?apikey=your_key&access_token=your_token`
3. Verify token is set: `/get_token_status?apikey=your_api_key`

### Notes

- Spaces in date-time parameters should be replaced with `+` (e.g., `2025-03-16+09:15:00`)
- All tickers must be in the format `TRADINGSYMBOL:EXCHANGE` (e.g., `SBIN:NSE`)
- The endpoint will return partial results if some tickers succeed and others fail
- Historical data availability depends on the Zerodha Kite API limitations
- Rate limits apply, always ask on implementation on how to add rate limits for historical data

---

## Troubleshooting

### Error: "Invalid `api_key` or `access_token`"

This error occurs when:
1. **No access token is configured**: Call `/get_token_status` to check
2. **Access token has expired**: Zerodha tokens expire after 24 hours - renew via login or `/set_access_token`
3. **Invalid token**: The token may be incorrect or revoked

**Solution:**
```bash
# Check token status
curl "http://your-server/get_token_status?apikey=your_key"

# If no token or expired, set a new one
curl "http://your-server/set_access_token?apikey=your_key&access_token=fresh_token"
```

### Access Token Renewal Workflow

Zerodha access tokens must be renewed daily. Two options:

**Option 1: Browser Login**
1. Visit `http://your-server/` (requires basic auth)
2. Click "Login to generate access token"
3. Complete Zerodha OAuth flow
4. Token is automatically saved

**Option 2: Manual API Call**
1. Login to Zerodha Kite Connect manually to get fresh token
2. Call `/set_access_token?apikey=your_key&access_token=new_token`

### Database Location

- **Instruments Cache**: `instruments.db` in application directory
- **Access Token**: Stored in `auth_tokens` table in same database
- **Persistence**: Database survives Docker container restarts (ensure volume is mounted)

