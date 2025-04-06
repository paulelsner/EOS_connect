import logging
import threading
import time
import requests

logger = logging.getLogger("__main__")
logger.info("[EVCC] loading module ")


class EvccInterface:

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
