# --- Stage 1: Development ---
FROM node:24-slim AS development

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Install nginx for dev proxy too
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173 80

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# --- Stage 2: Build ---
FROM node:24-slim AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Stage 3: Production ---
FROM nginx:stable-alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static files
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8081

CMD ["nginx", "-g", "daemon off;"]
