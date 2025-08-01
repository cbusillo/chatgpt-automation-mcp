# CLAUDE.md

Claude Code guidance for ChatGPT Automation MCP.

## 🎯 Critical Thinking Directive

**ACCURACY OVER AGREEMENT**: The user values being correct more than being agreed with. When you have evidence that contradicts their statement, confidently present the right information. Pattern: "Actually, I think [X] because [evidence]. Here's why [Y] would be better." Be assertive about facts, not opinions.

## Project Overview

MCP server for automating ChatGPT web interface via Playwright. Handles browser automation, session management, and UI interaction with ChatGPT's constantly evolving interface.

**Stack**: Python 3.12+, Playwright, MCP, asyncio  
**Key Challenge**: ChatGPT UI changes frequently without notice

## 📚 Essential Documentation

- **[README.md](README.md)** - Installation, usage, API reference
- **[docs/DEVELOPMENT_BEST_PRACTICES.md](docs/DEVELOPMENT_BEST_PRACTICES.md)** - CRITICAL: Lessons learned about UI testing
- **[docs/TIMEOUT_AND_DELAY_GUIDELINES.md](docs/TIMEOUT_AND_DELAY_GUIDELINES.md)** - Model-specific timeouts
- **[docs/CHROME_PROFILE_MANAGEMENT.md](docs/CHROME_PROFILE_MANAGEMENT.md)** - CRITICAL: Chrome profile troubleshooting

## 🚨 Critical Rules for This Project

### 0. Chrome Profile Management (CRITICAL)

**Why Separate Profile Required:**
Chrome security prevents `--remote-debugging-port` on default profiles. Attempting to use default profile results in Chrome opening folder listings instead of web pages.

**Automatic Management:**
- **Location**: `~/Library/Application Support/Google/Chrome-Automation` (macOS)
- **Creation**: Browser controller copies default profile on first run
- **Purpose**: Maintains ChatGPT login while enabling debugging

**Common Issues & Solutions:**

1. **Chrome opens folder listing instead of ChatGPT**:
   ```bash
   # Root cause: Profile corruption or incorrect command line args
   rm -rf ~/Library/Application\ Support/Google/Chrome-Automation
   # MCP will recreate from current default profile
   ```

2. **"Not logged in" after profile recreation**:
   - Expected on first run with new profile
   - Login to ChatGPT in automation browser
   - Session persists for future runs

3. **Command line argument parsing issues**:
   - Paths with spaces must be properly quoted in shell commands
   - Browser controller uses shell=True on macOS for proper path handling
   - Incorrect: `--user-data-dir /path with spaces/` → Opens folder as file
   - Correct: `--user-data-dir "/path with spaces/"` → Uses as profile

**Technical Implementation:**
```python
# macOS shell command approach (handles spaces)
cmd = f'"{chrome_path}" --remote-debugging-port={port} --user-data-dir="{user_data_dir}" "https://chatgpt.com"'
subprocess.Popen(cmd, shell=True)

# NOT: args list approach (fails with spaces)
args = [chrome_path, f"--user-data-dir={user_data_dir}"]  # Breaks on spaces
```

**Profile Recovery:**
- Always delete automation profile, never try to fix in-place
- MCP creates fresh copy from current default profile
- Preserves latest login state and preferences

### 1. Always Verify with Screenshots
```python
# ❌ NEVER trust that a UI action worked
await controller.toggle_search_mode(True)  # This can "succeed" but do nothing!

# ✅ ALWAYS verify the outcome
await controller.toggle_search_mode(True)
await page.screenshot(path="verify.png")
assert await page.locator('text="Search the web"').count() > 0
```

