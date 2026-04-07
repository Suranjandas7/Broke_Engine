# Options & Derivatives Support - Implementation Summary

## Overview

**Broke Engine now fully supports options and futures contracts** alongside stocks. The system automatically detects options (CE/PE) and futures (FUT) from the instruments database and handles them seamlessly with all existing endpoints.

## What's Been Implemented

### ✅ Database Schema Updates

1. **New OI Columns Added to Historical Data Tables**
   - `oi` (REAL, default 0) - Open Interest
   - `oi_day_high` (REAL, default 0) - Highest OI during the day
   - `oi_day_low` (REAL, default 0) - Lowest OI during the day

2. **Auto-Migration System**
   - Created `app/database/migrations.py` with migration utilities
   - Runs automatically on app startup
   - Updates existing tables and ensures new tables include OI columns
   - Idempotent - safe to run multiple times

3. **Updated Table Creation**
   - `app/database/historical_data.py` now creates tables with OI columns by default
   - All new ticker tables (stocks or options) include the full schema

### ✅ Code Updates

1. **Option Detection Helper** (`app/services/historical_fetcher.py`)
   - `is_option_instrument()` function auto-detects options from `instrument_type`
   - Checks for CE, PE, FUT in instrument metadata
   - Logs detected options for visibility

2. **Data Insertion Updated** (`app/database/historical_data.py`)
   - `insert_historical_data()` accepts optional OI fields
   - Defaults to 0 if not provided (compatible with Kite API)
   - Bulk insert statements updated to include OI columns

3. **Data Retrieval Updated**
   - `get_historical_data()` returns OI fields in query results
   - `get_historical_data_by_date_range()` includes OI fields
   - All export formats (JSON, Arrow, Parquet, CSV, MessagePack) include OI

4. **Response Metadata Enhanced** (`app/routes/history_routes.py`)
   - Responses now include `instrument_type` field
   - Helps identify stocks (EQ) vs options (CE/PE/FUT)
   - Added to both year-based and date-based queries

