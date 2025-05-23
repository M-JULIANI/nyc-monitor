# Backend

## Local development

Run backend with `make dev-backend`, and then in a separate terminal run:

```
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "What is Vertex AI?"}'
``` 