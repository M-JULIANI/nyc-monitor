# Cloud Armor Security Setup for Atlas

This guide walks you through setting up Google Cloud Armor protection for your Atlas frontend service.

## Overview

Cloud Armor provides advanced DDoS protection, Web Application Firewall (WAF) capabilities, and bot management for your applications. For Atlas, we're applying it to the frontend service since:

- Users only access the frontend directly
- The frontend proxies all API calls to the backend 
- Your backend already has application-level rate limiting
- Protecting the frontend covers both services

## What's Protected

Our Cloud Armor setup provides:

### 🛡️ DDoS Protection
- Automatic detection and mitigation of volumetric attacks
- Protection against layer 3, 4, and 7 attacks
- Google's global anycast network absorption

### 🚦 Rate Limiting
- **General traffic**: 100 requests per minute per IP
- **API endpoints**: 30 requests per minute per IP (stricter)
- Temporary bans for violators (5-10 minutes)

### 🤖 Bot Protection
- Blocks malicious bots, scrapers, and automated tools
- Allows legitimate crawlers (Googlebot, Bingbot, etc.)
- Detects headless browsers and automation frameworks

### 🔒 Application Security
- SQL injection protection
- Cross-site scripting (XSS) protection  
- Protocol attack prevention
- Large payload protection (>1MB blocked)

## Setup Instructions

### Prerequisites

1. **Deployed Frontend Service**: Your frontend must be deployed to Cloud Run first
```bash
make deploy-web
```

2. **Environment Variables**: Ensure your `.env` file has:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
DOCKER_IMAGE_PREFIX=atlas
```

### Step 1: Run Cloud Armor Setup

```bash
# Set up Cloud Armor protection
make setup-cloud-armor
```

This will:
- Create a Cloud Armor security policy
- Set up a Global Load Balancer
- Configure rate limiting and security rules
- Reserve a static IP address
- Optionally set up HTTPS with managed SSL certificates

### Step 2: Deploy with Protection (Alternative)

For new deployments, you can deploy and protect in one step:

```bash
# Deploy frontend with Cloud Armor protection
make deploy-web-secure
```

## Management Commands

### Check Status
```bash
# View Cloud Armor policy and rules
make check-cloud-armor
```

### View Security Logs
```bash
# See blocked requests and rate limiting events
make logs-cloud-armor
```

### Test Protection
```bash
# Test rate limiting and basic access
make test-cloud-armor
```

### Get Protected URLs
```bash
# Get your new static IP and URLs
make get-secure-frontend-url
```

## Architecture Changes

### Before Cloud Armor
```
User → Cloud Run Frontend (direct access)
     → Cloud Run Backend (via proxy)
```

### After Cloud Armor
```
User → Global Load Balancer → Cloud Armor → Cloud Run Frontend
                                          → Cloud Run Backend (via proxy)
```

## Custom Domain Setup

When running `make setup-cloud-armor`, you'll be prompted to set up HTTPS with a custom domain:

1. **During setup**: Enter your domain (e.g., `atlas.yourdomain.com`)
2. **DNS Configuration**: Add an A record pointing to the static IP
3. **SSL Certificate**: Google will automatically provision a managed certificate
4. **Wait time**: Certificate provisioning takes 10-60 minutes

### Manual DNS Setup
```bash
# Get your static IP
make get-secure-frontend-url

# Add this A record to your DNS:
# atlas.yourdomain.com → [static-ip-address]
```

## Security Rules Details

| Priority | Rule | Action | Description |
|----------|------|---------|-------------|
| 1000 | Rate Limit General | Ban 10min | 100 req/min per IP |
| 2000 | Rate Limit API | Ban 5min | 30 req/min per IP for API calls |
| 3000 | Bot Protection | Block | Malicious bots/scrapers |
| 5000 | SQLi/XSS | Block | SQL injection & XSS attacks |
| 6000 | Protocol Attacks | Block | Network protocol attacks |
| 7000 | Large Bodies | Block | Requests >1MB |

## Monitoring & Troubleshooting

### View Blocked Requests
```bash
make logs-cloud-armor
```

### Check Policy Status
```bash
make check-cloud-armor
```

### Common Issues

**Issue**: Static IP not accessible
- **Solution**: Wait 5-10 minutes for propagation, check firewall rules

**Issue**: SSL certificate not working  
- **Solution**: Verify DNS A record points to static IP, wait up to 60 minutes

**Issue**: Rate limiting too aggressive
- **Solution**: Modify rules in Cloud Console or via gcloud commands

### Customizing Rules

Edit security policy rules:
```bash
# Update rate limiting threshold
gcloud compute security-policies rules update 1000 \
    --security-policy="atlas-frontend-security-policy" \
    --rate-limit-threshold-count=200

# Add geographic restrictions
gcloud compute security-policies rules create 4000 \
    --security-policy="atlas-frontend-security-policy" \
    --action="deny-403" \
    --expression="origin.region_code == 'CN'" \
    --description="Block specific regions"
```

## Cost Considerations

Cloud Armor pricing (approximate):
- **Policy**: $1/month per policy
- **Rules**: $1/month per rule (first 10 free)
- **Requests**: $0.75 per million requests
- **Global Load Balancer**: $18/month base + usage

For a typical Atlas deployment: ~$25-50/month depending on traffic.

## Cleanup

To remove Cloud Armor protection:

```bash
# Remove all Cloud Armor infrastructure
make remove-cloud-armor
```

**⚠️ Warning**: This removes ALL protection and reverts to direct Cloud Run access.

## Backend Protection (Optional)

Your backend already has application-level rate limiting via SlowAPI. If you need to add Cloud Armor to the backend for direct API access:

1. **Duplicate the setup script** for backend service
2. **Modify service names** in the script
3. **Apply stricter rules** for API-only traffic

However, this is usually unnecessary since users access backend through the protected frontend.

## Next Steps

After Cloud Armor is set up:

1. **Monitor logs** regularly with `make logs-cloud-armor`
2. **Adjust rules** based on traffic patterns
3. **Set up alerting** in Google Cloud Console
4. **Consider WAF custom rules** for application-specific threats
5. **Test disaster recovery** by temporarily disabling protection

For advanced configuration, see the [Google Cloud Armor documentation](https://cloud.google.com/armor/docs).
