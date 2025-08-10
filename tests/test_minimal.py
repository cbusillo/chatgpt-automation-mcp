#!/usr/bin/env python3
"""
Minimal test suite that can run with simple 'uv run pytest'
Provides basic validation without browser dependencies
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all modules can be imported"""
    import chatgpt_automation_mcp
    from chatgpt_automation_mcp.server import list_tools
    from chatgpt_automation_mcp.config import Config
    from chatgpt_automation_mcp.browser_controller import ChatGPTBrowserController
    assert True


def test_config():
    """Test configuration loading"""
    from chatgpt_automation_mcp.config import Config
    config = Config()
    assert config.HEADLESS in [True, False]
    assert isinstance(config.CDP_URL, str)
    assert isinstance(config.USE_CDP, bool)


@pytest.mark.asyncio
async def test_list_tools():
    """Test MCP tool listing"""
    from chatgpt_automation_mcp.server import list_tools
    tools = await list_tools()
    assert len(tools) > 0
    assert all(hasattr(tool, 'name') for tool in tools)
    assert all(hasattr(tool, 'description') for tool in tools)


@pytest.mark.asyncio
async def test_tool_schemas():
    """Test tool input schemas are valid"""
    from chatgpt_automation_mcp.server import list_tools
    tools = await list_tools()
    
    for tool in tools:
        assert hasattr(tool, 'inputSchema')
        schema = tool.inputSchema
        assert 'type' in schema
        assert schema['type'] == 'object'
        
        if 'properties' in schema:
            assert isinstance(schema['properties'], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])