# Test Execution Times and Timeout Recommendations

## Actual Test Execution Times (Aug 14, 2025)

Based on real test runs with ChatGPT Automation MCP:

### Individual Test Times

| Test Suite | Tests | Total Time | Average Per Test |
|------------|-------|------------|------------------|
| test_deep_research_verification.py | 2 tests | ~64s | ~32s |
| test_think_longer_verification.py | 3 tests | ~119s | ~40s |
| Combined verification tests | 5 tests | 183s (3:03) | ~37s |
| test_all_features.py | 1 test | 72s | 72s |

### Breakdown by Operation

| Operation | Typical Time | Notes |
|-----------|--------------|--------|
| Browser launch (CDP) | 25-30s | Includes sidebar close attempt |
| New chat creation | 2-3s | Quick operation |
| Send simple message | 1-2s | Just sending, not waiting |
| Wait for response (regular) | 5-10s | Dynamic detection |
| Model switch | 5-10s | URL navigation + verify |
| Enable Think Longer | 10-15s | Model switch to gpt-5-thinking |
| Enable Deep Research | 5-10s | Menu click + verify |
| File upload | 3-5s | Small files |

## Timeout Recommendations

### pytest.ini / pyproject.toml Configuration
```toml
[tool.pytest.ini_options]
addopts = [
    "--timeout=300",  # 5 minute default per test
]
timeout_method = "thread"  # Better for async tests
timeout_func_only = false  # Include setup/teardown
```

### Command Line Usage
```bash
# Quick tests (Think Longer, Deep Research verification)
uv run pytest tests/test_*_verification.py --timeout=300

# Comprehensive tests
uv run pytest tests/test_all_features.py --timeout=600

# Full test suite
uv run pytest tests/ --timeout=300
```

### Code-Level Timeouts

For `send_and_get_response()`:
```python
# Regular models (gpt-4o, etc.)
response = await controller.send_and_get_response(message, timeout=60)

# Think Longer models (gpt-5-thinking)
response = await controller.send_and_get_response(message, timeout=300)

# Deep Research (can take hours for full research)
response = await controller.send_and_get_response(message, timeout=600)

# o3-pro (can take 60+ minutes)
response = await controller.send_and_get_response(message, timeout=3600)
```

## Performance Tips

### 1. Use CDP Mode (Default)
- 10x faster than launching new browser
- Maintains session persistence
- Setup time: ~5s vs ~30s

### 2. Batch Operations
```python
# Use batch_operations for multiple actions
results = await controller.batch_operations([
    {"operation": "new_chat"},
    {"operation": "send_message", "args": {"message": "Hello"}},
    {"operation": "get_last_response"},
])
```

### 3. Environment Variables
```bash
# Speed up animations for testing
export CHATGPT_ANIMATION_SPEED=0.5  # 2x faster

# Run tests in parallel (when possible)
uv run pytest tests/ -n auto
```

## CI/CD Recommendations

For GitHub Actions or other CI:
```yaml
- name: Run tests
  run: |
    uv run pytest tests/ \
      --timeout=600 \
      --tb=short \
      -v
  timeout-minutes: 15  # GitHub Actions timeout
```

## Important Notes

1. **Dynamic Response Detection**: The code uses dynamic waiting, not fixed sleeps
2. **Timeout != Expected Time**: Tests typically complete well before timeout
3. **Network Dependent**: Actual times vary based on ChatGPT's response speed
4. **Model Matters**: Thinking models need significantly longer timeouts
5. **Setup Overhead**: Browser setup takes 25-30s (one-time cost with CDP)

## Summary

- **Default timeout**: 300s (5 minutes) - covers most cases
- **Typical test run**: 3-4 minutes for verification suite
- **Safe CI timeout**: 15 minutes for full suite
- **Per-test average**: 30-40 seconds including setup