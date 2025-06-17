# Google Slides & Drive Integration Setup Guide

## 🚀 **UPDATED - Simplified Setup!**

**✅ Changes Made:**
1. **Removed `SERVICE_ACCOUNT_KEY_PATH`** - Now uses same Google Cloud credentials as other services
2. **Enhanced image placeholders** - Agents can now insert actual collected images into slides  
3. **Simplified CI/CD** - Just add `GOOGLE_DRIVE_FOLDER_ID` and `STATUS_TRACKER_TEMPLATE_ID` as GitHub secrets

**🎯 Key Benefits:**
- **Consistent credential management** across all services
- **Automatic image insertion** from agent-collected evidence (screenshots, photos, etc.)
- **Professional 2x2 grid layout** with captions for evidence images
- **No separate service account files** to manage

---

This guide walks you through setting up Google Slides and Drive integration for the NYC Atlas Investigation System to automatically generate professional reports.

## 🎯 **Overview**

The system will:
- ✅ **Create presentations** from Google Slides templates
- ✅ **Auto-populate** with investigation data and evidence
- ✅ **Include screenshots and images** from evidence collection
- ✅ **Share publicly** for easy demonstration access
- ✅ **Use Status Tracker template** from Google Slides template gallery

## 🛠️ **Step 1: Create Google Cloud Service Account**

### 1.1 Google Cloud Console Setup
```bash
# 1. Go to Google Cloud Console
https://console.cloud.google.com/

# 2. Select your project (atlas-460522)
# 3. Navigate to: IAM & Admin > Service Accounts
# 4. Click "Create Service Account"
```

### 1.2 Service Account Configuration
```
Service Account Details:
- Name: atlas-reports-service
- Description: Service account for NYC Atlas investigation report generation
- Service Account ID: atlas-reports-service@atlas-460522.iam.gserviceaccount.com
```

### 1.3 Download Credentials
```bash
# 1. Click on the created service account
# 2. Go to "Keys" tab
# 3. Click "Add Key" > "Create New Key"
# 4. Choose "JSON" format
# 5. Download the JSON file
# 6. Save as: /path/to/atlas-service-account.json
```

## 📁 **Step 2: Create Public Google Drive Folder**

### 2.1 Create Folder Structure
```
📁 NYC Atlas Investigation Reports (Public)
├── 📁 Templates/
│   └── 📄 Atlas Status Tracker Template
├── 📁 Active Investigations/
├── 📁 Evidence/
└── 📁 Archive/
```

### 2.2 Share with Service Account
```bash
# 1. Right-click folder > Share
# 2. Add service account email: atlas-reports-service@atlas-460522.iam.gserviceaccount.com
# 3. Set permission: Editor
# 4. Click "Share"
```

### 2.3 Make Folder Public (for viewing)
```bash
# 1. Right-click folder > Share
# 2. Click "Change to anyone with the link"
# 3. Set permission: Viewer
# 4. Copy folder link/ID
```

## 📊 **Step 3: Create Status Tracker Template**

### 3.1 From Google Slides Template Gallery
```bash
# 1. Go to Google Slides: https://slides.google.com/
# 2. Click "Template Gallery" 
# 3. Search for "Status Tracker" or "Project Status"
# 4. Select a professional template
# 5. Click "Use Template"
```

### 3.2 Customize Template with Placeholders
Replace content with these placeholders:
```
Title Slide:
- {{investigation_title}}
- {{timestamp}}

Executive Summary:
- Alert Location: {{alert_location}}
- Severity: {{alert_severity}}
- Status: {{status}}
- Confidence: {{confidence_score}}

Key Findings:
- {{findings_summary}}

Evidence Summary:
- Evidence Items: {{evidence_count}}
- Types Found: {{evidence_types}}
- High Relevance: {{high_relevance_count}}

Investigation Details:
- Investigation ID: {{investigation_id}}
- Phase: {{phase}}
- Iteration: {{iteration_count}}
```

