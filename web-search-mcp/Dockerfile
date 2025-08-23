# Build stage
FROM node:20-alpine as builder

# Install dependencies needed for Playwright
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    git

WORKDIR /app

# Clone the repository
RUN git clone https://github.com/mrkrsl/web-search-mcp.git .

# Install npm dependencies
RUN npm install

# Build the TypeScript project
RUN npm run build

# Production stage
FROM node:20-alpine

# Install runtime dependencies for Playwright browsers
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    firefox \
    xvfb-run

# Set up Playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin

WORKDIR /app

# Copy built files and dependencies from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

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