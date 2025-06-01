(One time setup, documenting for posterity)
# Custom Domain Setup Guide

This guide walks you through setting up a custom domain for your Atlas frontend service deployed on Google Cloud Run.

## Overview

Instead of using the default Cloud Run URL (`https://atlas-frontend-290750569862.us-central1.run.app`), you can serve your frontend from a custom domain like `nyc-monitor.app`.

## Prerequisites

1. **Own a domain** - Purchase from any registrar (Google Domains, Namecheap, GoDaddy, etc.)
2. **Google Cloud Project** - With Cloud Run service already deployed
3. **Domain verification** - Complete Google Search Console verification only

## Recommended Domain Options

### Best Options:
- `nyc-monitor.app` - Clean, professional, secure by default
- `nycmonitor.app` - Shorter variant
- `atlas-nyc.app` - Branded option
- `nycwatch.app` - Alternative monitoring focus

### Why .app domains are great:
- HTTPS enforced by default
- Professional appearance
- Reasonably priced
- Google-owned TLD with good performance

## Step-by-Step Setup

### 1. Purchase Your Domain

Choose a domain registrar and purchase your preferred domain (e.g., `nyc-monitor.app`).

### 2. Verify Domain Ownership (Google Search Console Only)

**NEW: App Engine verification is no longer required!**

#### Google Search Console:
1. Go to [Google Search Console](https://search.google.com/search-console)
2. Add your domain as a property
3. Verify ownership using one of the provided methods:
   - **DNS TXT record** (recommended - add TXT record to your domain's DNS)
   - **HTML file upload** (upload verification file to your website)
   - **Google Analytics** (if you have GA on your site)
   - **Google Tag Manager** (if you use GTM)

**That's it!** No App Engine setup required.

### 3. Configure Environment

Add your domain to your `.env` file:

```bash
# Add to your .env file
CUSTOM_DOMAIN=nyc-monitor.app
```

### 4. Run Domain Setup

Use our automated setup script:

```bash
# Use the new direct method (recommended)
make setup-domain-direct
```

check domain mapping, and required dns configuration

```bash
gcloud alpha run domain-mappings describe --domain=nyc-monitor.app --region=us-central1 --format="value(status.resourceRecords[].rrdata)" | head -4
```

### 5. Configure DNS Records

The setup script will display DNS records like:

```
DOMAIN          TYPE    VALUE
nyc-monitor.app CNAME   ghs.googlehosted.com
```

#### In your domain registrar's DNS settings:
1. Add a CNAME record pointing your domain to the provided value
2. If using a subdomain (like `app.nyc-monitor.com`), create:
   - Type: CNAME
   - Name: app (or whatever subdomain you want)
   - Value: ghs.googlehosted.com

### 6. Wait for DNS Propagation

- DNS changes can take up to 48 hours to propagate globally
- Usually happens within 5 minutes to 2 hours
- You can check status with `dig your-domain.com` or online DNS checkers

### 7. Verify Setup

Check your domain mapping status:

```bash
make check-domain
```

Or test directly:
```bash
curl -I https://your-domain.com
```

## SSL Certificate

Google Cloud automatically provisions and manages SSL certificates for your custom domain. The certificate will be issued once:
1. Domain mapping is created
2. DNS records are properly configured
3. DNS has propagated

## Traffic Routing

Once configured, all traffic will flow through your custom domain:

1. **User visits** `https://nyc-monitor.app`
2. **DNS resolves** to Google's load balancer
3. **Google routes** to your Cloud Run service
4. **Cloud Run serves** your frontend application

## Useful Commands

```bash
# Set up domain mapping (NEW DIRECT METHOD)
make setup-domain-direct

# Alternative method (may require App Engine)
make setup-domain

# Check domain status
make check-domain

# List all domain mappings
make list-domains

# Remove domain mapping
make remove-domain

# Manual gcloud commands
gcloud run domain-mappings list --region=us-central1 --platform=managed
gcloud run domain-mappings describe YOUR_DOMAIN --region=us-central1 --platform=managed
```

## Troubleshooting

### Common Issues:

#### 1. "Domain not verified" error
- Complete verification in Google Search Console
- ~~No longer need App Engine verification~~

#### 2. "SSL certificate pending"
- Wait for DNS propagation
- Check DNS records are correctly configured
- Can take up to 24 hours

#### 3. "Domain not found" in DNS
- Verify DNS records were added correctly
- Check for typos in domain name
- Wait for DNS propagation

#### 4. 404 errors on custom domain
- Check Cloud Run service is running
- Verify domain mapping points to correct service
- Check nginx configuration

#### 5. App Engine errors in console
- **Skip App Engine entirely** - use `make setup-domain-direct`
- App Engine is no longer required for Cloud Run domain mapping

### Checking DNS Propagation:

```bash
# Check DNS resolution
dig your-domain.com

# Check from different locations
nslookup your-domain.com 8.8.8.8

# Test your domain
curl -I https://your-domain.com
```

## Security Considerations

1. **HTTPS Only** - .app domains enforce HTTPS
2. **SSL Certificate** - Automatically managed by Google
3. **Security Headers** - Enhanced in nginx.conf
4. **CSP Policy** - Content Security Policy configured

## Cost Considerations

- **Domain purchase**: $10-50/year depending on TLD
- **Google Cloud**: No additional cost for domain mapping
- **SSL Certificate**: Free (Google-managed)

## Multiple Domains/Subdomains

You can map multiple domains to the same service:

```bash
# Map different domains
CUSTOM_DOMAIN=nyc-monitor.app make setup-domain-direct
CUSTOM_DOMAIN=app.nyc-monitor.com make setup-domain-direct
```

## Production Deployment

After domain setup, deploy normally:

```bash
make deploy-frontend
```

Your service will be accessible via both:
- Original Cloud Run URL (still works)
- Your custom domain (new primary access)

## What Changed in 2024

**OLD METHOD (still works but complex):**
- Required App Engine application
- Needed verification in both Search Console AND App Engine
- Often had console errors

**NEW METHOD (recommended):**
- Only requires Google Search Console verification
- Direct Cloud Run domain mapping
- No App Engine required
- Simpler, more reliable

## Monitoring

Monitor your custom domain in:
- [Google Cloud Console](https://console.cloud.google.com/run)
- [Google Search Console](https://search.google.com/search-console)
- Domain registrar analytics 

## Authentication Configuration Updates

After setting up your custom domain, you need to update authentication configurations:

### 1. Google OAuth Console

**Most Important**: Update your Google OAuth credentials:

1. Go to [Google Cloud Console OAuth Credentials](https://console.cloud.google.com/apis/credentials)
2. Find your OAuth 2.0 Client ID (starts with your project number)
3. Click to edit it
4. Add to **"Authorized JavaScript origins"**:
   - `https://nyc-monitor.app` (or your custom domain)
5. Add to **"Authorized redirect URIs"** (if needed):
   - `https://nyc-monitor.app`
   - `https://nyc-monitor.app/login`

### 2. Backend Configuration

The backend CORS settings have been updated to include your custom domain. After domain setup, redeploy the backend:

```bash
make deploy-backend-api
```

### 3. Frontend Configuration  

The nginx configuration includes API proxying to your backend. After domain setup, redeploy the frontend:

```bash
make deploy-frontend
```

### 4. Testing Authentication

After DNS propagation and redeployment:

1. Visit `https://nyc-monitor.app`
2. Try logging in with Google OAuth
3. Verify API calls work properly

If authentication fails, check:
- Google OAuth console configuration
- Browser developer tools for CORS errors
- Backend logs for authentication errors 