5. **Documentation Updates** (`app/routes/market_routes.py`)
   - Updated docstrings to mention options support
   - Clarified OI limitations (Kite API doesn't provide historical OI)
   - Examples include option trading symbols

### ✅ Comprehensive Documentation

1. **New "Options & Derivatives Support" Section in README**
   - Auto-detection explanation
   - Trading symbol format guide
   - Response format examples (stocks vs options)
   - How to find option symbols
   - Key differences table (stocks vs options)
   - Future enhancements roadmap
   - API usage examples for options

2. **Updated Troubleshooting Section**
   - Added options-related issues and solutions
   - OI fields showing 0 - explained as expected behavior
   - How to find option symbols
   - Expired options handling

3. **Updated Changelog**
   - Options support listed as latest feature
   - Detailed breakdown of what's included

4. **Updated Features List**
   - Highlighted options & derivatives support
   - Mentioned auto-detection
   - OI fields ready for future use

## How It Works

### For Users (No API Changes Needed!)

All API endpoints require JWT Bearer token authentication:

```bash
# First, get a JWT token
TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')
```

**Stock Query:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/fetch_history?ticker=SBIN:NSE&from_year=2024&to_year=2024"
```

**Option Query (identical syntax):**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/fetch_history?ticker=HDFCAMC26MAR2880CE:NFO&from_year=2026&to_year=2026"
```

The system automatically detects the instrument type and handles it appropriately.

### Behind the Scenes

1. **User requests data** for `HDFCAMC26MAR2880CE:NFO`
2. **System looks up instrument** in database
3. **Auto-detects** instrument_type = `CE` (Call European)
4. **Fetches data** from Kite API (OHLCV only - no OI from API)
5. **Stores in database** with OI fields = 0
6. **Returns response** with `instrument_type: "CE"` in metadata
7. **User gets** OHLCV + OI fields (OI is 0, but structure is there)

## Response Format

### Stock Response (SBIN:NSE)
```json
{
  "status": "success",
  "ticker": "SBIN",
  "exchange": "NSE",
  "instrument_type": "EQ",
  "from_year": 2024,
  "to_year": 2024,
  "record_count": 89750,
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

### Option Response (HDFCAMC26MAR2880CE:NFO)
```json
{
  "status": "success",
  "ticker": "HDFCAMC26MAR2880CE",
  "exchange": "NFO",
  "instrument_type": "CE",
  "from_year": 2026,
  "to_year": 2026,
  "record_count": 45000,
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

**Key Difference:** `instrument_type` field identifies the type (EQ vs CE/PE/FUT)

## Important Notes

### ⚠️ OI Limitation

**Historical OI data is not available** from Kite's `historical_data` API endpoint. Therefore:
- OI fields will always be `0` in historical data responses
- This is a Kite API limitation, not a Broke Engine limitation
- The database schema is ready for OI data when/if it becomes available

### Future Enhancement Options

To add real-time OI tracking (out of scope for current implementation):

1. **WebSocket Streaming** (Real-time)
   - Subscribe to tick-by-tick data via Kite WebSocket
   - Capture OI values in real-time
   - Store with each candle
   - Only works for current/future data

2. **Daily Quote Snapshots** (Historical)
   - Make separate `kite.quote()` API calls
   - Get daily OI values
   - Very slow (3 req/sec rate limit)
   - May not have full historical OI data

3. **Hybrid Approach**
   - Use historical_data for OHLCV (fast)
   - Use quote API for daily OI snapshots
   - Best balance of speed and data completeness

## Testing Results

### ✅ Migration Test
- Existing `SBIN_NSE_history` table successfully migrated
- OI columns added without data loss
- Defaults set to 0 as expected

### ✅ New Table Test
- New tables created with OI columns by default
- Schema matches specification

### ✅ Option Detection Test
```
HDFCAMC26MAR2880CE:NFO (CE) -> Option: True
NIFTY26APR24000PE:NFO (PE) -> Option: True
SBIN:NSE (EQ) -> Option: False
```

### ✅ Data Query Test
```sql
SELECT timestamp, open, high, low, close, volume, oi, oi_day_high, oi_day_low
FROM SBIN_NSE_history
```
All columns present and returning data correctly.

## Files Modified

1. **app/database/migrations.py** (NEW)
   - Migration utilities
   - OI column addition logic
   - Migration status checking

2. **app/database/historical_data.py**
   - Updated table creation schema
   - Updated insert statements
   - Updated query statements

3. **app/__init__.py**
   - Added migration call on startup
   - Imports migration module

4. **app/services/historical_fetcher.py**
   - Added `is_option_instrument()` helper
   - Updated docstrings with OI notes

5. **app/routes/history_routes.py**
   - Added `instrument_type` to response metadata
   - Imports instrument lookup for type detection

6. **app/routes/market_routes.py**
   - Updated endpoint docstrings
   - Mentioned options support

7. **README.md**
   - New "Options & Derivatives Support" section (200+ lines)
   - Updated Features section
   - Updated Changelog
   - Updated Troubleshooting
   - Updated examples throughout

## Backward Compatibility

✅ **Fully backward compatible** - all existing functionality works unchanged:
- Existing stock queries work identically
- Old cached data remains intact
- Auto-migration is non-destructive
- OI fields default to 0 for stocks

## User Impact

### No Breaking Changes
- No API parameter changes
- No response structure changes (only additions)
- Existing clients continue to work

### New Capabilities
- Can now query options and futures
- Get instrument_type in responses
- OI fields present (even if 0)
- Ready for future OI enhancements

## Summary

**Status:** ✅ Complete and Tested

**What Users Get:**
- Full options & futures support
- Auto-detection (no special parameters)
- Unified API (same endpoints for stocks and options)
- OI-ready database schema
- Comprehensive documentation
- Backward compatibility

**What's Next (Future):**
- Real-time OI tracking via WebSocket
- ~~Greeks calculation (IV, Delta, Gamma, Theta, Vega)~~ ✅ **IMPLEMENTED** - See `/greeks` and `/greeks/batch` endpoints
- Option chain builder
- Spread strategy builder

---

**Implementation Date:** March 20, 2026
**Tested:** ✅ Migration, Schema, Detection, Queries
**Documentation:** ✅ Complete
**Status:** Ready for Production
