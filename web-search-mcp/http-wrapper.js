import { spawn } from 'child_process';
import http from 'http';
import url from 'url';

// Environment variables
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';

// Start the MCP server
const mcpProcess = spawn('node', ['dist/index.js'], {
  stdio: ['pipe', 'pipe', 'pipe'], // Changed from 'inherit' to 'pipe' to capture stderr
  env: {
    ...process.env,
    MAX_CONTENT_LENGTH: process.env.MAX_CONTENT_LENGTH || '15000',
    DEFAULT_TIMEOUT: process.env.DEFAULT_TIMEOUT || '6000',
    MAX_BROWSERS: process.env.MAX_BROWSERS || '2',
    BROWSER_HEADLESS: 'true',
    ENABLE_RELEVANCE_CHECKING: process.env.ENABLE_RELEVANCE_CHECKING || 'true',
    RELEVANCE_THRESHOLD: process.env.RELEVANCE_THRESHOLD || '0.3',
    PLAYWRIGHT_BROWSERS_PATH: '/usr/bin'
  }
});

// Log MCP process stderr for debugging
mcpProcess.stderr.on('data', (data) => {
  console.error('MCP Server Error:', data.toString());
});

// Handle MCP process exit
mcpProcess.on('exit', (code, signal) => {
  console.error(`MCP process exited with code ${code} and signal ${signal}`);
});

mcpProcess.on('error', (err) => {
  console.error('Failed to start MCP process:', err);
});

// Handle process lifecycle
process.on('SIGTERM', () => {
  mcpProcess.kill('SIGTERM');
  process.exit(0);
});

// Create HTTP server that forwards JSON-RPC requests
const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('OK');
    return;
  }
  
  if (req.method === 'POST' && req.url === '/') {
    let body = '';
    
    req.on('data', chunk => {
      body += chunk.toString();
    });
    
    req.on('end', () => {
      try {
        const request = JSON.parse(body);
        
        // Forward to MCP server via stdin
        mcpProcess.stdin.write(JSON.stringify(request) + '\n');
        
        // Wait for response from MCP server
        const responseHandler = (data) => {
          try {
            const response = JSON.parse(data.toString());
            if (response.id === request.id) {
              mcpProcess.stdout.removeListener('data', responseHandler);
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify(response));
            }
          } catch (e) {
            // Continue accumulating data if JSON parse fails
          }
        };
        
        mcpProcess.stdout.on('data', responseHandler);
        
        // Timeout after 30 seconds
        setTimeout(() => {
          mcpProcess.stdout.removeListener('data', responseHandler);
          if (!res.headersSent) {
            res.writeHead(504, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
              jsonrpc: '2.0',
              error: { code: -32603, message: 'Request timeout' },
              id: request.id
            }));
          }
        }, 30000);
        
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          jsonrpc: '2.0',
          error: { code: -32700, message: 'Parse error' },
          id: null
        }));
      }
    });
  } else {
    res.writeHead(404);
    res.end();
  }
});

server.listen(PORT, HOST, () => {
  console.log(`HTTP wrapper listening on http://${HOST}:${PORT}`);
  console.log('MCP web-search server started');
  console.log('Health endpoint available at /health');
});
