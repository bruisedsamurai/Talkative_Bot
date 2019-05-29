import logging
from typing import Dict, Any

import requests
from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

from Facebook import Send
from Facebook.message import Message

client = Client("", auto_log_stacks=True)  # sentry client
handler = SentryHandler(client)
handler.setLevel(logging.ERROR)
setup_logging(handler)

send = Send(page_access_token="")


# @handlers.text_handler("!giphy", Position.START)
def giphy_search(message: Message):
    logger = logging.getLogger("giphy.giphy_search")
    logger.setLevel(logging.ERROR)
    user_id = message.user_id
    send.sender_action(user_id)
    send.sender_action(user_id, "typing_on")
    api_key: str = ""
    url: str = "https://api.giphy.com/v1/gifs/search"
    msg: str = message.message_received.text
    msg = msg.replace(" ", "+")
    params = {"api_key": api_key, "q": msg, "limit": 5, "rating": "PG", "lang": "en"}
    resp_giphy = requests.get(url, params)
    assert resp_giphy.status_code == 200, (
        "giphy responded with an error,"
        "status code - %s. Expected 200" % resp_giphy.status_code
    )
    resp_giphy_json: Dict[str, Any] = resp_giphy.json()
    for each_gif in resp_giphy_json["data"]:
        diff_format_gif: Dict[str, Dict[str, str]] = each_gif["images"]
        orig_gif: Dict[str, str] = diff_format_gif["original"]
        gif_url: str = orig_gif["url"]
        logger.error("gif_url")
        resp_img = send.send_attachment(user_id, "image", gif_url)
