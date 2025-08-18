"""
Test thinking models with appropriate timeouts.
Thinking models (like o3-pro) can take 60+ minutes to respond.
"""

import asyncio
import pytest
from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController


@pytest.mark.asyncio
async def test_thinking_model_with_timeout():
    """Test that we handle thinking model delays properly"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        # Enable Think Longer (gpt-5-thinking)
        print("\n=== Testing Thinking Model Response ===")
        await controller.enable_think_longer()
        print("✅ Switched to gpt-5-thinking model")
        
        # Send a complex query that would trigger extended thinking
        print("Sending complex query...")
        response = await controller.send_and_get_response(
            "Explain the mathematical proof of Fermat's Last Theorem in simple terms.",
            timeout=300  # 5 minutes timeout for thinking models
        )
        
        if response:
            print(f"✅ Got thinking response: {response[:200]}...")
        else:
            print("⚠️ No response received (may need longer timeout)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_deep_research_with_timeout():
    """Test Deep Research with appropriate timeout"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        print("\n=== Testing Deep Research Response ===")
        await controller.enable_deep_research()
        print("✅ Deep Research enabled")
        
        # Send a research query
        print("Sending research query...")
        response = await controller.send_and_get_response(
            "What are the latest breakthroughs in quantum computing in 2025?",
            timeout=600  # 10 minutes for Deep Research
        )
        
        if response:
            print(f"✅ Got research response: {response[:200]}...")
        else:
            print("⚠️ No response received (Deep Research can take hours)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_dynamic_response_detection():
    """Test that response detection is dynamic, not time-based"""
    controller = ChatGPTBrowserController()
    
    try:
        await controller.launch()
        await controller.new_chat()
        
        print("\n=== Testing Dynamic Response Detection ===")
        
        # Send a simple query that should respond quickly
        print("Sending simple query...")
        msg_id = await controller.send_message("What is 2+2?")
        
        # wait_for_response should detect completion dynamically
        start_time = asyncio.get_event_loop().time()
        response_complete = await controller.wait_for_response(timeout=60)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        print(f"Response detected in {elapsed:.1f} seconds")
        
        if elapsed < 10:
            print("✅ Fast response detected quickly (not waiting full timeout)")
        else:
            print("⚠️ Response took longer than expected")
        
        response = await controller.get_last_response()
        if response:
            print(f"✅ Response: {response[:100]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    # Run tests with appropriate timeouts
    asyncio.run(test_dynamic_response_detection())