# Infrastructure Overview

## Frontend
- The frontend is a React application built with Vite.
- It is containerized using Docker and served via NGINX.
- Deployment is managed through Google Cloud Run, which provides scalable, serverless hosting for the static frontend assets.

## Backend
- The backend leverages Google Vertex AI for scalable, managed machine learning and inference services.
- Backend deployment is handled directly to Vertex AI endpoints, not as a traditional web server.

## Development Environment
- The project uses a **devcontainer** (VS Code Dev Containers) for a reproducible, isolated development environment.
- This ensures all contributors have a consistent setup with required dependencies and tools pre-installed.

## Automation
- A comprehensive **Makefile** is provided to automate common tasks:
  - Dependency installation
  - Local development server startup
  - Linting, formatting, and testing
  - Building and deploying both frontend and backend
- This streamlines both local development and production deployment workflows.
