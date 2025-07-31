# CDP Setup Guide

## Quick Start

1. **Launch Chrome with debugging port**:
   ```bash
   # Close all Chrome instances first
   
   # Then launch with debugging:
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
   ```

2. **Login to ChatGPT**:
   - Navigate to https://chatgpt.com in the Chrome window that opens
   - Login with your Pro account
   - Keep this Chrome window open

3. **Test CDP connection**:
   ```bash
   cd /Users/cbusillo/Developer/chatgpt-automation-mcp
   uv run python test_cdp_connection.py
   ```

4. **Run the MCP server**:
   ```bash
   uv run chatgpt-mcp
   ```

## Why CDP?

- **Bypasses Cloudflare**: Uses your real browser session
- **No automation detection**: No --enable-automation flags
- **Pro account access**: Uses your existing login

## Troubleshooting

If CDP connection fails:
1. Make sure no other Chrome is running: `pkill -f Chrome`
2. Check port 9222 is free: `lsof -i :9222`
3. Try a different port in both Chrome launch and .env file