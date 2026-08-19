# ==============================================================================
# Production Dockerfile for LOCK IN AI Frontend
# Multi-Stage Build: Node 20 (Vite build) -> Nginx 1.27 (Production Server)
# ==============================================================================

# ── Stage 1: Build React/Vite Application ─────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications first for optimal Docker layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Accept optional build argument for API URL if deployed separately (defaults to relative /api)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Copy frontend source files
COPY . .

# Build production bundle
RUN npm run build

# ── Stage 2: Serve with Nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove default nginx static assets and configuration
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy production static build from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Healthcheck for Nginx
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
