# ChatGPT Automation MCP

A Model Context Protocol (MCP) server for automating ChatGPT web interface using Playwright. Provides programmatic control over ChatGPT conversations including model selection, message sending, and response retrieval.

## Features

- 🌐 **Browser Automation**: Controls ChatGPT web interface via Playwright
- 🤖 **Model Selection**: Switch between GPT-4, GPT-4.1, O1, O3, and other models
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

To bypass Cloudflare protection, we use a copy of your Chrome profile with remote debugging enabled:

1. **The MCP will automatically create a Chrome profile copy** at:
   - macOS: `~/Library/Application Support/Google/Chrome-Automation`
   - Windows: `%LOCALAPPDATA%\Google\Chrome-Automation`
   - Linux: `~/.config/google-chrome-automation`

2. **First time setup**: The MCP will copy your default Chrome profile to preserve logins

3. **Chrome will launch automatically** with debugging enabled when you use the MCP

4. **Keep Chrome running** while using the MCP server

**Important**: When uninstalling, remember to delete the Chrome-Automation profile directory to free up disk space.

**Note**: The debugging port allows the MCP to control Chrome. This is safe for local use only.

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
- `chatgpt_send_and_get_response` - Send message and wait for response
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
uv run run-tests --all         # All tests
uv run run-tests --coverage    # With coverage report
```

### Test Structure

- `tests/test_browser_controller.py` - Unit tests with mocked browser
- `tests/test_integration.py` - Integration tests with real browser
- `tests/test_functional.py` - Quick smoke test for basic functionality
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

### Login Issues
- Ensure credentials are set in `.env`
- Try with `HEADLESS=false` to debug visually
- Check if browser session is persisted correctly

### Response Detection
- The tool waits for ChatGPT's thinking animation to complete
- Increase timeout for complex queries or reasoning models
- Enable debug mode for detailed logs

### Model Selection
- Not all models may be available to your account
- O3 models require Pro subscription
- Model names are case-sensitive

### Error Recovery
- Error recovery is automatic and logged at INFO level
- Set logging level to DEBUG for detailed recovery information
- Recovery attempts are limited to prevent infinite loops
- Browser restart is the ultimate fallback for persistent issues

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