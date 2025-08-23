# Build stage
FROM node:20-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone the repository
RUN git clone https://github.com/mrkrsl/web-search-mcp.git .

# Install npm dependencies
RUN npm install

# Build the TypeScript project
RUN npm run build

# Production stage  
FROM node:20-slim

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libxss1 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built files and dependencies from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Install Playwright browsers
RUN npx playwright install chromium firefox
RUN npx playwright install-deps

# Copy the HTTP wrapper
COPY http-wrapper.js /app/http-wrapper.js

# Set display for headless operation
ENV DISPLAY=:99

# Copy and set up startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 3000

# Run the startup script
CMD ["/app/start.sh"]