# RAG Backend

This is the backend service for the RAG (Retrieval-Augmented Generation) application. It provides an API for question answering using Vertex AI RAG Engine.

## Features

- Question answering using Vertex AI RAG Engine
- FastAPI-based REST API
- Integration with Google Cloud services

## Development

To set up the development environment:

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Run the development server:
   ```bash
   poetry run uvicorn rag.main:app --reload
   ```

## Project Structure

- `rag/` - Main application code
- `tests/` - Test suite
- `eval/` - Evaluation scripts
- `deployment/` - Deployment configurations 