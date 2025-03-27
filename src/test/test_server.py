import logging

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

from mcp_server.entities.ifly_client import SysTool

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="uvx",  # Executable
    args=[
        "--from",
        "../..",
        "ifly_workflow_mcp_server"
    ],  # Optional command line arguments
    env={
        "CONFIG_PATH": "../../config.yaml"
    },  # Optional environment variables
)


# Optional: create a sampling callback
async def handle_sampling_message(
        message: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello, world! from model",
        ),
        model="gpt-3.5-turbo",
        stopReason="endTurn",
    )


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
                read, write, sampling_callback=handle_sampling_message
        ) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            logging.info(f"tools: {tools}")

            # Call a tool
            sys_upload_file_result = await session.call_tool(
                SysTool.SYS_UPLOAD_FILE.value,
                arguments={"file": "/Users/hygao1024/Documents/iFlytek/Work/测试图片.jpg"}
            )
            logging.info(f"call sys_upload_file result: {sys_upload_file_result}")

            image_generator_result = await session.call_tool("image_generator", arguments={"AGENT_USER_INPUT": "你好"})
            logging.info(f"call image_generator result: {image_generator_result}")

            llm_test_result = await session.call_tool("llm_test", arguments={"AGENT_USER_INPUT": "你好"})
            logging.info(f"call llm_test_result result: {llm_test_result}")


def test_run():
    import asyncio

    asyncio.run(run())
