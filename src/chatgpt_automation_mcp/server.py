"""
ChatGPT Automation MCP Server
Provides tools to control ChatGPT web interface via Playwright
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, ServerCapabilities, TextContent, Tool, ToolsCapability

from .browser_controller import ChatGPTBrowserController
from .timeout_helper import get_default_timeout, format_timeout_for_display

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
async def list_tools() -> list[Tool]:
    """List available ChatGPT automation tools"""
    return [
        Tool(
            name="chatgpt_launch",
            description="Launch ChatGPT in browser",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="chatgpt_send_message",
            description="Send a message to ChatGPT",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message to send to ChatGPT"}
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="chatgpt_new_chat",
            description="Start a new chat conversation",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="chatgpt_get_model",
            description="Get the currently selected model",
            inputSchema={"type": "object", "properties": {}, "required": []},
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
                        "enum": [
                            "gpt-5",
                            "5",
                            "gpt-5-thinking",
                            "gpt-5-pro",
                            "gpt-4o",
                            "4o",
                            "gpt-4.5",
                            "o3",
                            "o3-pro",
                            "o4-mini",
                            "gpt-4.1",
                            "gpt-4.1-mini",
                        ],
                    }
                },
                "required": ["model"],
            },
        ),
        Tool(
            name="chatgpt_status",
            description="Check if ChatGPT is ready",
            inputSchema={"type": "object", "properties": {}, "required": []},
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
                        "default": 30,
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="chatgpt_send_and_get_response",
            description="Send a message to ChatGPT and wait for the complete response. Automatically enables web search for messages containing research keywords (latest, current, recent, update, search, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message to send to ChatGPT"},
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum time to wait for response in seconds (default 120s for thinking models)",
                        "default": 120,
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="chatgpt_get_conversation",
            description="Get all messages in the current conversation",
            inputSchema={"type": "object", "properties": {}, "required": []},
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
                        "default": 10,
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="chatgpt_upload_file",
            description="Upload a file to the current conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to upload"}
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="chatgpt_regenerate",
            description="Regenerate the last response from ChatGPT",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="chatgpt_export_conversation",
            description="Export the current conversation in markdown or JSON format",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="chatgpt_save_conversation",
            description="Export and save the current conversation to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Custom filename (without extension). Auto-generated if not provided.",
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="chatgpt_edit_message",
            description="Edit a previous user message in the conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_index": {
                        "type": "integer",
                        "description": "Index of the user message to edit (0-based)",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New content for the message",
                    },
                },
                "required": ["message_index", "new_content"],
            },
        ),
        Tool(
            name="chatgpt_list_conversations",
            description="List all available ChatGPT conversations",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="chatgpt_switch_conversation",
            description="Switch to a different conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": ["string", "integer"],
                        "description": "Conversation ID or index to switch to",
                    }
                },
                "required": ["conversation_id"],
            },
        ),
        Tool(
            name="chatgpt_delete_conversation",
            description="Delete a conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": ["string", "integer"],
                        "description": "Conversation ID or index to delete",
                    }
                },
                "required": ["conversation_id"],
            },
        ),
        Tool(
            name="chatgpt_enable_think_longer",
            description="Enable Think Longer mode for the next message (enhanced reasoning)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="chatgpt_enable_deep_research",
            description="Enable Deep Research mode for comprehensive web research (250/month quota)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="chatgpt_batch_operations",
            description="Execute multiple ChatGPT operations in sequence",
            inputSchema={
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "description": "List of operations to execute in sequence",
                        "items": {
                            "type": "object",
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "description": "Operation name",
                                    "enum": [
                                        "new_chat",
                                        "send_message",
                                        "send_and_get_response",
                                        "get_last_response",
                                        "get_conversation",
                                        "select_model",
                                        "get_current_model",
                                        "enable_think_longer",
                                        "enable_deep_research",
                                        "upload_file",
                                        "regenerate_response",
                                        "export_conversation",
                                        "save_conversation",
                                        "edit_message",
                                        "list_conversations",
                                        "switch_conversation",
                                        "delete_conversation",
                                        "wait_for_response",
                                    ],
                                },
                                "args": {
                                    "type": "object",
                                    "description": "Arguments for the operation",
                                    "additionalProperties": True,
                                },
                                "continue_on_error": {
                                    "type": "boolean",
                                    "description": "Whether to continue if this operation fails",
                                    "default": False,
                                },
                            },
                            "required": ["operation"],
                        },
                    }
                },
                "required": ["operations"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute ChatGPT automation tools"""

    try:
        ctrl = await get_controller()

        if name == "chatgpt_launch":
            await ctrl.launch()
            return [TextContent(type="text", text="ChatGPT launched successfully")]

        elif name == "chatgpt_send_message":
            message = arguments["message"]
            result = await ctrl.send_message(message)
            return [TextContent(type="text", text=result)]

        elif name == "chatgpt_new_chat":
            result = await ctrl.new_chat()
            return [TextContent(type="text", text=result)]

        elif name == "chatgpt_get_model":
            model = await ctrl.get_current_model()
            return [TextContent(type="text", text=f"Current model: {model or 'Unknown'}")]

        elif name == "chatgpt_select_model":
            model = arguments["model"]
            success = await ctrl.select_model(model)
            status = "selected successfully" if success else "selection failed"
            return [TextContent(type="text", text=f"Model {model}: {status}")]

        elif name == "chatgpt_status":
            is_ready = await ctrl.is_ready()
            status = "ready" if is_ready else "not ready"

            result = {"status": status, "ready": is_ready}

            if is_ready:
                model = await ctrl.get_current_model()
                result["current_model"] = model

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "chatgpt_wait_response":
            timeout = arguments.get("timeout", 30)
            success = await ctrl.wait_for_response(timeout)
            status = "response complete" if success else "timeout waiting for response"
            return [TextContent(type="text", text=status)]

        elif name == "chatgpt_send_and_get_response":
            message = arguments["message"]
            
            # Get current model to determine appropriate timeout
            current_model = await ctrl.get_current_model()
            
            # Check if Deep Research or other special mode is active
            # (You could enhance this by tracking the current mode)
            mode = None
            if "research" in message.lower() or "deep research" in message.lower():
                mode = "deep_research"
            
            # Use provided timeout or calculate based on model/mode
            default_timeout = get_default_timeout(model=current_model, mode=mode)
            timeout = arguments.get("timeout", default_timeout)
            
            # Log the timeout being used
            logger.info(f"Using timeout of {format_timeout_for_display(timeout)} for model {current_model or 'unknown'}")

            response = await ctrl.send_and_get_response(message, timeout)

            if response:
                return [TextContent(type="text", text=response)]
            else:
                return [TextContent(type="text", text="No response received")]

        elif name == "chatgpt_get_conversation":
            conversation = await ctrl.get_conversation()

            return [TextContent(type="text", text=json.dumps(conversation, indent=2))]

        elif name == "chatgpt_get_last_response":
            timeout = arguments.get("timeout", 10)

            # Wait a bit if still responding
            await ctrl.wait_for_response(timeout)

            response = await ctrl.get_last_response()

            if response:
                return [TextContent(type="text", text=response)]
            else:
                return [TextContent(type="text", text="No response found")]

        elif name == "chatgpt_upload_file":
            file_path = arguments["file_path"]
            success = await ctrl.upload_file(file_path)

            if success:
                return [TextContent(type="text", text=f"File uploaded successfully: {file_path}")]
            else:
                return [TextContent(type="text", text=f"Failed to upload file: {file_path}")]

        elif name == "chatgpt_regenerate":
            success = await ctrl.regenerate_response()

            if success:
                return [TextContent(type="text", text="Response regeneration initiated")]
            else:
                return [TextContent(type="text", text="Failed to regenerate response")]

        elif name == "chatgpt_export_conversation":
            format = arguments.get("format", "markdown")
            content = await ctrl.export_conversation(format)

            if content:
                return [TextContent(type="text", text=content)]
            else:
                return [TextContent(type="text", text="Failed to export conversation")]

        elif name == "chatgpt_save_conversation":
            filename = arguments.get("filename")
            format = arguments.get("format", "markdown")

            file_path = await ctrl.save_conversation(filename, format)

            if file_path:
                return [TextContent(type="text", text=f"Conversation saved to: {file_path}")]
            else:
                return [TextContent(type="text", text="Failed to save conversation")]

        elif name == "chatgpt_edit_message":
            message_index = arguments["message_index"]
            new_content = arguments["new_content"]

            success = await ctrl.edit_message(message_index, new_content)

            if success:
                return [
                    TextContent(type="text", text=f"Message {message_index} edited successfully")
                ]
            else:
                return [TextContent(type="text", text=f"Failed to edit message {message_index}")]

        elif name == "chatgpt_list_conversations":
            conversations = await ctrl.list_conversations()

            if conversations:
                return [TextContent(type="text", text=json.dumps(conversations, indent=2))]
            else:
                return [TextContent(type="text", text="No conversations found")]

        elif name == "chatgpt_switch_conversation":
            conversation_id = arguments["conversation_id"]

            success = await ctrl.switch_conversation(conversation_id)

            if success:
                return [
                    TextContent(type="text", text=f"Switched to conversation: {conversation_id}")
                ]
            else:
                return [
                    TextContent(
                        type="text", text=f"Failed to switch to conversation: {conversation_id}"
                    )
                ]

        elif name == "chatgpt_delete_conversation":
            conversation_id = arguments["conversation_id"]

            success = await ctrl.delete_conversation(conversation_id)

            if success:
                return [TextContent(type="text", text=f"Deleted conversation: {conversation_id}")]
            else:
                return [
                    TextContent(
                        type="text", text=f"Failed to delete conversation: {conversation_id}"
                    )
                ]

        elif name == "chatgpt_enable_think_longer":
            success = await ctrl.enable_think_longer()

            if success:
                return [TextContent(type="text", text="Think Longer mode enabled for next message")]
            else:
                return [TextContent(type="text", text="Failed to enable Think Longer mode")]

        elif name == "chatgpt_enable_deep_research":
            success = await ctrl.enable_deep_research()

            if success:
                return [TextContent(type="text", text="Deep Research mode enabled")]
            else:
                return [TextContent(type="text", text="Failed to enable Deep Research mode")]

        elif name == "chatgpt_batch_operations":
            operations = arguments["operations"]
            result = await ctrl.execute_batch_operations(operations)

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise McpError(ErrorData(code=-32601, message=f"Unknown tool: {name}"))

    except McpError:
        # Re-raise McpError as-is
        raise
    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
        raise McpError(ErrorData(code=-32603, message=f"Tool execution failed: {str(e)}"))


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
                    capabilities=ServerCapabilities(tools=ToolsCapability()),
                ),
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
