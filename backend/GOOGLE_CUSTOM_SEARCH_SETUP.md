# Google Custom Search API Setup Guide

## 🎯 **Overview**
This guide helps you set up Google Custom Search API as a fallback for **both web search and image search** when DuckDuckGo is rate limited.

**What Google Custom Search Replaces:**
- **General web search** (`ddgs.text()` and `ddgs.news()`) - finds web pages, articles, news
- **Image search** (`ddgs.images()`) - finds and downloads images from the web
- **Complete evidence collection** - screenshots of web pages + image downloads

**Benefits:**
- 100 free searches per day (covers both web + image searches)
- High-quality Google results for both content types
- Reliable Google infrastructure
- Automatic fallback when DuckDuckGo fails

---

## 🔧 **Step 1: Enable Google Custom Search API**

### A. Go to Google Cloud Console
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `atlas-460522`
3. Go to **APIs & Services** → **Library**

### B. Enable the API
1. Search for **"Custom Search API"**
2. Click on **"Custom Search API"**
3. Click **"Enable"**

---

## 🔑 **Step 2: Create API Key**

### A. Create Credentials
1. Go to **APIs & Services** → **Credentials**
2. Click **"+ Create Credentials"** → **"API Key"**
3. Copy the generated API key
4. **Save it as**: `GOOGLE_CUSTOM_SEARCH_API_KEY`

### B. Restrict API Key (Recommended)
1. Click the **Edit** button (pencil icon) next to your API key
2. Under **"API restrictions"**, select **"Restrict key"**
3. Choose **"Custom Search API"**
4. Click **"Save"**

---

## 🔍 **Step 3: Create Custom Search Engine**

