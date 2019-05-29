from typing import Dict, Union, List, Tuple, Any

import requests

try:
    import ujson as json
except ImportError:
    import json  # type: ignore
import logging  # type: ignore

logger = logging.getLogger(__name__)


class Rail:
    @staticmethod
    def _parse(response):
        data: str = "https://travel.paytm.com/api/trains/v1/search?client=web&departureDate=20170618&destination=PTK&source=DLI"
        link: str = "https://travel.paytm.com/api/trains/v1/station/DLI - Delhi?client=web"
        availability: str = "https://travel.paytm.com/api/trains/v1/detail?class=2S&client=web&departureDate=20170620&destination=PTK&quota=GN&requestid=30f8a79e-22b7-44a1-b2bb-49b6c4ca3d0c&source=DLI&trainNumber=22429&train_type=O"

    @staticmethod
    def fetch_stations(station: str) -> List[Tuple[str, Union[int, str]]]:
        """
        fetches the names and codes of stations existing in name of station passed. And returns a list of tuple
        consisting of names of related stations.
        :param station: Name of the station
        :return:
        """
        url: str = "https://travel.paytm.com/api/trains/v1/station/{}"
        source_station_url: str = url.format(station)
        payload: Dict[str, str] = {"client": "web"}
        src_station_data: Dict[str, str] = (
            requests.get(url=source_station_url, params=payload)
        ).json()
        station_parse = ParseStations(src_station_data)
        stations = station_parse.parse_stations()
        return stations

    @staticmethod
    def fetch_trains(source: str, destination: str, date: str) -> List["ParseTrains"]:
        """

        :param source: Name of the source platform from which the passenger will board
        :type source: str
        :param destination: Name of the destination platform
        :type destination: str
        :param date: Date of boarding
        :type date: str
        :return: A list of instances containing all the data about train boarding, tiers available, train  number etc.All the stuff
        """
        link: str = "https://travel.paytm.com/api/trains/v1/search"
        payload: Dict[str, Any] = {
            "client": "web",
            "departureDate": date,
            "destination": destination,
            "source": source,
        }
        response = requests.get(url=link, params=payload)
        data: Dict[str, Any] = (response.json())
        data_body: Dict[str, Any] = data["body"]
        train_data = data_body["trains"]
        trains: List[ParseTrains] = []
        for train in train_data:
            trains.append(ParseTrains(train))
        return trains

    @staticmethod
    def fetch_availability(
        source,
        destination,
        departureDate,
        rail_class,
        trainNumber,
        train_type,
        quota="GN",
    ):

        """

        :param source:
        :param destination:
        :param departureDate:
        :param rail_class: belongs to seating class o railway. Like 3 tier, chair car etc
        :param quota:
        :param trainNumber:
        :param train_type:
        :return:
        """
        from random import choice
        from string import ascii_uppercase

        logger = logging.getLogger("Rail.fetch_availability")
        requestid = "".join(choice(ascii_uppercase) for i in range(12))
        url: str = "https://travel.paytm.com/api/trains/v1/detail"
        payload = {
            "client": "web",
            "requestid": requestid,
            "source": source,
            "destination": destination,
            "departureDate": departureDate,
            "class": rail_class,
            "quota": quota,
            "trainNumber": trainNumber,
            "train_type": train_type,
        }
        response = requests.get(url=url, params=payload)
        data = response.json()
        logger.info(data)
        body = data["body"]
        avail_data = []
        for avail in body["availability"]:
            availability_PerDate = ParseAvailability(avail)
            availability_PerDate.fare = body["fare"]["total_collectible"]
            availability_PerDate.distance = body["distance"]
            availability_PerDate.trainName = body["trainName"]
            avail_data.append(availability_PerDate)
        return avail_data


class ParseStations:
    """
    parses the names and codes of stations from json data received from paytm
    """

    def __init__(self, stations_data: Dict[str, str]) -> None:
        self.source_json: Dict[str, Any] = stations_data

    def parse_stations(self) -> List[Tuple[str, Union[int, str]]]:
        """
        collects the names and stations in a list of tuple.
        Tuple contains name at 'zero' index and code os station at 'one'
        :return: a list of tuple containing name and code of station
        """
        meat_stations_data: List[Dict[str, str]] = self.source_json["body"]
        stations_data: List[Tuple[str, Union[int, str]]] = [
            (data.get("name"), data.get("code")) for data in meat_stations_data
        ]
        return stations_data


class ParseTrains:
    def __init__(self, train_data: Dict[str, str]) -> None:
        self.DepartureTime: str = train_data.get("departure")
        self.ArrivalTime = train_data.get("arrival")
        self.trainName = train_data.get("trainName")
        self.trainNumber = train_data.get("trainNumber")
        self.source = train_data.get("source")
        self.destination = train_data.get("destination")
        self.source_name: str = train_data.get("source_name")
        self.destination_name: str = train_data.get("destination_name")
        self.duration = train_data.get("duration")
        self.classes = train_data.get("classes")
        self.train_type = train_data.get("train_type")
        self.runningOn = train_data.get("runningOn")


class ParseAvailability:
    def __init__(self, availability_data: Dict[str, str]) -> None:
        logger = logging.getLogger("Rail.ParseAvailability")
        self.date = availability_data.get("date")
        self.status = availability_data.get("status")
        logger.info(self.status)
        self.booking_allowed = availability_data.get("booking_allowed")
