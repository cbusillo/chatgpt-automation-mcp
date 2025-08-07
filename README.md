# ChatGPT Automation MCP

A Model Context Protocol (MCP) server for automating ChatGPT web interface using Playwright. Provides programmatic control over ChatGPT conversations including model selection, message sending, and response retrieval.

## Features

- 🌐 **Browser Automation**: Controls ChatGPT web interface via Playwright
- 🤖 **Model Selection**: Switch between GPT-4o, o3, o3-pro, o4-mini, o4-mini-high, GPT-4.5, GPT-4.1, and GPT-4.1-mini
- 💬 **Conversation Management**: New chats, send messages, get responses
- 🔄 **Session Persistence**: Maintain login state across sessions
- 🛡️ **Secure Configuration**: Environment-based configuration with .env support
- 🔍 **Search Mode**: Toggle web search functionality
- 📤 **Export Conversations**: Save chats in various formats
- 🔧 **Comprehensive Error Recovery**: Automatic handling of network errors, timeouts, browser crashes, and session expiration
- ⚡ **Batch Operations**: Execute multiple operations in sequence for efficiency

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/chatgpt-automation-mcp.git
cd chatgpt-automation-mcp

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .

# Install Playwright browsers (only needed if not using CDP)
uv run playwright install chromium
```

### Chrome Setup for CDP Mode (Recommended)

**⚠️ CRITICAL**: Chrome does NOT allow `--remote-debugging-port` on the default profile for security reasons. We must use a separate profile copy.

#### Automatic Profile Management

The MCP automatically manages a dedicated Chrome profile for automation:

1. **Profile Location**:
   - macOS: `~/Library/Application Support/Google/Chrome-Automation`
   - Windows: `%LOCALAPPDATA%\Google\Chrome-Automation`
   - Linux: `~/.config/google-chrome-automation`

2. **First-time Setup**:
   - MCP copies your default Chrome profile to preserve logins
   - ChatGPT session and bookmarks are maintained
   - Profile runs independently of your main Chrome

3. **Automatic Launch**:
   - Chrome launches with `--remote-debugging-port=9222`
   - Navigates directly to ChatGPT
   - Maintains persistent login state

#### Troubleshooting Profile Issues

**If Chrome opens to a folder listing instead of ChatGPT:**

1. **Delete the automation profile**:
   ```bash
   # macOS
   rm -rf ~/Library/Application\ Support/Google/Chrome-Automation
   
   # Windows
   rmdir /s "%LOCALAPPDATA%\Google\Chrome-Automation"
   
   # Linux
   rm -rf ~/.config/google-chrome-automation
   ```

2. **Restart the MCP** - it will recreate the profile from your current default profile

3. **Login to ChatGPT** in the new automation browser window

**Profile becomes corrupted:**
- Same solution as above - delete and recreate
- The MCP will always copy from your current default profile

**Why This Architecture?**
- **Security**: Chrome blocks debugging on default profiles
- **Isolation**: Automation doesn't interfere with regular browsing  
- **Persistence**: Maintains ChatGPT login across sessions
- **Recovery**: Easy to reset by deleting automation profile

**Important Notes**:
- Keep Chrome running while using the MCP server
- Profile uses ~100-500MB disk space (copy of your default profile)
- Safe for local use only - debugging port is localhost-only
- When uninstalling, delete Chrome-Automation directory to free space

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```env
# Optional - browser may already be logged in
CHATGPT_EMAIL=your_email@example.com
CHATGPT_PASSWORD=your_password

# Browser settings
HEADLESS=false
BROWSER_TIMEOUT=30000

