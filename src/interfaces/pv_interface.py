"""
pv_interface.py

This module provides the PvInterface class, which serves as an interface for fetching and summarizing photovoltaic (PV) power and temperature forecasts. It handles configuration validation, periodic background updates, and provides default fallback values in case of API errors. The module is designed to interact with the EOS API to retrieve forecast data for one or more PV systems, aggregate the results, and make them available for further processing or monitoring.

Classes:
    PvInterface: Manages PV and temperature forecast retrieval, configuration validation, periodic updates, and provides summarized forecast data.

Constants:
    EOS_API_GET_PV_FORECAST: The endpoint URL for fetching PV forecast data from the EOS API.

Logging:
    Uses the standard Python logging module to log information, debug messages, and errors related to configuration, API requests, and background updates.
"""

from datetime import datetime, timedelta
import threading
import time
import logging
import requests

logger = logging.getLogger("__main__")
logger.info("[PV-IF] loading module ")

EOS_API_GET_PV_FORECAST = "https://api.akkudoktor.net/forecast"

class PvInterface:
    """
    Interface for fetching and summarizing PV (photovoltaic) and temperature forecasts.
    Handles configuration validation, periodic updates, and default fallbacks.
    """

    def __init__(
        self,
        config,
        timezone="UTC",
    ):
        self.config = config
        self.time_zone = timezone

        self.__check_config()  # Validate configuration parameters

        self.pv_forcast_array = []
        self.temp_forecast_array = []

        self._update_thread = None
        self._stop_event = threading.Event()
        self.update_interval = 15 * 60  # Update 15 minutes (in seconds)
        logger.info(
            "[PV-IF] Initialized"
        )
        self.__start_update_service()  # Start the background thread for periodic updates

    def __check_config(self):
        """
        Checks the configuration for required parameters.

        This function checks if the necessary parameters are present in the configuration.
        If any required parameter is missing, it raises a ValueError.

        Raises:
            ValueError: If any required parameter is missing from the configuration.
        """
        if not len(self.config) > 0:
            logger.error("[PV-IF] Initialize - No pv entries found")
        else:
            logger.debug("[PV-IF] Initialize - pv entries found: %s", len(self.config))
            for config_entry in self.config:
                # check for each entries the mandatory params
                # name: Garden
                # lat: 45.2328
                # lon: 8.32742
                # azimuth: 13
                # tilt: 31
                # power: 860
                # powerInverter: 800
                # inverterEfficiency: 0.95
                # horizont: 0,0,0,0,0,0,0,0,50t0.4,70,0,0,0,0,0,0,0,0
                if config_entry.get("name",""):
                    logger.debug("[PV-IF] Initialize - config entry name: %s", config_entry.get("name",""))
                else:
                    logger.debug("[PV-IF] Initialize - config entry name not found")
                if config_entry.get("lat", None) is None:
                    raise ValueError("[PV-IF] Initialize - lat not found in config entry")
                if config_entry.get("lon", None) is None:
                    raise ValueError("[PV-IF] Initialize - lon not found in config entry")
                if config_entry.get("azimuth", None) is None:
                    raise ValueError("[PV-IF] Initialize - azimuth not found in config entry")
                if config_entry.get("tilt", None) is None:
                    raise ValueError("[PV-IF] Initialize - tilt not found in config entry")
                if config_entry.get("power", None) is None:
                    raise ValueError("[PV-IF] Initialize - power not found in config entry")
                # if config_entry.get("powerInverter", None) is None:
                #     raise ValueError("[PV-IF] Initialize - powerInverter not found in config entry")
                # if config_entry.get("inverterEfficiency", None) is None:
                #     raise ValueError("[PV-IF] Initialize - inverterEfficiency not found in config entry")
                # if config_entry.get("horizont", None) is None:
                #     config_entry["horizont"] = ""
                #     logger.debug("[PV-IF] Initialize - horizont not found in config entry, using default empty value")    

    def __start_update_service(self):
        """
        Starts the background thread to periodically update the charging state.
        """
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_event.clear()
            self._update_thread = threading.Thread(
                target=self.__update_pv_state_loop, daemon=True
            )
            self._update_thread.start()
            logger.info("[PV-IF] Update service started.")

    def shutdown(self):
        """
        Stops the background thread and shuts down the update service.
        """
        if self._update_thread and self._update_thread.is_alive():
            self._stop_event.set()
            self._update_thread.join()
            logger.info("[PV-IF] Update service stopped.")

    def __update_pv_state_loop(self):
        """
        The loop that runs in the background thread to update the pv state.
        """
        while not self._stop_event.is_set():
            # Fetch the PV forecast data
            self.pv_forcast_array = self.get_summarized_pv_forecast(48)
            self.temp_forecast_array = self.get_pv_forecast(tgt_value="temperature", pv_config_entry=self.config[0], tgt_duration=48)
            logger.info("[PV-IF] PV and Temperature updated")
            # Break the sleep interval into smaller chunks to allow immediate shutdown
            sleep_interval = self.update_interval
            while sleep_interval > 0:
                if self._stop_event.is_set():
                    return  # Exit immediately if stop event is set
                time.sleep(min(1, sleep_interval))  # Sleep in 1-second chunks
                sleep_interval -= 1

        self.start_update_service()

    def get_current_pv_forecast(self):
        """
        """
        # logger.debug(
        #     "[PV-IF] Returning current PV forecast: %s", self.pv_forcast_array
        # )
        return self.pv_forcast_array

    def get_current_temp_forecast(self):
        """
        """
        # logger.debug(
        #     "[PV-IF] Returning current temp forecast: %s", self.temp_forecast_array
        # )
        return self.temp_forecast_array

    def __create_forecast_request(self, pv_config_entry):
        """
        Creates a forecast request URL for the EOS server.
        """
        horizont_string = ""
        if pv_config_entry["horizont"] != "":
            horizont_string = "&horizont=" + str(pv_config_entry["horizont"])
        return (
            EOS_API_GET_PV_FORECAST
            + "?lat="
            + str(pv_config_entry["lat"])
            + "&lon="
            + str(pv_config_entry["lon"])
            + "&azimuth="
            + str(pv_config_entry["azimuth"])
            + "&tilt="
            + str(pv_config_entry["tilt"])
            + "&power="
            + str(pv_config_entry["power"])
            + "&powerInverter="
            + str(pv_config_entry["powerInverter"])
            + "&inverterEfficiency="
            + str(pv_config_entry["inverterEfficiency"])
            + horizont_string
        )

    def __get_default_pv_forcast(self, pv_power):
        """
        Creates a default PV forecast with fixed values based on max power.
        """
        # Create a 24-hour default forecast
        forecast_24h = [
            pv_power * 0.0, # 0% at 00:00
            pv_power * 0.0, # 0% at 01:00
            pv_power * 0.0, # 0% at 02:00
            pv_power * 0.0, # 0% at 03:00
            pv_power * 0.0, # 0% at 04:00
            pv_power * 0.0, # 0% at 05:00
            pv_power * 0.1, # 30% at 06:00
            pv_power * 0.2, # 50% at 07:00
            pv_power * 0.3, # 60% at 08:00
            pv_power * 0.4, # 70% at 09:00
            pv_power * 0.5, # 90% at 10:00
            pv_power * 0.6, # 80% at 11:00
            pv_power * 0.7, # 70% at 12:00
            pv_power * 0.6, # 60% at 13:00
            pv_power * 0.5, # 50% at 14:00 
            pv_power * 0.4, # 40% at 15:00
            pv_power * 0.3, # 30% at 16:00
            pv_power * 0.2, # 20% at 17:00
            pv_power * 0.1, # 10% at 18:00
            pv_power * 0.0, # 0% at 19:00
            pv_power * 0.0, # 0% at 20:00
            pv_power * 0.0, # 0% at 21:00
            pv_power * 0.0, # 0% at 22:00
            pv_power * 0.0, # 0% at 23:00,
        ]
        # Repeat for the next day (48 hours total)
        # logger.debug("[PV-IF] Using default PV forecast with %s W max power", pv_power)
        return forecast_24h * 2

    def __get_default_temperature_forecast(self):
        """
        Creates a default temperature forecast with fixed values.
        The values are set to 20 degrees Celsius for the entire day.
        """
        # Create a 24-hour default temperature forecast
        forecast_24h = [15.0] * 24  # 15 degrees Celsius for each hour
        logger.debug("[PV-IF] Using default temperature forecast with 15 degrees")
        return forecast_24h * 2  # Repeat for the next day (48 hours total)

    def get_pv_forecast(self, tgt_value="power", pv_config_entry=None, tgt_duration=24):
        """
        Fetches the PV forecast data from the EOS API and processes it to extract
        power and temperature values for the specified duration starting from the current hour.
        """
        if pv_config_entry is None:
            logger.error("[PV-IF] No PV config entry provided for target: %s", tgt_value)
            return []
        forecast_request_payload = self.__create_forecast_request(pv_config_entry)
        # print(forecast_request_payload)
        recv_error = False
        try:
            response = requests.get(forecast_request_payload, timeout=5)
            response.raise_for_status()
            day_values = response.json()
            day_values = day_values["values"]
        except requests.exceptions.Timeout:
            logger.error("[PV-IF] Request timed out while fetching PV forecast. (%s)", tgt_value)
            recv_error = True
        except requests.exceptions.RequestException as e:
            logger.error("[PV-IF] Request failed while fetching PV forecast (%s): %s", tgt_value, e)
            recv_error = True
        if recv_error:
            if tgt_value == "power":
                logger.info(
                    "[PV-IF] Using default PV forecast with max %s W for %s",
                    pv_config_entry["power"], pv_config_entry["name"]
                )
                # return a default forecast with 0% at night and 100% at noon
                return self.__get_default_pv_forcast(pv_config_entry["power"])
            else:
                logger.info(
                    "[PV-IF] Using default temperature forecast for %s",
                    pv_config_entry["name"],
                )
                # return a default temperature forecast with 0% at night and 100% at noon
                return self.__get_default_temperature_forecast()

        forecast_values = []
        # current_time = datetime.now(self.time_zone).astimezone()
        current_time = (
            datetime.now(self.time_zone)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone()
        )
        end_time = current_time + timedelta(hours=tgt_duration)

        for forecast_entry in day_values:
            for forecast in forecast_entry:
                entry_time = datetime.fromisoformat(forecast["datetime"]).astimezone()
                if current_time <= entry_time < end_time:
                    value = forecast.get(tgt_value, 0)
                    # if power is negative, set it to 0 (fixing wrong values form api)
                    if tgt_value == "power" and value < 0:
                        value = 0
                    forecast_values.append(value)
        request_type = "PV forecast"
        pv_config_name = "for " + pv_config_entry["name"]
        if tgt_value == "temperature":
            request_type = "Temperature forecast"
            pv_config_name = ""
        logger.info(
            "[PV-IF] %s fetched successfully %s",
            request_type,
            pv_config_name,
        )
        # fix for time changes e.g. western europe then fill or reduce the array to 48 values
        if len(forecast_values) > tgt_duration:
            forecast_values = forecast_values[:tgt_duration]
            logger.debug(
                "[PV-IF] Day of time change %s values reduced to %s for %s",
                request_type,
                tgt_duration,
                pv_config_name,
            )
        elif len(forecast_values) < tgt_duration:
            forecast_values.extend(
                [forecast_values[-1]] * (tgt_duration - len(forecast_values))
            )
            logger.debug(
                "[PV-IF] Day of time change %s values extended to %s for %s",
                request_type,
                tgt_duration,
                pv_config_name,
            )
        return forecast_values

    def get_summarized_pv_forecast(self, tgt_duration=24):
        """
        requesting pv forecast freach config entry and summarize the values
        """
        forecast_values = []
        for config_entry in self.config:
            logger.debug("[PV-IF] fetching forecast for '%s'", config_entry["name"])
            forecast = self.get_pv_forecast("power", config_entry, tgt_duration)
            # print("values for " + config_entry+ " -> ")
            # print(forecast)
            if not forecast_values:
                forecast_values = forecast
            else:
                forecast_values = [x + y for x, y in zip(forecast_values, forecast)]
        return forecast_values
