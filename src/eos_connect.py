"""
This module fetches energy data from OpenHAB, processes it, and creates a load profile.
"""

import os
import sys
from datetime import datetime, timedelta
import time
import logging
import json
from threading import Thread
import sched
import pytz
import requests
from flask import Flask, Response, render_template_string
from gevent.pywsgi import WSGIServer
from config import ConfigManager
from interfaces.base_control import BaseControl
from interfaces.load_interface import LoadInterface
from interfaces.battery_interface import BatteryInterface
from interfaces.inverter_fronius import FroniusWR
from interfaces.evcc_interface import EvccInterface
from interfaces.eos_interface import EosInterface

EOS_TGT_DURATION = 48


###################################################################################################
# Custom formatter to use the configured timezone
class TimezoneFormatter(logging.Formatter):
    """
    A custom logging formatter that formats log timestamps according to a specified timezone.
    """

    def __init__(self, fmt=None, datefmt=None, tz=None):
        super().__init__(fmt, datefmt)
        self.tz = tz

    def formatTime(self, record, datefmt=None):
        # Convert the record's timestamp to the configured timezone
        record_time = datetime.fromtimestamp(record.created, self.tz)
        return record_time.strftime(datefmt or self.default_time_format)


###################################################################################################
LOGLEVEL = logging.DEBUG  # start before reading the config file
logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"
)
streamhandler = logging.StreamHandler(sys.stdout)

streamhandler.setFormatter(formatter)
logger.addHandler(streamhandler)
logger.setLevel(LOGLEVEL)
logger.info("[Main] Starting eos_connect")
###################################################################################################
base_path = os.path.dirname(os.path.abspath(__file__))
# get param to set a specific path
if len(sys.argv) > 1:
    current_dir = sys.argv[1]
else:
    current_dir = base_path
###################################################################################################
config_manager = ConfigManager(current_dir)
time_zone = pytz.timezone(config_manager.config["time_zone"])

LOGLEVEL = config_manager.config["log_level"].upper()
logger.setLevel(LOGLEVEL)
formatter = TimezoneFormatter(
    "%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S", tz=time_zone
)
streamhandler.setFormatter(formatter)
logger.info(
    "[Main] set user defined time zone to %s and loglevel to %s",
    config_manager.config["time_zone"],
    LOGLEVEL,
)
# initialize eos interface
eos_interface = EosInterface(
    eos_server=config_manager.config["eos"]["server"],
    eos_port=config_manager.config["eos"]["port"],
    timezone=time_zone,
)
# initialize base control
base_control = BaseControl(config_manager.config, time_zone)
# initialize the inverter interface
inverter_interface = None
if config_manager.config["inverter"]["type"] == "fronius_gen24":
    inverter_config = {
        "address": config_manager.config["inverter"]["address"],
        "max_grid_charge_rate": config_manager.config["inverter"][
            "max_grid_charge_rate"
        ],
        "max_pv_charge_rate": config_manager.config["inverter"]["max_pv_charge_rate"],
        "user": config_manager.config["inverter"]["user"],
        "password": config_manager.config["inverter"]["password"],
    }
    inverter_interface = FroniusWR(inverter_config)
else:
    logger.info(
        "[Inverter] Inverter type %s - no external connection."
        + " Changing to show only mode.",
        config_manager.config["inverter"]["type"],
    )


# callback function for evcc interface
def charging_state_callback(new_state):
    """
    Callback function that gets triggered when the charging state changes.
    """
    logger.info("[MAIN] EVCC Event - Charging state changed to: %s", new_state)
    change_control_state()


evcc_interface = EvccInterface(
    url=config_manager.config["evcc"]["url"],
    update_interval=10,
    on_charging_state_change=charging_state_callback,
)

# time.sleep(120)

# evcc_interface.shutdown()

# sys.exit(0)

