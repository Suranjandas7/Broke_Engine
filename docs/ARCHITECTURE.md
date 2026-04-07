# Architecture Overview - Broke Engine

## Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   main.py      │
                    │  (Entry Point) │
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  app/__init__  │
                    │ (App Factory)  │
                    └────────┬───────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌──────────────────┐      ┌──────────────────┐
    │   Middleware     │      │  Error Handlers  │
    │                  │      │                  │
    │ • API Key Check  │      │ • 400, 401, etc  │
    │ • Basic Auth     │      │ • Exception Mgmt │
    └────────┬─────────┘      └──────────────────┘
             │
             ▼
    ┌────────────────────────────────────────┐
    │           Route Blueprints             │
    ├────────────────────────────────────────┤
    │  • auth_routes    (/, /login)          │
    │  • instruments_bp (/cache_instruments) │
    │  • market_bp      (/historical_data)   │
    │  • tokens_bp      (/set_access_token)  │
    └───────────┬────────────────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
┌──────────┐          ┌──────────┐
│ Services │          │ Database │
│          │          │          │
│ Kite API │◄────────►│ SQLite   │
│ Client   │          │          │
│          │          │ • Auth   │
│          │          │ • Cache  │
└──────────┘          └──────────┘
     │
     ▼
┌──────────────┐
│ Kite Connect │
│   (Zerodha)  │
└──────────────┘
```

## Layer Responsibilities

### 1. Entry Point (`main.py`)
- Minimal bootstrap code
- Creates Flask app using factory
- Starts the server

### 2. App Factory (`app/__init__.py`)
- Initializes Flask application
- Loads configuration
- Registers blueprints
- Sets up middleware
- Initializes databases
- Registers error handlers

### 3. Configuration (`app/config.py`)
- Environment variable loading
- Application constants
- Zerodha API configuration
- Validation of required settings

### 4. Middleware (`app/middleware/`)
- **JWT Authentication**: Validates Bearer token in Authorization header
- **Basic Auth**: Protects sensitive endpoints (/, /cache_instruments)
- Executed before route handlers

### 5. Routes (`app/routes/`)
Each blueprint handles a specific domain:

#### Auth Routes
- User authentication flow
- OAuth callback handling
- Session management

#### Instrument Routes
- Cache instruments from Kite API
- Query cached instruments
- Manage cache lifecycle

#### Market Routes
- Fetch historical OHLC data
- Support multiple tickers
- Time-series data retrieval

#### Token Routes
- Set access tokens programmatically
- Check token status
- Clear tokens

#### History Routes
- Cache 1-minute historical data
- Export cached data in multiple formats
- Check history cache status

#### Greeks Routes
- Calculate option Greeks (Delta, Gamma, Theta, Vega, Rho)
- Batch Greeks calculation
- Implied Volatility calculation

### 6. Services (`app/services/`)
- **Kite Client**: Factory for KiteConnect instances
- **Historical Fetcher**: Fetches and caches historical data with rate limiting
- **Greeks Calculator**: High-level options Greeks calculation service
- **Greeks Module** (`greeks/`): Black-Scholes pricing, IV calculation, Greeks formulas
- Handles token retrieval from session/database
- Provides configured API clients to routes

### 7. Database (`app/database/`)
- **Connection**: Thread-safe SQLite connections
- **Instruments**: Cache of trading instruments
- **Auth Tokens**: Persistent token storage
- **Historical Data**: Cached 1-minute OHLCV data
- **Migrations**: Schema migrations for updates

### 8. Models (`app/models/`)
- **Request Models**: Validate incoming data (Pydantic)
- **Response Models**: Standardize outgoing data
- Type safety and automatic validation

### 9. Error Handlers (`app/error_handlers.py`)
- Centralized error handling
- Consistent JSON error responses
- Logging of errors
- HTTP status code management

### 10. Templates (`app/templates/`)
- Jinja2 HTML templates
- Login page UI
- Success/error pages

## Data Flow Example: Historical Data Request

```
1. Client → GET /historical_data?tickers=SBIN:NSE&from=2025-01-01...
2. Middleware → Validates API key
3. Market Routes → Parses request parameters
4. Market Routes → Validates ticker format
5. Database → Looks up instrument tokens
6. Services → Gets Kite API client
7. Kite Client → Fetches data from Zerodha
8. Market Routes → Formats response
9. Client ← Returns JSON with OHLC data
```

## Security Layers

```
┌─────────────────────────────────────┐
│        Request Security             │
├─────────────────────────────────────┤
│ 1. Basic Auth (for / and           │
│    /cache_instruments)              │
│ 2. JWT Bearer Token (all other     │
│    authenticated routes)            │
│ 3. OAuth Token (Kite Connect)       │
│ 4. Rate Limiting (per-user)         │
└─────────────────────────────────────┘
```

## Database Schema

### Instruments Table
```sql
CREATE TABLE instruments (
    tradingsymbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    instrument_token INTEGER PRIMARY KEY,
    exchange_token INTEGER,
    name TEXT,
    last_price REAL,
    expiry TEXT,
    strike REAL,
    tick_size REAL,
    lot_size INTEGER,
    instrument_type TEXT,
    segment TEXT,
    UNIQUE(tradingsymbol, exchange)
);

CREATE INDEX idx_tradingsymbol ON instruments(tradingsymbol);
```

### Auth Tokens Table
```sql
CREATE TABLE auth_tokens (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    access_token TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Module Dependencies

```
main.py
  └── app/__init__.py
       ├── app/config.py
       ├── app/middleware/
       │    ├── auth.py
       │    └── api_key.py (JWT validation)
       ├── app/database/
       │    ├── connection.py
       │    ├── instruments.py
       │    ├── auth_tokens.py
       │    ├── historical_data.py
       │    └── migrations.py
       ├── app/services/
       │    ├── kite_client.py
       │    ├── historical_fetcher.py
       │    ├── greeks_calculator.py
       │    └── greeks/
       │         ├── black_scholes.py
       │         ├── greeks.py
       │         ├── implied_volatility.py
       │         └── utils.py
       ├── app/routes/
       │    ├── auth_routes.py
       │    ├── instrument_routes.py
       │    ├── market_routes.py
       │    ├── token_routes.py
       │    ├── history_routes.py
       │    └── greeks_routes.py
       ├── app/models/
       │    ├── requests.py
       │    └── responses.py
       ├── app/error_handlers.py
       └── app/utils/
            ├── __init__.py
            └── export_formats.py
```

## Testing Strategy

Each layer can be tested independently:

1. **Database Layer**: Mock SQLite connections
2. **Services**: Mock KiteConnect API calls
3. **Routes**: Use Flask test client
4. **Middleware**: Test with mock requests
5. **Models**: Test Pydantic validation

## Scalability Considerations

- **Horizontal Scaling**: Use Gunicorn with multiple workers (configured with gevent)
- **Database**: Can migrate to PostgreSQL if needed
- **Caching**: Can add Redis for instrument cache
- **Rate Limiting**: Already implemented via Flask-Limiter (per-user, in-memory)
- **API Gateway**: Can add nginx as reverse proxy

## Configuration Management

Environment variables are loaded in `app/config.py`:

```python
KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")
AUTH_USER = os.getenv("AUTH_USER")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.urandom(24))
JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "180"))
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.065"))
```

All configuration is validated on startup.
