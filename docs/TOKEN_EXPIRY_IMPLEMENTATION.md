# Token Expiry Auto-Redirection Implementation

## Overview

This document describes the implementation of automatic token expiry handling using KiteConnect's `set_session_expiry_hook` feature. When a Zerodha access token expires, the system now automatically handles the expiry with smart redirection for browser requests and JSON error responses for API calls.

## Implementation Summary

### Changes Made

#### 1. **Error Handler for TokenException** (`app/error_handlers.py`)
- Added import for `TokenException` from `kiteconnect.exceptions`
- Registered error handler for `TokenException` that returns:
  - HTTP Status: 401 Unauthorized
  - JSON response with clear error message and login URL
  - Error code: `TOKEN_EXPIRED`
  - Action required message for API clients

**Response Format:**
```json
{
  "status": "error",
  "error_code": "TOKEN_EXPIRED",
  "message": "Access token has expired or is invalid. Please login again.",
  "login_url": "/",
  "action_required": "Re-authenticate via browser at the provided login_url"
}
```

#### 2. **Session Expiry Hook** (`app/services/kite_client.py`)
Implemented automatic token expiry detection and handling:

**Helper Functions:**
- `_is_browser_request()`: Detects if request is from browser (HTML) or API client (JSON)
- `_handle_token_expiry()`: Callback function for KiteConnect's session expiry hook

**Token Expiry Behavior:**
1. **Logging**: Logs token expiry event with warning level
2. **Database Cleanup**: Automatically clears expired token from database
3. **Session Cleanup**: Removes token from Flask session if present
4. **Smart Redirection**:
   - **Browser Requests** (Accept: text/html):
     - Flash error message to user
     - Redirect to homepage with `?error=token_expired` parameter
   - **API Requests** (Accept: application/json):
     - Raise TokenException (caught by error handler)
     - Returns JSON error response with 401 status

**Hook Registration:**
- Hook is set on every KiteConnect client instance in `get_kite_client()`
- Uses KiteConnect's built-in `set_session_expiry_hook()` method
- Ensures automatic token expiry handling for all API calls

#### 3. **UI Error Display** (`app/templates/index.html`)

**Added Flash Message Support:**
- Displays server-side flash messages with category-based styling
- Supports error, info, and success message types
- Messages appear at top of page with appropriate colors

**Token Expiry Banner:**
- Red error banner displayed when redirected with `?error=token_expired`
- Clear message: "Your Zerodha access token has expired"
- JavaScript automatically shows banner and cleans URL parameter
- Banner includes instructions to re-authenticate

**CSS Styling:**
- Error banner: Red left border, light red background
- Flash messages: Category-based colors (error=red, info=blue, success=green)
- Prominent display for better user visibility

## How It Works

### Flow Diagram

```
API Call Made
     |
     v
KiteConnect Client
     |
     v
Token Expired?
     |
     +---> YES --> session_expiry_hook callback triggered
     |                    |
     |                    v
     |             _handle_token_expiry()
     |                    |
     |                    +---> Clear DB token
     |                    +---> Clear session token
     |                    +---> Log event
     |                    |
     |                    v
     |             Check Request Type
     |                    |
     |         +----------+----------+
     |         |                     |
     |    Browser Request      API Request
     |         |                     |
     |         v                     v
     |    Flash message        Raise TokenException
     |    Redirect to /              |
     |         |                     v
     |         v              Error handler catches
     |    Show error          Returns JSON 401
     |    banner on page
     |
     +---> NO --> Continue normal execution
```

### User Experience

#### For Browser Users:
1. User navigates to protected page (e.g., `/testing`)
2. Token is expired
3. Hook triggers → clears token → flashes message → redirects to `/`
4. Homepage displays prominent red banner: "Access Token Expired"
5. User clicks "Login to generate access token"
6. Completes OAuth flow
7. New token saved, user can continue

#### For API Clients:
1. Client makes API call (e.g., `/historical_data`)
2. Token is expired
3. Hook triggers → clears token → raises TokenException
4. Error handler returns JSON response with 401 status
5. Client receives structured error with:
   - Error code: `TOKEN_EXPIRED`
   - Clear message about re-authentication
   - Login URL for user redirection
6. Client can display error or redirect user to login page

## Testing the Implementation

### Manual Testing Steps

**Note:** All API endpoints now require JWT Bearer token authentication. Get a token first:
```bash
TOKEN=$(curl -s -X POST http://localhost:5010/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' | jq -r '.token')
```