### 3.3 Save Template to Shared Folder
```bash
# 1. File > Move to > Select your shared folder/Templates/
# 2. Rename to: "Atlas Investigation Status Tracker Template"
# 3. Copy the presentation ID from URL
```

## 🔧 **Step 4: Configure Environment Variables**

### 4.1 Add to .env file (for local development)
```bash
# Google Slides & Drive Configuration
GOOGLE_DRIVE_FOLDER_ID="1234567890abcdef_your_folder_id"
STATUS_TRACKER_TEMPLATE_ID="1abcdef234567890_your_template_id"
```

### 4.2 Add to GitHub Secrets (for CI/CD deployment)
```bash
# In your GitHub repository:
# Settings > Secrets and variables > Actions > Repository secrets
# Add these secrets:
GOOGLE_DRIVE_FOLDER_ID=1234567890abcdef_your_folder_id
STATUS_TRACKER_TEMPLATE_ID=1abcdef234567890_your_template_id
```

**Note**: The system now uses the same Google Cloud credentials as other services (`GOOGLE_APPLICATION_CREDENTIALS`), so you don't need a separate service account key file!

## 🚀 **Step 5: Enable APIs**

### 5.1 Enable Required APIs
```bash
# In Google Cloud Console > APIs & Services > Library
# Search and enable:
1. Google Slides API
2. Google Drive API
```

### 5.2 Verify API Access
```bash
# Test the setup
cd backend
poetry run python -c "
from rag.tools.report_tools import create_slides_presentation_func
result = create_slides_presentation_func('TEST-001', 'Test Report')
print('✅ Setup successful!' if result['success'] else '❌ Setup failed')
print(f'URL: {result[\"url\"]}')
"
```

## 🔒 **Step 6: Security Best Practices**

### 6.1 Service Account Permissions
```bash
# Minimum required permissions:
- Google Slides API: Read/Write
- Google Drive API: Read/Write (specific folder only)
- No other permissions needed
```

### 6.2 Public Folder Security
```bash
# ✅ Safe for development:
- Public viewing of reports (good for demos)
- Service account has edit access only

# 🔄 Production considerations:
- Restrict folder to specific users/groups
- Use organization-owned Drive accounts
- Enable audit logging
```

### 6.3 Credential Security
```bash
# ✅ Secure credential handling:
- Store JSON file outside of git repository
- Use environment variables for paths
- Rotate service account keys periodically
- Monitor service account usage
```

## 📋 **Step 7: Test the Integration**

### 7.1 Run Integration Test
```bash
# Test with real investigation data
cd backend
poetry run python rag/test_investigation.py

# Should output:
# ✅ Created presentation: [PRESENTATION_URL]
# ✅ Evidence included: X items
# ✅ Public access enabled
```

### 7.2 Verify Results
```bash
# Check that:
1. Presentation appears in Drive folder
2. Placeholders are replaced with real data
3. Evidence images are included
4. Public link works for viewing
5. Professional template formatting preserved
```

## 🎨 **Step 8: Template Customization**

### 8.1 Available Placeholders
```javascript
// Investigation Data
{{investigation_title}}     // "Community Protest Investigation - Washington Square Park"
{{investigation_id}}        // "ALERT-001_20250617_123456"
{{alert_location}}          // "Washington Square Park, Manhattan"
{{alert_severity}}          // "7/10"
{{alert_summary}}           // Full alert description
{{status}}                  // "Analysis", "Complete", etc.
{{confidence_score}}        // "85.3%"

// Findings & Evidence
{{findings_summary}}        // Bullet points of key findings
{{evidence_count}}          // "15"
{{evidence_types}}          // "screenshots, images, documents"
{{high_relevance_count}}    // "8"

// Timeline & Status
{{timestamp}}               // "2025-06-17 14:30:22"
{{phase}}                   // "Reconnaissance", "Analysis", etc.
{{iteration_count}}         // "3"

// Image Placeholders (automatically replaced with actual images)
{{EVIDENCE_IMAGE_1}}        // First high-relevance evidence image
{{EVIDENCE_IMAGE_2}}        // Second high-relevance evidence image  
{{EVIDENCE_IMAGE_3}}        // Third high-relevance evidence image
{{EVIDENCE_SCREENSHOT_1}}   // First screenshot from web/social media
{{EVIDENCE_SCREENSHOT_2}}   // Second screenshot from web/social media
{{MAP_LOCATION}}            // Location map (when available)
{{TIMELINE_CHART}}          // Investigation timeline chart
```

