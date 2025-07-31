"""
ChatGPT Automation MCP Server
Provides tools to control ChatGPT web interface via Playwright
"""

import asyncio
from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability
from mcp import McpError
import json
import logging

from .browser_controller import ChatGPTBrowserController

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("chatgpt-automation")
controller = None  # Will be created on first use


async def get_controller():
    """Get or create controller instance"""
    global controller
    if controller is None:
        controller = ChatGPTBrowserController()
    return controller


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available ChatGPT automation tools"""
    return [
        Tool(
            name="chatgpt_launch",
            description="Launch ChatGPT in browser",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="chatgpt_send_message",
            description="Send a message to ChatGPT",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to ChatGPT"
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="chatgpt_new_chat",
            description="Start a new chat conversation",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="chatgpt_get_model",
            description="Get the currently selected model",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="chatgpt_select_model",
            description="Select a specific model",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Model to select",
                        "enum": ["gpt-4", "gpt-4.5", "o1", "o1-preview", "o1-mini", "o3", "o3-mini"]
                    }
                },
                "required": ["model"]
            }
        ),
        Tool(
            name="chatgpt_status",
            description="Check if ChatGPT is ready",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="chatgpt_wait_response",
            description="Wait for ChatGPT to finish responding",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait in seconds",
                        "default": 30
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="chatgpt_send_and_get_response",
            description="Send a message to ChatGPT and wait for the complete response",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to ChatGPT"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait for response in seconds (default 120s for thinking models)",
                        "default": 120
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="chatgpt_get_conversation",
            description="Get all messages in the current conversation",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="chatgpt_get_last_response",
            description="Get the last response from ChatGPT",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait if still responding",
                        "default": 10
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute ChatGPT automation tools"""
    
    try:
        ctrl = await get_controller()
        
        if name == "chatgpt_launch":
            await ctrl.launch()
            return [TextContent(
                type="text",
                text="ChatGPT launched successfully"
            )]
            
        elif name == "chatgpt_send_message":
            message = arguments["message"]
            result = await ctrl.send_message(message)
            return [TextContent(
                type="text",
                text=result
            )]
            
        elif name == "chatgpt_new_chat":
            result = await ctrl.new_chat()
            return [TextContent(
                type="text",
                text=result
            )]
            
        elif name == "chatgpt_get_model":
            model = await ctrl.get_current_model()
            return [TextContent(
                type="text",
                text=f"Current model: {model or 'Unknown'}"
            )]
            
        elif name == "chatgpt_select_model":
            model = arguments["model"]
            success = await ctrl.select_model(model)
            status = "selected successfully" if success else "selection failed"
            return [TextContent(
                type="text",
                text=f"Model {model}: {status}"
            )]
            
        elif name == "chatgpt_status":
            is_ready = await ctrl.is_ready()
            status = "ready" if is_ready else "not ready"
            
            result = {
                "status": status,
                "ready": is_ready
            }
            
            if is_ready:
                model = await ctrl.get_current_model()
                result["current_model"] = model
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        elif name == "chatgpt_wait_response":
            timeout = arguments.get("timeout", 30)
            success = await ctrl.wait_for_response(timeout)
            status = "response complete" if success else "timeout waiting for response"
            return [TextContent(
                type="text",
                text=status
            )]
            
        elif name == "chatgpt_send_and_get_response":
            message = arguments["message"]
            timeout = arguments.get("timeout", 120)
            
            response = await ctrl.send_and_get_response(message, timeout)
            
            if response:
                return [TextContent(
                    type="text",
                    text=response
                )]
            else:
                return [TextContent(
                    type="text",
                    text="No response received"
                )]
            
        elif name == "chatgpt_get_conversation":
            conversation = await ctrl.get_conversation()
            
            return [TextContent(
                type="text",
                text=json.dumps(conversation, indent=2)
            )]
            
        elif name == "chatgpt_get_last_response":
            timeout = arguments.get("timeout", 10)
            
            # Wait a bit if still responding
            await ctrl.wait_for_response(timeout)
            
            response = await ctrl.get_last_response()
            
            if response:
                return [TextContent(
                    type="text",
                    text=response
                )]
            else:
                return [TextContent(
                    type="text",
                    text="No response found"
                )]
            
        else:
            raise McpError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
        raise McpError(f"Tool execution failed: {str(e)}")


async def cleanup():
    """Cleanup resources on shutdown"""
    global controller
    if controller:
        try:
            await controller.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        controller = None


async def run_server():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="chatgpt-automation",
                    server_version="0.1.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability()
                    )
                )
            )
    finally:
        await cleanup()


def main():
    """Entry point for the MCP server"""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)


if __name__ == "__main__":
    main()