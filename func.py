import logging
from typing import Dict, Any, List, Union

try:
    import ujson
except ImportError:
    import json as ujson  # type: ignore

import requests

import Facebook.generate
import rail


def get_me(result, user_id: str, sent: Facebook.Send):
    logger = logging.getLogger("func.get_me")
    logger.setLevel(logging.DEBUG)
    first_name, last_name, pic_url, locale, time_zone, gender = sent.get_user_info(
        user_id
    )
    ele = Facebook.Generate.element(
        first_name + " " + last_name, gender + "\n" + locale, pic_url
    )
    res = sent.send_generic_template(user_id, [ele])
    logger.info(res)  # type: ignore


def get_forecast(result, user_id: str, sent: Facebook.Send):
    logger = logging.getLogger("Bot.get_forecast")
    logger.setLevel(logging.DEBUG)
    state_country: str = ""
    if result.get("parameters").get("geo-city"):
        state = result.get("parameters").get("geo-city")
        state_country = state
    if result.get("parameters").get("geo-country"):
        country = result.get("parameters").get("geo-country")
        state_country = (state_country + ",{}").format(country)
    date = result.get("parameters").get("date")
    url = "://api.openweathermap.org/data/2.5/weather"
    key = ""
    params = {"q": state_country, "APPID": key, "units": "metric"}
    response = requests.get(url, params)
    data: Union[Dict[str, Any], bytearray] = response.json()
    try:
        data = ujson.loads(data)
    except:
        pass
    weather: Dict[str, Any] = data["weather"][0]
    description: str = weather["description"]
    print(description)
    icon: str = weather["icon"]
    icon_url: str = "http://openweathermap.org/img/w/{}.png".format(icon)
    temperature = data["main"]["temp"]
    element: Dict[str, Any] = Facebook.Generate.element(
        "Today", str(temperature) + "°C\n" + description, image_url=icon_url
    )
    element_list: List[Dict[str, Any]] = [element]
    response_data = sent.send_generic_template(user_id, element_list)
    logger.info(response_data)  # type: ignore


def foursquare(result, user_id: str, sent: Facebook.Send):
    logger = logging.getLogger("Bot.foursqaure")
    logger.setLevel(logging.DEBUG)
    url: str = "https://api.foursquare.com/v2/venues/explore"
    parameters = result.get("parameters")
    coordinates = parameters.get("location")
    place = parameters.get("place")
    elements: List[Dict[str, Any]] = []
    payload = {
        "ll": coordinates,
        "section": place,
        "limit": 10,
        "venuePhotos": 1,
        "client_id": "",
        "client_secret": "",
        "v": 20170318,
    }
    response = requests.get(url, params=payload)
    all_places: List[FoursquarePlace] = _get_each_place_attribute(response.json())
    for each_place in all_places:
        ele: Dict[str, Any] = Facebook.Generate.element(
            each_place.name, each_place.address, each_place.photo
        )
        elements.append(ele)
    response = sent.send_generic_template(user_id, elements=elements)
    logger.info(response)


def _get_each_place_attribute(response: Dict[str, Any]) -> List["FoursquarePlace"]:
    all_places = []
    for item in response["response"]["groups"][0]["items"]:
        each_place: FoursquarePlace = FoursquarePlace()
        if item.get("venue"):
            each_place.name = item["venue"]["name"]
            address: str = item["venue"]["location"]["formattedAddress"]
            temp: str = ""
            for each in address:
                temp = temp + each + "\n"
            each_place.address = temp
            if item["venue"]["photos"]["groups"]:
                group = item["venue"]["photos"]["groups"][0]
                src = group["items"][0]
                each_place.photo = src["prefix"] + "original" + src["suffix"]
        all_places.append(each_place)
    return all_places


class FoursquarePlace:
    # To store callback data from foursquare
    def __init__(self,) -> None:
        self.name: str = None
        self.address: str = None
        self.photo: str = None


