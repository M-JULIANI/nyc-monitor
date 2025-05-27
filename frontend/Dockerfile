# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY ./package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . ./

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy nginx config
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

# Use the default nginx entrypoint (no custom entrypoint needed) 