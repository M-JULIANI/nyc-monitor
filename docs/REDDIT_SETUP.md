ONE TIME SETUP - ignore, documenting for posterity

# Reddit API Setup for Monitor System

The monitor system requires Reddit API credentials to collect data from NYC-related subreddits.

## Getting Reddit API Credentials

1. **Create a Reddit App**:
   - Go to https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - Choose "script" as the app type
   - Fill in the required fields:
     - Name: `atlas-monitor` (or any name you prefer)
     - Description: `NYC monitoring system`
     - Redirect URI: `http://localhost:8080` (required but not used)

2. **Get Your Credentials**:
   - **Client ID**: Found under the app name (short alphanumeric string)
   - **Client Secret**: The "secret" field (longer string)
   - **Refresh Token**: You'll need to generate this using OAuth2 flow

## Setting Up Environment Variables

### For Local Development

Create a `.env` file in the root directory:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
STAGING_BUCKET=gs://your-project-vertex-deploy
DOCKER_REGISTRY=us-central1-docker.pkg.dev/your-project-id/your-repo
DOCKER_IMAGE_PREFIX=atlas

# Reddit API Credentials
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_REFRESH_TOKEN=your_reddit_refresh_token
```

### For Cloud Deployment

The Makefile automatically reads from `.env` and sets these as environment variables in the Cloud Run job.

### For GitHub Actions (CI/CD)

Add these as repository secrets:
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_REFRESH_TOKEN`

Then modify the GitHub Actions workflow to pass them to the Cloud Run job.

## Getting a Refresh Token

To get a refresh token, you'll need to run an OAuth2 flow. **Good news: For "script" type Reddit apps, refresh tokens are typically permanent and don't expire!**

### Quick Setup:

1. **Create Reddit app and add credentials to .env:**
   ```bash
   # First, add your Reddit app credentials to .env file
   echo "REDDIT_CLIENT_ID=your_actual_client_id" >> .env
   echo "REDDIT_CLIENT_SECRET=your_actual_client_secret" >> .env
   ```

2. **Run the token script:**
   ```bash
   cd /workspaces/atlas-bootstrapped
   
   # Option 1: If you have poetry environment set up
   cd backend && poetry run python ../scripts/get_reddit_token.py
   
   # Option 2: If you have python-dotenv installed globally
   python scripts/get_reddit_token.py
   ```

3. **Follow the prompts:**
   - Open the URL in your browser
   - Authorize the app
   - Copy the `code` parameter from the redirect URL
   - Paste it into the script

4. **Add the refresh token to .env:**
   ```bash
   # The script will output this line for you to add:
   echo "REDDIT_REFRESH_TOKEN=your_generated_refresh_token" >> .env
   ```

### For Production:

**Refresh Token Persistence:** Reddit refresh tokens for "script" apps are designed to be long-lived and typically don't expire unless:
- You manually revoke the app
- Reddit suspends your account  
- You regenerate your app credentials

**This means you only need to run this script once** and can use the same refresh token for months/years.

## Testing Your Setup

After setting up the credentials:

```bash
# Test locally (if you have the dependencies installed)
cd backend
poetry run python -c "
from monitor.collectors.reddit_collector import RedditCollector
collector = RedditCollector()
print('✅ Reddit credentials configured correctly!')
"

# Test the deployed monitor system
make test-monitor
```

## Security Notes

- **Never commit credentials to git**
- Add `.env` to your `.gitignore` file
- Use Google Cloud Secret Manager for production deployments
- Regularly rotate your Reddit app credentials
- Use least-privilege principles for Reddit API access

## Troubleshooting

1. **"Missing Reddit API credentials" error**:
   - Verify your `.env` file has the correct variable names
   - Check that the values don't have extra spaces or quotes

2. **"401 Unauthorized" from Reddit API**:
   - Verify your client ID and secret are correct
   - Check that your refresh token hasn't expired
   - Make sure your Reddit app type is "script"

3. **"exec format error" in Cloud Run**:
   - This is a Docker platform issue, not Reddit-related
   - Make sure you're building with `--platform linux/amd64` 