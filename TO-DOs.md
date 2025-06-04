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
- [ ] twitter
- [ ] yelp
- [ ] tripadvisor
- [ ] google trends

~~## MCP implementations to study~~
~~- [ ] [reddit mcp](https://github.com/adhikasp/mcp-reddit)~~
~~- [ ] [trip advisor mcp](https://github.com/pab1it0/tripadvisor-mcp)~~
~~- [ ] [google search](https://github.com/mixelpixx/Google-Search-MCP-Server)~~
~~- [ ] [twitter mcp](https://github.com/EnesCinr/twitter-mcp)~~


## Agents (Backend)
These are basically the agents. The search one will do most of the work, so maybe worth splitting into search APIs and search datasets

- [ ] Searcher: APIs
- [ ] Searcher: Datasets
- [ ] Ingest (takes data and ingests it into vertex AI to be able to RAG over data)
- [ ] Chat

## Frontend
- [ ] Chat interface
- [ ] Map functionality