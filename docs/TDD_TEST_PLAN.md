# TDD Test Plan for ChatGPT Automation MCP

## 🎯 Mission: Fix All Broken Features Using TDD

**Date**: August 14, 2025  
**Approach**: Test-Driven Development with Visual Verification  
**Tool**: Browser MCP (NOT Playwright MCP)

## 📊 Current Feature Status (Aug 14, 2025)

### ✅ Working (Verified)
| Feature | Status | Test Coverage | Notes |
|---------|--------|---------------|-------|
| URL Model Selection | ✅ Working | Needs tests | Revolutionary breakthrough! |
| Send Message | ✅ Working | Has tests | Basic functionality intact |
| Get Response | ✅ Working | Has tests | Works with timeouts |
| Get Current Model | ✅ Working | Updated | Handles new UI text |
| Launch Browser | ✅ Working | Has tests | Session persistence works |

### 🔧 Code Updated (Need Verification)
| Feature | Status | Changes Made | Priority |
|---------|--------|--------------|----------|
| Think Longer Mode | 🔧 Updated | Now uses model switch to gpt-5-thinking | VERIFY NOW |
| Deep Research Mode | 🔧 Updated | Found in attachment menu, code updated | VERIFY NOW |
| MCP Tool Integration | ⚠️ Partial | Some tools fail via MCP | HIGH |
| Web Search Toggle | ❓ Unknown | Not tested | MEDIUM |
| File Upload | ❓ Unknown | Not tested | LOW |

## 🧪 TDD Implementation Plan

### Phase 1: Visual Discovery Tests (Week 1)

#### Test 1: Map Current UI Elements
```python
# tests/test_ui_discovery.py
import pytest
from browser_mcp import BrowserMCP

@pytest.mark.visual
@pytest.mark.discovery
async def test_discover_all_ui_elements():
    """
    Use Browser MCP to map ALL interactive elements.
    This test documents the current UI state.
    """
    browser = BrowserMCP()
    await browser.navigate("https://chatgpt.com")
    
    # Take comprehensive screenshots
    screenshots = []
    
    # 1. Main interface
    screenshots.append(await browser.screenshot("main_interface"))
    
    # 2. Model selector expanded
    await browser.click_model_selector()
    screenshots.append(await browser.screenshot("model_menu"))
    
    # 3. Input area focused
    await browser.click_input_area()
    screenshots.append(await browser.screenshot("input_focused"))
    
    # 4. Look for attachment/menu buttons
    snapshot = await browser.get_snapshot()
    
    # Document all buttons found
    buttons = extract_all_buttons(snapshot)
    save_ui_map(buttons, screenshots)
    
    assert len(buttons) > 0, "Should find interactive elements"
```

#### Test 2: Find Think Longer UI
```python
# tests/test_think_longer_tdd.py
@pytest.mark.visual
@pytest.mark.tdd
async def test_find_think_longer_mode():
    """
    TDD: This test WILL FAIL initially.
    Goal: Find where Think Longer mode is in the new UI.
    """
    browser = BrowserMCP()
    await browser.navigate("https://chatgpt.com/?model=gpt-5-thinking")
    
    # Expected: Find a way to enable Think Longer
    # Hypothesis 1: It's in a menu near the input
    # Hypothesis 2: It's a toggle/button when certain models selected
    # Hypothesis 3: It appears contextually with certain prompts
    
    # This SHOULD fail initially
    result = await find_think_longer_option(browser)
    assert result is not None, "Think Longer option should exist somewhere"
    
    # When found, document location
    await browser.screenshot("think_longer_location")
```

#### Test 3: Find Deep Research UI
```python
# tests/test_deep_research_tdd.py
@pytest.mark.visual
@pytest.mark.tdd
async def test_find_deep_research_mode():
    """
    TDD: This test WILL FAIL initially.
    Goal: Find where Deep Research mode is in the new UI.
    """
    browser = BrowserMCP()
    await browser.navigate("https://chatgpt.com/?model=gpt-5-pro")
    
    # Deep Research might be:
    # - In a tools menu
    # - A button that appears with research queries
    # - In model-specific options
    
    # This SHOULD fail initially
    result = await find_deep_research_option(browser)
    assert result is not None, "Deep Research should exist (users pay for it!)"
    
    await browser.screenshot("deep_research_location")
```

### Phase 2: Implementation Tests (Week 2)

#### Test 4: Model Selection Comprehensive
```python
# tests/test_model_selection_comprehensive.py
@pytest.mark.visual
@pytest.mark.comprehensive
async def test_all_model_selections():
    """Test every model with visual verification."""
    
    test_cases = [
        ("gpt-5", "ChatGPT 5"),
        ("gpt-5-thinking", "ChatGPT 5 Thinking"),
        ("gpt-5-pro", "ChatGPT 5 Pro"),
        ("o3", "ChatGPT o3"),
        ("gpt-4-1", "ChatGPT 4.1"),
    ]
    
    for model_key, expected_text in test_cases:
        # Navigate using URL method
        await browser.navigate(f"https://chatgpt.com/?model={model_key}")
        
        # Visual verification
        screenshot = await browser.screenshot(f"model_{model_key}")
        
        # Structural verification
        current_model = await get_current_model_from_ui(browser)
        assert expected_text in current_model
        
        # Store reference screenshot
        save_reference_screenshot(screenshot, model_key)
```

