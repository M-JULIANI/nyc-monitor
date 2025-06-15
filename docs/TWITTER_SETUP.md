# Twitter Collector Setup Guide

This guide explains how to set up the Twitter collector for the NYC monitoring system.

## Prerequisites

You need Twitter Developer access with API keys. If you already have these credentials, skip to the [Configuration](#configuration) section.

## Getting Twitter API Access

### Step 1: Apply for Twitter Developer Account

1. **Go to Twitter Developer Portal**: Visit [developer.twitter.com](https://developer.twitter.com)
2. **Sign in** with your Twitter account
3. **Apply for a developer account**:
   - Select your use case (e.g., "Academic research", "Building tools for Twitter users")
   - Describe your intended use: "Monitoring NYC emergency and public event signals for community safety"
   - Complete the application form

### Step 2: Create a Twitter App

1. **Navigate to the Developer Portal Dashboard**
2. **Create a new App**:
   - App name: "NYC Monitor" (or similar)
   - Description: "Emergency and event monitoring system for NYC"
   - Website URL: Your project URL or placeholder
   - Use case: Emergency monitoring and public safety

3. **Configure App Permissions**:
   - Set to "Read" (we only need to read tweets)
   - No write permissions needed

### Step 3: Generate API Keys

In your app dashboard:

1. **Go to "Keys and Tokens" tab**
2. **Generate/Copy these credentials**:
   - API Key (Consumer Key)
   - API Key Secret (Consumer Secret)  
   - Bearer Token

⚠️ **Important**: Save these credentials securely - you won't be able to see the secrets again.

## Configuration

### Environment Variables

Set these environment variables in your system or `.env` file:

```bash
# Twitter API Credentials
TWITTER_API_KEY="your_api_key_here"
TWITTER_API_KEY_SECRET="your_api_key_secret_here"
TWITTER_BEARER_TOKEN="your_bearer_token_here"
```

### For Development

Create a `.env` file in your backend directory:

```bash
# backend/.env
TWITTER_API_KEY=AaBbCcDdEeFfGg123456789
TWITTER_API_KEY_SECRET=XxYyZzAaBbCcDdEeFfGg123456789XxYyZzAaBbCcDdEeFf
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAABearerTokenHere123456789
```

### For Production

Set environment variables in your deployment platform:

#### Google Cloud Run
```bash
gcloud run deploy nyc-monitor \
  --set-env-vars TWITTER_API_KEY="your_key" \
  --set-env-vars TWITTER_API_KEY_SECRET="your_secret" \
  --set-env-vars TWITTER_BEARER_TOKEN="your_token"
```

#### Docker
```bash
docker run -e TWITTER_API_KEY="your_key" \
           -e TWITTER_API_KEY_SECRET="your_secret" \
           -e TWITTER_BEARER_TOKEN="your_token" \
           your-app
```

## Testing the Twitter Collector

### Quick Test

Run the test script to verify your setup:

```bash
cd backend
python scripts/test_twitter_collector.py
```

### Expected Output

```
🚀 Starting Twitter collector test
🔧 Initializing Twitter collector...
🔑 TWITTER CREDENTIALS CHECK:
   API_KEY: ✅ SET (AaBbCcDdEe...)
   API_KEY_SECRET: ✅ SET ([REDACTED])
   BEARER_TOKEN: ✅ SET (AAAAAAAAAA...)
✅ Twitter collector initialized successfully
🔍 Testing signal collection...
🔍 Executing query 1/15: "911" "NYC" -is:retweet lang:en
✅ Processed 25 tweets from query 1
📊 COLLECTION SUMMARY: 45 unique Twitter signals collected
✅ Collection completed in 12.34 seconds
```

### Integration Test

Test the collector within the full monitor system:

```bash
cd backend
python scripts/test_integration_clean.py
```

## How the Twitter Collector Works

### Search Strategy

The Twitter collector uses targeted search queries:

1. **Emergency Keywords**: `911`, `emergency`, `fire`, `shooting`, `explosion`, `ambulance`, `police`
2. **Infrastructure Issues**: `power outage`, `blackout`, `gas leak`, `subway shutdown`
3. **Public Events**: `parade`, `festival`, `concert`, `marathon`, `protest`
4. **Location Filtering**: Combined with NYC location terms

### Example Search Queries

```
"911" "NYC" -is:retweet lang:en
"emergency" "Manhattan" -is:retweet lang:en
"power outage" (NYC OR "New York City" OR Manhattan) -is:retweet lang:en
"parade" (NYC OR "New York City") -is:retweet lang:en
```

### Rate Limiting

- **API Limits**: 300 requests per 15-minute window (Twitter v2)
- **Collector Limits**: 15 search queries, 25 tweets per query, 100 total tweets
- **Built-in Delays**: 1 second between queries, automatic rate limit handling

### Data Processing

1. **NYC Relevance Check**: Filters tweets for NYC-specific content
2. **Priority Detection**: Identifies emergency vs. event content
3. **Location Extraction**: Extracts NYC neighborhoods, streets, landmarks
4. **Geocoding**: Attempts to get coordinates for location references
5. **Engagement Scoring**: Calculates engagement based on retweets, likes, replies

## Troubleshooting

### Common Issues

#### ❌ "Missing Twitter API credentials"

**Solution**: Check that all three environment variables are set:
```bash
echo $TWITTER_API_KEY
echo $TWITTER_API_KEY_SECRET
echo $TWITTER_BEARER_TOKEN
```

#### ❌ "401 Unauthorized"

**Solution**: 
- Verify your API keys are correct
- Check that your Twitter app has the right permissions
- Ensure your developer account is approved

#### ❌ "429 Rate Limit Exceeded"

**Solution**: 
- Wait for the rate limit window to reset (15 minutes)
- Reduce the number of search queries
- The collector has built-in rate limiting, but external testing can hit limits

#### ❌ "No Twitter signals collected"

**Possible causes**:
- All tweets filtered out due to lack of NYC relevance
- No recent tweets matching search criteria
- Overly restrictive location specificity filtering

**Solutions**:
- Check if there are recent NYC-related events
- Verify search queries are not too specific
- Review collector logs for filtering reasons

### Monitoring and Logs

The collector provides detailed logging:

```bash
# View collector logs
tail -f /tmp/monitor.log

# Search for Twitter-specific logs
grep "TWITTER" /tmp/monitor.log
```

### API Rate Limit Status

Check your current rate limit status:

```python
# Quick rate limit check script
import tweepy
import os

client = tweepy.Client(bearer_token=os.getenv("TWITTER_BEARER_TOKEN"))
rate_limit = client.get_rate_limit_status()
print(rate_limit)
```

## Configuration Options

### Adjusting Search Parameters

Edit `twitter_collector.py` to customize:

```python
# Search parameters
self.max_tweets_per_query = 25  # Tweets per search query
self.max_total_tweets = 100     # Total tweets across all queries  
self.time_window_hours = 2      # How far back to search
```

### Adding Custom Search Queries

Modify the `_build_search_queries()` method:

```python
# Add your custom queries
custom_queries = [
    '"your keyword" NYC -is:retweet lang:en',
    '"another term" Manhattan -is:retweet lang:en'
]
queries.extend(custom_queries)
```

### Emergency Keyword Customization

Update emergency detection in `base_collector.py`:

```python
# Add to PRIORITY_KEYWORDS list
PRIORITY_KEYWORDS = [
    # Your additional emergency terms
    'your_emergency_term', 'another_urgent_keyword',
    # ... existing keywords
]
```

## Twitter API Limitations

### Free Tier Limits

- **Monthly Tweets**: 10,000 tweets per month
- **Rate Limits**: 300 requests per 15 minutes
- **Search Window**: Last 7 days only
- **Real-time Streaming**: Not available

### Paid Tier Benefits (if needed)

- **Higher Limits**: Up to 2M tweets per month
- **Extended Search**: 30-day search window
- **Real-time Streaming**: Live tweet monitoring
- **Enhanced Filtering**: More advanced search operators

### Best Practices

1. **Optimize Search Queries**: Use specific, targeted searches
2. **Monitor Rate Limits**: Track API usage to avoid hitting limits
3. **Cache Results**: Store signals to avoid re-fetching
4. **Filter Aggressively**: Only collect relevant, actionable content
5. **Handle Errors Gracefully**: Continue operation if one query fails

## Support

If you encounter issues:

1. **Check Twitter Developer Documentation**: [developer.twitter.com/docs](https://developer.twitter.com/docs)
2. **Review Tweepy Documentation**: [docs.tweepy.org](https://docs.tweepy.org)
3. **Monitor API Status**: [api.twitterstat.us](https://api.twitterstat.us)
4. **Contact Twitter Support**: Through the Developer Portal

## Security Notes

⚠️ **Important Security Practices**:

- Never commit API keys to version control
- Use environment variables for all credentials
- Rotate API keys periodically
- Monitor API usage for unusual activity
- Use minimum required permissions (read-only)

---

✅ Once configured, the Twitter collector will automatically integrate with your NYC monitoring system and begin collecting relevant signals for triage analysis. 