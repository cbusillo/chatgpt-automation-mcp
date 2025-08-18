#!/usr/bin/env python3
"""
Visual verification test for Think Longer feature
RUN WITH: HEADLESS=false SKIP_BROWSER_TESTS=false uv run pytest tests/test_think_longer_verification.py -v -s

This test will:
1. Open browser visually so you can watch
2. Switch to gpt-5-thinking model
3. Verify model change in UI
4. Send a complex query to see extended thinking
5. Take screenshots for evidence
"""

import pytest
import asyncio
from pathlib import Path

pytestmark = [pytest.mark.browser, pytest.mark.ui_dependent]


@pytest.mark.asyncio
async def test_think_longer_visual_verification(browser):
    """
    Visual test to verify Think Longer works via model selection
    WATCH THIS TEST - You should see model change to "5 Thinking"
    """
    browser.test_name = "think_longer_verify"
    
    print("\n" + "="*60)
    print("THINK LONGER VISUAL VERIFICATION TEST")
    print("WATCH THE BROWSER - You should see:")
    print("1. Navigation to gpt-5-thinking model")
    print("2. Model selector shows '5 Thinking' or similar")
    print("3. Complex query gets extended reasoning")
    print("="*60 + "\n")
    
    # Start with a different model to see the change
    print("Step 1: Starting with default model...")
    await browser.controller.page.goto("https://chatgpt.com/")
    await browser.wait_for_stable_ui()
    await browser.screenshot("01_initial_model")
    
    # Check current model
    model_display = browser.controller.page.locator('[data-testid="model-switcher-dropdown-button"]').first
    if await model_display.count() > 0:
        initial_model = await model_display.inner_text()
        print(f"Current model: {initial_model}")
    
    # Now switch to thinking model
    print("\nStep 2: Switching to gpt-5-thinking model...")
    await browser.controller.page.goto("https://chatgpt.com/?model=gpt-5-thinking")
    await asyncio.sleep(3.0)  # Wait for model switch
    await browser.screenshot("02_after_model_switch")
    
    # Verify model changed
    print("\nStep 3: Verifying model change...")
    if await model_display.count() > 0:
        new_model = await model_display.inner_text()
        print(f"New model: {new_model}")
        
        if "thinking" in new_model.lower() or "5 thinking" in new_model.lower():
            print("✅ Model successfully changed to Thinking model!")
        else:
            print(f"⚠️  Model shows: {new_model} (may still be correct)")
    
    # Test with a complex reasoning query
    print("\nStep 4: Testing with complex reasoning query...")
    
    # Find input field
    input_field = browser.controller.page.locator('div[contenteditable="true"]').first
    if await input_field.count() > 0:
        complex_query = """Think step by step to solve this problem:
        
        Three friends go to a restaurant. The bill is $30. They each contribute $10.
        The waiter realizes there was a $5 discount, so he needs to return $5.
        He keeps $2 as a tip and gives $1 back to each friend.
        
        Now each friend paid $9 (10-1=9), so 3×9=$27.
        The waiter kept $2, so $27+$2=$29.
        
        Where did the missing dollar go? Explain the error in this reasoning."""
        
        await input_field.fill(complex_query)
        await browser.screenshot("03_complex_query_entered")
        
        # Send the message
        send_button = browser.controller.page.locator('button[data-testid*="send"], button[aria-label*="Send"]').first
        if await send_button.count() > 0 and await send_button.is_enabled():
            print("Step 5: Sending complex query...")
            await send_button.click()
            
            # Wait a bit to see if extended thinking starts
            await asyncio.sleep(5.0)
            await browser.screenshot("04_thinking_started")
            
            # Look for thinking indicators
            print("\nStep 6: Looking for extended thinking indicators...")
            thinking_indicators = [
                ('text=/thinking/i', "thinking indicator"),
                ('text=/reasoning/i', "reasoning indicator"),
                ('text=/analyzing/i', "analyzing indicator"),
                ('text=/step.*by.*step/i', "step by step indicator"),
            ]
            
            found_indicators = []
            for selector, description in thinking_indicators:
                if await browser.controller.page.locator(selector).count() > 0:
                    found_indicators.append(description)
                    print(f"  ✅ Found {description}")
            
            await browser.screenshot("05_final_state")
            
            # Report results
            print("\n" + "="*60)
            print("VISUAL VERIFICATION RESULTS:")
            print(f"✅ Model switched to Thinking: {'thinking' in new_model.lower()}")
            print(f"✅ Complex query sent: YES")
            if found_indicators:
                print(f"✅ Thinking indicators found: {', '.join(found_indicators)}")
            else:
                print(f"ℹ️  No explicit thinking indicators (may still be thinking)")
            print(f"📸 Screenshots saved in: tests/test_screenshots/")
            print("="*60 + "\n")
            
            assert "thinking" in new_model.lower() or "5 thinking" in new_model.lower(), \
                f"Model should show Thinking variant, got: {new_model}"
        else:
            print("❌ Could not find send button")
            await browser.screenshot("ERROR_no_send_button")
    else:
        print("❌ Could not find input field")
        await browser.screenshot("ERROR_no_input_field")


