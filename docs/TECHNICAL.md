# Technical Documentation

## Architecture Overview

The ChatGPT Automation MCP uses Playwright to control the ChatGPT web interface through browser automation. By default, it connects to an existing Chrome instance via CDP (Chrome DevTools Protocol) to bypass Cloudflare protection.

### Why CDP Mode?

- **Cloudflare Bypass**: Connects to your real browser with authenticated session
- **No Automation Flags**: Uses your actual Chrome profile without detection
- **Session Persistence**: Leverages existing cookies and login state
- **Real User Context**: Maintains authentic browser fingerprint

## Core Components

### 1. MCP Server (`server.py`)
- Implements the Model Context Protocol specification
- Exposes tools for ChatGPT automation
- Handles async communication with Claude

### 2. Browser Controller (`browser_controller.py`)
- Manages Playwright browser instance
- Handles page navigation and interactions
- Implements response detection logic

### 3. Configuration (`config.py`)
- Environment-based configuration
- Secure credential management
- Path and timeout settings

## Implementation Details

### Browser Automation Strategy

We use Playwright with CDP connection because:
- **Cloudflare Protection**: CDP mode bypasses anti-automation detection
- **Cross-platform**: Works on macOS, Linux, Windows
- **Reliable selectors**: CSS and accessibility-based element selection  
- **Session persistence**: Uses existing browser session
- **Fallback Support**: Can launch new browser if CDP unavailable

### CDP vs Standard Mode

| Feature | CDP Mode | Standard Mode |
|---------|----------|---------------|
| Cloudflare Protection | ✅ Bypassed | ❌ Blocked |
| Uses Existing Session | ✅ Yes | ❌ No |
| Requires Chrome Running | ✅ Yes | ❌ No |
| Automation Detection | ✅ Hidden | ❌ Visible |

### Key Challenges Solved

1. **Response Detection**
   - Monitor DOM changes for completion indicators
   - Track network activity for API calls
   - Detect thinking animations and streaming

2. **Model Selection**
   - Navigate model picker UI reliably
   - Handle dynamic model lists
   - Verify selection success

3. **Session Management**
   - Persist browser context between runs
   - Handle re-authentication when needed
   - Manage cookies and local storage

### Selector Strategy

```javascript
// Primary selectors used
const SELECTORS = {
  newChatButton: '[data-testid="new-chat-button"]',
  messageInput: '#prompt-textarea',
  sendButton: '[data-testid="send-button"]',
  modelPicker: '[data-testid="model-picker"]',
  responseContainer: '[data-testid="conversation-turn"]:last-child',
  thinkingIndicator: '[data-testid="thinking-indicator"]'
}
```

## API Design

### Tool Patterns

Each tool follows a consistent pattern:
1. Validate input parameters
2. Ensure browser is ready
3. Perform action with retries
4. Return structured response

### Error Handling

- **Timeout errors**: Configurable timeouts with clear messages
- **Element not found**: Retry with exponential backoff
- **Network errors**: Graceful degradation
- **Auth errors**: Prompt for re-login

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**
   - Only launch browser when needed
   - Reuse existing pages when possible

2. **Smart Waiting**
   - Use Playwright's built-in wait conditions
   - Avoid fixed sleeps

3. **Resource Management**
   - Close unused tabs
   - Clear memory periodically
   - Limit screenshot storage

## Security

### Credential Handling
- Never log passwords
- Use environment variables
- Secure session storage

### Browser Isolation
- Separate context per session
- Clear sensitive data on exit
- Sandbox browser process

## Testing Strategy

### Unit Tests
- Mock Playwright interactions
- Test error conditions
- Validate tool schemas

### Integration Tests
- Real browser automation
- End-to-end workflows
- Visual regression tests

## Future Enhancements

### Planned Features
1. **WebSocket support** for real-time updates
2. **Plugin system** for custom extensions
3. **Batch operations** for efficiency
4. **Export formats** (PDF, Markdown, JSON)

### Architecture Evolution
- Consider CDP for advanced features
- Explore native messaging APIs
- Investigate official ChatGPT API when available