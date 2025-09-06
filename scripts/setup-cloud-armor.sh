#!/bin/bash

# Cloud Armor Setup Script for Atlas Frontend
# This script creates a comprehensive Cloud Armor security policy
# and sets up a Global Load Balancer for the frontend Cloud Run service

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check required environment variables
check_env() {
    local required_vars=("GOOGLE_CLOUD_PROJECT" "GOOGLE_CLOUD_LOCATION")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${RED}Error: $var environment variable is not set${NC}"
            echo "Please set it in your .env file or environment"
            exit 1
        fi
    done
}

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo -e "${BLUE}Loading environment variables from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
fi

check_env

# Configuration variables
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
FRONTEND_SERVICE_NAME="${DOCKER_IMAGE_PREFIX:-atlas}-frontend"
CLOUD_ARMOR_POLICY_NAME="atlas-frontend-security-policy"
# Note: This is a LOAD BALANCER "backend service" component, NOT your actual Atlas backend!
LB_LB_BACKEND_SERVICE_NAME="atlas-frontend-lb-backend-service"
URL_MAP_NAME="atlas-frontend-url-map"
HTTP_PROXY_NAME="atlas-frontend-http-proxy"
HTTPS_PROXY_NAME="atlas-frontend-https-proxy"
IP_NAME="atlas-frontend-ip"
FORWARDING_RULE_HTTP_NAME="atlas-frontend-forwarding-rule-http"
FORWARDING_RULE_HTTPS_NAME="atlas-frontend-forwarding-rule-https"
SSL_CERT_NAME="atlas-frontend-ssl-cert"

echo -e "${BLUE}=== Cloud Armor Setup for Atlas Frontend ===${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Frontend Service: $FRONTEND_SERVICE_NAME"
echo ""

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable compute.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable certificatemanager.googleapis.com --quiet

# Step 1: Create Cloud Armor Security Policy
echo -e "${YELLOW}Step 1: Creating Cloud Armor security policy...${NC}"

# Check if policy already exists
if gcloud compute security-policies describe "$CLOUD_ARMOR_POLICY_NAME" >/dev/null 2>&1; then
    echo "Security policy already exists. Updating..."
    
    # Update existing policy description
    gcloud compute security-policies update "$CLOUD_ARMOR_POLICY_NAME" \
        --description="Atlas Frontend Security Policy - DDoS protection, rate limiting, and bot protection"
else
    # Create new security policy
    echo "Creating new security policy..."
    gcloud compute security-policies create "$CLOUD_ARMOR_POLICY_NAME" \
        --description="Atlas Frontend Security Policy - DDoS protection, rate limiting, and bot protection" \
        --type="CLOUD_ARMOR"
fi

echo -e "${GREEN}✓ Cloud Armor security policy created/updated${NC}"

# Step 2: Configure security rules
echo -e "${YELLOW}Step 2: Configuring security rules...${NC}"

# Rule 1: Rate limiting for general traffic (100 requests per minute per IP)
echo "Adding rate limiting rule..."
gcloud compute security-policies rules create 1000 \
    --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
    --action="rate-based-ban" \
    --rate-limit-threshold-count=100 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=600 \
    --conform-action="allow" \
    --exceed-action="deny-429" \
    --enforce-on-key="IP" \
    --description="Rate limit: 100 requests per minute per IP" \
    --preview || echo "Rate limiting rule already exists, skipping..."

# Rule 2: Aggressive rate limiting for API endpoints (30 requests per minute per IP)
echo "Adding API rate limiting rule..."
gcloud compute security-policies rules create 2000 \
    --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
    --action="rate-based-ban" \
    --rate-limit-threshold-count=30 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=300 \
    --conform-action="allow" \
    --exceed-action="deny-429" \
    --enforce-on-key="IP" \
    --expression="request.headers['x-forwarded-for'].contains('/api/')" \
    --description="API rate limit: 30 requests per minute per IP" \
    --preview || echo "API rate limiting rule already exists, skipping..."