### 8.2 **Image Placeholder Usage**
The system automatically inserts real evidence images collected by agents:

**How it works:**
1. **Agents collect images** during investigation (screenshots, photos, etc.)
2. **System filters** for high-relevance images (relevance_score > 0.7)
3. **Images are inserted** in a 2x2 grid layout on evidence slides
4. **Captions are added** with descriptions and evidence numbers

**Template Design:**
- Create slides with placeholder shapes or text boxes
- Use placeholder text like "{{EVIDENCE_IMAGE_1}}" 
- The system will replace these with actual collected images
- Images are sized to 160x120 points with professional captions

**Evidence Image Types:**
- **Screenshots**: From web pages, social media, news articles
- **Photos**: From Reddit posts, Twitter, other social sources  
- **Maps**: Location-based evidence
- **Charts**: Data visualizations from analysis

**Pro Tips:**
- Leave adequate space for 2x2 image grid (640x240 points minimum)
- Use consistent placeholder naming for automatic detection
- Test with mock data first using the verification commands below

## 🔄 **Step 9: Iteration and Improvement**

### 9.1 Template Versioning
```bash
# Create multiple templates for different scenarios:
- Emergency Response Template
- Community Investigation Template
- Infrastructure Analysis Template
- Public Safety Template
```

### 9.2 Evidence Integration Enhancement
```bash
# Future improvements:
- Automatic image resizing and placement
- Evidence categorization and grouping
- Interactive charts and graphs
- Timeline visualizations
- Map integrations
```

## 🎯 **Expected Results**

After setup, the system will automatically:

1. **Create professional presentations** from your Status Tracker template
2. **Populate with real investigation data** from the multi-agent system  
3. **Include collected evidence** (screenshots, images, documents)
4. **Share publicly** for easy demonstration and stakeholder access
5. **Organize in Drive folders** with clear naming conventions
6. **Maintain professional formatting** while showing real investigative work

## 📞 **Support & Troubleshooting**

### Common Issues:
- **403 Forbidden**: Check service account has correct folder permissions
- **Template not found**: Verify template ID in environment variables
- **API not enabled**: Enable Slides & Drive APIs in Cloud Console
- **Quota exceeded**: Check API quotas and rate limits

### Testing Commands:
```bash
# Test Google Cloud authentication (same as other services)
poetry run python -c "from google.auth import default; credentials, project = default(); print('✅ Auth works')"

# Test Google Slides integration
poetry run python -c "from rag.tools.report_tools import _get_google_services; print('✅ Slides auth works' if _get_google_services()[0] else '❌ Slides auth failed')"

# Test template access and image insertion
poetry run python -c "from rag.tools.report_tools import create_slides_presentation_func; print(create_slides_presentation_func('TEST', template_type='status_tracker'))"

# Test with evidence images (mock data)
poetry run python -c "
from rag.tools.report_tools import create_slides_presentation_func
result = create_slides_presentation_func('TEST-001', 'Test Report with Images', evidence_types='all')
print(f'Result: {result}')
"
```

## 📋 **Quick Setup Summary**

1. **Create service account** with Google Slides & Drive permissions
2. **Share your Drive folder** with the service account email  
3. **Enable APIs**: Google Slides API, Google Drive API
4. **Set environment variables**:
   - Local: Add `GOOGLE_DRIVE_FOLDER_ID` and `STATUS_TRACKER_TEMPLATE_ID` to `.env`
   - CI/CD: Add same variables as GitHub secrets
5. **No separate credential file needed** - uses existing Google Cloud auth!

---

**🎉 Ready to generate professional investigation reports with real Google Slides integration!** 