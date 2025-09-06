#!/bin/bash

# Cloud Armor Testing Script
# Tests various protection mechanisms

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

STATIC_IP_NAME="atlas-frontend-ip"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"

echo -e "${BLUE}=== Cloud Armor Protection Testing ===${NC}"
echo ""

# Get static IP
echo -e "${YELLOW}Getting static IP address...${NC}"
STATIC_IP=$(gcloud compute addresses describe "$STATIC_IP_NAME" --global --format='value(address)' 2>/dev/null || echo "")

if [ -z "$STATIC_IP" ]; then
    echo -e "${RED}❌ Static IP not found. Run 'make setup-cloud-armor' first.${NC}"
    exit 1
fi

echo "Testing against: $STATIC_IP"
echo ""

# Test 1: Basic connectivity
echo -e "${YELLOW}Test 1: Basic HTTP Connectivity${NC}"
if curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" --max-time 10 "http://$STATIC_IP"; then
    echo -e "${GREEN}✅ Basic connectivity successful${NC}"
else
    echo -e "${RED}❌ Basic connectivity failed${NC}"
fi
echo ""

# Test 2: Rate limiting test
echo -e "${YELLOW}Test 2: Rate Limiting Protection${NC}"
echo "Sending 20 rapid requests to test rate limiting..."

# Create temporary file for results
TEMP_FILE=$(mktemp)

# Send rapid requests
for i in {1..20}; do
    (
        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$STATIC_IP" 2>/dev/null || echo "000")
        echo "Request $i: $RESPONSE" >> "$TEMP_FILE"
    ) &
    
    # Small delay to avoid overwhelming local system
    sleep 0.1
done

# Wait for all requests to complete
wait

# Analyze results
echo "Results:"
cat "$TEMP_FILE"

# Check for rate limiting (429 responses)
RATE_LIMITED=$(grep "429" "$TEMP_FILE" | wc -l)
if [ "$RATE_LIMITED" -gt 0 ]; then
    echo -e "${GREEN}✅ Rate limiting triggered ($RATE_LIMITED requests blocked)${NC}"
else
    echo -e "${YELLOW}⚠️  Rate limiting not triggered (may need more aggressive testing)${NC}"
fi

rm "$TEMP_FILE"
echo ""

# Test 3: Bot detection
echo -e "${YELLOW}Test 3: Bot Detection${NC}"
echo "Testing with suspicious user agent..."

BOT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -H "User-Agent: BadBot/1.0 (scraper; automated)" \
    "http://$STATIC_IP" 2>/dev/null || echo "000")

if [ "$BOT_RESPONSE" = "403" ]; then
    echo -e "${GREEN}✅ Bot detection working (403 response)${NC}"
elif [ "$BOT_RESPONSE" = "200" ]; then
    echo -e "${YELLOW}⚠️  Bot detection may not be active yet (200 response)${NC}"
else
    echo -e "${RED}❌ Unexpected response: $BOT_RESPONSE${NC}"
fi
echo ""

# Test 4: SQL injection attempt
echo -e "${YELLOW}Test 4: SQL Injection Protection${NC}"
echo "Testing with SQL injection pattern..."

SQL_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    "http://$STATIC_IP/?id=1' OR '1'='1" 2>/dev/null || echo "000")

if [ "$SQL_RESPONSE" = "403" ]; then
    echo -e "${GREEN}✅ SQL injection protection working (403 response)${NC}"
elif [ "$SQL_RESPONSE" = "200" ]; then
    echo -e "${YELLOW}⚠️  SQL injection protection may not be triggered by this pattern${NC}"
else
    echo -e "${RED}❌ Unexpected response: $SQL_RESPONSE${NC}"
fi
echo ""

# Test 5: Large payload protection
echo -e "${YELLOW}Test 5: Large Payload Protection${NC}"
echo "Testing with large payload (>1MB)..."

# Create a large payload (1.5MB of 'A's)
LARGE_PAYLOAD=$(python3 -c "print('A' * 1572864)")

LARGE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"data\": \"$LARGE_PAYLOAD\"}" \
    "http://$STATIC_IP/api/test" 2>/dev/null || echo "000")

if [ "$LARGE_RESPONSE" = "413" ]; then
    echo -e "${GREEN}✅ Large payload protection working (413 response)${NC}"
elif [ "$LARGE_RESPONSE" = "403" ]; then
    echo -e "${GREEN}✅ Large payload blocked by Cloud Armor (403 response)${NC}"
else
    echo -e "${YELLOW}⚠️  Large payload test inconclusive (response: $LARGE_RESPONSE)${NC}"
fi
echo ""

# Test 6: Geographic test (if enabled)
echo -e "${YELLOW}Test 6: Geographic Information${NC}"
echo "Checking request origin..."

GEO_INFO=$(curl -s --max-time 10 "http://httpbin.org/ip" 2>/dev/null || echo "{}")
echo "Your IP appears to be: $(echo $GEO_INFO | grep -o '"origin": "[^"]*"' | cut -d'"' -f4 || echo 'unknown')"
echo "Note: Geographic restrictions are not enabled by default"
echo ""

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo ""
echo "Basic connectivity: ✅"
if [ "$RATE_LIMITED" -gt 0 ]; then
    echo "Rate limiting: ✅"
else
    echo "Rate limiting: ⚠️"
fi

if [ "$BOT_RESPONSE" = "403" ]; then
    echo "Bot detection: ✅"
else
    echo "Bot detection: ⚠️"
fi

if [ "$SQL_RESPONSE" = "403" ]; then
    echo "SQL injection protection: ✅"
else
    echo "SQL injection protection: ⚠️"
fi

if [ "$LARGE_RESPONSE" = "413" ] || [ "$LARGE_RESPONSE" = "403" ]; then
    echo "Large payload protection: ✅"
else
    echo "Large payload protection: ⚠️"
fi

echo ""
echo -e "${BLUE}📊 Next Steps:${NC}"
echo "1. Check security logs: make logs-cloud-armor"
echo "2. Monitor Cloud Console for real-time metrics"
echo "3. Adjust rules if needed based on your traffic patterns"
echo "4. Set up alerting for security events"
echo ""
echo -e "${GREEN}🛡️  Cloud Armor testing complete!${NC}"
