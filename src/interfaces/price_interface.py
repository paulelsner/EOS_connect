'''
This module provides the `PriceInterface` class, which is designed to handle electricity price 
data retrieval, processing, and management from various sources. It includes methods for fetching
current prices, generating feed-in prices, and updating price data for a specified duration and
start time. The module supports integration with the Akkudoktor API and Tibber API for retrieving
electricity prices.
Classes:
    PriceInterface: A class for managing electricity price data, including fetching, processing, 
    and generating feed-in prices.
Constants:
    AKKUDOKTOR_API_PRICES (str): The URL for the Akkudoktor API to fetch electricity prices.
    TIBBER_API (str): The URL for the Tibber API to fetch electricity prices.
Dependencies:
    - datetime: For handling date and time operations.
    - json: For parsing JSON responses from APIs.
    - logging: For logging messages and errors.
    - requests: For making HTTP requests to APIs.
Usage:
    Create an instance of the `PriceInterface` class with the desired configuration, and use its
    methods to fetch and process electricity price data.
Example:
    price_interface = PriceInterface(
        src="tibber",
        access_token="your_access_token",
        feed_in_tariff_price=5.0,
        negative_price_switch=True,
        timezone="Europe/Berlin"
    price_interface.update_prices(tgt_duration=24, start_time=datetime.now())
    current_prices = price_interface.get_current_prices()
    current_feedin_prices = price_interface.get_current_feedin_prices()
'''
from datetime import datetime, timedelta
import json
import logging
import requests

logger = logging.getLogger("__main__")
logger.info("[PRICE-IF] loading module ")

AKKUDOKTOR_API_PRICES = "https://api.akkudoktor.net/prices"
TIBBER_API = "https://api.tibber.com/v1-beta/gql"


