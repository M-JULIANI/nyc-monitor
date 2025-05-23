# Infrastructure Overview

## Frontend
- The frontend is a React application built with Vite.
- It is containerized using Docker and served via NGINX.
- Deployment is managed through Google Cloud Run, which provides scalable, serverless hosting for the static frontend assets.

## Backend
- The backend is a FastAPI application containerized and deployed to Google Cloud Run.
- This backend acts as a **proxy** to Vertex AI agents, providing:
  - Error handling
  - Rate limiting
  - Authentication (Google OAuth2)
- The FastAPI backend receives requests from the frontend, applies these controls, and then calls the Vertex AI agent endpoints to fulfill the request.

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
