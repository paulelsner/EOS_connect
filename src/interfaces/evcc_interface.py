'''
This module provides the `EvccInterface` class, which serves as an interface to interact 
with the Electric Vehicle Charging Controller (EVCC) API. The class enables periodic 
fetching of the charging state and triggers a callback when the state changes.
Classes:
    EvccInterface: A class to interact with the EVCC API, manage charging state updates, 
                   and handle state change callbacks.
Dependencies:
    - logging: For logging messages and errors.
    - threading: For managing background threads.
    - time: For implementing delays in the update loop.
    - requests: For making HTTP requests to the EVCC API.
Usage:
    Create an instance of the `EvccInterface` class by providing the EVCC API URL, 
    an optional update interval, and a callback function to handle charging state changes. 
    The class will automatically start a background thread to periodically fetch the 
    charging state from the API.
'''
import logging
import threading
import time
import requests

logger = logging.getLogger("__main__")
logger.info("[EVCC] loading module ")


class EvccInterface:
    '''
        EvccInterface is a class that provides an interface to interact with the EVCC
        (Electric Vehicle Charging Controller) API. 
        It periodically fetches the charging state and triggers a callback when the state changes.
        Attributes:
            last_known_charging_state (bool): The last known charging state.
            on_charging_state_change (callable): A callback function to be called when
                                                 the charging state changes.
            _update_thread (threading.Thread):   The background thread for updating
                                                 the charging state.
            _stop_event (threading.Event):       An event to signal the thread to stop.
        Methods:
            __init__(url, update_interval=15, on_charging_state_change=None):
            get_charging_state():
            start_update_service():
            shutdown():
            _update_charging_state_loop():
            request_charging_state():
                Fetches the EVCC state from the API and updates the charging state.
            fetch_evcc_state_via_api():
    '''
    def __init__(self, url, update_interval=15, on_charging_state_change=None):
        """
        Initializes the EVCC interface and starts the update service.

        Args:
            url (str): The base URL for the EVCC API.
            update_interval (int): The interval (in seconds) for updating the charging state.
            on_charging_state_change (callable): A callback function to be called when the
            charging state changes.
        """
        self.url = url
        self.last_known_charging_state = False
        self.update_interval = update_interval
        self.on_charging_state_change = on_charging_state_change  # Store the callback
        self._update_thread = None
        self._stop_event = threading.Event()
        self.start_update_service()

    def get_charging_state(self):
        """
        Returns the last known charging state.
        """
        return self.last_known_charging_state

    def start_update_service(self):
        """
        Starts the background thread to periodically update the charging state.
        """
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_event.clear()
            self._update_thread = threading.Thread(
                target=self._update_charging_state_loop, daemon=True
            )
            self._update_thread.start()
            logger.info("[EVCC] Update service started.")

    def shutdown(self):
        """
        Stops the background thread and shuts down the update service.
        """
        if self._update_thread and self._update_thread.is_alive():
            self._stop_event.set()
            self._update_thread.join()
            logger.info("[EVCC] Update service stopped.")

    def _update_charging_state_loop(self):
        """
        The loop that runs in the background thread to update the charging state.
        """
        while not self._stop_event.is_set():
            try:
                self.request_charging_state()
            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                logger.error("[EVCC] Error while updating charging state: %s", e)
            time.sleep(self.update_interval)

        self.start_update_service()

    def request_charging_state(self):
        """
        Fetches the EVCC state from the API and returns the charging state.
        """
        data = self.fetch_evcc_state_via_api()
        if not data or not isinstance(data.get("result", {}).get("loadpoints"), list):
            logger.error("[EVCC] Invalid or missing loadpoints in the response.")
            return None
        loadpoint = data["result"]["loadpoints"][0] if data["result"]["loadpoints"] else None
        charging_state = loadpoint.get("charging") if loadpoint else None
        if not isinstance(charging_state, bool):
            logger.error("[EVCC] Charging state is not a valid boolean value.")
            return None
        logger.debug("[EVCC] Charging state: %s", charging_state)

        # Check if the charging state has changed
        if charging_state != self.last_known_charging_state:
            logger.info("[EVCC] Charging state changed to: %s", charging_state)
            self.last_known_charging_state = charging_state

            # Trigger the callback if provided
            if self.on_charging_state_change:
                self.on_charging_state_change(charging_state)

        return charging_state

    def fetch_evcc_state_via_api(self):
        """
        Fetches the state of the EVCC (Electric Vehicle Charging Controller) via its API.

        This method sends a GET request to the EVCC API endpoint to retrieve the current state.
        If the request is successful, the response is parsed as JSON and returned.
        In case of a timeout or other request-related errors, the method logs the error and
        returns None.

        Returns:
            dict: The JSON response from the EVCC API containing the state information, 
                  or None if the request fails or times out.
        """
        evcc_url = self.url + "/api/state"
        # logger.debug("[EVCC] fetching evcc state with url: %s", evcc_url)
        try:
            response = requests.get(evcc_url, timeout=6)
            response.raise_for_status()
            data = response.json()
            # logger.debug("[EVCC] successfully fetched EVCC state")
            return data
        except requests.exceptions.Timeout:
            logger.error("[EVCC] Request timed out while fetching EVCC state.")
            return None  # Default SOC value in case of timeout
        except requests.exceptions.RequestException as e:
            logger.error(
                "[EVCC] Request failed while fetching EVCC state. Error: %s.", e
            )
            return None  # Default SOC value in case of request failure
