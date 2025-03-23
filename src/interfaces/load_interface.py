"""
This module provides the `LoadInterface` class, which is used to fetch and process energy data 
from various sources such as OpenHAB and Home Assistant. It also includes methods to create 
load profiles based on historical energy consumption data.
"""
from datetime import datetime, timedelta
import logging
import requests

logger = logging.getLogger("__main__")
logger.info("[LOAD-IF] loading module ")

class LoadInterface:
    """
        LoadInterface class provides methods to fetch and process energy data from various sources 
        such as OpenHAB and Home Assistant. It also supports creating load profiles based on the 
        retrieved energy data.
    """
    def __init__(self,src,url,load_sensor,access_token,timezone="Europe/Berlin"):
        self.src = src
        self.url = url
        self.load_sensor = load_sensor
        self.access_token = access_token
        self.time_zone = timezone

    # get load data from url persistance source
    def fetch_energy_data_from_openhab(self, openhab_item_url, start_time, end_time):
        """
        Fetch energy data from the specified OpenHAB item URL within the given time range.
        """
        if openhab_item_url == "":
            return {"data": []}
        openhab_item_url = ( self.url + "/rest/persistence/items/" +
                            self.load_sensor)
        params = {"starttime": start_time.isoformat(), "endtime": end_time.isoformat()}
        try:
            response = requests.get(openhab_item_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("[LOAD-IF] OPENHAB - Request timed out while fetching energy data.")
            return {"data": []}
        except requests.exceptions.RequestException as e:
            logger.error("[LOAD-IF] OPENHAB - Request failed while fetching energy data: %s", e)
            return {"data": []}

    def fetch_historical_energy_data_from_homeassistant(self, entity_id, start_time, end_time):
        """
        Fetch historical energy data for a specific entity from Home Assistant.

        Args:
            entity_id (str): The ID of the entity to fetch data for.
            start_time (datetime): The start time for the historical data.
            end_time (datetime): The end time for the historical data.

        Returns:
            list: A list of historical state changes for the entity.
        """
        # Headers for the API request
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }

        # API endpoint to get the history of the entity
        url = f'{self.url}/api/history/period/{start_time.isoformat()}'

        # Parameters for the API request
        params = {
            'filter_entity_id': entity_id,
            'end_time': end_time.isoformat()
        }
        # print debug start and end time human readable
        # print(f'HA Request - Start time: {start_time}')
        # print(f'HA Request - End time: {end_time}')

        # Make the API request
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            # Check if the request was successful
            if response.status_code == 200:
                historical_data = response.json()
                # Extract only 'state' and 'last_updated' from the historical data
                filtered_data = [
                    {"state": entry["state"], "last_updated": entry["last_updated"]}
                    for sublist in historical_data
                    for entry in sublist
                ]
                return filtered_data
            logger.error(
                '[LOAD-IF] HOMEASSISTANT - Failed to retrieve historical data: %s',
                response.status_code
            )
            logger.error(response.text)
            return []
        except requests.exceptions.Timeout:
            logger.error(
                ("[LOAD-IF] HOMEASSISTANT - Request timed out ",
                "while fetching historical energy data.")
            )
            return []
        except requests.exceptions.RequestException as e:
            logger.error(
                ("[LOAD-IF] HOMEASSISTANT - Request failed ",
                "while fetching historical energy data: %s"),
                e)
            return []

    def process_energy_data(self, data):
        """
        Processes energy data to calculate the average energy consumption.
        """
        total_energy = 0
        count = len(data["data"])
        for data_entry in data["data"]:
            try:
                float(data_entry["state"])
            except ValueError:
                count -= 1
                continue
            total_energy += float(data_entry["state"]) * -1
        if count > 0:
            # print(f'Total energy: {round(total_energy / count, 4)}')
            return round(total_energy / count, 4)
        return 0

    def create_load_profile_openhab_from_last_days(self, tgt_duration, start_time=None):
        """
        Creates a load profile for energy consumption over the last `tgt_duration` hours.

        The function calculates the energy consumption for each hour from the current hour
        going back `tgt_duration` hours. It fetches energy data for base load and additional loads,
        processes the data, and sums the energy values. If the total energy for an hour is zero,
        it skips that hour. The resulting load profile is a list of energy consumption values
        for each hour.

        """
        logger.info("[LOAD-IF] Creating load profile from openhab ...")
        current_time = datetime.now(self.time_zone).replace(minute=0, second=0, microsecond=0)
        if start_time is None:
            start_time = current_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(hours=tgt_duration)
            end_time = start_time + timedelta(hours=tgt_duration)
        else:
            start_time = current_time - timedelta(hours=tgt_duration)
            end_time = current_time

        load_profile = []
        current_hour = start_time

        while current_hour < end_time:
            next_hour = current_hour + timedelta(hours=1)
            # logger.debug("[LOAD] Fetching data for %s to %s",current_hour, next_hour)

            energy_data = self.fetch_energy_data_from_openhab(
                self.url, current_hour, next_hour
            )
            energy = self.process_energy_data(energy_data)
            if energy == 0:
                current_hour += timedelta(hours=1)
                continue

            energy_sum = energy
            # easy workaround to prevent car charging energy data in the standard load profile
            if energy_sum > 10800:
                energy_sum = energy_sum - 10800
            elif energy_sum > 9200:
                energy_sum = energy_sum - 9200

            load_profile.append(energy_sum)
            logger.debug("[LOAD-IF] Energy for %s: %s", current_hour, energy_sum)

            current_hour += timedelta(hours=1)
        logger.info("[LOAD-IF] Load profile created successfully.")
        return load_profile

    def create_load_profile_homeassistant_from_last_days(self, tgt_duration, start_time=None):
        """
        Creates a load profile for energy consumption over the last `tgt_duration` hours.

        This function calculates the energy consumption for each hour from the current hour
        going back `tgt_duration` hours. It fetches energy data from Home Assistant,
        processes the data, and sums the energy values. If the total energy for an hour is zero,
        it skips that hour. The resulting load profile is a list of energy consumption values
        for each hour.

        Args:
            tgt_duration (int): The target duration in hours for which the load profile is needed.
            start_time (datetime, optional): The start time for fetching the load profile.
            Defaults to None.

        Returns:
            list: A list of energy consumption values for the specified duration.
        """
        logger.info("[LOAD] Creating load profile from Home Assistant ...")
        current_time = datetime.now(self.time_zone).replace(minute=0, second=0, microsecond=0)
        if start_time is None:
            start_time = current_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(hours=tgt_duration)
            end_time = start_time + timedelta(hours=tgt_duration)
        else:
            start_time = current_time - timedelta(hours=tgt_duration)
            end_time = current_time

        load_profile = []
        current_hour = start_time

        # print(f'HA Start time: {start_time}')
        # print(f'HA End time: {end_time}')

        while current_hour < end_time:
            next_hour = current_hour + timedelta(hours=1)
            # logger.debug("[LOAD] Fetching data for %s to %s", current_hour, next_hour)

            energy_data = self.fetch_historical_energy_data_from_homeassistant(
                self.load_sensor, current_hour, next_hour
            )
            energy = self.process_energy_data({"data": energy_data})
            if energy == 0:
                current_hour += timedelta(hours=1)
                continue

            energy_sum = energy
            # easy workaround to prevent car charging energy data in the standard load profile
            if energy_sum > 10800:
                energy_sum = energy_sum - 10800
            elif energy_sum > 9200:
                energy_sum = energy_sum - 9200

            load_profile.append(energy_sum)
            logger.debug("[LOAD-IF] Energy for %s: %s", current_hour, energy_sum)

            current_hour += timedelta(hours=1)
        logger.info("[LOAD-IF] Load profile created successfully.")
        return load_profile

    def get_load_profile(self, tgt_duration, start_time=None):
        """
        Retrieves the load profile based on the configured source.

        Depending on the configuration, this function fetches the load profile from one of the
        following sources:
        - Default: Returns a predefined static load profile.
        - OpenHAB: Fetches the load profile from an OpenHAB instance.
        - Home Assistant: Fetches the load profile from a Home Assistant instance.

        Args:
            tgt_duration (int): The target duration in hours for which the load profile is needed.
            start_time (datetime, optional): The start time for fetching the load profile.
            Defaults to None.

        Returns:
            list: A list of energy consumption values for the specified duration.
        """
        if self.src == "default":
            logger.info("[LOAD-IF] Using load source default")
            default_profile = [
                200.0, # 0:00 - 1:00 -- day 1
                200.0, # 1:00 - 2:00
                200.0, # 2:00 - 3:00
                200.0, # 3:00 - 4:00
                200.0, # 4:00 - 5:00
                300.0, # 5:00 - 6:00
                350.0, # 6:00 - 7:00
                400.0, # 7:00 - 8:00
                350.0, # 8:00 - 9:00
                300.0, # 9:00 - 10:00
                300.0, # 10:00 - 11:00
                550.0, # 11:00 - 12:00
                450.0, # 12:00 - 13:00
                400.0, # 13:00 - 14:00
                300.0, # 14:00 - 15:00
                300.0, # 15:00 - 16:00
                400.0, # 16:00 - 17:00
                450.0, # 17:00 - 18:00
                500.0, # 18:00 - 19:00
                500.0, # 19:00 - 20:00
                500.0, # 20:00 - 21:00
                400.0, # 21:00 - 22:00
                300.0, # 22:00 - 23:00
                200.0, # 23:00 - 0:00
                200.0, # 0:00 - 1:00 -- day 2
                200.0, # 1:00 - 2:00
                200.0, # 2:00 - 3:00
                200.0, # 3:00 - 4:00
                200.0, # 4:00 - 5:00
                300.0, # 5:00 - 6:00
                350.0, # 6:00 - 7:00
                400.0, # 7:00 - 8:00
                350.0, # 8:00 - 9:00
                300.0, # 9:00 - 10:00
                300.0, # 10:00 - 11:00
                550.0, # 11:00 - 12:00
                450.0, # 12:00 - 13:00
                400.0, # 13:00 - 14:00
                300.0, # 14:00 - 15:00
                300.0, # 15:00 - 16:00
                400.0, # 16:00 - 17:00
                450.0, # 17:00 - 18:00
                500.0, # 18:00 - 19:00
                500.0, # 19:00 - 20:00
                500.0, # 20:00 - 21:00
                400.0, # 21:00 - 22:00
                300.0, # 22:00 - 23:00
                200.0, # 23:00 - 0:00
            ]
            return default_profile[:tgt_duration]
        if self.src == "openhab":
            # logger.info("[LOAD] Using load source openhab")
            return self.create_load_profile_openhab_from_last_days(tgt_duration, start_time)
        if self.src == "homeassistant":
            # logger.info("[LOAD] Using load source homeassistant")
            return self.create_load_profile_homeassistant_from_last_days(tgt_duration, start_time)
        logger.error(
            "[LOAD-IF] Load source '%s' currently not supported. Using default.",
            self.src,
        )
        return []
