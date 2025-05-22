# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy nginx configuration template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Create startup script
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo 'PORT=${PORT:-8080}' >> /docker-entrypoint.sh && \
    echo 'BACKEND_URL=${BACKEND_URL:-}' >> /docker-entrypoint.sh && \
    echo 'echo "Starting nginx with PORT=$PORT and BACKEND_URL=$BACKEND_URL"' >> /docker-entrypoint.sh && \
    echo 'envsubst "\$PORT \$BACKEND_URL" < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf' >> /docker-entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Expose port (will be overridden by Cloud Run)
EXPOSE 8080

# Start nginx using the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"] 