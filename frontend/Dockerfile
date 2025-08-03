# Build stage
FROM node:20-alpine AS builder

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
COPY frontend/.npmrc ./
COPY pnpm-workspace.yaml ../

# Install dependencies using npm for better binary support in Docker
RUN npm install --include=dev

# Copy source code
COPY frontend/ ./

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

# Use the default nginx entrypoint (no custom entrypoint needed) 