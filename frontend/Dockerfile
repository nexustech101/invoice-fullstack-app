# Frontend Dockerfile - React + Vite + pnpm
# Build stage
FROM node:22-alpine AS build
WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm

# Copy lock file and package.json
COPY pnpm-lock.yaml package.json ./

# Install dependencies with pnpm
RUN pnpm install --frozen-lockfile

# Copy application code
COPY . .

# Build arg for API URL — override at build time if needed
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Build the application
RUN pnpm build

# Production stage — serve with nginx
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Copy built files from build stage
COPY --from=build /app/dist .

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port for nginx
EXPOSE 3001

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
