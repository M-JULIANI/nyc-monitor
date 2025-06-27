# 🏙️ NYC Monitor
**AI-Powered Urban Intelligence for Real-Time City Monitoring**

Atlas is an autonomous investigation system that monitors New York City through social media, 311 complaints, and news feeds. When incidents emerge—from protests in Brooklyn to infrastructure failures on Manhattan Bridge—our AI agent automatically researches the scope, maps the impact, collects visual evidence, and generates professional briefings in under 8 minutes.

## ✨ Key Features

🔍 **Intelligent Investigation**: AI agent performs comprehensive research using web search, satellite mapping, and visual evidence collection

📊 **Real-Time Monitoring**: Continuous scanning of Reddit, Twitter, 311 data, and news sources every 15 minutes

🗺️ **Interactive Mapping**: Live alert visualization with priority-based filtering and geographic context

📋 **Professional Reports**: Automated Google Slides generation with artifacts, analysis, and actionable insights

🔐 **Role-Based Access**: Secure authentication with viewer, analyst, and admin permissions

⚡ **Sub-8-Minute Response**: Complete investigation cycle faster than traditional media coverage

## 🚀 Live Demo

### **Frontend**: [nyc-monitor.app](https://nyc-monitor.app)
- Interactive map with real-time alerts
- Investigation dashboard and report gallery
- Google OAuth authentication required

### **Backend API**: [atlas-backend-blz2r3yjgq-uc.a.run.app](https://atlas-backend-blz2r3yjgq-uc.a.run.app)
- RESTful API for alert management
- AI agent investigation endpoints
- Real-time data collection services

## 🧪 How to Use the System

### **Create Investigation**
1. **Navigate**: Go to [nyc-monitor.app](https://nyc-monitor.app) and login with Google OAuth
2. **Find Reddit Alert**: Browse the map or dashboard for a Reddit alert (avoid 311 alerts for now as they may lead to rabbit holes)
3. **Trigger Investigation**: Click "Create Report" on the alert card
4. **Wait Patiently**: Investigation takes up to 5 minutes to complete
5. **Return to Alert**: Go back to the same alert card after waiting
6. **View Results**: Click "View Investigation" to see the generated report with maps, images, and analysis

### **Explore Alerts**
- **Time Travel**: Use the time slider to see what alerts were created at different times
- **Historical View**: Slide back to see how incidents emerged and evolved over time
- **Pattern Recognition**: Notice how alerts cluster geographically and temporally

### **Understand Alert Categories**
- **Map Filters**: Use view modes and category filters to see specific types of alerts (Reddit, Twitter, 311, traffic)
- **Visual Analysis**: Different alert types appear with distinct icons and priority colors
- **Insights Dashboard**: Go to "Insights" tab to see:
  - Alert breakdown by category (pie charts)
  - Time patterns by day and hour (scatter plots)
  - Priority distribution and trends
  - Geographic clustering analysis

### **View Reports**
1. **Navigate**: Go to [nyc-monitor.app](https://nyc-monitor.app)
2. **Login**: Authenticate with Google OAuth
3. **Investigate**: Navigate to '/reports' tab, and view cards displaying reports that have already been generated ([sample report](https://docs.google.com/presentation/d/16pSm3nSPESrj6Tgoiltrhuu6kZvXzz8jVhrlO1GznIo/edit?slide=id.gc6fa3c898_0_0#slide=id.gc6fa3c898_0_0)). To view all reports generated, feel free to go this this publicly viewable [drive folder](https://drive.google.com/drive/u/0/folders/1dw2UL95bWqoswsgKFK5_9FHlXjXKQlkd).


## 🏗️ Architecture Overview

**Technology Stack**:
- **AI Engine**: Google ADK with Gemini 2.0 Flash Experimental
- **Backend**: FastAPI + Firestore + BigQuery + Vertex AI Vector DB
- **Frontend**: React + Mapbox + Role-based authentication
- **Reports**: Google Slides API integration
- **Deployment**: Google Cloud Run with CI/CD

**Investigation Workflow**:
1. **Web Search**: DuckDuckGo + Google Custom Search for real-time intelligence
2. **Geographic Analysis**: Multi-zoom satellite map generation
3. **Visual Evidence**: Targeted image collection from multiple sources
4. **Report Generation**: Professional briefing with all artifacts and insights

## 📁 Project Structure

```
nyc-monitor/
├── frontend/          # React application with Mapbox integration
├── backend/           # FastAPI services and AI agent system
│   ├── rag/agents/   # AI investigation agent
│   ├── rag/tools/    # Web search, mapping, and report tools
│   └── api/          # REST endpoints and data collection
├── docs/             # Architecture and setup documentation
└── .devcontainer/    # Development environment configuration
```

## 🚀 Getting Started

### **Development Setup**
Refer to [docs/setup.md](./docs/setup.md) for complete development environment configuration.

### **Key Requirements**
- **Cloud Deployment Required**: Vertex AI ADK needs cloud execution
- **Google Cloud Project**: For AI services and data storage
- **Authentication**: Google OAuth for secure access

### **Why Cloud Deployment?**
- **Vertex AI ADK**: Multi-agent system requires cloud resources
- **Real AI Interactions**: Local testing shows only fallback behavior  
- **Distributed Tracing**: Full monitoring needs cloud infrastructure

## 📖 Documentation

- **[Architecture Overview](./docs/architecture.md)**: Detailed system design and data flow
- **[Setup Guide](./docs/setup.md)**: Development environment and deployment
- **[API Documentation](https://atlas-backend-blz2r3yjgq-uc.a.run.app/docs)**: Interactive API reference

## 🎯 (Potential) Use Cases

**City Officials**: Real-time incident awareness with professional briefings  
**Emergency Response**: Rapid situational assessment with visual evidence  
**Urban Planning**: Pattern detection across neighborhoods and time periods  
**Media Relations**: Fact-checked information faster than traditional reporting
