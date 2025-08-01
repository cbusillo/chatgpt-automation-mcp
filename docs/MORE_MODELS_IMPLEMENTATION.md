# More Models Submenu Implementation

This document describes the improved implementation for accessing models in the "More models" submenu (GPT-4.1, GPT-4.5, GPT-4.1-mini).

## Implementation Details

### 1. Enhanced Menu Detection

The implementation now tries multiple selectors to find the "More models" menu item:

```python
more_button_selectors = [
    'div[role="menuitem"]:has-text("More models")',
    'div:has-text("More models"):not(:has(div))',
    '[role="menuitem"]:has-text("More models")',
    'button:has-text("More models")',
]
```

### 2. Hover Support

Some menus require hovering before clicking:

```python
await more_button.hover()
await asyncio.sleep(0.3)
await more_button.click()
```

### 3. Enhanced Model Selection

The implementation now uses multiple strategies to find models in the submenu:

1. **Standard menu item selectors** - For typical menu structures
2. **Leaf node selectors** - For finding the actual clickable text elements
3. **Exact text matching** - Using `:text-is()` for precise matches
4. **Fallback broad search** - If standard methods fail

### 4. Improved Model Verification

The verification logic now handles multiple variations:

- Direct substring matching
- Version number extraction for GPT models
- Handling of model descriptions in the UI

## Usage Example

```python
# Select GPT-4.1 (from More models menu)
controller = ChatGPTBrowserController()
await controller.launch()
await controller.new_chat()

# This will automatically:
# 1. Open the model picker
# 2. Click "More models" 
# 3. Select GPT-4.1 from the submenu
success = await controller.select_model("gpt-4.1")

if success:
    model = await controller.get_current_model()
    print(f"Now using: {model}")
```

## Supported Models

### Main Menu Models
- `gpt-4o` (default)
- `o3`
- `o3-pro`
- `o4-mini`
- `o4-mini-high`

### More Models Submenu
- `gpt-4.5` - Research preview (deprecated July 14, 2025)
- `gpt-4.1` - Great for quick coding and analysis
- `gpt-4.1-mini` - Faster for everyday tasks

## Troubleshooting

### Model Not Found

If a model selection fails:

1. **Check the model name** - Use exact names from the list above
2. **Try manual selection** - The UI might have changed
3. **Check browser logs** - Look for JavaScript errors
4. **Verify menu structure** - Use the debug script to inspect

### Submenu Not Opening

If "More models" doesn't open:

1. **Wait longer** - Increase the sleep after clicking
2. **Try hover first** - Some menus need hover interaction
3. **Check z-index** - Menu might be behind other elements

### Debug Mode

Enable debug logging to see detailed selection attempts:

```python
import logging
logging.getLogger("chatgpt_automation_mcp").setLevel(logging.DEBUG)
```

## Known Limitations

1. **UI Changes** - ChatGPT's UI updates frequently, selectors may need updates
2. **Animation Timing** - Submenu animations can cause timing issues
3. **Model Availability** - Some models may not be available for all accounts

## Testing

Run the test script to verify More models functionality:

```bash
python tests/test_more_models_submenu.py
```

This will:
1. Debug the menu structure
2. Test selecting each model in the submenu
3. Verify the selection was successful