#!/usr/bin/env python3
"""
Test suite for MCP server functionality.
Tests the MCP protocol implementation and tool definitions.
"""

import pytest
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatgpt_automation_mcp.server import (
    list_tools,
    call_tool,
)


@pytest.mark.asyncio
async def test_list_tools():
    """Test that all tools are properly defined"""
    tools = await list_tools()
    
    # Check we have tools
    assert len(tools) > 0
    
    # Check for essential tools
    tool_names = [tool.name for tool in tools]
    assert "chatgpt_send_message" in tool_names
    assert "chatgpt_get_last_response" in tool_names
    assert "chatgpt_select_model" in tool_names
    assert "chatgpt_regenerate" in tool_names
    
    # Check tool structure
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "inputSchema")




@pytest.mark.asyncio
async def test_tool_input_schemas():
    """Test that tool input schemas are valid"""
    tools = await list_tools()
    
    for tool in tools:
        schema = tool.inputSchema
        
        # Check it's a valid JSON schema
        assert "type" in schema
        assert schema["type"] == "object"
        
        # Check for required fields if present
        if "required" in schema:
            assert isinstance(schema["required"], list)
            
        # Check properties if present
        if "properties" in schema:
            assert isinstance(schema["properties"], dict)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])