# Session persistence
PERSIST_SESSION=true
SESSION_NAME=default
```

## Usage

### As MCP Server

Add to your Claude desktop configuration:

```json
{
  "mcpServers": {
    "chatgpt": {
      "command": "uv",
      "args": ["run", "chatgpt-mcp"],
      "cwd": "/path/to/chatgpt-automation-mcp"
    }
  }
}
```

### Available Tools

- `chatgpt_launch` - Launch ChatGPT in browser
- `chatgpt_new_chat` - Start a new conversation
- `chatgpt_send_message` - Send a message
- `chatgpt_send_and_get_response` - Send message and wait for response (auto-enables web search for research keywords)
- `chatgpt_get_last_response` - Get the most recent response
- `chatgpt_get_conversation` - Get full conversation history
- `chatgpt_select_model` - Switch to a different model
- `chatgpt_get_model` - Check current model
- `chatgpt_status` - Check if ChatGPT is ready
- `chatgpt_wait_response` - Wait for response completion
- `chatgpt_toggle_search` - Enable/disable web search mode
- `chatgpt_toggle_browsing` - Enable/disable web browsing mode
- `chatgpt_upload_file` - Upload a file to the conversation
- `chatgpt_regenerate` - Regenerate the last response
- `chatgpt_export_conversation` - Export conversation as markdown or JSON
- `chatgpt_save_conversation` - Save conversation to file
- `chatgpt_edit_message` - Edit a previous user message
- `chatgpt_list_conversations` - List all available conversations
- `chatgpt_switch_conversation` - Switch to a different conversation
- `chatgpt_delete_conversation` - Delete a conversation
- `chatgpt_batch_operations` - Execute multiple operations in sequence

### Example Usage

```python
# Basic conversation flow
await chatgpt_launch()
await chatgpt_new_chat()
await chatgpt_select_model(model="o3")
response = await chatgpt_send_and_get_response(
    message="Explain quantum computing",
    timeout=120  # O3 can take time to think
)
print(response)

# Batch operations for efficiency
batch_result = await chatgpt_batch_operations(operations=[
    {"operation": "new_chat"},
    {"operation": "select_model", "args": {"model": "o3"}},
    {"operation": "send_and_get_response", "args": {
        "message": "Write a Python function to sort a list",
        "timeout": 60
    }},
    {"operation": "save_conversation", "args": {"filename": "python_help"}},
])
print(f"Batch completed: {batch_result['successful_operations']}/{batch_result['total_operations']} operations successful")
```

## Smart Features

### Auto-Enable Web Search

The `chatgpt_send_and_get_response` tool automatically enables web search when your message contains research-related keywords:

**Trigger Keywords:**
- `research`, `latest`, `current`, `recent`, `2025`, `2024`, `2026`
- `update`, `new`, `find`, `search`, `discover`, `investigate`
- `what's new`, `recent changes`, `current state`, `up to date`

**Example:**
```python
# This will automatically enable web search
response = await chatgpt_send_and_get_response(
    message="What are the latest Odoo 18 performance improvements?"
)

# This will not trigger auto-enable
response = await chatgpt_send_and_get_response(
    message="Write a Python function to sort a list"
)
```

This ensures ChatGPT has access to current information for research queries, preventing hallucinated responses about recent developments.

## Available Models (July 2025)

### Main Models
- **GPT-4o** - Default model, multimodal (text/image/audio), very fast (<1s)
- **o3** - Advanced reasoning, 1-2s response + thinking time
- **o3-pro** - Best reasoning, can take 10+ minutes! Use sparingly
- **o4-mini** - Fastest reasoning model (0.5-1s)
- **o4-mini-high** - Best balance of speed and coding ability (0.8-1.5s) - **Recommended default**

### Additional Models (More models menu)
- **GPT-4.5** - Creative ideation, novel solutions (deprecated July 14, 2025)
- **GPT-4.1** - Huge context (1M tokens), 15s-1min for large files
- **GPT-4.1-mini** - Faster variant of GPT-4.1 with same context

### Model Selection Tips
- **Default choice**: `o4-mini-high` for most development tasks
- **Quick scripts**: `o4-mini` for fastest response
- **Complex problems**: `o3` when you need deep reasoning
- **Critical code**: `o3-pro` only for mission-critical analysis (very slow!)
- **Large codebases**: `GPT-4.1` or `GPT-4.1-mini` for 1M token context

## Development

### Installing Dependencies

This project uses UV for dependency management:

```bash
# Install all dependencies including dev dependencies
uv sync --dev
```

### Running Tests

```bash
# Run unit tests
uv run pytest tests/test_browser_controller.py -v

# Run all tests with coverage
uv run pytest --cov=src/chatgpt_automation_mcp --cov-report=html

# Run specific test
uv run pytest -k test_sidebar_handling -v

# Run functional test (requires browser)
uv run python tests/test_functional.py

# Or use the test runner script
uv run run-tests --unit        # Unit tests only
uv run run-tests --integration # Integration tests (requires browser)
uv run run-tests --auto-enable # Auto-enable web search tests (fast, no browser needed)
uv run run-tests --all         # All tests
uv run run-tests --coverage    # With coverage report
```

### Test Structure

