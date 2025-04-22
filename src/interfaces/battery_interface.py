"""
- BatteryInterface: A class to interact with SOC data sources, retrieve battery SOC, and calculate
  dynamic maximum charge power based on SOC.
- threading: For managing background update services.
- time: For managing sleep intervals in the update loop.
sensor identifier, access token (if required), and maximum fixed charge power. Use the
`battery_request_current_soc` method to fetch the current SOC value or `get_max_charge_power_dyn`
to calculate the dynamic maximum charge power.
    access_token=None,
    max_charge_power_w=3000
max_charge_power = battery_interface.get_max_charge_power_dyn()
print(f"Max Charge Power: {max_charge_power}W")
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
    sensor identifier, and access token (if required). Use the `battery_request_current_soc`
    method to fetch the current SOC value.
Example:
    ```python
    battery_interface = BatteryInterface(
        src="openhab",
        url="http://openhab-server",
        soc_sensor="BatterySOC",
        access_token=None
    current_soc = battery_interface.battery_request_current_soc()
    print(f"Current SOC: {current_soc}%")
    ```
"""

import logging
import threading
import time
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
        battery_request_current_soc():
            Fetches the current SOC of the battery based on the configured source.
    """

    def __init__(self, src, url, soc_sensor, access_token, battery_data):
        self.src = src
        self.url = url
        self.soc_sensor = soc_sensor
        self.access_token = access_token
        self.max_charge_power_fix = battery_data.get("max_charge_power_w", 0)
        self.battery_data = battery_data
        self.current_soc = 0
        self.current_usable_capacity = 0
        self.update_interval = 30
        self._update_thread = None
        self._stop_event = threading.Event()
        self.start_update_service()

    def __fetch_soc_data_from_openhab(self):
        """
        Fetches the State of Charge (SOC) data for the battery from the OpenHAB server.

        This method sends a GET request to the OpenHAB REST API to retrieve the SOC value
        for the battery. If the request is successful, the SOC value is extracted, converted
        to a percentage, and returned. In case of a timeout or request failure, a default
        SOC value of 5% is returned, and an error is logged.

        Returns:
            int: The SOC value as a percentage (0-100). Defaults to 5% in case of an error.
        """
        logger.debug("[BATTERY-IF] getting SOC from openhab ...")
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
                "Using default SOC = %s%%.",
                soc,
            )
            return soc  # Default SOC value in case of timeout
        except requests.exceptions.RequestException as e:
            logger.error(
                (
                    "[BATTERY-IF] OPENHAB - Request failed while fetching battery SOC: %s. "
                    "Using default SOC = %s%%."
                ),
                e,
                soc,
            )
            return soc  # Default SOC value in case of request failure

    def __fetch_soc_data_from_homeassistant(self):
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
        # logger.debug("[BATTERY-IF] getting SOC from homeassistant ...")
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
            logger.debug("[BATTERY-IF] successfully fetched SOC = %s %%", soc)
            return round(soc, 1)
        except requests.exceptions.Timeout:
            logger.error(
                (
                    "[BATTERY-IF] HOMEASSISTANT - Request timed out while fetching battery SOC. "
                    "Using default SOC = %s%%.",
                    soc,
                )
            )
            return soc  # Default SOC value in case of timeout
        except requests.exceptions.RequestException as e:
            logger.error(
                (
                    "[BATTERY-IF] HOMEASSISTANT - Request failed while fetching battery SOC: %s. "
                    "Using default SOC = %s %%."
                ),
                e,
                soc,
            )
            return soc  # Default SOC value in case of request failure

    def __battery_request_current_soc(self):
        """
        Fetch the current state of charge (SOC) of the battery from OpenHAB.
        """
        # default value for start SOC = 5
        if self.src == "default":
            logger.debug("[BATTERY-IF] source set to default with start SOC = 5%")
            return 5
        if self.src == "openhab":
            self.current_soc = self.__fetch_soc_data_from_openhab()
            return self.current_soc
        if self.src == "homeassistant":
            self.current_soc = self.__fetch_soc_data_from_homeassistant()
            return self.current_soc
        logger.error(
            "[BATTERY-IF] source currently not supported. Using default start SOC = 5%."
        )
        return 5

    def get_current_soc(self):
        """
        Returns the current state of charge (SOC) of the battery.
        """
        return self.current_soc

    def get_current_usable_capacity(self):
        """
        Returns the current usable capacity of the battery.
        """
        return round(self.current_usable_capacity, 2)

    def get_max_charge_power_dyn(self, soc=None):
        """
        Calculates the maximum charge power of the battery depending on the SOC.

        - If SOC < 60%, the fixed maximum charge power is used.
        - If SOC >= 60% and < 95%, the maximum charge power decreases linearly.
        - If SOC >= 95%, the maximum charge power is fixed at 500W.

        Args:
            soc (float, optional): The state of charge to use for calculation.
                       If None, the current SOC is used.

        Returns:
            float: The dynamically calculated maximum charge power in watts.
        """
        if soc is None:
            soc = self.current_soc

        if soc < 70:
            return self.max_charge_power_fix
        elif soc >= 70 and soc < 95:
            return max(500, self.max_charge_power_fix * ((95 - soc) / 35))
            # return max(500, self.max_charge_power_fix * (1 - (soc / 100)**2))
        else:  # SOC >= 95
            return 500

    def start_update_service(self):
        """
        Starts the background thread to periodically update the state.
        """
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_event.clear()
            self._update_thread = threading.Thread(
                target=self._update_state_loop, daemon=True
            )
            self._update_thread.start()
            logger.info("[BATTERY-IF] Update service started.")

    def shutdown(self):
        """
        Stops the background thread and shuts down the update service.
        """
        if self._update_thread and self._update_thread.is_alive():
            self._stop_event.set()
            self._update_thread.join()
            logger.info("[BATTERY-IF] Update service stopped.")

    def _update_state_loop(self):
        """
        The loop that runs in the background thread to update the state.
        """
        while not self._stop_event.is_set():
            try:
                self.__battery_request_current_soc()
                self.current_usable_capacity = (
                    self.battery_data.get("capacity_wh", 0)
                    * self.battery_data.get("discharge_efficiency",1.0)
                    * (self.current_soc - self.battery_data.get("min_soc_percentage",0)) / 100
                )
            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                logger.error("[BATTERY-IF] Error while updating state: %s", e)
                # Break the sleep interval into smaller chunks to allow immediate shutdown
            sleep_interval = self.update_interval
            while sleep_interval > 0:
                if self._stop_event.is_set():
                    return  # Exit immediately if stop event is set
                time.sleep(min(1, sleep_interval))  # Sleep in 1-second chunks
                sleep_interval -= 1

        self.start_update_service()
