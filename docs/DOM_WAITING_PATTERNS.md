# DOM Waiting Patterns

This document describes the improved waiting patterns used in the ChatGPT automation to avoid theme flashes and ensure reliable UI interactions.

## Why Not Use Arbitrary Delays?

Using `asyncio.sleep()` or `wait_for_timeout()` is unreliable because:
- Too short: Operations fail when the system is slow
- Too long: Wastes time when the system is fast
- Can't adapt: Fixed delays don't account for varying conditions
- Theme flashes: UI changes happen after the delay

## Better Approaches

### 1. Wait for Specific Elements

```python
# Wait for element to appear
await self.page.wait_for_selector(
    'button:has-text("Sources")',
    state="visible",
    timeout=5000
)

# Wait for element to disappear
await self.page.wait_for_selector(
    'div[role="menu"]',
    state="hidden",
    timeout=3000
)
```

### 2. Wait for DOM Conditions

```python
# Wait for theme to be applied
await self.page.wait_for_function(
    """() => {
        const html = document.querySelector('html');
        return html && (html.classList.contains('dark') || html.classList.contains('light'));
    }""",
    timeout=5000
)

# Wait for loading to complete
await self.page.wait_for_function(
    """() => !document.querySelector('body').classList.contains('loading')""",
    timeout=5000
)
```

### 3. Wait for Network Activity

```python
# Wait for all network requests to finish
await self.page.goto("https://chatgpt.com", wait_until="networkidle")

# Better than "domcontentloaded" for SPAs
await self.page.goto(url, wait_until="networkidle", timeout=60000)
```

### 4. Wait for Custom Conditions

```python
# Wait for any condition you can express in JavaScript
await self.page.wait_for_function(
    """() => {
        // Check if Deep Research UI is ready
        const input = document.querySelector('input[placeholder*="research"]');
        const button = document.querySelector('button:has-text("Sources")');
        return input && button;
    }""",
    timeout=5000
)
```

## When to Use Each Method

| Method | Use When |
|--------|----------|
| `wait_for_selector` | Waiting for specific elements to appear/disappear |
| `wait_for_function` | Waiting for complex DOM states or multiple conditions |
| `wait_until="networkidle"` | After navigation to ensure all resources loaded |
| `wait_for_timeout` | Only for CSS animations with no DOM changes |

## Example: Avoiding Theme Flash

```python
# Bad: Theme flash happens after navigation
await self.page.goto("https://chatgpt.com")
await asyncio.sleep(2)  # Theme might apply before or after this

# Good: Wait for theme to actually be applied
await self.page.goto("https://chatgpt.com", wait_until="networkidle")
await self.page.wait_for_function(
    """() => {
        const html = document.querySelector('html');
        return html && (html.classList.contains('dark') || html.classList.contains('light'));
    }"""
)
```

## Benefits

1. **Reliability**: Operations proceed only when the UI is actually ready
2. **Speed**: No unnecessary waiting when things load quickly
3. **Adaptability**: Handles varying load times automatically
4. **Maintainability**: Code clearly expresses what it's waiting for
5. **No theme flashes**: UI transitions complete before proceeding