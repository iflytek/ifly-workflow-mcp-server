import asyncio
import os
from typing import Iterator

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from mcp_server.entities.workflow_api import IFlyWorkflowAPI

config_path = os.getenv("CONFIG_PATH")
server = Server("ifly_workflow_mcp_server")
ifly_workflow_api = IFlyWorkflowAPI(config_path)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools，and convert them to MCP client can call.
    :return:
    """
    tools = []
    for i, flow in enumerate(ifly_workflow_api.flows):
        tools.append(
            types.Tool(
                name=flow.name,
                description=flow.description,
                inputSchema=flow.input_schema,
            )
        )
    return tools


@server.call_tool()
async def handle_call_tool(
        name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Process valid tool call requests and convert them to MCP responses
    :param name:        tool name
    :param arguments:   tool arguments
    :return:
    """
    if name not in ifly_workflow_api.name_idx:
        raise ValueError(f"Unknown tool: {name}")
    flow = ifly_workflow_api.flows[ifly_workflow_api.name_idx[name]]
    if name == "sys_upload_file":
        data = ifly_workflow_api.upload_file(
            flow.api_key,
            arguments["file"],
        )
    else:
        data = ifly_workflow_api.chat_message(
            flow,
            arguments,
        )
    mcp_out = []

    if isinstance(data, Iterator):
        for res in data:
            mcp_out.append(
                types.TextContent(
                    type='text',
                    text=res
                )
            )
    else:
        mcp_out.append(
            types.TextContent(
                type='text',
                text=data
            )
        )
    return mcp_out


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ifly_workflow_mcp_server",
                server_version="0.0.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
