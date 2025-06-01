#!/bin/bash

# Direct Custom Domain Setup for Cloud Run (No App Engine Required)
# Usage: ./scripts/setup-custom-domain-direct.sh your-domain.com

set -e

# Check if domain is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <your-domain>"
    echo "Example: $0 nyc-monitor.app"
    exit 1
fi

CUSTOM_DOMAIN="$1"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="atlas-frontend"

echo "🚀 Setting up custom domain (NEW METHOD - No App Engine required): $CUSTOM_DOMAIN"
echo "📍 Project: $PROJECT_ID"
echo "📍 Region: $REGION"
echo "📍 Service: $SERVICE_NAME"
echo ""

# Step 1: Check if the service exists
echo "🔍 Checking if Cloud Run service exists..."
if ! gcloud run services describe "$SERVICE_NAME" --region="$REGION" --platform=managed >/dev/null 2>&1; then
    echo "❌ Error: Cloud Run service '$SERVICE_NAME' not found in region '$REGION'"
    echo "Available services:"
    gcloud run services list --platform=managed --region="$REGION"
    exit 1
fi
echo "✅ Service found"

# Step 2: Domain verification via Search Console (Manual step)
echo ""
echo "⚠️  IMPORTANT: Domain verification via Google Search Console:"
echo "   1. Go to https://search.google.com/search-console"
echo "   2. Add your domain '$CUSTOM_DOMAIN' as a property"
echo "   3. Verify ownership using DNS TXT record or HTML file upload"
echo ""
read -p "Have you verified your domain in Google Search Console? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please complete domain verification in Google Search Console first."
    echo "This is the ONLY verification step needed (no App Engine required)."
    exit 1
fi

echo "🔗 Creating domain mapping directly..."

# Step 3: Create domain mapping directly (using alpha commands)
if gcloud alpha run domain-mappings describe --domain="$CUSTOM_DOMAIN" --region="$REGION" >/dev/null 2>&1; then
    echo "⚠️  Domain mapping already exists. Updating..."
    gcloud alpha run domain-mappings delete --domain="$CUSTOM_DOMAIN" --region="$REGION" --quiet
    sleep 2
fi

gcloud alpha run domain-mappings create \
    --service="$SERVICE_NAME" \
    --domain="$CUSTOM_DOMAIN" \
    --region="$REGION"

echo ""
echo "✅ Domain mapping created successfully!"
echo ""

# Step 4: Get DNS configuration
echo "🔍 Getting DNS configuration..."
sleep 3  # Wait for the mapping to be fully created

gcloud alpha run domain-mappings describe --domain="$CUSTOM_DOMAIN" \
    --region="$REGION" \
    --format="table(
        status.resourceRecords[].type:label='TYPE',
        status.resourceRecords[].rrdata:label='VALUE'
    )"

echo ""
echo "📝 Next Steps:"
echo "1. Configure DNS records with your domain registrar:"
echo "   - Add the A records shown above (use any one of the IP addresses)"
echo "   - Point your domain to one of the provided IP addresses"
echo ""
echo "2. Wait for DNS propagation (usually 5 minutes to 2 hours)"
echo ""
echo "3. Check status with:"
echo "   make check-domain"
echo "   or: gcloud alpha run domain-mappings describe --domain=$CUSTOM_DOMAIN --region=$REGION"
echo ""
echo "4. Test your domain:"
echo "   curl -I https://$CUSTOM_DOMAIN"
echo ""
echo "🌐 Once DNS propagates, your app will be available at:"
echo "   https://$CUSTOM_DOMAIN"
echo ""
echo "🔒 SSL certificate will be automatically provisioned by Google Cloud" 