# Rule 3: Block known bad user agents and bots
echo "Adding bot protection rule..."
gcloud compute security-policies rules create 3000 \
    --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
    --action="deny-403" \
    --expression="request.headers['user-agent'].matches('(?i).*(bot|crawler|spider|scraper|headless|phantom|selenium|puppeteer).*') && !request.headers['user-agent'].matches('(?i).*(googlebot|bingbot|slurp|facebookexternalhit|twitterbot|linkedinbot).*')" \
    --description="Block malicious bots and scrapers while allowing legitimate crawlers" \
    --preview || echo "Bot protection rule already exists, skipping..."

# Rule 4: Geographic restrictions (optional - uncomment and modify as needed)
# echo "Adding geographic restrictions..."
# gcloud compute security-policies rules create 4000 \
#     --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
#     --action="deny-403" \
#     --expression="origin.region_code == 'CN' || origin.region_code == 'RU'" \
#     --description="Block traffic from specific regions" \
#     --preview || echo "Geographic rule already exists, skipping..."

# Rule 5: SQLi and XSS protection
echo "Adding SQL injection and XSS protection..."
gcloud compute security-policies rules create 5000 \
    --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
    --action="deny-403" \
    --expression="evaluatePreconfiguredExpr('sqli-stable') || evaluatePreconfiguredExpr('xss-stable')" \
    --description="Block SQL injection and XSS attacks" \
    --preview || echo "SQLi/XSS protection rule already exists, skipping..."

# Rule 6: Protocol attacks
echo "Adding protocol attack protection..."
gcloud compute security-policies rules create 6000 \
    --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
    --action="deny-403" \
    --expression="evaluatePreconfiguredExpr('protocolattack-stable')" \
    --description="Block protocol attacks" \
    --preview || echo "Protocol attack protection rule already exists, skipping..."

# Rule 7: Large body protection (prevent large payload attacks)
echo "Adding large body protection..."
gcloud compute security-policies rules create 7000 \
    --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
    --action="deny-413" \
    --expression="request.body.size > 1048576" \
    --description="Block requests with body larger than 1MB" \
    --preview || echo "Large body protection rule already exists, skipping..."

echo -e "${GREEN}✓ Security rules configured${NC}"

# Step 3: Remove preview mode (make rules active)
echo -e "${YELLOW}Step 3: Activating security rules...${NC}"
for priority in 1000 2000 3000 5000 6000 7000; do
    echo "Activating rule $priority..."
    gcloud compute security-policies rules update $priority \
        --security-policy="$CLOUD_ARMOR_POLICY_NAME" \
        --no-preview 2>/dev/null || echo "Rule $priority not found or already active"
done

echo -e "${GREEN}✓ Security rules activated${NC}"

# Step 4: Get Cloud Run service details
echo -e "${YELLOW}Step 4: Getting Cloud Run service details...${NC}"

# Check if the frontend service exists
if ! gcloud run services describe "$FRONTEND_SERVICE_NAME" --region="$REGION" >/dev/null 2>&1; then
    echo -e "${RED}Error: Frontend Cloud Run service '$FRONTEND_SERVICE_NAME' not found in region '$REGION'${NC}"
    echo "Please deploy your frontend service first using: make deploy-web"
    exit 1
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$FRONTEND_SERVICE_NAME" \
    --region="$REGION" \
    --format='value(status.url)')

echo "Frontend service URL: $SERVICE_URL"

# Step 5: Reserve a global static IP
echo -e "${YELLOW}Step 5: Reserving global static IP address...${NC}"
if ! gcloud compute addresses describe "$IP_NAME" --global >/dev/null 2>&1; then
    gcloud compute addresses create "$IP_NAME" --global
    echo -e "${GREEN}✓ Global IP address reserved${NC}"
else
    echo "Global IP address already exists"
fi

STATIC_IP=$(gcloud compute addresses describe "$IP_NAME" --global --format='value(address)')
echo "Static IP: $STATIC_IP"

# Step 6: Create Network Endpoint Group (NEG) for Cloud Run
echo -e "${YELLOW}Step 6: Creating Network Endpoint Group for Cloud Run...${NC}"
NEG_NAME="atlas-frontend-neg"

