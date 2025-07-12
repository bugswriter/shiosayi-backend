#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
BASE_URL="http://127.0.0.1:5001"
if [ -f .env ]; then
    export $(cat .env | sed 's/#.*//g' | xargs)
fi
DB_FILE=${DATABASE_FILENAME:-"shiosayi.db"}

# --- Colors for output ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --- Helper function for checking status codes ---
check_status() {
    local expected=$1
    local actual=$2
    local message=$3
    if [ "$expected" == "$actual" ]; then
        echo -e "${GREEN}SUCCESS:${NC} $message (Status: $actual)"
    else
        echo -e "${RED}FAILURE:${NC} $message (Expected: $expected, Got: $actual)"
        exit 1
    fi
}

# --- Pre-flight Check ---
check_server_is_running() {
    echo -e "${YELLOW}--- 0. Pre-flight Check: Verifying Server Connection ---${NC}"
    if ! curl --connect-timeout 5 -s -f "$BASE_URL/health" > /dev/null 2>&1; then
        echo -e "${RED}ERROR: Could not connect to the Flask server at $BASE_URL.${NC}"
        echo "Please ensure the server is running in another terminal via 'flask --app app run --port 5001'"
        exit 1
    fi
    echo -e "${GREEN}SUCCESS:${NC} Server is responding."
}

# --- Test Functions ---

cleanup_and_seed() {
    echo -e "${YELLOW}--- 1. Cleaning and Initializing Database ---${NC}"
    rm -f "$DB_FILE"
    flask --app app init-db
    echo "Database '$DB_FILE' created."

    echo -e "${YELLOW}--- 2. Seeding Orphan Films ---${NC}"
    sqlite3 "$DB_FILE" "INSERT INTO films (title, year, status, magnet) VALUES ('Spirited Away', 2001, 'orphan', 'magnet:?xt=urn:btih:film1');"
    sqlite3 "$DB_FILE" "INSERT INTO films (title, year, status, magnet) VALUES ('My Neighbor Totoro', 1988, 'orphan', 'magnet:?xt=urn:btih:film2');"
    sqlite3 "$DB_FILE" "INSERT INTO films (title, year, status) VALUES ('Princess Mononoke', 1997, 'abandoned');" # No magnet
    echo "Seeded 3 films into the database."
}

test_webhook_and_get_token() {
    echo -e "\n${YELLOW}--- 3. Testing New 'Lover' Tier Subscription (/webhook) ---${NC}"
    
    TEST_EMAIL="test-lover-user-$RANDOM@example.com"
    
    read -r -d '' PAYLOAD << EOM
{
  "verification_token": "$KOFI_VERIFICATION_TOKEN",
  "message_id": "test-$(uuidgen)",
  "timestamp": "2025-07-12T18:06:19Z",
  "type": "Subscription",
  "is_public": true,
  "from_name": "Test Lover",
  "email": "$TEST_EMAIL",
  "amount": "3.00",
  "currency": "USD",
  "is_subscription_payment": true,
  "is_first_subscription_payment": true,
  "tier_name": "Lover Tier"
}
EOM

    local status_code=$(curl --connect-timeout 5 -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$PAYLOAD" "$BASE_URL/webhook")
    check_status 200 "$status_code" "Webhook received new subscription"

    API_TOKEN=$(sqlite3 "$DB_FILE" "SELECT token FROM guardians WHERE email='$TEST_EMAIL';")
    
    if [ -z "$API_TOKEN" ]; then
        echo -e "${RED}FAILURE: API Token not found in database for $TEST_EMAIL${NC}"
        exit 1
    fi
    echo -e "${GREEN}SUCCESS:${NC} Retrieved API Token for new user."
}

test_endpoints_with_token() {
    echo -e "\n${YELLOW}--- 4. Testing Endpoints with API Token ---${NC}"

    echo "Testing GET /auth..."
    auth_response=$(curl --connect-timeout 5 -s -w "\n%{http_code}" "$BASE_URL/auth?token=$API_TOKEN")
    auth_status_code=$(tail -n1 <<< "$auth_response")
    auth_body=$(sed '$ d' <<< "$auth_response")
    check_status 200 "$auth_status_code" "/auth endpoint"
    tier=$(echo "$auth_body" | jq -r '.tier')
    if [ "$tier" == "lover" ]; then
        echo -e "${GREEN}SUCCESS:${NC} Verified tier is 'lover' from /auth response."
    else
        echo -e "${RED}FAILURE: Tier was '$tier', expected 'lover'.${NC}"
        exit 1
    fi

    echo "Testing POST /adopt/1 (should succeed)..."
    adopt_status_1=$(curl --connect-timeout 5 -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/adopt/1?TOKEN=$API_TOKEN")
    check_status 200 "$adopt_status_1" "/adopt for first film"

    echo "Testing POST /adopt/2 (should fail due to tier limit)..."
    adopt_status_2=$(curl --connect-timeout 5 -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/adopt/2?TOKEN=$API_TOKEN")
    check_status 403 "$adopt_status_2" "/adopt for second film (tier limit)"

    echo "Testing GET /magnet/1 (should succeed)..."
    magnet_status_1=$(curl --connect-timeout 5 -s -o /dev/null -w "%{http_code}" "$BASE_URL/magnet/1?TOKEN=$API_TOKEN")
    check_status 200 "$magnet_status_1" "/magnet for adopted film"

    echo "Testing GET /magnet/3 (should fail as no magnet exists)..."
    magnet_status_3=$(curl --connect-timeout 5 -s -o /dev/null -w "%{http_code}" "$BASE_URL/magnet/3?TOKEN=$API_TOKEN")
    check_status 404 "$magnet_status_3" "/magnet for film without magnet link"

    echo "Testing GET /auth with invalid token (should fail)..."
    invalid_status=$(curl --connect-timeout 5 -s -o /dev/null -w "%{http_code}" "$BASE_URL/auth?token=invalid-token-123")
    check_status 401 "$invalid_status" "Endpoint access with invalid token"
}


# --- Main Execution ---

main() {
    echo "===== Starting API Integration Test ====="
    check_server_is_running # <-- NEW STEP
    cleanup_and_seed
    test_webhook_and_get_token
    test_endpoints_with_token
    echo -e "\n${GREEN}===== All Tests Passed Successfully! =====${NC}"
}
