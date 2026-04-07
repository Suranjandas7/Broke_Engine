#!/bin/bash
# Simple API test script for Broke Engine
# Tests basic endpoint availability when the server is live

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Prompt for credentials
read -p "Enter API URL (e.g., http://localhost:5000): " BASE_URL
read -p "Enter username: " USERNAME
read -s -p "Enter password: " PASSWORD
echo ""

# Remove trailing slash if present
BASE_URL="${BASE_URL%/}"

# Build basic auth header for endpoints that need it
BASIC_AUTH=$(echo -n "$USERNAME:$PASSWORD" | base64)

echo ""
echo "========================================="
echo "Testing Broke Engine API at $BASE_URL"
echo "========================================="
echo ""

# Step 1: Get JWT token via POST with JSON body
echo -e "${BLUE}--- Authenticating ---${NC}"
printf "%-50s" "Getting JWT token..."

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "$BASE_URL/auth/token" 2>/dev/null)

HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}FAIL${NC} (HTTP $HTTP_CODE)"
    echo "Could not authenticate. Check your credentials."
    echo "Response: $BODY"
    exit 1
fi

# Extract token from JSON response
JWT_TOKEN=$(echo "$BODY" | grep -o '"token"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/"token"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')

if [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}FAIL${NC} (Could not parse token)"
    echo "Response: $BODY"
    exit 1
fi

echo -e "${GREEN}PASS${NC} (Got JWT token)"
echo ""

PASSED=0
FAILED=0

test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local description="$3"
    local data="$4"
    
    printf "%-50s" "Testing: $description..."
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    else
        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -X "$method" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    fi
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $response)"
        PASSED=$((PASSED + 1))
    elif [ "$response" = "404" ]; then
        echo -e "${YELLOW}WARN${NC} (HTTP 404 - endpoint exists but resource not found)"
        PASSED=$((PASSED + 1))
    elif [ "$response" = "000" ]; then
        echo -e "${RED}FAIL${NC} (Connection refused)"
        FAILED=$((FAILED + 1))
    elif [ "$response" = "401" ]; then
        echo -e "${RED}AUTH${NC} (HTTP 401 - token rejected)"
        FAILED=$((FAILED + 1))
    else
        echo -e "${YELLOW}WARN${NC} (HTTP $response)"
        PASSED=$((PASSED + 1))
    fi
}

# Test endpoint that uses Basic Auth (not JWT)
test_basic_auth_endpoint() {
    local endpoint="$1"
    local description="$2"
    
    printf "%-50s" "Testing: $description..."
    
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Basic $BASIC_AUTH" \
        "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $response)"
        PASSED=$((PASSED + 1))
    elif [ "$response" = "000" ]; then
        echo -e "${RED}FAIL${NC} (Connection refused)"
        FAILED=$((FAILED + 1))
    else
        echo -e "${YELLOW}WARN${NC} (HTTP $response)"
        PASSED=$((PASSED + 1))
    fi
}

# Basic endpoints
echo "--- Basic Endpoints ---"
test_basic_auth_endpoint "/" "Root endpoint (Basic Auth)"
test_endpoint "GET" "/cache_status" "Cache status"

# Instrument endpoints
echo ""
echo "--- Instrument Endpoints ---"
test_endpoint "GET" "/get_instrument?tradingsymbol=SBIN&exchange=NSE" "Get instrument"
test_basic_auth_endpoint "/cache_instruments" "Cache instruments (Basic Auth)"

# Market data endpoints
echo ""
echo "--- Market Data Endpoints ---"
test_endpoint "GET" "/ltp?tickers=SBIN:NSE" "LTP endpoint"
test_endpoint "GET" "/historical_data?tickers=SBIN:NSE&from=2024-01-01%2009:15:00&to=2024-01-05%2015:30:00&interval=day" "Historical data"

# History endpoints
echo ""
echo "--- History Database Endpoints ---"
test_endpoint "GET" "/history_cache_status" "History cache status"
test_endpoint "GET" "/fetch_history?ticker=SBIN:NSE&from_year=2024&to_year=2024" "Fetch history"
test_endpoint "GET" "/get_history?ticker=SBIN:NSE&from_year=2024&to_year=2024" "Get history"

# Greeks endpoints
echo ""
echo "--- Greeks Endpoints ---"
test_endpoint "GET" "/greeks?ticker=HDFCBANK26MAY800CE:NFO" "Greeks calculation"
test_endpoint "POST" "/greeks/batch" "Greeks batch" '{"tickers":["HDFCBANK26MAY800CE:NFO"]}'

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All endpoints responding!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some endpoints may need attention.${NC}"
    exit 1
fi
