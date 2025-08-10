# ChatGPT Automation MCP

A Model Context Protocol (MCP) server for automating ChatGPT web interface using Playwright. Provides programmatic control over ChatGPT conversations including model selection, message sending, and response retrieval.

## Features

- 🌐 **Browser Automation**: Controls ChatGPT web interface via Playwright
- 🤖 **Model Selection**: Switch between GPT-5, GPT-5 Thinking, GPT-5 Pro, and legacy models (o3, o4-mini, GPT-4.5, etc.)
- 💬 **Conversation Management**: New chats, send messages, get responses
- 🔄 **Session Persistence**: Maintain login state across sessions
- 🛡️ **Secure Configuration**: Environment-based configuration with .env support
- 🔍 **Auto Web Search**: Automatically enables web search for research-related queries
- 🔄 **Response Regeneration**: Regenerate ChatGPT responses through UI automation
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

# Install Playwright browsers
uv run playwright install chromium
```

### Browser Configuration

The MCP uses direct Playwright browser automation (no longer requires Chrome debugging setup). Browser sessions maintain login state across runs using Playwright's storage state feature.

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
- `chatgpt_select_model` - Switch to a different model (gpt-5, gpt-5-thinking, gpt-5-pro)
- `chatgpt_get_model` - Check current model
- `chatgpt_status` - Check if ChatGPT is ready
- `chatgpt_wait_response` - Wait for response completion
- `chatgpt_enable_think_longer` - Enable Think Longer mode for enhanced reasoning
- `chatgpt_enable_deep_research` - Enable Deep Research mode for comprehensive web research (250/month quota)
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
await chatgpt_select_model(model="gpt-5")
response = await chatgpt_send_and_get_response(
    message="Explain quantum computing",
    timeout=300  # GPT-5 thinking time
)
print(response)

# Enhanced reasoning with Think Longer
await chatgpt_enable_think_longer()
response = await chatgpt_send_and_get_response(
    message="Solve this complex logic puzzle...",
    timeout=600  # Extended timeout for thinking
)

# Deep Research for comprehensive information
await chatgpt_enable_deep_research()
response = await chatgpt_send_and_get_response(
    message="Research the history and impact of quantum computing",
    timeout=3600  # Deep research can take up to an hour
)

# Batch operations for efficiency
batch_result = await chatgpt_batch_operations(operations=[
    {"operation": "new_chat"},
    {"operation": "select_model", "args": {"model": "gpt-5-thinking"}},
    {"operation": "enable_think_longer"},
    {"operation": "send_and_get_response", "args": {
        "message": "Analyze this complex problem step by step",
        "timeout": 900
    }},
    {"operation": "save_conversation", "args": {"filename": "analysis"}},
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

**How it works:** When research keywords are detected, the tool adds "(Please search the web for this)" to your message, triggering ChatGPT's web search capability. This approach is more reliable than trying to navigate ChatGPT's frequently changing UI.

## Available Models (August 2025)

### Current Models

#### GPT-5 Family
- **GPT-5** - Flagship model, excellent for most tasks (5 minute timeout)
- **GPT-5 Thinking** - Get more thorough answers with extended reasoning (15 minute timeout)
- **GPT-5 Pro** - Research-grade intelligence for most advanced tasks (30 minute timeout)

### Legacy Models

#### GPT-4 Family
- **GPT-4o** - Legacy model, still reliable for general tasks (2 minute timeout)
- **GPT-4.5** - Good for writing and exploring ideas (3 minute timeout)
- **GPT-4.1** - Great for quick coding and analysis (1.5 minute timeout)
- **GPT-4.1-mini** - Faster for everyday tasks (1 minute timeout)

#### o-Series Reasoning Models
- **o3** - Uses advanced reasoning (10 minute timeout)
- **o3-pro** - Legacy reasoning expert (15 minute timeout)
- **o4-mini** - Fastest at advanced reasoning (1 minute timeout)

### Model Selection Tips
- **Default choice**: `gpt-5` for most development and creative tasks
- **Complex reasoning**: `gpt-5-thinking` or `o3-pro` for deep analysis
- **Critical research**: `gpt-5-pro` for the most sophisticated reasoning
- **Quick tasks**: `o4-mini` or `gpt-4.1-mini` for fastest responses
- **Writing focus**: `gpt-4.5` optimized for creative writing
- **Quick access**: Use `5` as shorthand for `gpt-5`, `4o` for `gpt-4o`

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

### Browser Session Issues

**Problem**: "Not logged in to ChatGPT"
- Login once in the browser window when it opens
- Session state will be saved automatically
- Future runs will maintain the login state

**Problem**: Browser won't launch
- Ensure Playwright Chromium is installed: `uv run playwright install chromium`
- Try with `HEADLESS=false` to see the browser window
- Restart the MCP server

### Login Issues
- Credentials in `.env` are optional (session state maintains login)
- Try with `HEADLESS=false` to debug visually
- Session state is stored in the temp/sessions directory

### Response Detection
- The tool waits for ChatGPT's thinking animation to complete
- Increase timeout for complex queries or reasoning models (GPT-5 Pro can take 30+ minutes!)
- Enable debug mode with `CHATGPT_LOG_LEVEL=DEBUG`

### Model Selection
- Not all models may be available to your account
- GPT-5 Thinking and GPT-5 Pro may require ChatGPT subscription
- Model names are case-sensitive
- GPT-5 Thinking and GPT-5 Pro are in the "Other models" menu

### Auto-Enable Web Search Issues
- Feature only works with `chatgpt_send_and_get_response` tool
- Check message contains research keywords: `latest`, `current`, `research`, etc.
- Web search may already be enabled (not an error)


### Error Recovery
- Error recovery is automatic and logged at INFO level
- Set `CHATGPT_LOG_LEVEL=DEBUG` for detailed recovery information
- Recovery attempts are limited to prevent infinite loops
- Browser restart is the ultimate fallback for persistent issues
- **Browser session reset** by deleting temp/sessions files is effective for persistent login issues

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