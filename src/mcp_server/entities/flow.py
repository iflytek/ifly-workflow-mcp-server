from typing import Any, Dict

from pydantic import BaseModel, Field


class Flow(BaseModel):
    flow_id: str
    name: str = ''
    description: str = ''
    api_key: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    """A JSON Schema object defining the expected parameters for the tool."""