class PriceInterface:
    '''
    PriceInterface is a class designed to handle electricity price data retrieval, processing, 
    and management from various sources. It provides methods to fetch current prices, 
    generate feed-in prices, and update price data for a specified duration and start time.
    Attributes:
        src (str): The source of the price data (e.g., 'tibber', 'default').
        access_token (str): The access token for authenticating with the price source.
        feed_in_tariff_price (float): The feed-in tariff price in cents per kWh.
        negative_price_switch (bool): A flag to determine whether to set feed-in prices to 0
        for negative prices.
        timezone (str): The timezone used for date and time operations.
        current_prices (list): A list of current prices fetched from the price source.
        current_prices_direct (list): A list of current prices without tax.
        current_feedin (list): A list of current feed-in prices.
    Methods:
        update_prices(tgt_duration, start_time):
            Updates the current prices and feed-in prices based on the target duration and
            start time.
        get_current_prices():
            Returns the current prices fetched from the price source.
        get_current_feedin_prices():
            Returns the current feed-in prices fetched from the price source.
        __create_feedin_prices():
            Creates feed-in prices based on the current prices and the configured feed-in
            tariff price.
        __retrieve_prices(tgt_duration, start_time=None):
            Retrieves prices based on the target duration and optional start time from the
            configured source.
        __retrieve_prices_from_akkudoktor(tgt_duration, start_time=None):
            Fetches and processes electricity prices for today and tomorrow from the
            Akkudoktor API.
        __retrieve_prices_from_tibber(tgt_duration, start_time=None):
            Fetches and processes electricity prices for today and tomorrow from the Tibber API.
    '''
    def __init__(
        self,
        src,
        access_token,
        feed_in_tariff_price=0.0,
        negative_price_switch=False,
        timezone="UTC",
    ):
        self.src = src
        self.access_token = access_token
        self.feed_in_tariff_price = feed_in_tariff_price
        self.negative_price_switch = negative_price_switch
        self.time_zone = timezone
        self.current_prices = []
        self.current_prices_direct = []  # without tax
        self.current_feedin = []

    def update_prices(self, tgt_duration, start_time):
        """
        Updates the current prices and feed-in prices based on the target duration 
        and start time provided.

        Args:
            tgt_duration (int): The target duration for which prices need to be retrieved.
            start_time (datetime): The starting time for retrieving prices.

        Updates:
            self.current_prices: Updates with the retrieved prices for the given duration
                                 and start time.
            self.current_feedin: Updates with the generated feed-in prices.

        Logs:
            Logs a debug message indicating that prices have been updated.
        """
        self.current_prices = self.__retrieve_prices(tgt_duration, start_time)
        self.current_feedin = self.__create_feedin_prices()
        logger.debug("[PRICE-IF] Prices updated")

    def get_current_prices(self):
        """
        Returns the current prices.

        This function returns the current prices fetched from the price source.
        If the source is not supported, it returns an empty list.

        Returns:
            list: A list of current prices.
        """
        return self.current_prices

    def get_current_feedin_prices(self):
        """
        Returns the current feed-in prices.

        This function returns the current feed-in prices fetched from the price source.
        If the source is not supported, it returns an empty list.

        Returns:
            list: A list of current feed-in prices.
        """
        return self.current_feedin

    def __create_feedin_prices(self):
        """
        Creates feed-in prices based on the current prices.

        This function generates feed-in prices based on the current prices and the
        configured feed-in tariff price. If the negative price switch is enabled,
        feed-in prices are set to 0 for negative prices. Otherwise, the feed-in tariff
        price is used for all prices.

        Returns:
            list: A list of feed-in prices.
        """
        if self.negative_price_switch:
            self.current_feedin = [
                0 if price < 0 else round(self.feed_in_tariff_price / 1000, 9)
                for price in self.current_prices_direct
            ]
        else:
            self.current_feedin = [
                round(self.feed_in_tariff_price / 1000, 9)
                for price in self.current_prices_direct
            ]
        return self.current_feedin

    def __retrieve_prices(self, tgt_duration, start_time=None):
        """
        Retrieve prices based on the target duration and optional start time.

        This function fetches prices from different sources based on the configuration.
        It supports fetching prices from 'tibber' and 'default' sources.

        Args:
            tgt_duration (int): The target duration for which prices are to be fetched.
            start_time (datetime, optional): The start time from which prices are to be fetched.
            Defaults to None.

        Returns:
            list: A list of prices for the specified duration and start time. Returns an empty list
            if the price source is not supported.
        """
        if self.src == "tibber":
            return self.__retrieve_prices_from_tibber(tgt_duration, start_time)
        if self.src == "default":
            return self.__retrieve_prices_from_akkudoktor(tgt_duration, start_time)
        logger.error("[PRICE-IF] Price source currently not supported.")
        return []

    def __retrieve_prices_from_akkudoktor(self, tgt_duration, start_time=None):
        """
        Fetches and processes electricity prices for today and tomorrow.

        This function retrieves electricity prices for today and tomorrow from an API,
        processes the prices, and returns a list of prices for the specified duration starting
        from the specified start time. If tomorrow's prices are not available, today's prices are
        repeated for tomorrow.

        Args:
            tgt_duration (int): The target duration in hours for which the prices are needed.
            start_time (datetime, optional): The start time for fetching prices. Defaults to None.

        Returns:
            list: A list of electricity prices for the specified duration starting
                from the specified start time.
        """
        if self.src != "default":
            logger.error(
                "[PRICE-IF] Price source %s currently not supported.",
                self.src,
            )
            return []
        logger.debug("[PRICE-IF] Fetching prices from akkudoktor ...")
        if start_time is None:
            start_time = datetime.now(self.time_zone).replace(
                minute=0, second=0, microsecond=0
            )
        current_hour = start_time.hour
        request_url = (
            AKKUDOKTOR_API_PRICES
            + "?start="
            + start_time.strftime("%Y-%m-%d")
            + "&end="
            + (start_time + timedelta(days=1)).strftime("%Y-%m-%d")
        )
        logger.debug("[PRICE-IF] Requesting prices from akkudoktor: %s", request_url)
        try:
            response = requests.get(request_url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            logger.error(
                "[PRICE-IF] Request timed out while fetching prices from akkudoktor."
            )
            return []
        except requests.exceptions.RequestException as e:
            logger.error(
                "[PRICE-IF] Request failed while fetching prices from akkudoktor: %s", e
            )
            return []

        prices = []
        for price in data["values"]:
            prices.append(round(price["marketpriceEurocentPerKWh"] / 100000, 9))
            # logger.debug(
            #     "[Main] day 1 - price for %s -> %s", price["marketpriceEurocentPerKWh"],
            #       price["start"]
            # )

        if start_time is None:
            start_time = datetime.now(self.time_zone).replace(
                minute=0, second=0, microsecond=0
            )
        current_hour = start_time.hour
        extended_prices = prices[current_hour : current_hour + tgt_duration]

        if len(extended_prices) < tgt_duration:
            remaining_hours = tgt_duration - len(extended_prices)
            extended_prices.extend(prices[:remaining_hours])
        logger.info("[PRICE-IF] Prices from AKKUDOKTOR fetched successfully.")
        self.current_prices_direct = extended_prices.copy()
        return extended_prices

    def __retrieve_prices_from_tibber(self, tgt_duration, start_time=None):
        """
        Fetches and processes electricity prices for today and tomorrow.

        This function retrieves electricity prices for today and tomorrow from a web service,
        processes the prices, and returns a list of prices for the specified duration starting
        from the specified start time. If tomorrow's prices are not available, today's prices are
        repeated for tomorrow.

        Args:
            tgt_duration (int): The target duration in hours for which the prices are needed.
            start_time (datetime, optional): The start time for fetching prices. Defaults to None.

        Returns:
            list: A list of electricity prices for the specified duration starting
                from the specified start time.
        """
        logger.debug("[PRICE-IF] Prices fetching from TIBBER started")
        if self.src != "tibber":
            logger.error("[PRICE-IF] Price source currently not supported.")
            return []
        headers = {
            "Authorization": self.access_token,
            "Content-Type": "application/json",
        }
        query = """
        {
            viewer {
                homes {
                    currentSubscription {
                        priceInfo {
                            today {
                                total
                                energy
                                startsAt
                            }
                            tomorrow {
                                total
                                energy
                                startsAt
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            response = requests.post(
                TIBBER_API, headers=headers, json={"query": query}, timeout=10
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(
                "[PRICE-IF] Request timed out while fetching prices from Tibber."
            )
            return []
        except requests.exceptions.RequestException as e:
            logger.error(
                "[PRICE-IF] Request failed while fetching prices from Tibber: %s", e
            )
            return []

        response.raise_for_status()
        data = response.json()
        if "errors" in data and data["errors"] is not None:
            logger.error(
                "[PRICE-IF] Error fetching prices - tibber API response: %s",
                data["errors"][0]["message"],
            )
            return []

        today_prices = json.dumps(
            data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"][
                "today"
            ]
        )
        tomorrow_prices = json.dumps(
            data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"][
                "tomorrow"
            ]
        )

        today_prices_json = json.loads(today_prices)
        tomorrow_prices_json = json.loads(tomorrow_prices)
        prices = []
        prices_direct = []

        for price in today_prices_json:
            prices.append(round(price["total"] / 1000, 9))
            prices_direct.append(round(price["energy"] / 1000, 9))
            # logger.debug(
            #     "[Main] day 1 - price for %s -> %s", price["startsAt"], price["total"]
            # )
        if tomorrow_prices_json:
            for price in tomorrow_prices_json:
                prices.append(round(price["total"] / 1000, 9))
                prices_direct.append(round(price["energy"] / 1000, 9))
                # logger.debug(
                #     "[Main] day 2 - price for %s -> %s", price["startsAt"], price["total"]
                # )
        else:
            prices.extend(prices[:24])  # Repeat today's prices for tomorrow
            prices_direct.extend(
                prices_direct[:24]
            )  # Repeat today's prices for tomorrow

        if start_time is None:
            start_time = datetime.now(self.time_zone).replace(
                minute=0, second=0, microsecond=0
            )
        current_hour = start_time.hour
        extended_prices = prices[current_hour : current_hour + tgt_duration]
        extended_prices_direct = prices_direct[
            current_hour : current_hour + tgt_duration
        ]

        if len(extended_prices) < tgt_duration:
            remaining_hours = tgt_duration - len(extended_prices)
            extended_prices.extend(prices[:remaining_hours])
            extended_prices_direct.extend(prices_direct[:remaining_hours])
        self.current_prices_direct = extended_prices_direct.copy()
        logger.info("[PRICE-IF] Prices from TIBBER fetched successfully.")
        return extended_prices
