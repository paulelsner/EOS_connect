"""
This module provides the `BatteryInterface` class, which serves as an interface for fetching 
the State of Charge (SOC) data of a battery from various sources such as OpenHAB and Home Assistant.
The `BatteryInterface` class allows users to configure the source of SOC data and retrieve the 
current SOC value through its methods. It supports fetching SOC data from OpenHAB using its REST API 
and from Home Assistant using its API with authentication.
Classes:
    - BatteryInterface: A class to interact with SOC data sources and retrieve battery SOC.
Dependencies:
    - logging: For logging information, warnings, and errors.
    - requests: For making HTTP requests to the SOC data sources.
Usage:
    Create an instance of the `BatteryInterface` class by providing the source, URL,
    sensor identifier, and access token (if required). Use the `battery_get_current_soc` method to
    fetch the current SOC value.
Example:
    ```python
    battery_interface = BatteryInterface(
        src="openhab",
        url="http://openhab-server",
        soc_sensor="BatterySOC",
        access_token=None
    current_soc = battery_interface.battery_get_current_soc()
    print(f"Current SOC: {current_soc}%")
    ```
"""
import logging
import requests

logger = logging.getLogger("__main__")
logger.info("[BATTERY-IF] loading module ")


class BatteryInterface:
    """
    BatteryInterface is a class that provides an interface for fetching the State of Charge (SOC)
    data of a battery from different sources such as OpenHAB and Home Assistant.
    Attributes:
        src (str): The source of the SOC data. Can be "default", "openhab", or "homeassistant".
        url (str): The base URL of the SOC data source.
        soc_sensor (str): The identifier of the SOC sensor in the data source.
        access_token (str): The access token for authentication (used for Home Assistant).
    Methods:
        fetch_soc_data_from_openhab():
            Fetches the SOC data from the OpenHAB server using its REST API.
        fetch_soc_data_from_homeassistant():
            Fetches the SOC data from the Home Assistant API.
        battery_get_current_soc():
            Fetches the current SOC of the battery based on the configured source.
    """

    def __init__(self, src, url, soc_sensor, access_token):
        self.src = src
        self.url = url
        self.soc_sensor = soc_sensor
        self.access_token = access_token

    def fetch_soc_data_from_openhab(self):
        """
        Fetches the State of Charge (SOC) data for the battery from the OpenHAB server.

        This method sends a GET request to the OpenHAB REST API to retrieve the SOC value
        for the battery. If the request is successful, the SOC value is extracted, converted
        to a percentage, and returned. In case of a timeout or request failure, a default
        SOC value of 5% is returned, and an error is logged.

        Returns:
            int: The SOC value as a percentage (0-100). Defaults to 5% in case of an error.
        """
        logger.info("[BATTERY-IF] getting SOC from openhab ...")
        openhab_url = self.url + "/rest/items/" + self.soc_sensor
        soc = 5  # Default SOC value in case of error
        try:
            response = requests.get(openhab_url, timeout=6)
            response.raise_for_status()
            data = response.json()
            soc = float(data["state"]) * 100
            logger.info("[BATTERY-IF] successfully fetched SOC = %s %%", soc)
            return round(soc)
        except requests.exceptions.Timeout:
            logger.error(
                "[BATTERY-IF] OPENHAB - Request timed out while fetching battery SOC. "
                "Using default SOC = %s%%.", soc
            )
            return soc  # Default SOC value in case of timeout
        except requests.exceptions.RequestException as e:
            logger.error(
                (
                    "[BATTERY-IF] OPENHAB - Request failed while fetching battery SOC: %s. "
                    "Using default SOC = %s%%."
                ),
                e,soc
            )
            return soc  # Default SOC value in case of request failure      
        

    def fetch_soc_data_from_homeassistant(self):
        """
        Fetches the state of charge (SOC) data from the Home Assistant API.
        This method sends a GET request to the Home Assistant API to retrieve the SOC
        value for a specific sensor. The SOC value is expected to be in the 'state' field
        of the API response and is converted to a percentage.
        Returns:
            int: The SOC value as a percentage, rounded to the nearest integer.
                 Returns a default value of 5% in case of a timeout or request failure.
        Raises:
            requests.exceptions.Timeout: If the request to the Home Assistant API times out.
            requests.exceptions.RequestException: If there is an error during the request.
        """
        logger.info("[BATTERY-IF] getting SOC from homeassistant ...")
        homeassistant_url = f"{self.url}/api/states/{self.soc_sensor}"
        # Headers for the API request
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        soc = 5  # Default SOC value in case of error
        try:
            response = requests.get(homeassistant_url, headers=headers, timeout=6)
            response.raise_for_status()
            entity_data = response.json()
            # print(f'Entity data: {entity_data}')
            soc = float(entity_data["state"])
            # print(f'State: {state}')
            logger.info("[BATTERY-IF] successfully fetched SOC = %s %%", soc)
            return round(soc)
        except requests.exceptions.Timeout:
            logger.error(
                (
                    "[BATTERY-IF] HOMEASSISTANT - Request timed out while fetching battery SOC. "
                    "Using default SOC = %s%%.", soc
                )
            )
            return soc  # Default SOC value in case of timeout
        except requests.exceptions.RequestException as e:
            logger.error(
                (
                    "[BATTERY-IF] HOMEASSISTANT - Request failed while fetching battery SOC: %s. "
                    "Using default SOC = %s %%."
                ),
                e,soc
            )
            return soc  # Default SOC value in case of request failure

    def battery_get_current_soc(self):
        """
        Fetch the current state of charge (SOC) of the battery from OpenHAB.
        """
        # default value for start SOC = 5
        if self.src == "default":
            logger.debug("[BATTERY-IF] source set to default with start SOC = 5%")
            return 5
        if self.src == "openhab":
            return self.fetch_soc_data_from_openhab()
        if self.src == "homeassistant":
            return self.fetch_soc_data_from_homeassistant()
        logger.error(
            "[BATTERY-IF] source currently not supported. Using default start SOC = 5%."
        )
        return 5