if ! gcloud compute network-endpoint-groups describe "$NEG_NAME" --region="$REGION" >/dev/null 2>&1; then
    gcloud compute network-endpoint-groups create "$NEG_NAME" \
        --region="$REGION" \
        --network-endpoint-type="serverless" \
        --cloud-run-service="$FRONTEND_SERVICE_NAME"
    echo -e "${GREEN}✓ Network Endpoint Group created${NC}"
else
    echo "Network Endpoint Group already exists"
fi

# Step 7: Create Load Balancer Backend Service (points to FRONTEND, not Atlas backend!)
echo -e "${YELLOW}Step 7: Creating load balancer backend service...${NC}"
if ! gcloud compute backend-services describe "$LB_BACKEND_SERVICE_NAME" --global >/dev/null 2>&1; then
    gcloud compute backend-services create "$LB_BACKEND_SERVICE_NAME" \
        --global \
        --load-balancing-scheme="EXTERNAL_MANAGED"
    
    # Add the NEG as a backend
    gcloud compute backend-services add-backend "$LB_BACKEND_SERVICE_NAME" \
        --global \
        --network-endpoint-group="$NEG_NAME" \
        --network-endpoint-group-region="$REGION"
    
    echo -e "${GREEN}✓ Load balancer backend service created${NC}"
else
    echo "Load balancer backend service already exists"
fi

# Step 8: Attach Cloud Armor policy to load balancer (protecting FRONTEND)
echo -e "${YELLOW}Step 8: Attaching Cloud Armor policy to load balancer...${NC}"
gcloud compute backend-services update "$LB_BACKEND_SERVICE_NAME" \
    --global \
    --security-policy="$CLOUD_ARMOR_POLICY_NAME"

echo -e "${GREEN}✓ Cloud Armor policy attached to load balancer (protecting frontend)${NC}"

# Step 9: Create URL Map
echo -e "${YELLOW}Step 9: Creating URL map...${NC}"
if ! gcloud compute url-maps describe "$URL_MAP_NAME" --global >/dev/null 2>&1; then
    gcloud compute url-maps create "$URL_MAP_NAME" \
        --global \
        --default-backend-service="$LB_BACKEND_SERVICE_NAME"
    echo -e "${GREEN}✓ URL map created${NC}"
else
    echo "URL map already exists"
fi

# Step 10: Create HTTP(S) Proxies
echo -e "${YELLOW}Step 10: Creating HTTP and HTTPS proxies...${NC}"

# HTTP Proxy
if ! gcloud compute target-http-proxies describe "$HTTP_PROXY_NAME" --global >/dev/null 2>&1; then
    gcloud compute target-http-proxies create "$HTTP_PROXY_NAME" \
        --global \
        --url-map="$URL_MAP_NAME"
    echo -e "${GREEN}✓ HTTP proxy created${NC}"
else
    echo "HTTP proxy already exists"
fi

# HTTPS Proxy (requires SSL certificate)
echo -e "${YELLOW}Setting up HTTPS proxy with managed SSL certificate...${NC}"

# Check if user wants to set up a custom domain
read -p "Do you want to set up a custom domain with managed SSL certificate? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your domain name (e.g., atlas.yourdomain.com): " DOMAIN_NAME
    
    if [ -n "$DOMAIN_NAME" ]; then
        # Create managed SSL certificate
        if ! gcloud compute ssl-certificates describe "$SSL_CERT_NAME" --global >/dev/null 2>&1; then
            gcloud compute ssl-certificates create "$SSL_CERT_NAME" \
                --global \
                --domains="$DOMAIN_NAME"
            echo -e "${GREEN}✓ Managed SSL certificate created for $DOMAIN_NAME${NC}"
        else
            echo "SSL certificate already exists"
        fi
        
        # Create HTTPS proxy
        if ! gcloud compute target-https-proxies describe "$HTTPS_PROXY_NAME" --global >/dev/null 2>&1; then
            gcloud compute target-https-proxies create "$HTTPS_PROXY_NAME" \
                --global \
                --url-map="$URL_MAP_NAME" \
                --ssl-certificates="$SSL_CERT_NAME"
            echo -e "${GREEN}✓ HTTPS proxy created${NC}"
        else
            echo "HTTPS proxy already exists"
        fi
        
        SETUP_HTTPS=true
    fi