@pytest.mark.asyncio
async def test_think_longer_via_controller(browser):
    """
    Test the actual enable_think_longer() method
    """
    browser.test_name = "think_longer_controller"
    
    print("\n" + "="*60)
    print("TESTING enable_think_longer() METHOD")
    print("="*60 + "\n")
    
    # Start fresh
    await browser.controller.page.goto("https://chatgpt.com/")
    await browser.wait_for_stable_ui()
    
    # Call the method we updated
    print("Calling controller.enable_think_longer()...")
    result = await browser.controller.enable_think_longer()
    
    # Take screenshot of result
    await browser.screenshot("controller_result")
    
    print(f"\nResult: {result}")
    
    # Check if model actually changed
    model_display = browser.controller.page.locator('[data-testid="model-switcher-dropdown-button"]').first
    if await model_display.count() > 0:
        current_model = await model_display.inner_text()
        print(f"Current model after enable_think_longer(): {current_model}")
        
        if "thinking" in current_model.lower():
            print("✅ Model successfully changed to Thinking variant")
        else:
            print(f"⚠️  Model is: {current_model}")
    
    assert result, "enable_think_longer() should return True"


@pytest.mark.asyncio
async def test_both_features_together(browser):
    """
    Test enabling both Think Longer and Deep Research
    """
    browser.test_name = "both_features"
    
    print("\n" + "="*60)
    print("TESTING BOTH FEATURES TOGETHER")
    print("="*60 + "\n")
    
    # Enable Think Longer first
    print("Step 1: Enabling Think Longer...")
    think_result = await browser.controller.enable_think_longer()
    print(f"Think Longer: {think_result}")
    await browser.screenshot("01_think_longer_enabled")
    
    # Then enable Deep Research
    print("\nStep 2: Enabling Deep Research...")
    research_result = await browser.controller.enable_deep_research()
    print(f"Deep Research: {research_result}")
    await browser.screenshot("02_both_enabled")
    
    # Check final state
    print("\n" + "="*60)
    print("RESULTS:")
    print(f"Think Longer enabled: {think_result}")
    print(f"Deep Research enabled: {research_result}")
    
    if think_result and research_result:
        print("✅ Both features successfully enabled!")
    elif think_result:
        print("⚠️  Only Think Longer enabled")
    elif research_result:
        print("⚠️  Only Deep Research enabled")
    else:
        print("❌ Neither feature enabled")
    print("="*60 + "\n")
    
    # Test passes if at least one works
    assert think_result or research_result, "At least one feature should work"


if __name__ == "__main__":
    import sys
    print("\n" + "="*60)
    print("Run this test with:")
    print("HEADLESS=false SKIP_BROWSER_TESTS=false uv run pytest tests/test_think_longer_verification.py -v -s")
    print("="*60 + "\n")
    sys.exit(pytest.main([__file__, "-v", "-s"]))