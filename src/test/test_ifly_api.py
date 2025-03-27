import logging

from typing import Iterator


def test_chat():
    from mcp_server.entities.ifly_client import IFlyWorkflowClient
    ifly_client = IFlyWorkflowClient()
    resp = ifly_client.chat_message(
        ifly_client.flows[0],
        {
            "AGENT_USER_INPUT": "a picture of a cat"
        }
    )
    if isinstance(resp, Iterator):
        for res in resp:
            logging.info(res)
    else:
        logging.info(resp)
