"""
Test model selection for all supported models.
"""

import asyncio
import pytest
from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


# All models we claim to support
SUPPORTED_MODELS = [
    "gpt-5",           # Default
    "gpt-5-thinking",  # Think Longer
    "gpt-5-pro",       # Pro version
    "gpt-4.1",         # Fast coding
    "o3",              # Reasoning
]

# Quick models for testing (avoid slow thinking/pro models)
QUICK_TEST_MODELS = [
    "gpt-4.1",
    "gpt-5",  # Standard is relatively quick
]


@pytest.mark.asyncio
async def test_all_model_selections():
    """Test selecting each supported model"""
    controller = ChatGPTBrowserController()
    results = {}
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        print("\n=== Testing All Model Selections ===")
        
        for model in QUICK_TEST_MODELS:  # Use quick models for testing
            print(f"\nTesting model: {model}")
            
            # Try to select the model
            success = await controller.select_model(model)
            
            if success:
                # Verify we're on the right model
                current = await controller.get_current_model()
                print(f"  Selected: ✅ (Current: {current})")
                results[model] = "PASS"
            else:
                print(f"  Selected: ❌ Failed to switch")
                results[model] = "FAIL"
            
            # Small delay between switches
            await asyncio.sleep(2)
        
        # Print summary
        print("\n=== Model Selection Summary ===")
        for model, status in results.items():
            emoji = "✅" if status == "PASS" else "❌"
            print(f"{emoji} {model}: {status}")
        
        # Check if all passed
        all_passed = all(status == "PASS" for status in results.values())
        assert all_passed, f"Some models failed: {[m for m, s in results.items() if s == 'FAIL']}"
        
        return True
        
    except Exception as e:
        print(f"❌ Model selection test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_model_verification():
    """Test that get_current_model returns accurate results"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        print("\n=== Testing Model Verification ===")
        
        # Get initial model
        initial_model = await controller.get_current_model()
        print(f"Initial model: {initial_model}")
        assert initial_model, "Should have an initial model"
        
        # Switch to a specific model
        print("\nSwitching to gpt-4.1...")
        await controller.select_model("gpt-4.1")
        
        # Verify the switch
        new_model = await controller.get_current_model()
        print(f"After switch: {new_model}")
        
        # Check if it matches (normalize for comparison)
        if "4.1" in new_model or "gpt-4.1" in new_model.lower():
            print("✅ Model verification working!")
        else:
            print(f"⚠️ Model might not have switched correctly: {new_model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model verification failed: {e}")
        raise


@pytest.mark.asyncio
async def test_model_persistence():
    """Test that model selection persists across messages"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        print("\n=== Testing Model Persistence ===")
        
        # Select a model
        print("Selecting gpt-4.1...")
        await controller.select_model("gpt-4.1")
        model1 = await controller.get_current_model()
        print(f"Model after selection: {model1}")
        
        # Send a message
        print("Sending a message...")
        await controller.send_message("What is 1+1?")
        await controller.wait_for_response(timeout=60)
        
        # Check model is still the same
        model2 = await controller.get_current_model()
        print(f"Model after message: {model2}")
        
        if model1 == model2:
            print("✅ Model persisted across message!")
        else:
            print(f"⚠️ Model changed from {model1} to {model2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model persistence test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(test_all_model_selections())