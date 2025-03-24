import logging

from typing import Iterator

from src.mcp_server.server import ifly_workflow_api


def test_chat():

    resp = ifly_workflow_api.chat_message(
        ifly_workflow_api.data[2],
        {
            "AGENT_USER_INPUT": "a picture of a cat"
        }
    )
    if isinstance(resp, Iterator):
        for res in resp:
            logging.info(res)
    else:
        logging.info(resp)
