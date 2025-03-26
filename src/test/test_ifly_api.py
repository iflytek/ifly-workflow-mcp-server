import logging

from typing import Iterator

from src.mcp_server.server import ifly_client


def test_chat():

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