# intialize the load interface
load_interface = LoadInterface(
    config_manager.config.get("load", {}).get("source", ""),
    config_manager.config.get("load", {}).get("url", ""),
    config_manager.config.get("load", {}).get("load_sensor", ""),
    config_manager.config.get("load", {}).get("car_charge_load_sensor", ""),
    config_manager.config.get("load", {}).get("access_token", ""),
    time_zone,
)

battery_interface = BatteryInterface(
    config_manager.config.get("battery", {}).get("source", ""),
    config_manager.config.get("battery", {}).get("url", ""),
    config_manager.config.get("battery", {}).get("soc_sensor", ""),
    config_manager.config.get("battery", {}).get("access_token", ""),
)

EOS_API_GET_PV_FORECAST = "https://api.akkudoktor.net/forecast"
AKKUDOKTOR_API_PRICES = "https://api.akkudoktor.net/prices"
TIBBER_API = "https://api.tibber.com/v1-beta/gql"


# getting data
def get_prices(tgt_duration, start_time=None):
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
    if config_manager.config["price"]["source"] == "tibber":
        return get_prices_from_tibber(tgt_duration, start_time)
    if config_manager.config["price"]["source"] == "default":
        return get_prices_from_akkudoktor(tgt_duration, start_time)
    logger.error("[PRICES] Price source currently not supported.")
    return []