### 2. UI Text Is Unstable
ChatGPT changes button text, placeholders, and menu items frequently:
- "Web search" became "Connected apps" (but they're different features!)
- "Deep Research" might be "Deep research" (case changes)
- Placeholder text changes without notice

**Solution**: Test for outcomes, not specific text when possible.

### 3. Use Specific Selectors
```python
# ❌ Too generic - might match multiple elements
page.locator('div:has-text("Deep Research")')

# ✅ Specific role + text
page.locator('div[role="menuitemradio"]:has-text("Deep research")').first
```

### 4. Timeouts Are Critical
- **o3-pro**: Can take 60+ minutes (not 15!)
- **Deep Research**: Can take 2-6 hours (not 10 minutes!)
- **Regular models**: Still need 2+ minutes for safety

Always use real data from actual usage, not documentation claims.

## 🧪 Testing Philosophy

1. **Integration tests > Unit tests** for browser automation
2. **Screenshot verification** for every critical flow
3. **Test against real UI** not mocks
4. **Expect UI changes** - build resilient selectors

## 🔧 Development Workflow

1. **Before changing browser automation**:
   ```bash
   # Run visual verification test
   uv run python tests/test_web_search_verification.py
   # Check screenshots in test_screenshots/
   ```

2. **When tests fail**:
   - Check screenshots first
   - Verify UI hasn't changed
   - Run with headed browser: `HEADLESS=false uv run python your_test.py`

3. **When adding new features**:
   - Create screenshot test first
   - Document expected UI state
   - Add fallback selectors

## 🤖 Smart Auto-Features

### Auto-Enable Web Search

The MCP automatically enables web search when research keywords are detected in `chatgpt_send_and_get_response`:

**Trigger Keywords**: `research`, `latest`, `current`, `recent`, `2025`, `2024`, `2026`, `update`, `new`, `find`, `search`, `discover`, `investigate`, `what's new`, `recent changes`, `current state`, `up to date`

This prevents ChatGPT from hallucinating about recent developments (like o3 model capabilities) and ensures access to current information.

## 🚀 Quick Patterns

### Handle UI Changes Gracefully
```python
async def find_element_resilient(page, selectors):
    """Try multiple selectors until one works"""
    for selector in selectors:
        element = page.locator(selector).first
        if await element.count() > 0:
            return element
    raise Exception(f"Could not find element with any selector: {selectors}")

# Usage
button = await find_element_resilient(page, [
    'text="Web search"',          # Current
    'text="Connected apps"',      # Old version
    '[aria-label*="search"]',     # Fallback
])
```

### Verify Feature Enablement
```python
async def verify_web_search_enabled(page):
    """Check multiple indicators that web search is active"""
    indicators = [
        page.locator('text="Search the web"'),
        page.locator('input[placeholder="Search the web"]'),
        page.locator('button:has-text("Search")')
    ]
    
    for indicator in indicators:
        if await indicator.count() > 0:
            return True
    return False
```

## ⚠️ Common Pitfalls

1. **Trusting success returns** - Always verify UI state
2. **Hardcoding timeouts** - Use model-aware timeouts
3. **Single selector strategy** - Have fallbacks
4. **Not capturing evidence** - Take screenshots
5. **Testing in isolation** - Run against real ChatGPT

## 🐛 Debugging Checklist

When something breaks:

1. ✅ Screenshot at failure point
2. ✅ Check if UI text changed (most common!)
3. ✅ Verify selector matches elements
4. ✅ Check browser console
5. ✅ Try with `HEADLESS=false`
6. ✅ Compare with reference screenshots

## 📈 Performance Considerations

- **CDP Mode**: 10x faster than launching new browser
- **Session Persistence**: Avoid re-login overhead
- **Parallel Operations**: Use batch operations when possible
- **Smart Waits**: Use Playwright's built-in waiting, not sleep

## 🔮 Future-Proofing

This project will require constant maintenance as ChatGPT evolves. When updating:

1. Document UI changes in git commits
2. Keep screenshot references
3. Add new selectors without removing old ones (initially)
4. Update timeout values based on real-world usage
5. Maintain compatibility with multiple UI versions when possible

Remember: **We're automating a moving target!**