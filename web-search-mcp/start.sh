#!/bin/sh
# Start Xvfb in background
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp &
export DISPLAY=:99

# Wait a moment for Xvfb to start
sleep 2

# Start our application
echo "Starting HTTP wrapper..."
exec node /app/http-wrapper.js
