#!/usr/bin/env python
import os

try:
    import ujson
except ImportError:
    import json as ujson  # type: ignore
import apiai
from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler
from redis import Redis
import Facebook
from Facebook import webhook, handlers
from Facebook.message import Message
from func import *
import ast  # Just to convert payload in quick_reply to dictionary

import giphy

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__author__ = "hundredeir"

api_ai_token: str = "redacted"
ai = apiai.ApiAI(api_ai_token)
client = Client("", auto_log_stacks=True)  # sentry client
handler = SentryHandler(client)
handler.setLevel(logging.INFO)
setup_logging(handler)

verify_token: str = ""
page_access_token: str = ""
app_secret_key = ""

sent: Facebook.Send = Facebook.Send(page_access_token)
redis = Redis("", 4040)


def _get_ai_session(message: Message) -> Any:
    user_id = message.user_id
    ai.session_id = user_id
    request = ai.text_request()
    request.lang = "en"
    return request


# @handlers.text_handler()
def text_func(message: Message) -> None:
    user_id: Union[int, str] = message.user_id
    request = _get_ai_session(message)
    sent.sender_action(user_id)
    sent.sender_action(user_id, action="typing_on")
    msg: str = message.message_received.text
    try:
        request.query = msg
        resp = ujson.loads(
            request.getresponse().read().decode()
        )  # reading raw and decoding it into utf-8
        result = resp["result"]  # result of the query sent to api.ai
        if result.get("action"):  # value of action is name of the function to be called
            for each_action in actions:
                if result.get("action") == each_action:
                    if message.message_received.quick_reply is not None:
                        logger.debug(message.message_received.quick_reply_payload)
                        result["payload"] = ast.literal_eval(
                            message.message_received.quick_reply_payload
                        )
                    actions[each_action](result, user_id, sent)
        else:
            reply = str(result["fulfillment"]["speech"])
            sent.send_text(user_id, reply)
    except KeyError:
        client.captureException()


# @handlers.attachment_handler
def attachment_func(message: Message) -> None:
    user_id: str = message.user_id
    sent.sender_action(user_id)
    sent.sender_action(user_id, action="typing_on")
    request = _get_ai_session(message)
    if message.message_received.attachments:
        type: str = message.message_received.attachments.type
        if message.message_received.attachments.url is not None:
            url: str = message.message_received.attachments.url
            try:
                sent.send_attachment(user_id, type, url)
            except Exception:
                client.captureException()


# @handlers.attachment_handler
def location_func(message: Message, attachment_type: str = "location") -> None:
    logger = logging.getLogger("Bot.location_func")
    logger.setLevel(logging.ERROR)
    user_id: str = message.user_id
    ai.session_id = user_id
    request = ai.text_request()
    if type == "location":
        lat = message.message_received.attachments.coordinates_lat
        long = message.message_received.attachments.coordinates_long
        try:
            location = str(lat) + "," + str(long)
        except:
            location = lat + "," + long
        request.query = location
        resp: Dict[str, Any] = ujson.loads(request.getresponse().read().decode())
        result = resp.get("result")
        if result.get("action"):
            for each_action in actions:
                if result["action"] == each_action:
                    actions[each_action](result, user_id, sent)
        else:
            sent.send_text(user_id, "Should I come there and meet you")


def _get_source_and_dest(user_id: str, payload: Dict[str, Any]) -> None:
    hash_name = "user:{}".format(user_id)
    if payload["station"] == "source":
        source = payload["code"]
        date = payload["date"]
        if redis.hexists(hash_name, "destination"):
            fetch_trains(
                sent,
                user_id,
                source,
                redis.hget(hash_name, "code"),
                redis.hget(hash_name, "date"),
            )
            redis.delete(hash_name)
        else:
            redis.hmset(hash_name, {"source": source, "date": date})
    elif payload["station"] == "destination":
        destination = payload["code"]
        if redis.hexists(hash_name, "source"):
            hash_dict = redis.hgetall(hash_name)
            logger.info(hash_dict)
            fetch_trains(
                sent,
                user_id,
                redis.hget(hash_name, "code"),
                destination,
                redis.hget(hash_name, "date"),
            )
            redis.delete(hash_name)
        else:
            redis.hmset(
                hash_name, {"destination": destination, "date": payload["date"]}
            )
    else:
        raise KeyError


# @handlers.postback_handler
def postback_func(message: Message) -> None:
    logger = logging.getLogger("Bot.postback_func")
    logger.setLevel(logging.ERROR)
    user_id: Union[str, int] = message.user_id
    request = _get_ai_session(message)
    payload = ast.literal_eval(message.message_received.postback_payload)
    logging.info(payload)
    if payload.get("query") == "fetch_trains":
        try:
            _get_source_and_dest(user_id, payload)
        except Exception:
            client.captureException()
    elif payload.get("query") == "check_avail":
        logger = logging.getLogger("Bot.main.postback.check_avail")
        logger.setLevel(logging.DEBUG)
        payload.pop("query")
        Generate = Facebook.Generate
        quick_replies = []
        for train_classes in payload.get("classes"):
            quick_reply = Generate.quick_reply(
                content_type="text",
                title=train_classes,
                payload=message.message_received.postback_payload,
            )
            quick_replies.append(quick_reply)
        response_from_facebook = sent.send_text(
            user_id, "choose a class", quick_replies=quick_replies
        )
    elif payload.get("query") == "more_info":
        logger = logging.getLogger("Bot.main.postback.more_info")
        classes = ""
        date = payload.get("date")
        proper_date = date[0:4] + "/" + date[4:6] + "/" + date[6:]
        for class_train in payload.get("classes"):
            classes = class_train + "," + classes
        text = (
            payload.get("trainNo")
            + "   "
            + payload.get("train_name")
            + "\n\n"
            + payload.get("source_name")
            + "  ->  "
            + payload.get("destination_name")
            + "\n"
            + "Date : "
            + proper_date
            + "\n"
            + "available classes : "
            + classes
        )
        response_from_facebook = sent.send_text(user_id, text)


def main(message):
    try:
        logger = logging.getLogger("Bot.main")
        logger.setLevel(logging.ERROR)
        logger.info("This works")
        location_func(message, "location")

    except:
        client.captureException()


actions = {
    "get_weather": get_forecast,
    "nearby": foursquare,
    "get_Me": get_me,
    "fetch_stations": fetch_stations,
    "fetch_trains": fetch_trains,
    "check_availability": check_avail,
}

PORT = int(os.environ.get("PORT", "5000"))
# func_list: Callable[..., Any] = [main, giphy.giphy_search, text_func, attachment_func]
web_api = webhook.HttpApi(verify_token, app_secret_key)
web_api.add_text_handler(giphy.giphy_search, "!giphy", handlers.Position.START)
web_api.add_text_handler(text_func)
web_api.add_attachment_handler(attachment_func)
web_api.add_attachment_handler(location_func, "location")
web_api.add_postback_handler(postback_func)

app = web_api.app
# app = webhook.http(func_list, verify_token, app_secret_key=app_secret_key)
