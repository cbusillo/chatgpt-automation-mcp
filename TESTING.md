# Testing Guide for ChatGPT Automation MCP

This document provides comprehensive guidance for running and maintaining the test suite for ChatGPT Automation MCP.

## 🎯 Test Overview

Our test suite provides **100% coverage** of all browser controller methods and comprehensive validation of MCP functionality with:

- **34 test functions** across **8 test files**
- **26 browser methods** fully tested
- **21 MCP tools** validated
- **Screenshot-based verification** for all UI interactions
- **Resilient selectors** with fallback strategies
- **Model-specific timeouts** for different ChatGPT models

## 🏗️ Test Infrastructure

### Test Categories

- **Unit Tests**: Fast tests without browser automation
- **Browser Tests**: Tests requiring browser interaction
- **Integration Tests**: Complete workflow tests  
- **Smoke Tests**: Basic functionality validation

### Test Markers

```python
@pytest.mark.browser      # Requires browser automation
@pytest.mark.integration  # Full integration test
@pytest.mark.slow         # Long-running test (minutes)
@pytest.mark.ui_dependent # Sensitive to UI changes
```

## 🚀 Running Tests

### Prerequisites

**IMPORTANT**: Browser tests require Chrome running with debugging port:
```bash
# Start Chrome with debugging (required for browser tests)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Or let the MCP handle it automatically when you run the MCP server
```

### Quick Start

```bash
# Run ALL tests (requires Chrome with debugging port)
uv run pytest

# Unit tests only (no browser required)
uv run pytest tests/test_mcp_server.py

# Specific browser test (requires Chrome)
uv run pytest tests/test_core_features.py::test_launch_browser

# Skip browser tests
SKIP_BROWSER_TESTS=true uv run pytest

# Use test suite runner
uv run python tests/test_suites.py unit  # Unit tests only
uv run python tests/test_suites.py smoke # Basic functionality
uv run python tests/test_suites.py all   # Everything
```

### Environment Variables

```bash
export SKIP_BROWSER_TESTS=false      # Enable browser tests
export SKIP_INTEGRATION_TESTS=false  # Enable integration tests  
export HEADLESS=true                 # Run browser in headless mode
export TEST_TIMEOUT=300              # Test timeout in seconds
```

### Test Suite Options

| Suite | Description | Duration | Browser Required |
|-------|-------------|----------|------------------|
| `unit` | MCP server tests only | < 1 min | No |
| `smoke` | Basic functionality | 2-5 min | Yes |
| `browser` | Browser automation | 5-15 min | Yes |
| `integration` | Complete workflows | 15-45 min | Yes |
| `all` | Full test suite | 30-60 min | Yes |

## 📁 Test File Organization

### Core Test Files

- **`test_mcp_server.py`** - MCP protocol and tool validation
- **`test_browser_features.py`** - Basic browser automation
- **`test_core_features.py`** - Core functionality (launch, screenshot, etc.)
- **`test_advanced_features.py`** - Advanced features (Think Longer, Deep Research)
- **`test_conversation_management.py`** - Conversation operations
- **`test_integration.py`** - End-to-end workflows

### Infrastructure Files

- **`conftest.py`** - Pytest fixtures and configuration
- **`test_utils.py`** - Resilient selectors and utilities
- **`test_suites.py`** - Test suite runner
- **`test_status_report.py`** - Coverage analysis

## 🔧 Test Features

### Screenshot-Based Verification

Every browser test automatically captures screenshots at key moments:

```python
async def test_send_message(browser):
    browser.test_name = "send_message"
    
    await browser.screenshot("before_send")
    await browser.controller.send_message("What is 2+2?")
    await browser.screenshot("after_send")
    
    # Verify with visual evidence
    await browser.verify_element('div[data-message-author-role="user"]')
```

Screenshots are saved to `tests/test_screenshots/` with descriptive names.

### Resilient Selectors

Tests use multiple fallback selectors to handle UI changes:

```python
# From test_utils.py
CHATGPT_SELECTORS = {
    'input_field': [
        'textarea[placeholder*="Message"]',
        'textarea#prompt-textarea', 
        'div[contenteditable="true"]',
        'textarea',
    ],
    'send_button': [
        'button[aria-label*="Send"]',
        'button:has-text("Send")',
        'button[data-testid*="send"]',
        'form button[type="submit"]',
    ]
}
```

### Adaptive Timeouts

Tests automatically adjust timeouts based on ChatGPT model:

```python
# From test_utils.py
MODEL_TIMEOUTS = {
    'gpt-5': 300,          # 5 minutes
    'gpt-5-thinking': 900,  # 15 minutes  
    'gpt-5-pro': 1800,     # 30 minutes
    'o3-pro': 3600,        # 60+ minutes
    'deep-research': 7200,  # 2 hours maximum
}
```

## 🛡️ Test Reliability

### Error Recovery

Tests include comprehensive error recovery:

```python
async def test_with_retry(browser):
    # Automatic retry with exponential backoff
    result = await TestRetryLogic.retry_with_backoff(
        lambda: browser.controller.select_model("GPT-5"),
        max_retries=3,
        base_delay=1.0
    )
```

### UI State Validation

```python
# Validate ChatGPT is ready before testing
validation = await UIStateValidator(browser.controller.page).validate_chatgpt_ready()

if not validation['ready']:
    pytest.skip(f"ChatGPT not ready: {validation['issues']}")
```

### Visual Debugging

Failed tests automatically capture diagnostic information:

- Screenshots at failure point
- Page content samples  
- Element detection results
- Suggested fixes

## 📊 Coverage Analysis

Generate detailed coverage reports:

```bash
# Generate test status report
uv run python tests/test_status_report.py

# View coverage by category
uv run pytest tests/ --collect-only --quiet
```

Current coverage: **100% of browser methods tested**

## 🔍 Debugging Tests

### Running Individual Tests

```bash
# Single test with verbose output
uv run pytest tests/test_core_features.py::test_launch_browser -v -s

# Run with visible browser (not headless)
HEADLESS=false uv run pytest tests/test_browser_features.py::test_send_message -v

# Run last failed tests only
uv run pytest --lf -v
```

### Debug Information

Tests provide extensive debug information:

- **Screenshots**: Visual evidence of test execution
- **Element Detection**: What selectors worked/failed
- **Timing Information**: How long operations took
- **Page State**: Content and structure analysis

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Tests hang | Waiting for UI element | Check screenshots, update selectors |
| Login required | Chrome profile issue | Delete automation profile, re-login |
| Timeout errors | Model taking too long | Increase timeout for specific model |
| Element not found | UI changed | Update selectors in test_utils.py |

## 🚀 Contributing Tests

### Adding New Tests

1. **Choose appropriate test file** based on feature category
2. **Use proper markers** (`@pytest.mark.browser`, etc.)
3. **Include screenshots** for UI verification
4. **Add multiple selectors** for resilience
5. **Set appropriate timeouts** based on operation

### Test Template

```python
@pytest.mark.browser
@pytest.mark.asyncio
async def test_new_feature(browser):
    """Test new feature with screenshot verification"""
    browser.test_name = "new_feature"
    
    # Setup
    await browser.screenshot("01_setup")
    
    # Execute feature
    result = await browser.controller.new_feature()
    await browser.screenshot("02_executed")
    
    # Verify result
    assert result is True
    await browser.verify_element('expected-element-selector')
    await browser.screenshot("03_verified")
```

### Best Practices

1. **Always verify with screenshots** - Don't trust return values alone
2. **Use descriptive test names** - Include feature and scenario
3. **Test edge cases** - Not just happy path
4. **Handle UI changes gracefully** - Multiple selectors, retries
5. **Keep tests independent** - Each test should work in isolation

## 📈 Performance

### Test Execution Times

- **Unit tests**: < 1 minute
- **Smoke tests**: 2-5 minutes  
- **Browser tests**: 5-15 minutes
- **Integration tests**: 15-45 minutes
- **Full suite**: 30-60 minutes

### Optimization Tips

- Run unit tests first for quick feedback
- Use smoke tests for continuous integration
- Run full suite before major releases
- Parallelize tests when possible (future enhancement)

## 🎯 Maintenance

### Regular Tasks

- **Weekly**: Run full test suite, check for flaky tests
- **Monthly**: Update selectors if ChatGPT UI changes
- **Quarterly**: Review test coverage and add missing tests
- **When needed**: Update timeouts based on model performance

### Monitoring

Watch for these indicators of needed maintenance:

- Tests failing due to "element not found"
- Increased timeout failures
- New browser methods not covered by tests
- New MCP tools without corresponding tests

## 📚 Additional Resources

- **CLAUDE.md**: Project-specific testing guidelines
- **docs/DEVELOPMENT_BEST_PRACTICES.md**: UI testing lessons learned
- **docs/TIMEOUT_AND_DELAY_GUIDELINES.md**: Model-specific timing
- **pytest.ini**: Test configuration and markers
- **test_status_report.md**: Latest coverage analysis

---

**Test Status**: 🟢 **EXCELLENT** (100% Coverage)  
**Production Ready**: ✅ **YES**