def _get_fetch_train_elements(response, **kwargs):
    date_joined = kwargs["date_joined"]
    logger = logging.getLogger("Bot.func.fetch_trains._get_buttons_for_rail")
    logger.setLevel(logging.INFO)
    Generate = Facebook.Generate
    elements: List[Dict[str, Any]] = []
    for indx, each_train in enumerate(response):
        payload: Dict[str, Any] = {
            "query": "more_info",
            "source": each_train.source,
            "source_name": each_train.source_name,
            "destination": each_train.destination,
            "destination_name": each_train.destination_name,
            "date": date_joined,
            "trainNo": each_train.trainNumber,
            "train_name": each_train.trainName,
            "type": each_train.train_type,
            "classes": each_train.classes,
        }
        button_for_info: Dict[str, Any] = Generate.button(
            "postback", title="info", payload=str(payload)
        )
        logger.info(button_for_info)
        payload["query"]: str = "check_avail"
        button_check_avail: Dict[str, Any] = Generate.button(
            "postback", title="Check availability", payload=str(payload)
        )
        logging.info(button_check_avail)
        buttons: List[Dict[str, Any]] = [button_for_info, button_check_avail]
        elements.append(
            Generate.element(
                title=each_train.trainNumber + "  " + each_train.trainName,
                subtitle=each_train.source_name
                + "->"
                + each_train.destination_name
                + "\n"
                + each_train.DepartureTime
                + "\n"
                + each_train.ArrivalTime,
                buttons=buttons,
            )
        )
        if indx < 10:
            pass
        return elements


def _get_element_fetch_stations(station, date, station_type):
    station_name: str = station[0]
    station_code: Union[str, int] = station[1]
    payload = {
        "query": "fetch_trains",
        "station": station_type,
        "name": station_name,
        "code": station_code,
        "date": date,
    }
    button = Facebook.Generate.button("postback", "select", payload=str(payload))
    element = Facebook.Generate.element(
        title=station_code, subtitle=station_name, buttons=[button]
    )
    return element


def fetch_stations(result, user_id, sent):
    parameters: Dict[str, Any] = result.get("parameters")
    date: str = parameters.get("date")
    date_list: List[str] = date.split("-")
    date_joined: str = "".join(date_list)
    source_name: str = parameters["geo-city"][0]
    destination_name: str = parameters["geo-city"][1]
    source_list = rail.Rail.fetch_stations(source_name)
    destination_list = rail.Rail.fetch_stations(destination_name)
    source_elements = []
    destination_elements = []
    for each_station in source_list:
        element = _get_element_fetch_stations(each_station, date_joined, "source")
        source_elements.append(element)
    for each_station in destination_list:
        element = _get_element_fetch_stations(each_station, date_joined, "destination")
        destination_elements.append(element)
    resp_facebook_source = sent.send_generic_template(user_id, source_elements)
    resp_facebook_destination = sent.send_generic_template(
        user_id, destination_elements
    )


def fetch_trains(sent, user_id, source, destination, date):
    # TODO: This needs a rework
    logger = logging.getLogger("Bot.fetch_trains")
    logger.setLevel(logging.ERROR)
    response = rail.Rail.fetch_trains(source, destination, date.decode("utf-8"))
    elements = _get_fetch_train_elements(response, date_joined=date)
    resp_from_facebook = sent.send_generic_template(user_id, elements)
    logger.info(resp_from_facebook)


def check_avail(result, user_id, sent):
    logger = logging.getLogger("Bot.check_avail")
    logger.setLevel(logging.DEBUG)
    train_class = result["parameters"]["train_classes"]
    payload = result["payload"]
    availability = rail.Rail.fetch_availability(
        payload["source"],
        payload["destination"],
        payload["date"],
        train_class,
        payload["trainNo"],
        payload["type"],
    )
    Generate = Facebook.Generate
    elements = []
    no_of_elements = 0
    for each_date in availability:
        if no_of_elements == 4:
            break
        no_of_elements += 1
        element = Generate.element(title=each_date.date, subtitle=each_date.status)
        elements.append(element)
    response_from_facebook = sent.send_list_template(user_id, elements, "compact")
    logger.info(response_from_facebook)
