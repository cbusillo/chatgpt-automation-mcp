# Technical Documentation

## Architecture Overview

The ChatGPT Automation MCP uses Playwright to control the ChatGPT web interface through browser automation. It connects to an existing Chrome instance via CDP (Chrome DevTools Protocol) using a copied Chrome profile to maintain session persistence and bypass Cloudflare protection.

### Why CDP with Chrome Profile Copy?

- **Cloudflare Bypass**: Uses real Chrome profile with authenticated session
- **Session Persistence**: Maintains login state across MCP restarts
- **No Automation Flags**: Appears as regular user browser
- **Chrome Security**: Chrome blocks CDP on default profile, so we use a copy

## Core Components

### 1. MCP Server (`server.py`)
- Implements Model Context Protocol specification
- Exposes 19 tools for ChatGPT automation
- Handles async communication with Claude
- Manages browser controller lifecycle

### 2. Browser Controller (`browser_controller.py`)
- Manages CDP connection to Chrome
- Implements all ChatGPT interactions
- Handles sidebar state management
- Provides comprehensive error recovery

### 3. Error Recovery (`error_recovery.py`)
- Automatic retry with exponential backoff
- Browser crash recovery
- Session restoration
- Network error handling

### 4. Configuration (`config.py`)
- Environment-based configuration
- Chrome profile management
- Timeout and path settings

## Implementation Details

### Chrome Profile Management

```python
# Profile locations by platform
CHROME_PROFILES = {
    "darwin": "~/Library/Application Support/Google/Chrome-Automation",
    "win32": "%LOCALAPPDATA%\\Google\\Chrome-Automation",
    "linux": "~/.config/google-chrome-automation"
}
```

The MCP automatically:
1. Detects if Chrome is running with debugging
2. Copies default profile to Chrome-Automation (first run only)
3. Launches Chrome with `--remote-debugging-port=9222`
4. Connects via CDP using `playwright.chromium.connect_over_cdp()`

### Key Features Implemented

1. **Sidebar State Management**
   - `is_sidebar_open()`: Detects sidebar visibility
   - `toggle_sidebar()`: Opens/closes with Ctrl+Shift+S
   - Automatic handling in conversation operations

2. **Model Selection**
   - Supports all GPT models (4, 4.5, o1, o3, etc.)
   - Model name mapping for UI consistency
   - Verification after selection

3. **Conversation Management**
   - List all conversations with metadata
   - Switch between conversations
   - Delete conversations
   - Export in markdown/JSON formats

4. **Advanced Features**
   - Search/browse mode toggling
   - File upload support
   - Message editing
   - Response regeneration
   - Batch operations

### Selector Strategy

```python
# Current selectors (as of Jan 2025)
SELECTORS = {
    'model_button': '[data-testid="model-switcher-dropdown-button"]',
    'message_input': '#prompt-textarea',
    'send_button': '[data-testid="send-button"]',
    'messages': 'main article',
    'sidebar': 'nav[aria-label="Chat history"]',
    'new_chat': 'button[aria-label="New chat"]',
    'tools_menu': 'button[aria-label="Tools"]',
    'regenerate': 'span:has-text("Try again")'
}
```

## Error Handling & Recovery

### Automatic Recovery Scenarios
- **Browser Crashes**: Restart and restore session
- **Network Errors**: Retry with exponential backoff
- **Session Expiration**: Re-authentication (if credentials provided)
- **Element Not Found**: Page refresh and retry
- **Rate Limiting**: Intelligent waiting

### Recovery Implementation

```python
@with_error_recovery(
    max_retries=3,
    retry_delay=1.0,
    error_handlers={
        PlaywrightTimeout: lambda: "Refresh page and retry",
        TargetClosedError: lambda: "Restart browser"
    }
)
async def send_message(self, message: str):
    # Implementation with automatic recovery
```

## Testing Strategy

### Test Structure
- `tests/test_browser_controller.py`: Unit tests with mocks
- `tests/test_integration.py`: Full browser automation tests
- `tests/test_functional.py`: Quick smoke test

### Running Tests
```bash
# Unit tests
uv run pytest tests/test_browser_controller.py -v

# Integration tests (requires browser)
uv run pytest tests/test_integration.py --integration -v

# All tests with coverage
uv run pytest --cov=src/chatgpt_automation_mcp
```

## Performance Optimizations

1. **Connection Reuse**
   - Single CDP connection for entire session
   - No browser restarts between operations

2. **Smart Waiting**
   - Dynamic waits based on UI state
   - No fixed sleep delays
   - Efficient response detection

3. **Batch Operations**
   - Execute multiple operations in sequence
   - Shared context for efficiency
   - Error handling per operation

## Security Considerations

1. **Profile Isolation**
   - Separate Chrome-Automation profile
   - No modification of default profile
   - Clear cleanup instructions

2. **Credential Management**
   - Optional credentials in .env
   - Never logged or exposed
   - Session-based authentication preferred

3. **Local Execution**
   - CDP only on localhost
   - No remote browser control
   - Sandboxed browser process

## Known Limitations

1. **Chrome Requirement**: Must use Chrome (not Chromium/Edge)
2. **Single Tab**: Operations on active tab only
3. **UI Dependencies**: May break with ChatGPT UI changes
4. **Pro Features**: Some features require ChatGPT Pro

## Future Considerations

1. **Multi-tab Support**: Handle multiple ChatGPT tabs
2. **Advanced Modes**: Canvas, Projects integration
3. **Performance Metrics**: Token usage tracking
4. **Voice/Image**: Support multimodal inputs