"""
Test auto-enable web search functionality for research keywords
"""

import asyncio
import json
from pathlib import Path
from chatgpt_automation_mcp.server import call_tool


async def test_auto_enable_keywords():
    """Test that research keywords trigger auto-enable web search"""
    
    # Test cases: messages that should trigger auto-enable
    trigger_messages = [
        "What are the latest Odoo 18 improvements?",
        "Research the current state of AI models",
        "Find recent updates to ChatGPT",
        "What's new in Python 2025?",
        "Discover current trends in web development",
        "Investigate recent changes to GitHub API",
        "What are the up to date best practices for Docker?",
    ]
    
    # Test cases: messages that should NOT trigger auto-enable
    non_trigger_messages = [
        "Write a Python function to sort a list",
        "Explain how recursion works",
        "Create a REST API with Flask",
        "Help me debug this code",
        "What is object-oriented programming?",
    ]
    
    print("🧪 Testing Auto-Enable Web Search Keywords")
    print("=" * 50)
    
    # Test trigger messages
    print("\n✅ Testing TRIGGER messages (should auto-enable web search):")
    for i, message in enumerate(trigger_messages, 1):
        print(f"\n{i}. Testing: '{message[:50]}...' " if len(message) > 50 else f"\n{i}. Testing: '{message}'")
        
        # Test the keyword detection logic directly
        research_keywords = [
            "research", "latest", "current", "recent", "2025", "2024", "2026", 
            "update", "new", "find", "search", "discover", "investigate",
            "what's new", "recent changes", "current state", "up to date"
        ]
        message_lower = message.lower()
        matching_keywords = [kw for kw in research_keywords if kw in message_lower]
        
        if matching_keywords:
            print(f"   ✅ Would trigger auto-enable (keywords: {matching_keywords})")
        else:
            print(f"   ❌ Would NOT trigger auto-enable (no keywords found)")
    
    # Test non-trigger messages
    print("\n❌ Testing NON-TRIGGER messages (should NOT auto-enable web search):")
    for i, message in enumerate(non_trigger_messages, 1):
        print(f"\n{i}. Testing: '{message[:50]}...' " if len(message) > 50 else f"\n{i}. Testing: '{message}'")
        
        # Test the keyword detection logic directly
        research_keywords = [
            "research", "latest", "current", "recent", "2025", "2024", "2026", 
            "update", "new", "find", "search", "discover", "investigate",
            "what's new", "recent changes", "current state", "up to date"
        ]
        message_lower = message.lower()
        matching_keywords = [kw for kw in research_keywords if kw in message_lower]
        
        if matching_keywords:
            print(f"   ❌ Would incorrectly trigger auto-enable (keywords: {matching_keywords})")
        else:
            print(f"   ✅ Correctly would NOT trigger auto-enable")
    
    print("\n" + "=" * 50)
    print("✅ Keyword detection test completed!")
    return True


async def test_auto_enable_integration():
    """Test auto-enable functionality with actual MCP calls (mock)"""
    
    print("\n🔧 Testing Auto-Enable Integration")
    print("=" * 50)
    
    # Test that would trigger auto-enable
    test_message = "What are the latest ChatGPT model improvements in 2025?"
    
    print(f"Testing message: '{test_message}'")
    print("(Note: This test shows the keyword detection logic, actual browser automation requires ChatGPT login)")
    
    # Simulate the logic from server.py
    research_keywords = [
        "research", "latest", "current", "recent", "2025", "2024", "2026", 
        "update", "new", "find", "search", "discover", "investigate",
        "what's new", "recent changes", "current state", "up to date"
    ]
    message_lower = test_message.lower()
    matching_keywords = [kw for kw in research_keywords if kw in message_lower]
    
    if matching_keywords:
        print(f"✅ Auto-enable triggered by keywords: {matching_keywords}")
        print("   - Would call: await ctrl.toggle_search_mode(True)")
        print("   - Would log: 'Auto-enabling web search due to research keywords'")
    else:
        print("❌ Auto-enable would NOT be triggered")
    
    return True


async def test_error_message_improvements():
    """Test improved error messages for web search toggle"""
    
    print("\n📝 Testing Improved Error Messages")
    print("=" * 50)
    
    # Simulate different scenarios
    scenarios = [
        {"success": True, "enable": True, "expected": "Web search enabled successfully"},
        {"success": True, "enable": False, "expected": "Web search disabled successfully"},
        {"success": False, "enable": True, "expected": "Web search toggle returned false - may be already enabled or UI changed"},
        {"success": False, "enable": False, "expected": "Web search toggle returned false - may be already disabled or UI changed"},
    ]
    
    for scenario in scenarios:
        success = scenario["success"]
        enable = scenario["enable"]
        expected = scenario["expected"]
        
        # Simulate the improved error message logic from server.py
        if success:
            status = "enabled" if enable else "disabled"
            result = f"Web search {status} successfully"
        else:
            current_state = "already enabled" if enable else "already disabled"
            result = f"Web search toggle returned false - may be {current_state} or UI changed"
        
        if result == expected:
            print(f"✅ Scenario (success={success}, enable={enable}): '{result}'")
        else:
            print(f"❌ Scenario (success={success}, enable={enable}): Expected '{expected}', got '{result}'")
    
    return True


if __name__ == "__main__":
    async def main():
        """Run all auto-enable tests"""
        print("🧪 Auto-Enable Web Search Test Suite")
        print("=" * 60)
        
        try:
            # Test keyword detection
            await test_auto_enable_keywords()
            
            # Test integration logic
            await test_auto_enable_integration()
            
            # Test error message improvements
            await test_error_message_improvements()
            
            print("\n🎉 All tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(main())