#### Test 1: API Request with Expired Token
```bash
# Set an invalid Zerodha token
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/set_access_token?access_token=invalid_token_12345"

# Make API call - should return JSON error
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/historical_data?tickers=SBIN:NSE&from=2025-03-16+09:15:00&to=2025-03-16+15:30:00&interval=day"

# Expected Response:
# {
#   "status": "error",
#   "error_code": "TOKEN_EXPIRED",
#   "message": "Access token has expired or is invalid...",
#   "login_url": "/"
# }
```

#### Test 2: Browser Request with Expired Token
```bash
# Visit in browser (with basic auth credentials):
http://localhost:5010/testing

# Expected behavior:
# 1. Redirected to http://localhost:5010/
# 2. Red error banner displayed
# 3. Message: "Your Zerodha access token has expired"
```

#### Test 3: Verify Token Cleared
```bash
# After token expiry, check token status
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/get_token_status"

# Expected Response:
# {
#   "status": "success",
#   "token_exists": false,
#   "message": "No access token found..."
# }
```

#### Test 4: Re-login Flow
```bash
# Visit homepage in browser
http://localhost:5010/

# Click "Login to generate access token"
# Complete OAuth flow
# Verify new token works
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5010/get_token_status"
```

## Key Features

✅ **Automatic Detection**: Uses KiteConnect's built-in hook mechanism  
✅ **Smart Routing**: Different handling for browser vs API requests  
✅ **Clean Database**: Expired tokens automatically removed  
✅ **Clear Messaging**: Users see friendly error messages  
✅ **Logging**: All token expiry events logged for monitoring  
✅ **No Rate Limiting Impact**: Token expiry handled before rate limiting  
✅ **Session Cleanup**: Both database and Flask session cleared  
✅ **API-Friendly**: Structured JSON errors for programmatic clients  

## Technical Details

### KiteConnect Session Expiry Hook
The hook is called by KiteConnect SDK whenever:
- Token is invalid
- Token has expired
- Token is missing
- API returns token-related authentication errors

### Request Type Detection
```python
def _is_browser_request():
    accept_header = request.headers.get('Accept', '')
    return 'text/html' in accept_header
```

Browsers typically send: `Accept: text/html,application/xhtml+xml...`  
API clients send: `Accept: application/json` or similar

### Flask Flash Messages
Flask's `flash()` stores messages in session for one-time display:
```python
flash("Your access token has expired...", "error")
```

Template retrieves and displays:
```jinja2
{% with messages = get_flashed_messages(with_categories=true) %}
```

## Logging

All token expiry events are logged with appropriate levels:

- **Warning**: Token expiry detected
- **Info**: Cleared token from session/database
- **Info**: Request type detected (browser/API)

Example log output:
```
2026-03-29 10:15:32 - WARNING - Token expired - clearing stored token and initiating re-authentication flow
2026-03-29 10:15:32 - INFO - Cleared expired token from session
2026-03-29 10:15:32 - INFO - Browser request detected - redirecting to login page
```

## Edge Cases Handled

1. **Token in session but not in DB**: Both cleared
2. **Token in DB but not in session**: DB token cleared
3. **Multiple concurrent requests**: Each handled independently
4. **Mixed browser/API requests**: Each routed appropriately
5. **No token present**: Hook not triggered (handled by other error handlers)

## Future Enhancements

Potential improvements for future versions:

1. **Token Refresh**: Implement automatic token refresh before expiry
2. **Email Notifications**: Alert users when token is about to expire
3. **Token Status Dashboard**: Show token age and expiry countdown
4. **Graceful Degradation**: Cache some data to allow offline queries
5. **Multi-User Support**: Per-user token storage and management

## Related Files

- `app/services/kite_client.py` - Session expiry hook implementation
- `app/error_handlers.py` - TokenException error handler
- `app/templates/index.html` - Error display UI
- `app/database/auth_tokens.py` - Token storage and cleanup
- `docs/API.md` - API documentation (includes token management)
- `docs/GUIDE.md` - User guide (includes token renewal workflow)

## References

- [KiteConnect Python Documentation](https://kite.trade/docs/pykiteconnect/v3/)
- [Zerodha API Documentation](https://kite.trade/docs/connect/v3/)
- [Flask Flash Messages](https://flask.palletsprojects.com/en/2.3.x/patterns/flashing/)