- `tests/test_browser_controller.py` - Unit tests with mocked browser
- `tests/test_integration.py` - Integration tests with real browser
- `tests/test_functional.py` - Quick smoke test for basic functionality
- `tests/test_auto_enable_search.py` - Auto-enable web search keyword detection tests
- `tests/test_server_auto_enable.py` - Server integration tests for auto-enable feature
- `tests/test_web_search_verification.py` - Visual verification tests with screenshots
- `run_tests.py` - Test runner with various options

### Code Quality

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix linting issues
uv run ruff check . --fix
```

### Development Best Practices

See [docs/DEVELOPMENT_BEST_PRACTICES.md](docs/DEVELOPMENT_BEST_PRACTICES.md) for important lessons learned about:
- Visual verification testing with screenshots
- Handling ChatGPT UI changes
- Selector best practices
- Common pitfalls and debugging tips

## Error Handling & Recovery

The MCP server includes comprehensive error handling and automatic recovery for common issues:

### Automatic Recovery Scenarios
- **Network Errors**: Automatic retry with exponential backoff
- **Browser Crashes**: Automatic browser restart and session restoration
- **Session Expiration**: Automatic re-authentication when needed
- **Element Not Found**: Page refresh and element waiting
- **Timeout Errors**: Extended waiting and page responsiveness checks
- **Rate Limiting**: Intelligent waiting with exponential backoff

### Error Types Handled
- Connection failures and network instability
- ChatGPT UI changes and element location issues
- Browser crashes and unexpected closures
- Authentication token expiration
- Rate limiting from excessive requests
- Page loading timeouts and delays

### Recovery Strategies
- **Exponential Backoff**: Progressively longer delays between retries
- **Multiple Selectors**: Fallback element selectors for UI changes
- **Session Restoration**: Automatic login when sessions expire
- **Context Preservation**: Maintain conversation state during recovery
- **Graceful Degradation**: Continue operation even with partial failures

## Troubleshooting

### Chrome Profile Issues (Most Common)

**Problem**: Chrome opens to folder listing instead of ChatGPT
```
Folder: file:///Users/user/Library/Application Support/Google/Chrome-Automation/
```

**Solution**:
```bash
# Delete corrupted automation profile
rm -rf ~/Library/Application\ Support/Google/Chrome-Automation  # macOS
rmdir /s "%LOCALAPPDATA%\Google\Chrome-Automation"              # Windows
rm -rf ~/.config/google-chrome-automation                       # Linux

# Restart MCP - it will recreate the profile
```

**Problem**: "Not logged in to ChatGPT" after profile reset
- **Expected behavior** on first run with new profile
- Login once in the automation browser window
- Session will persist for future runs

**Problem**: Browser won't launch or connect
- Check if port 9222 is already in use: `lsof -i :9222` (macOS/Linux)
- Close existing Chrome debugging sessions
- Restart the MCP server

### Login Issues
- Credentials in `.env` are optional (profile usually maintains login)
- Try with `HEADLESS=false` to debug visually
- Check if automation profile has valid ChatGPT session

### Response Detection
- The tool waits for ChatGPT's thinking animation to complete
- Increase timeout for complex queries or reasoning models (o3-pro can take 60+ minutes!)
- Enable debug mode with `CHATGPT_LOG_LEVEL=DEBUG`

### Model Selection
- Not all models may be available to your account
- O3 models require ChatGPT Pro subscription
- Model names are case-sensitive
- Some models may be in "More models" menu

### Auto-Enable Web Search Issues
- Feature only works with `chatgpt_send_and_get_response` tool
- Check message contains research keywords: `latest`, `current`, `research`, etc.
- Web search may already be enabled (not an error)

### Known CDP Connection Limitations
**UI Rendering Issues with CDP Mode**
- When using CDP mode (required to bypass Cloudflare), some UI elements may not render correctly
- Sidebar icons may appear invisible or white-on-white
- Theme may appear inconsistent (mix of light/dark mode)
- **This is a known limitation** of Chrome DevTools Protocol connections
- **The automation remains fully functional** despite visual issues
- This cannot be fixed from our side - it's a fundamental CDP limitation
- If you need proper UI visibility, you would need to use regular Playwright mode (which gets blocked by Cloudflare)

### Error Recovery
- Error recovery is automatic and logged at INFO level
- Set `CHATGPT_LOG_LEVEL=DEBUG` for detailed recovery information
- Recovery attempts are limited to prevent infinite loops
- Browser restart is the ultimate fallback for persistent issues
- **Chrome profile reset** is the most effective solution for persistent issues

## Security

- Credentials are stored in `.env` (never commit this file)
- Browser sessions are isolated in temp directories
- Screenshots on error are stored locally only
- All temporary files are gitignored

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details