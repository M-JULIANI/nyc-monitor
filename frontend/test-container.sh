#!/bin/bash

# Build the container
docker build -t atlas-frontend:test -f Dockerfile .

# Run the container with backend URL
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e BACKEND_URL=http://localhost:8000 \
  atlas-frontend:test 