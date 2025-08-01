# Chrome Profile Management for ChatGPT MCP

This document explains the critical Chrome profile architecture and troubleshooting for the ChatGPT MCP server.

## Why Separate Profile Required

**Chrome Security Restriction**: Chrome prevents `--remote-debugging-port` on the default user profile for security reasons. Attempting to use the default profile results in:
- Chrome opening folder listings instead of web pages
- Command line arguments being interpreted as file paths
- Complete failure to enable remote debugging

## Architecture Overview

```
Default Chrome Profile (Regular Browsing)
├── ~/Library/Application Support/Google/Chrome/Default/
└── Used for: Normal web browsing, personal data, extensions

Chrome-Automation Profile (MCP Control)
├── ~/Library/Application Support/Google/Chrome-Automation/
├── Copied from: Default profile (preserves logins)
├── Used for: ChatGPT automation, debugging enabled
└── Isolated from: Regular browsing activities
```

## Automatic Profile Management

### Profile Creation Process

1. **First Launch**: MCP checks if Chrome-Automation profile exists
2. **Profile Copy**: If not found, copies entire Default profile
3. **Launch Chrome**: Uses automation profile with debugging enabled
4. **Session Persistence**: ChatGPT login maintained across sessions

### Profile Locations

| Platform | Path |
|----------|------|
| **macOS** | `~/Library/Application Support/Google/Chrome-Automation` |
| **Windows** | `%LOCALAPPDATA%\Google\Chrome-Automation` |
| **Linux** | `~/.config/google-chrome-automation` |

## Common Issues & Solutions

### 1. Chrome Opens Folder Listing

**Symptoms**:
```
Chrome displays: file:///Users/user/Library/Application Support/Google/Chrome-Automation/
Instead of: https://chatgpt.com
```

**Root Causes**:
- Corrupted automation profile
- Command line argument parsing errors
- Path with spaces not properly quoted

**Solution**:
```bash
# macOS
rm -rf ~/Library/Application\ Support/Google/Chrome-Automation

# Windows (Command Prompt)
rmdir /s "%LOCALAPPDATA%\Google\Chrome-Automation"

# Windows (PowerShell)
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Google\Chrome-Automation"

# Linux
rm -rf ~/.config/google-chrome-automation

# Then restart MCP - profile will be recreated
```

### 2. Not Logged In After Profile Reset

**Expected Behavior**: New automation profile won't have ChatGPT login initially.

**Solution**:
1. Login to ChatGPT in the automation browser window
2. Session will persist for future MCP runs
3. No need to update `.env` credentials

### 3. Command Line Argument Issues

**Problem**: Paths with spaces cause argument parsing failures

**Technical Details**:
```python
# ❌ BROKEN: Arguments list approach
args = ["chrome", "--user-data-dir=/path with spaces/"]
# Results in: Chrome interprets as file:// URL

# ✅ WORKING: Shell command approach (macOS)
cmd = f'"{chrome_path}" --user-data-dir="{profile_path}" "https://chatgpt.com"'
subprocess.Popen(cmd, shell=True)
```

### 4. Port Already in Use

**Symptoms**:
```
Error: Port 9222 already in use
```

**Diagnosis**:
```bash
# Check what's using port 9222
lsof -i :9222  # macOS/Linux
netstat -ano | findstr :9222  # Windows
```

**Solution**:
```bash
# Kill existing Chrome debugging processes
pkill -f "remote-debugging-port=9222"  # macOS/Linux

# Or restart with different port (advanced)
# Change BROWSER_DEBUG_PORT in .env
```

### 5. Profile Corruption

**Symptoms**:
- Chrome launches but fails to navigate to ChatGPT
- Repeated authentication prompts
- Browser crashes on startup

**Solution**: Always delete and recreate (never try to repair):
```bash
# Complete profile reset
rm -rf ~/Library/Application\ Support/Google/Chrome-Automation
# MCP will recreate from current default profile
```

## Advanced Profile Management

### Manual Profile Creation

```bash
# 1. Create profile directory
mkdir -p ~/Library/Application\ Support/Google/Chrome-Automation

# 2. Copy default profile (preserves logins)
cp -R ~/Library/Application\ Support/Google/Chrome/Default/* ~/Library/Application\ Support/Google/Chrome-Automation/

# 3. Launch with debugging (manual)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome-Automation" \
  "https://chatgpt.com"
```

### Profile Size Management

**Typical Sizes**:
- Fresh profile: ~50-100MB
- With history/cache: ~200-500MB
- Full default copy: ~1-2GB

**Cleanup Options**:
```bash
# Remove cache but keep logins
rm -rf ~/Library/Application\ Support/Google/Chrome-Automation/Default/Cache
rm -rf ~/Library/Application\ Support/Google/Chrome-Automation/Default/Code\ Cache

# Full reset (recommended)
rm -rf ~/Library/Application\ Support/Google/Chrome-Automation
```

## Security Considerations

### Local Development Safety

- **Debugging port**: Only listens on localhost (127.0.0.1:9222)
- **Profile isolation**: Automation doesn't affect regular browsing
- **No external access**: Chrome debugging protocol not exposed externally

### Production Warnings

- **Never use in production**: Debugging port is a security risk
- **Firewall rules**: Ensure port 9222 is blocked externally
- **VPN/Network**: Be cautious on shared networks

## Best Practices

### Profile Maintenance

1. **Regular cleanup**: Delete automation profile monthly
2. **Fresh starts**: Reset profile when encountering persistent issues
3. **Don't repair**: Always delete and recreate corrupted profiles

### Development Workflow

1. **Keep Chrome running**: Don't close automation browser during development
2. **Monitor logs**: Enable DEBUG logging for profile creation issues
3. **Test after updates**: Chrome updates can affect profile compatibility

### Debugging Commands

```bash
# Check profile exists
ls -la ~/Library/Application\ Support/Google/Chrome-Automation

# Monitor Chrome processes
ps aux | grep chrome | grep debugging

# Check profile size
du -sh ~/Library/Application\ Support/Google/Chrome-Automation

# Test Chrome launch manually
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome-Automation" \
  "https://chatgpt.com"
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHROME_USER_DATA_DIR` | Auto-detected | Override automation profile path |
| `BROWSER_DEBUG_PORT` | 9222 | Chrome debugging port |
| `HEADLESS` | false | Show/hide Chrome window |

## Troubleshooting Checklist

When encountering Chrome issues:

- [ ] Delete automation profile directory
- [ ] Restart MCP server
- [ ] Check port 9222 availability
- [ ] Verify default Chrome profile has ChatGPT login
- [ ] Test manual Chrome launch with debugging
- [ ] Check Chrome version compatibility
- [ ] Review MCP logs for profile creation errors
- [ ] Confirm sufficient disk space for profile copy

Remember: **Profile deletion and recreation** solves 95% of Chrome automation issues.