def get_prices_from_akkudoktor(tgt_duration, start_time=None):
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
    if config_manager.config["price"]["source"] != "default":
        logger.error(
            "[PRICES] Price source %s currently not supported.",
            config_manager.config["price"]["source"],
        )
        return []
    logger.debug("[PRICES] Fetching prices from akkudoktor ...")
    if start_time is None:
        start_time = datetime.now(time_zone).replace(minute=0, second=0, microsecond=0)
    current_hour = start_time.hour
    request_url = (
        AKKUDOKTOR_API_PRICES
        + "?start="
        + start_time.strftime("%Y-%m-%d")
        + "&end="
        + (start_time + timedelta(days=1)).strftime("%Y-%m-%d")
    )
    logger.debug("[PRICES] Requesting prices from akkudoktor: %s", request_url)
    try:
        response = requests.get(request_url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.error(
            "[PRICES] Request timed out while fetching prices from akkudoktor."
        )
        return []
    except requests.exceptions.RequestException as e:
        logger.error(
            "[PRICES] Request failed while fetching prices from akkudoktor: %s", e
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
        start_time = datetime.now(time_zone).replace(minute=0, second=0, microsecond=0)
    current_hour = start_time.hour
    extended_prices = prices[current_hour : current_hour + tgt_duration]

    if len(extended_prices) < tgt_duration:
        remaining_hours = tgt_duration - len(extended_prices)
        extended_prices.extend(prices[:remaining_hours])
    logger.info("[PRICES] Prices from AKKUDOKTOR fetched successfully.")
    return prices

def get_prices_from_tibber(tgt_duration, start_time=None):
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
    logger.debug("[PRICES] Prices fetching from TIBBER started")
    if config_manager.config["price"]["source"] != "tibber":
        logger.error("[PRICES] Price source currently not supported.")
        return []
    headers = {
        "Authorization": config_manager.config["price"]["token"],
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
                            startsAt
                        }
                        tomorrow {
                            total
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
        logger.error("[PRICES] Request timed out while fetching prices from Tibber.")
        return []
    except requests.exceptions.RequestException as e:
        logger.error("[PRICES] Request failed while fetching prices from Tibber: %s", e)
        return []

    response.raise_for_status()
    data = response.json()
    if "errors" in data and data["errors"] is not None:
        logger.error(
            "[PRICES] Error fetching prices - tibber API response: %s",
            data["errors"][0]["message"],
        )
        return []

    today_prices = json.dumps(
        data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]["today"]
    )
    tomorrow_prices = json.dumps(
        data["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"][
            "tomorrow"
        ]
    )

    today_prices_json = json.loads(today_prices)
    tomorrow_prices_json = json.loads(tomorrow_prices)
    prices = []

    for price in today_prices_json:
        prices.append(round(price["total"] / 1000, 9))
        # logger.debug(
        #     "[Main] day 1 - price for %s -> %s", price["startsAt"], price["total"]
        # )
    if tomorrow_prices_json:
        for price in tomorrow_prices_json:
            prices.append(round(price["total"] / 1000, 9))
            # logger.debug(
            #     "[Main] day 2 - price for %s -> %s", price["startsAt"], price["total"]
            # )
    else:
        prices.extend(prices[:24])  # Repeat today's prices for tomorrow

    if start_time is None:
        start_time = datetime.now(time_zone).replace(minute=0, second=0, microsecond=0)
    current_hour = start_time.hour
    extended_prices = prices[current_hour : current_hour + tgt_duration]

    if len(extended_prices) < tgt_duration:
        remaining_hours = tgt_duration - len(extended_prices)
        extended_prices.extend(prices[:remaining_hours])
    logger.info("[PRICES] Prices from TIBBER fetched successfully.")
    return extended_prices

def create_forecast_request(pv_config_entry):
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

def get_pv_forecast(tgt_value="power", pv_config_entry=None, tgt_duration=24):
    """
    Fetches the PV forecast data from the EOS API and processes it to extract
    power and temperature values for the specified duration starting from the current hour.
    """
    if pv_config_entry is None:
        logger.error("[FORECAST] No PV config entry provided.")
        return []
    forecast_request_payload = create_forecast_request(pv_config_entry)
    # print(forecast_request_payload)
    try:
        response = requests.get(forecast_request_payload, timeout=10)
        response.raise_for_status()
        day_values = response.json()
        day_values = day_values["values"]
    except requests.exceptions.Timeout:
        logger.error("[FORECAST] Request timed out while fetching PV forecast.")
        return []
    except requests.exceptions.RequestException as e:
        logger.error("[FORECAST] Request failed while fetching PV forecast: %s", e)
        return []

    forecast_values = []
    # current_time = datetime.now(time_zone).astimezone()
    current_time = (
        datetime.now(time_zone)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone()
    )
    end_time = current_time + timedelta(hours=tgt_duration)

    for forecast_entry in day_values:
        for forecast in forecast_entry:
            entry_time = datetime.fromisoformat(forecast["datetime"]).astimezone()
            if current_time <= entry_time < end_time:
                forecast_values.append(forecast.get(tgt_value, 0))
    request_type = "PV forecast"
    pv_config_name = "for " + pv_config_entry["name"]
    if tgt_value == "temperature":
        request_type = "Temperature forecast"
        pv_config_name = ""
    logger.info(
        "[FORECAST] %s fetched successfully %s",
        request_type,
        pv_config_name,
    )
    # fix for time changes e.g. western europe then fill or reduce the array to 48 values
    if len(forecast_values) > tgt_duration:
        forecast_values = forecast_values[:tgt_duration]
        logger.debug(
            "[FORECAST] Day of time change %s values reduced to %s for %s",
            request_type,
            tgt_duration,
            pv_config_name,
        )
    elif len(forecast_values) < tgt_duration:
        forecast_values.extend(
            [forecast_values[-1]] * (tgt_duration - len(forecast_values))
        )
        logger.debug(
            "[FORECAST] Day of time change %s values extended to %s for %s",
            request_type,
            tgt_duration,
            pv_config_name,
        )
    return forecast_values

def get_summerized_pv_forecast(tgt_duration=24):
    """
    requesting pv forecast freach config entry and summarize the values
    """
    forecast_values = []
    for config_entry in config_manager.config["pv_forecast"]:
        logger.debug("[FORECAST] fetching forecast for %s", config_entry["name"])
        forecast = get_pv_forecast("power", config_entry, tgt_duration)
        # print("values for " + config_entry+ " -> ")
        # print(forecast)
        if not forecast_values:
            forecast_values = forecast
        else:
            forecast_values = [x + y for x, y in zip(forecast_values, forecast)]
    return forecast_values

# summarize all date
def create_optimize_request(api_version="new"):
    """
    Creates an optimization request payload for energy management systems.

    Args:
        api_version (str): The API version to use for the request. Defaults to "new".

    Returns:
        dict: A dictionary containing the payload for the optimization request.
    """

    def get_ems_data():
        return {
            "pv_prognose_wh": get_summerized_pv_forecast(EOS_TGT_DURATION),
            "strompreis_euro_pro_wh": get_prices(
                EOS_TGT_DURATION,
                datetime.now(time_zone).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
            ),
            "einspeiseverguetung_euro_pro_wh": [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
            "preis_euro_pro_wh_akku": 0,
            "gesamtlast": load_interface.get_load_profile(
                EOS_TGT_DURATION
            ),
        }

    def get_pv_akku_data(api_version="new"):
        if api_version != "new":
            return {
                "kapazitaet_wh": config_manager.config["battery"]["capacity_wh"],
                "lade_effizienz": config_manager.config["battery"]["charge_efficiency"],
                "entlade_effizienz": config_manager.config["battery"][
                    "discharge_efficiency"
                ],
                "max_ladeleistung_w": config_manager.config["battery"][
                    "max_charge_power_w"
                ],
                "start_soc_prozent": battery_interface.battery_request_current_soc(),
                "min_soc_prozent": config_manager.config["battery"][
                    "min_soc_percentage"
                ],
                "max_soc_prozent": config_manager.config["battery"][
                    "max_soc_percentage"
                ],
            }
        return {
            "device_id": "battery1",
            "hours": None,
            "capacity_wh": config_manager.config["battery"]["capacity_wh"],
            "charging_efficiency": config_manager.config["battery"][
                "charge_efficiency"
            ],
            "discharging_efficiency": config_manager.config["battery"][
                "discharge_efficiency"
            ],
            "max_charge_power_w": config_manager.config["battery"][
                "max_charge_power_w"
            ],
            "initial_soc_percentage": battery_interface.battery_request_current_soc(),
            "min_soc_percentage": config_manager.config["battery"][
                "min_soc_percentage"
            ],
            "max_soc_percentage": config_manager.config["battery"][
                "max_soc_percentage"
            ],
        }

    def get_wechselrichter_data(api_version="new"):
        if api_version != "new":
            return {"max_leistung_wh": 8500}
        return {
            "device_id": "inverter1",
            "max_power_wh": 8500,
            "battery_id": "battery1",}

    def get_eauto_data(api_version="new"):
        if api_version != "new":
            return {
                "kapazitaet_wh": 1,
                "lade_effizienz": 0.90,
                "entlade_effizienz": 0.95,
                "max_ladeleistung_w": 1,
                "start_soc_prozent": 50,
                "min_soc_prozent": 5,
                "max_soc_prozent": 100,
            }
        return {
            "device_id": "ev1",
            "capacity_wh": 27000,
            "charging_efficiency": 0.90,
            "discharging_efficiency": 0.95,
            "max_charge_power_w": 7360,
            "initial_soc_percentage": 50,
            "min_soc_percentage": 5,
            "max_soc_percentage": 100,
        }

    def get_dishwasher_data():
        return {
            "device_id": "dishwasher1",
            "consumption_wh": 1,
            "duration_h": 1}

    if api_version != "new":
        payload = {
            "ems": get_ems_data(),
            "pv_akku": get_pv_akku_data(api_version),
            "inverter": get_wechselrichter_data(api_version),
            "eauto": get_eauto_data(api_version),
            "dishwasher": get_dishwasher_data(),
            "temperature_forecast": get_pv_forecast(
                tgt_value="temperature",
                pv_config_entry=config_manager.config["pv_forecast"][0],
                tgt_duration=EOS_TGT_DURATION,
            ),
            "start_solution": None,
        }
    else:
        payload = {
            "ems": get_ems_data(),
            "pv_akku": get_pv_akku_data(),
            "inverter": get_wechselrichter_data(),
            "eauto": get_eauto_data(),
            "dishwasher": get_dishwasher_data(),
            "temperature_forecast": get_pv_forecast(
                tgt_value="temperature",
                pv_config_entry=config_manager.config["pv_forecast"][0],
                tgt_duration=EOS_TGT_DURATION,
            ),
            "start_solution": eos_interface.get_last_start_solution(),
        }
    logger.debug("[Main] optimize request payload - startsolution: %s", payload["start_solution"])
    return payload


def setting_control_data(ac_charge_demand_rel, dc_charge_demand_rel, discharge_allowed):
    """
    Process the optimized response from EOS and update the load interface.

    Args:
        ac_charge_demand_rel (float): The relative AC charge demand.
        dc_charge_demand_rel (float): The relative DC charge demand.
        discharge_allowed (bool): Whether discharge is allowed (True/False).
    """
    base_control.set_current_ac_charge_demand(ac_charge_demand_rel)
    base_control.set_current_dc_charge_demand(dc_charge_demand_rel)
    base_control.set_current_discharge_allowed(bool(discharge_allowed))
    # set the current battery state of charge
    base_control.set_current_battery_soc(battery_interface.get_current_soc())


def change_control_state():
    """
    Adjusts the control state of the inverter based on the current overall state.

    This function checks the current overall state of the inverter and performs
    the corresponding action. The possible states and their actions are:
    - MODE_CHARGE_FROM_GRID (state 0): Sets the inverter to charge from the grid
      with the specified AC charge demand.
    - MODE_AVOID_DISCHARGE (state 1): Sets the inverter to avoid discharge.
    - MODE_DISCHARGE_ALLOWED (state 2): Sets the inverter to allow discharge.
    - Uninitialized state (state < 0): Logs a warning indicating that the inverter
      mode is not initialized yet.

    Returns:
        bool: True if the state was changed recently and an action was performed,
              False otherwise.
    """
    inverter_en = False
    if config_manager.config["inverter"]["type"] == "fronius_gen24":
        inverter_en = True

    # getting the current charging state from evcc
    base_control.set_current_evcc_charging_state(evcc_interface.get_charging_state())

    # Check if the overall state of the inverter was changed recently
    if base_control.was_overall_state_changed_recently(180):
        logger.debug("[Main] Overall state changed recently")
        # MODE_CHARGE_FROM_GRID
        if base_control.get_current_overall_state() == 0:
            if inverter_en:
                inverter_interface.set_mode_force_charge(
                    base_control.get_current_ac_charge_demand()
                )
            logger.info(
                "[Main] Inverter mode set to charge from grid with %s W (_____|||||_____)",
                base_control.get_current_ac_charge_demand(),
            )
        # MODE_AVOID_DISCHARGE
        elif base_control.get_current_overall_state() == 1:
            if inverter_en:
                inverter_interface.set_mode_avoid_discharge()
            logger.info("[Main] Inverter mode set to AVOID discharge (_____-----_____)")
        # MODE_DISCHARGE_ALLOWED
        elif base_control.get_current_overall_state() == 2:
            if inverter_en:
                inverter_interface.set_mode_allow_discharge()
            logger.info("[Main] Inverter mode set to ALLOW discharge (_____+++++_____)")
        elif base_control.get_current_overall_state() < 0:
            logger.warning("[Main] Inverter mode not initialized yet")
        return True
    # Log the current state if no recent changes were made
    state_mapping = {
        0: "charge from grid",
        1: "avoid discharge",
        2: "allow discharge",
    }
    current_state = base_control.get_current_overall_state()
    logger.info(
        "[Main] Overall state not changed recently"+
        " - remaining in current state: %s  (_____OOOOO_____)",
        state_mapping.get(current_state, "unknown state"),
    )
    return False

# web server
app = Flask(__name__)


@app.route("/", methods=["GET"])
def main_page():
    """
    Renders the main page of the web application.

    This function reads the content of the 'index.html' file located in the 'web' directory
    and returns it as a rendered template string.
    """
    with open(base_path + "/web/index.html", "r", encoding="utf-8") as html_file:
        return render_template_string(html_file.read())


@app.route("/json/optimize_request.json", methods=["GET"])
def get_optimize_request():
    """
    Returns the content of the 'optimize_request.json' file as a JSON response.
    """
    try:
        with open(
            base_path + "/json/optimize_request.json", "r", encoding="utf-8"
        ) as json_file:
            return Response(json_file.read(), content_type="application/json")
    except FileNotFoundError as e:
        logger.error(
            "[Main] File not found error while reading optimize_request.json: %s", e
        )
        return json.dumps({"error": "optimize_request.json file not found"})
    except json.JSONDecodeError as e:
        logger.error(
            "[Main] JSON decode error while reading optimize_request.json: %s", e
        )
        return json.dumps({"error": "Invalid JSON format in optimize_request.json"})
    except OSError as e:
        logger.error("[Main] OS error while reading optimize_request.json: %s", e)
        return json.dumps({"error": str(e)})


@app.route("/json/optimize_response.json", methods=["GET"])
def get_optimize_response():
    """
    Returns the content of the 'optimize_response.json' file as a JSON response.
    """
    try:
        with open(
            base_path + "/json/optimize_response.json", "r", encoding="utf-8"
        ) as json_file:
            return json_file.read()
    except FileNotFoundError:
        default_response = {
            "ac_charge": [],
            "dc_charge": [],
            "discharge_allowed": [],
            "eautocharge_hours_float": None,
            "result": {},
            "eauto_obj": {},
            "start_solution": [],
            "washingstart": 0,
            "timestamp": datetime.now(time_zone).isoformat(),
        }
        return Response(json.dumps(default_response), content_type="application/json")


@app.route("/json/current_controls.json", methods=["GET"])
def serve_current_demands():
    """
    Returns the current demands for AC and DC charging as a JSON response.
    """
    current_ac_charge_demand = base_control.get_current_ac_charge_demand()
    current_dc_charge_demand = base_control.get_current_dc_charge_demand()
    current_discharge_allowed = base_control.get_current_discharge_allowed()
    response_data = {
        "current_states": {
            "current_ac_charge_demand": current_ac_charge_demand,
            "current_dc_charge_demand": current_dc_charge_demand,
            "current_discharge_allowed": current_discharge_allowed,
            "inverter_mode": base_control.get_current_overall_state(False),
            "evcc_charging_state": base_control.get_current_evcc_charging_state(),
        },
        "battery_soc": base_control.get_current_battery_soc(),
        "timestamp": datetime.now(time_zone).isoformat(),
    }
    return Response(json.dumps(response_data), content_type="application/json")


if __name__ == "__main__":
    # initial config
    # set_config_value("latitude", 48.812)
    # set_config_value("longitude", 8.907)

    # set_config_value("measurement_load0_name", "Household")
    # set_config_value("loadakkudoktor_year_energy", 4600)

    # # set_config_value("pvforecast_provider", "PVForecastAkkudoktor")
    # set_config_value("pvforecast_provider", "PVForecast")
    # set_config_value("pvforecast0_surface_tilt", 31)
    # set_config_value("pvforecast0_surface_azimuth", 13)
    # set_config_value("pvforecast0_peakpower", 860.0)
    # set_config_value("pvforecast0_inverter_paco", 800)
    # # set_config_value("pvforecast0_userhorizon", [0,0])

    # # persist and update config
    # eos_save_config_to_config_file()

    # json_optimize_input = create_optimize_request()

    # with open(
    #     base_path + "/json/optimize_request.json", "w", encoding="utf-8"
    # ) as file:
    #     json.dump(json_optimize_input, file, indent=4)

    # optimized_response = eos_interface.eos_set_optimize_request(
    #     json_optimize_input, config_manager.config["eos"]["timeout"]
    # )
    # optimized_response["timestamp"] = datetime.now(time_zone).isoformat()

    # with open(
    #     base_path + "/json/optimize_response.json", "w", encoding="utf-8"
    # ) as file:
    #     json.dump(optimized_response, file, indent=4)
        
    # sys.exit()

    http_server = WSGIServer(
        ("0.0.0.0", config_manager.config["eos_connect_web_port"]),
        app,
        log=None,
        error_log=logger,
    )

    def run_optimization_loop():
        """
        Continuously runs the optimization loop until interrupted.
        This function performs the following steps in an infinite loop:
        1. Logs the start of a new run.
        2. Creates an optimization request and saves it to a JSON file.
        3. Sends the optimization request and receives the optimized response.
        4. Adds a timestamp to the optimized response and saves it to a JSON file.
        5. Calculates the time to the next evaluation based on a predefined interval.
        6. Logs the next evaluation time and sleeps until that time.
        The loop can be interrupted with a KeyboardInterrupt, which will log an exit message and
        terminate the program.
        Raises:
            KeyboardInterrupt: If the loop is interrupted by the user.
        """

        scheduler = sched.scheduler(time.time, time.sleep)

        def run_optimization_event(sc):
            logger.info("[Main] start new run")
            # create optimize request
            json_optimize_input = create_optimize_request()

            with open(
                base_path + "/json/optimize_request.json", "w", encoding="utf-8"
            ) as file:
                json.dump(json_optimize_input, file, indent=4)

            optimized_response = eos_interface.eos_set_optimize_request(
                json_optimize_input, config_manager.config["eos"]["timeout"]
            )
            optimized_response["timestamp"] = datetime.now(time_zone).isoformat()

            with open(
                base_path + "/json/optimize_response.json", "w", encoding="utf-8"
            ) as file:
                json.dump(optimized_response, file, indent=4)
            # +++++++++
            ac_charge_demand, dc_charge_demand, discharge_allowed, error = (
                eos_interface.examine_repsonse_to_control_data(optimized_response)
            )
            if error is not True:
                setting_control_data(ac_charge_demand, dc_charge_demand, discharge_allowed)
                change_control_state()
            # +++++++++

            loop_now = datetime.now(time_zone).astimezone()
            # reset base to full minutes on the clock
            next_eval = loop_now - timedelta(
                minutes=loop_now.minute % config_manager.config["refresh_time"],
                seconds=loop_now.second,
                microseconds=loop_now.microsecond,
            )
            # add time increments to trigger next evaluation
            next_eval += timedelta(
                minutes=config_manager.config["refresh_time"], seconds=0, microseconds=0
            )
            sleeptime = (next_eval - loop_now).total_seconds()
            minutes, seconds = divmod(sleeptime, 60)
            logger.info(
                "[Main] Next optimization at %s. Sleeping for %d min %.0f seconds\n",
                next_eval.astimezone(time_zone).strftime("%H:%M:%S"),
                minutes,
                seconds,
            )
            scheduler.enter(sleeptime, 1, run_optimization_event, (sc,))

        scheduler.enter(0, 1, run_optimization_event, (scheduler,))
        scheduler.run()

    optimization_thread = Thread(target=run_optimization_loop)
    optimization_thread.start()

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logger.info("[Main] Shutting down server")
        http_server.stop()
        # restore the old config
        if (
            config_manager.config["inverter"]["type"] == "fronius_gen24"
            and inverter_interface is not None
        ):
            inverter_interface.shutdown()
        evcc_interface.shutdown()
        optimization_thread.join(timeout=10)
        if optimization_thread.is_alive():
            logger.warning(
                "[Main] Optimization thread did not finish in time, terminating."
            )
            # Terminate the thread (not recommended, but shown here for completeness)
            # Note: Python does not provide a direct way to kill a thread. This is a workaround.
            import ctypes

            if optimization_thread.ident is not None:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(optimization_thread.ident),
                    ctypes.py_object(SystemExit),
                )
        logger.info("[Main] Server stopped")
        sys.exit(0)
