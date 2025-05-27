# TO-DOs

## Setup
- [x] devcontainers setup
- [x] build backend - not required vertex ai handles this during run/deploy
- [x] build frontend
- [x] deploy backend
- [x] deploy frontend
- [x] fix deployment frontend
- [x] connect backend to frontend
- [ ] serve frontend to a proper url
- [ ] buy a simple domain?
- [x] CI/CD? (when we merge an MR get it auto-deployed)
    - [ ] run build & testfor a PR pipeline
    - [ ] push to artifact registry & deploy on PR merge

## Explore datasets and APIs
Decide which of these are valuable and worth pursuing as we will build an integration/api call to fetch data from them (our `searcher` agent). Are these api calls searchable by topic, lat, lon?

- [ ] reddit
- [ ] twitter
- [ ] yelp
- [ ] tripadvisor
- [ ] google trends

## Agents (Backend)
These are basically the agents. The search one will do most of the work, so maybe worth splitting into search APIs and search datasets

- [ ] Searcher: APIs
- [ ] Searcher: Datasets
- [ ] Ingest (takes data and ingests it into vertex AI to be able to RAG over data)
- [ ] Chat

## Frontend
- [ ] Chat interface
- [ ] Map functionality