# TO-DOs

## Setup
- [x] devcontainers setup
- [x] build backend - not required vertex ai handles this during run/deploy
- [x] build frontend
- [x] deploy backend
- [x] deploy frontend
- [x] fix deployment frontend
- [x] connect backend to frontend
- [x] serve frontend to a proper url
- [x] buy a simple domain?
- [x] CI/CD? (when we merge an MR get it auto-deployed)
    - [x] run build & test for a PR pipeline
    - [x] push to artifact registry & deploy on PR merge

## Explore datasets and APIs
Decide which of these are valuable and worth pursuing as we will build an integration/api call to fetch data from them (our `searcher` agent). Are these api calls searchable by topic, lat, lon?

- [x] reddit
- [x] hackernews
- [x] twitter
- [x] 311
- [ ] yelp

~~## MCP implementations to study~~
~~- [ ] [reddit mcp](https://github.com/adhikasp/mcp-reddit)~~
~~- [ ] [trip advisor mcp](https://github.com/pab1it0/tripadvisor-mcp)~~
~~- [ ] [google search](https://github.com/mixelpixx/Google-Search-MCP-Server)~~
~~- [ ] [twitter mcp](https://github.com/EnesCinr/twitter-mcp)~~


## Agents (Backend)
These are basically the agents. The search one will do most of the work, so maybe worth splitting into search APIs and search datasets

- [ ] Searcher: 
    - [x] web-search
    - [ ] api calls?
- [ ] Searcher: Datasets
    - [ ] big query census

- [ ] Ingest (takes data and ingests it into vertex AI to be able to RAG over data)
- [ ] Chat

## Frontend
- [ ] Chat interface
- [x] Map functionality
    - [x] filtering by day range
    - [x] filtering by source
    - [x] filtering by severity
- [x] Insights tab: rollup incident categories (311) using /stats & categories endpoints
    - [x] pie chart of category types
    - [x] scatterplot with time patterns (day vs hour), colored by category
    - [x] clickable markers showing alert details
    - [x] priority breakdown charts
    - [x] category information display

## Critical path
- [x] ensure 311 daily collector works
- [x] fix basic auth: should be able to login via google oauth, and it should kick you out if you leave and ask you to login again
- [x] ensure map filters work
    - [x] include twitter, reddit, 311 icons
    - [x] add time slider to filter items
    - [x] ensure different priorities are being populated correctly
- [x] alert cards on map
    - [x] display category
    - [x] display status
    - [x] display source
    - [x] display location
    - [x] display link to report, if it exists
    - [x] display link to agent investigation
- [x] ensure twitter collector is actually working?
- [x] collector improvements: no duplicates
- [x] reddit strategies: other search terms?
- [x] ensure 'create report' button works for certain (non 311) alerts, and when a report doesnt already exist
- [x] ensure when a report is created, it is linked back to an alert, so that no duppicate reports can be created for an alert
- [x] when a report is created, have it persist to the alert card, not just an in session persistence
- [ ] ensure that a report is findable & clickable from '/reports' tab
    - [x] once a report is created, a 'reportLink' field should be created in the alert object in firestore.
- [x] loading spinner during login
- [x] improved reports with actual insights and a useful executive summary
- [ ] in the alerts & report cards in the UI, there should be a link to the agent logs which can be rendered in place (markdown)
- [ ] when an adhoc report is triggered via a button, figure out how to display that in a non-blocking way to indicate that the report us underway. _ideally_ with streaming of the report state.
- [ ] 'daily report' agent
    - [ ] 'daily reports' folder
    - [ ] 'weekly reports' folder
    - [ ] 'ad-hoc' folder
- [ ] chat agent
    - [ ] can perform rag on existing dataset

- [ ] video narrative
- [ ] video