### A. Access Custom Search Console
1. Go to [Google Custom Search](https://cse.google.com/cse/)
2. Click **"Add"** or **"New search engine"**

### B. Configure Search Engine
1. **Sites to search**: Enter `*` (asterisk to search entire web)
2. **Language**: English
3. **Name**: `Atlas Investigation Search`
4. Click **"Create"**

### C. Enable Both Web and Image Search
1. In your new search engine, click **"Setup"**
2. Turn **ON** "Image search" (for image fallback)
3. Turn **ON** "SafeSearch" (optional, for content filtering)
4. Under **"Advanced"**, you can also:
   - Set region to "United States"
   - Adjust other preferences

**Important:** The same search engine handles **both web pages AND images** - no separate setup needed!

### D. Get Search Engine ID
1. In the **"Setup"** tab, find **"Search engine ID"**
2. Copy the ID (looks like: `a1b2c3d4e5f6g7h8i`)
3. **Save it as**: `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`

---

## 🌍 **Step 4: Add Environment Variables**

Add these to your `.env` file:

```bash
# Google Custom Search API (Fallback for image search)
GOOGLE_CUSTOM_SEARCH_API_KEY=your_api_key_here
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_search_engine_id_here
```

**Example:**
```bash
GOOGLE_CUSTOM_SEARCH_API_KEY=AIzaSyBvOkBw28qvp2b1puRhHGMHD5uIefbIgOo
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=a1b2c3d4e5f6g7h8i
```

---

## 🧪 **Step 5: Test the Setup**

Run the test script to verify everything works:

```bash
cd backend
poetry run python test_google_search_fallback.py
```

**Expected output:**
```
🚀 Google Custom Search Fallback Test
============================================================
🔍 Testing Google Custom Search Fallback
============================================================
📋 Configuration Check:
   API Key: ✅ Set
   Engine ID: ✅ Set

🔍 Testing Google Custom Search...
✅ Search completed successfully!
   Results found: 3
   1. Protest in NYC - Manhattan demonstration...
      URL: https://example.com/image1.jpg...
      Source: nytimes.com

🔄 Testing Fallback Mechanism
============================================================
🔍 Testing fallback search for 'Manhattan protest'...
✅ Fallback search completed!
   Results found: 3

📊 Test Summary:
   Configuration: ✅ PASS
   Fallback Mechanism: ✅ PASS

🎉 All tests passed! Google Custom Search fallback is ready.
```

---

## 📊 **How the Fallback Works**

### **Two Separate Fallback Systems:**

#### **1. Web Search Fallback (`web_search_func`):**
**Search Priority Order:**
1. **DuckDuckGo Text Search** (`ddgs.text()`) - Primary
2. **DuckDuckGo News Search** (`ddgs.news()`) - For news-specific queries  
3. **Google Custom Search Web** - Fallback for both text and news
4. **Mock Results** - Last resort for testing

**What Gets Collected:**
- Web page URLs, titles, snippets
- Screenshots of found web pages
- Related images from the web pages

#### **2. Image Search Fallback (`collect_media_content_func`):**
**Search Priority Order:**
1. **DuckDuckGo Image Search** (`ddgs.images()`) - Primary
2. **Google Custom Search Images** - Fallback  
3. **Mock Images** - Last resort for testing

**What Gets Collected:**
- Direct image URLs and downloads
- Images saved to Google Cloud Storage
- Image metadata (dimensions, source, etc.)

### **Automatic Fallback Triggers:**
- DuckDuckGo returns HTTP 403 (rate limit)
- DuckDuckGo returns HTTP 202 (rate limit)
- DuckDuckGo throws any exception
- DuckDuckGo returns no results

### **Usage Limits:**
- **Google Custom Search**: 100 searches per day total (shared between web + image searches)
- **DuckDuckGo**: No official limit, but rate limiting occurs

### **Investigation Workflow:**
1. **Agent calls `web_search_func`** → Finds relevant web pages
2. **System takes screenshots** of found pages  
3. **Agent calls `collect_media_content_func`** → Downloads related images
4. **All artifacts saved** to investigation for report generation

---

## 🔧 **Step 6: Test with Full Investigation**

Run a full investigation test to see the fallback in action:

```bash
cd backend
poetry run python rag/test_investigation.py
```

**Look for these log messages:**
```
# Web Search Fallback:
🔍 DuckDuckGo found 5 text results for: Manhattan protest  
🔄 Falling back to Google Custom Search web for: Manhattan protest
✅ Google Custom Search web fallback found 3 results

# Image Search Fallback:
🔍 DuckDuckGo found 3 images for: No Kings protest
🔄 Falling back to Google Custom Search for: Manhattan protest  
✅ Google Custom Search fallback found 3 images

# Complete Investigation:
✅ Web search: 8 results found (5 DDG + 3 Google fallback)
✅ Screenshots: 3 web pages captured
✅ Images: 6 images downloaded and saved to GCS
✅ Report generation: All artifacts available for slides
```

---

## 🚨 **Troubleshooting**

### Common Issues:

#### 1. "API key not valid" error
- **Check**: API key is correctly copied
- **Fix**: Regenerate API key in Google Cloud Console
- **Verify**: API key restrictions allow Custom Search API

#### 2. "Invalid search engine ID" error
- **Check**: Search engine ID is correctly copied
- **Fix**: Verify the ID in Custom Search console
- **Ensure**: Search engine is set to search entire web (`*`)

#### 3. "Quota exceeded" error
- **Issue**: Used more than 100 searches today
- **Solution**: Wait until next day or upgrade to paid plan
- **Monitor**: Check usage in Google Cloud Console

#### 4. No image search results
- **Check**: Image search is enabled in Custom Search engine
- **Verify**: Search engine is set to search entire web
- **Test**: Try the search manually at cse.google.com

### Debug Commands:
```bash
# Check environment variables
echo $GOOGLE_CUSTOM_SEARCH_API_KEY
echo $GOOGLE_CUSTOM_SEARCH_ENGINE_ID

# Test API directly
curl "https://www.googleapis.com/customsearch/v1?key=YOUR_API_KEY&cx=YOUR_ENGINE_ID&q=test&searchType=image"
```

---

## 💰 **Cost Information**

### Free Tier:
- **100 searches per day** - completely free
- **No credit card required**
- **Resets daily at midnight Pacific Time**

### Paid Tier (if needed):
- **$5 per 1,000 additional queries**
- **Maximum 10,000 queries per day**
- **Only charged for usage above free tier**

For Atlas investigation system, 100 searches/day should be sufficient for most use cases.

---

## ✅ **Verification Checklist**

- [ ] Custom Search API enabled in Google Cloud Console
- [ ] API key created and restricted to Custom Search API
- [ ] Custom Search Engine created with `*` for entire web search
- [ ] Image search enabled in Custom Search Engine
- [ ] Environment variables added to `.env` file
- [ ] Test script runs successfully
- [ ] Full investigation test shows fallback working
- [ ] Log messages confirm Google Custom Search is being used when DuckDuckGo fails

---

**🎉 Once complete, your Atlas system will have reliable image search with automatic fallback!** 