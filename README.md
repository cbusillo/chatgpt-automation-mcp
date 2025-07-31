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
- `chatgpt_upload_file` - Upload a file to the conversation
- `chatgpt_regenerate` - Regenerate the last response
- `chatgpt_export_conversation` - Export conversation as markdown or JSON
- `chatgpt_save_conversation` - Save conversation to file
- `chatgpt_edit_message` - Edit a previous user message

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
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .
```

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