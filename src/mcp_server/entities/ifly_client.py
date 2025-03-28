import json
import os
from abc import ABC
from enum import Enum
from typing import Dict, Any

import requests
import yaml

from mcp_server.entities.flow import Flow


class SysTool(Enum):
    """
    sys tools enum
    """
    SYS_UPLOAD_FILE = "SYS_UPLOAD_FILE"
    """ Workflow provides file upload """


class IFlyWorkflowClient(ABC):
    base_url = "https://xingchen-api.xf-yun.com"

    def __init__(self, config_path: str = os.getenv("CONFIG_PATH")):
        """
        init
        :param config_path: config path，default is CONFIG_PATH
        """
        if not config_path:
            raise ValueError("CONFIG_PATH is not set")

        with open(config_path, 'r', encoding='utf-8') as file:
            self.flows = [Flow(**flow) for flow in yaml.safe_load(file)]
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
                flow_id=SysTool.SYS_UPLOAD_FILE.value,
                name=SysTool.SYS_UPLOAD_FILE.value,
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