#### Test 5: Think Longer Activation
```python
# tests/test_think_longer_activation.py
@pytest.mark.visual
@pytest.mark.integration
async def test_activate_think_longer():
    """Test Think Longer activation after we know where it is."""
    
    controller = ChatGPTController()
    
    # Setup
    await controller.select_model("gpt-5-thinking")
    await browser.screenshot("before_think_longer")
    
    # Activate (this should work after Phase 1 discovery)
    result = await controller.enable_think_longer()
    assert result == True
    
    # Verify visually
    await browser.screenshot("after_think_longer")
    
    # Verify functionally
    await controller.send_message("Complex reasoning question...")
    response = await controller.wait_for_response(timeout=600)
    
    # Think Longer responses should have certain characteristics
    assert len(response) > 1000  # Longer responses
    assert "thinking" in response.lower()  # May reference its thinking
```

### Phase 3: Regression Tests (Week 3)

#### Test 6: Visual Regression Suite
```python
# tests/test_visual_regression.py
@pytest.mark.visual
@pytest.mark.regression
async def test_visual_regression():
    """Compare current UI with reference screenshots."""
    
    test_scenarios = [
        "main_interface",
        "model_menu_open",
        "message_sent",
        "response_received",
        "think_longer_enabled",
        "deep_research_enabled",
    ]
    
    for scenario in test_scenarios:
        current = await capture_scenario(scenario)
        reference = load_reference_screenshot(scenario)
        
        diff = compare_screenshots(current, reference)
        assert diff < 0.05, f"UI changed significantly for {scenario}"
        
        if diff > 0.01:
            log_warning(f"Minor UI change in {scenario}: {diff}")
```

## 📋 Test Execution Strategy

### Daily Tests (CI/CD)
```bash
# Quick smoke tests - 5 minutes
pytest -m "smoke" --browser-mcp

# Visual regression - 10 minutes  
pytest -m "visual and regression"
```

### Weekly Tests
```bash
# Comprehensive feature tests - 30 minutes
pytest -m "comprehensive" --browser-mcp --screenshots

# TDD tests for broken features
pytest -m "tdd" --browser-mcp
```

### On Demand
```bash
# Discovery tests when UI changes
pytest -m "discovery" --browser-mcp --save-screenshots

# Specific feature test
pytest tests/test_think_longer_tdd.py -v
```

## 🛠️ Test Infrastructure Requirements

### 1. Browser MCP Setup
```python
# conftest.py
import pytest
from browser_mcp import BrowserMCP

@pytest.fixture
async def browser():
    """Provide Browser MCP instance for tests."""
    browser = BrowserMCP()
    await browser.launch()
    yield browser
    await browser.close()

@pytest.fixture
def screenshot_dir(tmp_path):
    """Create directory for test screenshots."""
    dir = tmp_path / "screenshots"
    dir.mkdir()
    return dir
```

### 2. Visual Comparison Tools
```python
# test_utils/visual.py
from PIL import Image
import imagehash

def compare_screenshots(img1_path, img2_path):
    """Compare two screenshots using perceptual hashing."""
    hash1 = imagehash.average_hash(Image.open(img1_path))
    hash2 = imagehash.average_hash(Image.open(img2_path))
    return hash1 - hash2

def save_reference_screenshot(img_path, name):
    """Save screenshot as reference for future comparisons."""
    ref_dir = Path("tests/reference_screenshots")
    ref_dir.mkdir(exist_ok=True)
    shutil.copy(img_path, ref_dir / f"{name}.png")
```

### 3. UI Mapping Tools
```python
# test_utils/ui_mapper.py
def extract_all_buttons(snapshot):
    """Extract all interactive elements from Browser MCP snapshot."""
    buttons = []
    for element in snapshot:
        if element.get('role') in ['button', 'menuitem', 'link']:
            buttons.append({
                'text': element.get('text'),
                'ref': element.get('ref'),
                'role': element.get('role'),
                'aria_label': element.get('aria-label'),
            })
    return buttons

def save_ui_map(elements, screenshots):
    """Save UI map for documentation."""
    with open('tests/ui_maps/current.json', 'w') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'elements': elements,
            'screenshots': [s.name for s in screenshots],
        }, f, indent=2)
```

## 🎯 Success Criteria

### Phase 1 Complete When:
- [x] All UI elements mapped and documented
- [x] Think Longer location found (automatic with model)
- [x] Deep Research location found (attachment menu)
- [x] Reference screenshots captured
- [ ] **FEATURES TESTED AND VERIFIED WORKING**

### Phase 2 Complete When:
- [ ] All broken features have passing tests
- [ ] Visual verification for all features
- [ ] Documentation updated with fixes

### Phase 3 Complete When:
- [ ] Visual regression suite running daily
- [ ] All tests passing consistently
- [ ] UI changes detected automatically

## 📈 Metrics

Track these metrics to measure progress:

1. **Test Coverage**: % of features with tests
2. **Visual Coverage**: % of UI states with screenshots
3. **Fix Rate**: Broken features fixed per week
4. **Regression Rate**: Tests catching UI changes
5. **Reliability**: % of tests passing consistently

## 🚨 Red Flags

Stop and reassess if:
- UI changes faster than we can update tests
- Browser MCP stops working with ChatGPT
- More than 50% of tests failing
- Can't find Think Longer/Deep Research after extensive search

## 🎉 Definition of Done

The project is complete when:
1. ✅ All features working and tested
2. ✅ Visual regression suite in place
3. ✅ Documentation complete and accurate
4. ✅ TDD process documented for future changes
5. ✅ 95%+ test pass rate for 7 consecutive days

---

*Remember: Write the test first, make it fail, then make it pass. This is the way.*