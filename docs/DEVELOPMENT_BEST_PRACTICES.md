# Development Best Practices for ChatGPT Automation MCP

## 🚀 BREAKTHROUGH: URL-Based Model Selection (August 2025)

### The Discovery
ChatGPT's UI changes constantly, breaking menu-based navigation. However, ChatGPT accepts URL parameters for model selection!

```python
# ❌ OLD: Complex, fragile UI navigation
await click_model_picker()
await wait_for_menu()
await hover_over_legacy_models()
await click_model_option()
# ... lots of error-prone steps

# ✅ NEW: Direct, reliable URL navigation
await page.goto("https://chatgpt.com/?model=gpt-5")
# Done! Model selected instantly and reliably
```

### Working URL Patterns
```python
# GPT-5 Family
"https://chatgpt.com/?model=gpt-5"          # Auto/Default
"https://chatgpt.com/?model=gpt-5-thinking" # Extended reasoning
"https://chatgpt.com/?model=gpt-5-pro"      # Research-grade

# Legacy Models  
"https://chatgpt.com/?model=o3"             # Reasoning model
"https://chatgpt.com/?model=gpt-4-1"        # Note: dash not dot!
```

### Why This Is Gold
- **100% reliable** - No UI changes can break it
- **10x faster** - Direct navigation vs menu clicking
- **Self-documenting** - URL shows exactly what model is selected
- **Future-proof** - URLs rarely change compared to UI

## 🔍 Testing Philosophy

### Always Verify with Visual Evidence

**Lesson Learned**: Tests can report success while the UI is in the wrong state.

```python
# ❌ BAD: Trust that click worked
await controller.toggle_search_mode(True)
assert result == True  # This passed but web search wasn't actually enabled!

# ✅ GOOD: Verify the actual UI state
await controller.toggle_search_mode(True)
await page.screenshot(path="verification.png")
assert await page.locator('text="Search the web"').count() > 0
```

**Key Principle**: Screenshots are your truth - automated assertions can lie, images don't.

### UI Text Changes Break Automation

**Lesson Learned**: ChatGPT changed "Web search" to "Connected apps" - our tests didn't catch it.

```python
# ❌ BAD: Mock the interaction
controller.toggle_search_mode = AsyncMock(return_value=True)

# ✅ GOOD: Test against real UI
success = await controller.toggle_search_mode(True)
# Then verify with screenshot or actual UI element check
```

**Mitigation Strategy**:
1. Run integration tests regularly against live UI
2. Store reference screenshots for comparison
3. Test for expected outcomes, not just method success

### Verify Outcomes, Not Actions

**Lesson Learned**: We clicked "Connected apps" thinking it was web search.

```python
# ❌ BAD: Verify the click happened
await click_button("Web search")  # Returns true even if wrong button!

# ✅ GOOD: Verify the result
await enable_web_search()
# Check that placeholder changed to "Search the web"
# Check that Search button appeared
# Check that globe icon is visible
```

### Be Specific with Selectors

**Lesson Learned**: Generic text selectors found 5 elements for "Deep Research".

```python
# ❌ BAD: Too generic
locator('div:has-text("Deep Research")')  # Found 5 elements!

# ✅ GOOD: Use specific roles and attributes
locator('div[role="menuitemradio"]:has-text("Deep research")').first
```

## 🧪 TDD Approach for Fixing Broken Features

### The Process
1. **Write failing test FIRST** showing expected behavior
2. **Use Browser MCP** to explore and find UI elements
3. **Update implementation** to make test pass
4. **Verify with screenshots** at every step
5. **Document the fix** for future reference

### Browser MCP > Playwright MCP
For testing and exploration, use Browser MCP:

```python
# Browser MCP provides better tools for exploration
await mcp__browsermcp__browser_navigate(url="https://chatgpt.com")
await mcp__browsermcp__browser_snapshot()   # Get page structure
await mcp__browsermcp__browser_screenshot() # Visual confirmation

# NOT Playwright MCP (more complex, less reliable)
# await mcp__playwright__browser_navigate(...)
```

## 📸 Screenshot Testing Pattern

Create visual verification tests for critical UI flows:

```python
async def test_feature_with_screenshots():
    """Test with visual verification at each step"""
    screenshots_dir = Path("test_screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    
    # Document each state
    await page.screenshot(path=screenshots_dir / "1_initial_state.png")
    
    # Perform action
    await controller.enable_feature()
    
    # Capture result
    await page.screenshot(path=screenshots_dir / "2_feature_enabled.png")
    
    # Verify both programmatically AND visually
    assert await page.locator('expected-ui-element').count() > 0
    print(f"Screenshots saved to: {screenshots_dir.absolute()}")
```

## 🎯 Selector Best Practices

### Hierarchy of Selector Reliability

1. **data-testid** - Most stable, designed for testing
2. **role + text** - Good for accessibility, fairly stable
3. **aria-label** - Stable for interactive elements
4. **Exact text match** - Use `text-is()` not `:has-text()`
5. **Class names** - Avoid unless no other option

### Examples

```python
# Best to worst
page.locator('[data-testid="model-switcher-dropdown-button"]')  # Best
page.locator('button[aria-label="Choose tool"]')  # Good
page.locator('div[role="menuitemradio"]:has-text("Deep research")').first  # OK
page.locator('div:has-text("Search")').first  # Risky
page.locator('.menu-item')  # Avoid
```

## 🔄 Handling UI Changes

### Expected UI Evolution Points

1. **Feature names** - "Web search" → "Connected apps" → ???
2. **Button locations** - Tools menu items reorder frequently
3. **Placeholder text** - Minor wording changes
4. **Icon changes** - Globe → Magnifying glass → ???

### Defensive Coding Pattern

```python
async def find_web_search_option(self):
    """Try multiple selectors for resilience"""
    selectors = [
        'text="Web search"',
        'text="Search the web"', 
        'text="Connected apps"',  # Old name
        '[aria-label*="search"]',
    ]
    
    for selector in selectors:
        element = self.page.locator(selector).first
        if await element.count() > 0:
            logger.info(f"Found web search using selector: {selector}")
            return element
    
    raise Exception("Could not find web search option with any known selector")
```

## 🧪 Test Strategy

### Three Levels of Testing

1. **Unit Tests** - Mock browser interactions, test logic
2. **Integration Tests** - Real browser, controlled environment
3. **Visual Verification Tests** - Screenshots at each step

### When to Use Each

- **Unit**: Business logic, error handling, state management
- **Integration**: Feature toggles, navigation, basic workflows
- **Visual**: UI changes, new features, debugging failures

## 🚨 Common Pitfalls

1. **Assuming stable UI** - ChatGPT updates frequently
2. **Testing clicks not outcomes** - Verify what happened, not what you did
3. **Ignoring timing** - UI animations need time
4. **Over-specific selectors** - Balance specificity with resilience
5. **Mocking too much** - Integration tests need real interactions

## 💡 Quick Debugging Checklist

When a test fails:

1. ✅ Take a screenshot at point of failure
2. ✅ Check if UI text changed
3. ✅ Verify selector still matches elements
4. ✅ Check browser console for errors
5. ✅ Increase wait times temporarily
6. ✅ Run test with headed browser to watch

## 🔮 Future-Proofing

1. **Version detection** - Check ChatGPT version, adjust selectors
2. **Feature flags** - Detect which UI variant is active
3. **Graceful degradation** - Fallback strategies for missing features
4. **Update notifications** - Alert when UI changes detected

Remember: **The UI is not your API** - it will change without notice!