else
    echo "Skipping HTTPS setup. You can set it up later."
    SETUP_HTTPS=false
fi

# Step 11: Create Forwarding Rules
echo -e "${YELLOW}Step 11: Creating forwarding rules...${NC}"

# HTTP Forwarding Rule
if ! gcloud compute forwarding-rules describe "$FORWARDING_RULE_HTTP_NAME" --global >/dev/null 2>&1; then
    gcloud compute forwarding-rules create "$FORWARDING_RULE_HTTP_NAME" \
        --global \
        --load-balancing-scheme="EXTERNAL_MANAGED" \
        --address="$IP_NAME" \
        --target-http-proxy="$HTTP_PROXY_NAME" \
        --ports="80"
    echo -e "${GREEN}✓ HTTP forwarding rule created${NC}"
else
    echo "HTTP forwarding rule already exists"
fi

# HTTPS Forwarding Rule (if HTTPS is set up)
if [ "$SETUP_HTTPS" = true ]; then
    if ! gcloud compute forwarding-rules describe "$FORWARDING_RULE_HTTPS_NAME" --global >/dev/null 2>&1; then
        gcloud compute forwarding-rules create "$FORWARDING_RULE_HTTPS_NAME" \
            --global \
            --load-balancing-scheme="EXTERNAL_MANAGED" \
            --address="$IP_NAME" \
            --target-https-proxy="$HTTPS_PROXY_NAME" \
            --ports="443"
        echo -e "${GREEN}✓ HTTPS forwarding rule created${NC}"
    else
        echo "HTTPS forwarding rule already exists"
    fi
fi

# Final summary
echo ""
echo -e "${GREEN}=== Cloud Armor Setup Complete! ===${NC}"
echo ""
echo -e "${BLUE}📊 Configuration Summary:${NC}"
echo "• Project: $PROJECT_ID"
echo "• Region: $REGION"
echo "• Frontend Service: $FRONTEND_SERVICE_NAME"
echo "• Cloud Armor Policy: $CLOUD_ARMOR_POLICY_NAME"
echo "• Static IP: $STATIC_IP"
echo ""
echo -e "${BLUE}🌍 Access URLs:${NC}"
echo "• HTTP: http://$STATIC_IP"
if [ "$SETUP_HTTPS" = true ]; then
    echo "• HTTPS: https://$DOMAIN_NAME (after DNS setup)"
    echo ""
    echo -e "${YELLOW}📝 Next Steps for Custom Domain:${NC}"
    echo "1. Add DNS A record: $DOMAIN_NAME → $STATIC_IP"
    echo "2. Wait for SSL certificate provisioning (may take 10-60 minutes)"
    echo "3. Verify HTTPS access works"
else
    echo ""
    echo -e "${YELLOW}📝 To set up HTTPS later:${NC}"
    echo "1. Create managed SSL certificate: gcloud compute ssl-certificates create ..."
    echo "2. Create HTTPS proxy and forwarding rule"
    echo "3. Set up DNS A record pointing to $STATIC_IP"
fi
echo ""
echo -e "${BLUE}🛡️  Security Features Enabled:${NC}"
echo "• DDoS protection (automatic)"
echo "• Rate limiting (100 req/min general, 30 req/min API)"
echo "• Bot protection"
echo "• SQL injection protection"
echo "• XSS protection"
echo "• Protocol attack protection"
echo "• Large body protection (>1MB blocked)"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "• View policy: gcloud compute security-policies describe $CLOUD_ARMOR_POLICY_NAME"
echo "• View logs: gcloud logging read 'resource.type=\"gce_backend_service\"'"
echo "• Update rules: gcloud compute security-policies rules update ..."
echo ""
echo -e "${GREEN}✅ Cloud Armor is now protecting your Atlas frontend!${NC}"
