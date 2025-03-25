import asyncio
import json
import os
from abc import ABC
from dataclasses import field
from typing import Dict, Any, Iterator

import mcp.server.stdio
import mcp.types as types
import requests
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from omegaconf import OmegaConf
from pydantic import BaseModel


class Flow(BaseModel):
    flow_id: str
    name: str = ''
    description: str = ''
    api_key: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    """A JSON Schema object defining the expected parameters for the tool."""


class IFlyWorkflowAPI(ABC):
    base_url = "https://xingchen-api.xf-yun.com"

    def __init__(self, config_path: str):
        if not config_path:
            raise ValueError("config path not provided")

        self.flows = [Flow(**flow) for flow in OmegaConf.load(config_path)]
        self.name_idx: Dict[str, int] = {}

        # get flow info
        for flow in self.flows:
            flow_info = self.get_flow_info(flow.flow_id, flow.api_key)
            flow.name = flow.name if flow.name else flow_info["data"]["name"]
            flow.description = flow.description if flow.description else flow_info["data"]["description"]
            flow.input_schema = flow_info["data"]["inputSchema"]

        self._add_sys_tool()

        # build name_idx
        for i, flow in enumerate(self.flows):
            self.name_idx[flow.name] = i

    def _add_sys_tool(self):
        """
        add default sys tools
        :return:
        """
        self.flows.append(
            # add sys_upload_file
            Flow(
                flow_id="sys_upload_file",
                name="sys_upload_file",
                api_key=self.flows[0].api_key,
                description="upload file. Format support: image(jpg、png、bmp、jpeg), doc(pdf)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "file path"
                        }
                    },
                    "required": ["file"]
                }
            )
        )

    def chat_message(
            self,
            flow: Flow,
            inputs: Dict[str, Any],
            stream: bool = True
    ) -> str:
        """
        flow chat request
        :param flow:
        :param inputs:
        :param stream:
        :return:
        """
        url = f"{self.base_url}/workflow/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {flow.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "flow_id": flow.flow_id,
            "parameters": inputs,
            "stream": stream
        }
        response = requests.post(
            url, headers=headers, json=data, stream=stream)
        response.raise_for_status()
        if stream:
            for line in response.iter_lines():
                if line and line.startswith(b'data:'):
                    try:
                        src_content = line[5:].decode('utf-8')
                        json_data = json.loads(src_content)
                        if json_data.get("code", 0) != 0:
                            yield src_content
                            break
                        choice = json_data["choices"][0]
                        yield choice["delta"]["content"]
                        if choice["finish_reason"] == "stop":
                            break
                    except json.JSONDecodeError:
                        yield f"Error decoding JSON: {line}"
        else:
            json_data = response.json()
            if json_data.get("code", 0) != 0:
                yield json.dumps(json_data)
            else:
                yield json_data["choices"][0]["delta"]["content"]

    def get_flow_info(
            self,
            flow_id: str,
            api_key: str
    ) -> Dict[str, Any]:
        """
        get flow info, such as flow description, parameters
        :param flow_id:
        :param api_key:
        :return:
        """
        url = f"{self.base_url}/workflow/v1/get_flow_info/{flow_id}"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        if json_data.get("code", 0) != 0:
            raise ValueError(json_data)
        return json_data

    def upload_file(
            self,
            api_key,
            file_path,
    ) -> str:

        url = f"{self.base_url}/workflow/v1/upload_file"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        with open(file_path, "rb") as file:
            files = {"file": file}
            response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.content.decode('utf-8')


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
