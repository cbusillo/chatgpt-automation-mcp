# Timeout and Delay Guidelines

This document provides recommendations for timeout values and animation delays in the ChatGPT automation.

## Timeout Recommendations by Model/Mode

### Default Timeouts (Current Implementation)

- **Default timeout**: 120 seconds (2 minutes)
- **Wait for response**: 30 seconds
- **Get last response**: 10 seconds

### Recommended Timeouts by Model

Based on real-world usage and model characteristics:

| Model/Mode | Recommended Timeout | Reasoning |
|------------|-------------------|-----------|
| **o4-mini** | 60-120 seconds | Fast response, minimal thinking time |
| **o4-mini-high** | 120-180 seconds | Slightly more thinking time |
| **o3** | 300-600 seconds (5-10 min) | Can think for several minutes |
| **o3-pro** | 1200-1800 seconds (20-30 min) | Extensive thinking, queue time |
| **Deep Research** | 1200-1800 seconds (20-30 min) | Multi-source analysis |
| **GPT-4.1** | 180-300 seconds | Large context processing |
| **GPT-4o** | 60-120 seconds | Fast multimodal processing |

### Why Current Defaults Are Insufficient

1. **o3-pro Reality**: 
   - Can think for 10-15 minutes before starting response
   - Queue times can add another 5-10 minutes
   - Total wait time often exceeds 20 minutes

2. **Deep Research**:
   - Performs comprehensive web searches
   - Analyzes multiple sources
   - Can take 15-30 minutes for complex queries

3. **Current 120-second default**:
   - Will timeout before o3-pro even starts responding
   - Insufficient for Deep Research mode
   - May fail even for o3 on complex problems

## Animation Delay Analysis

### Current Animation Delays in Browser Controller

| Action | Current Delay | Purpose | Recommendation |
|--------|--------------|---------|----------------|
| Page navigation | 2-3 seconds | Page load | Keep as is |
| Menu open/close | 0.5 seconds | Animation | Increase to 0.7s |
| Submenu open | 1.0 second | Nested animation | Keep as is |
| Hover actions | 0.2-0.3 seconds | Hover state | Increase to 0.5s |
| Model selection | 1.5 seconds | Selection apply | Keep as is |
| Sidebar toggle | 1.0 second | Slide animation | Keep as is |
| After click | 0.5 seconds | UI update | Increase to 0.7s |

### Recommended Changes

1. **Increase minimum animation delay**: 
   - Current: 0.5s for most animations
   - Recommended: 0.7s minimum
   - Reasoning: Accounts for slower systems and network latency

2. **Add configurable animation multiplier**:
   ```python
   ANIMATION_DELAY_MULTIPLIER = 1.0  # Can be increased for slower systems
   ```

3. **Use adaptive delays**:
   - Detect if animations are still running
   - Wait for CSS transitions to complete
   - Use `wait_for_function` instead of fixed delays where possible

## Implementation Recommendations

### 1. Update Default Timeouts

```python
# In server.py and browser_controller.py
def get_default_timeout(model: str = None, mode: str = None) -> int:
    """Get appropriate timeout based on model/mode"""
    if mode == "deep_research":
        return 1800  # 30 minutes
    elif model and "o3-pro" in model.lower():
        return 1800  # 30 minutes  
    elif model and "o3" in model.lower():
        return 600   # 10 minutes
    elif model and "gpt-4.1" in model.lower():
        return 300   # 5 minutes
    else:
        return 120   # 2 minutes default
```

### 2. Animation Delay Configuration

```python
# Add to config.py
class Config:
    # Animation delays (in seconds)
    ANIMATION_DELAY_SHORT = 0.3   # Quick transitions
    ANIMATION_DELAY_MEDIUM = 0.7  # Standard animations
    ANIMATION_DELAY_LONG = 1.0    # Complex animations
    ANIMATION_DELAY_MULTIPLIER = float(os.getenv("CHATGPT_ANIMATION_MULTIPLIER", "1.0"))
    
    @classmethod
    def get_animation_delay(cls, delay_type: str = "medium") -> float:
        """Get animation delay with multiplier applied"""
        delays = {
            "short": cls.ANIMATION_DELAY_SHORT,
            "medium": cls.ANIMATION_DELAY_MEDIUM,
            "long": cls.ANIMATION_DELAY_LONG
        }
        return delays.get(delay_type, cls.ANIMATION_DELAY_MEDIUM) * cls.ANIMATION_DELAY_MULTIPLIER
```

### 3. Replace Fixed Delays

Instead of:
```python
await asyncio.sleep(0.5)
```

Use:
```python
await asyncio.sleep(self.config.get_animation_delay("medium"))
```

Or better, use DOM waiting:
```python
await self.page.wait_for_function(
    """() => {
        const menu = document.querySelector('div[role="menu"]');
        if (!menu) return false;
        const style = window.getComputedStyle(menu);
        return style.opacity === '1' && style.visibility === 'visible';
    }""",
    timeout=5000
)
```

## Usage Examples

### Setting Appropriate Timeouts

```python
# For o3-pro
response = await controller.send_and_get_response(
    message="Complex analysis request",
    timeout=1800  # 30 minutes
)

# For Deep Research
await controller.enable_deep_research()
response = await controller.send_and_get_response(
    message="Research quantum computing applications",
    timeout=1800  # 30 minutes
)

# For standard models
response = await controller.send_and_get_response(
    message="Simple question",
    timeout=120  # 2 minutes is fine
)
```

### Handling Slow Systems

```bash
# Set animation multiplier for slower systems
export CHATGPT_ANIMATION_MULTIPLIER=1.5

# Or in code
os.environ["CHATGPT_ANIMATION_MULTIPLIER"] = "1.5"
```

## Testing Recommendations

1. **Test with slow network**: Use browser DevTools to throttle network
2. **Test with CPU throttling**: Simulate slower machines
3. **Test timeout edge cases**: Verify timeouts work correctly
4. **Monitor actual response times**: Log how long operations really take

## Monitoring and Debugging

Add logging to track actual times:

```python
import time

start_time = time.time()
response = await controller.send_and_get_response(message, timeout=1800)
actual_time = time.time() - start_time

logger.info(f"Response took {actual_time:.1f} seconds (timeout was {timeout})")
```

## Summary

1. **Current timeouts are too short** for advanced models
2. **Animation delays could be slightly longer** for reliability
3. **Use adaptive waiting** instead of fixed delays where possible
4. **Make delays configurable** for different environments
5. **Monitor actual times** to refine recommendations