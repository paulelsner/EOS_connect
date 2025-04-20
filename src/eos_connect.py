"""
This module fetches energy data from OpenHAB, processes it, and creates a load profile.
"""

import os
import sys
from datetime import datetime, timedelta
import time
import logging
import json
import threading
import pytz
import requests
from flask import Flask, Response, render_template_string
from gevent.pywsgi import WSGIServer
from version import __version__
from config import ConfigManager
from interfaces.base_control import BaseControl
from interfaces.load_interface import LoadInterface
from interfaces.battery_interface import BatteryInterface
from interfaces.inverter_fronius import FroniusWR
from interfaces.evcc_interface import EvccInterface
from interfaces.eos_interface import EosInterface
from interfaces.price_interface import PriceInterface

EOS_TGT_DURATION = 48
EOS_API_GET_PV_FORECAST = "https://api.akkudoktor.net/forecast"


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
logger.info("[Main] Starting eos_connect - version: %s", __version__)
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
    # update the base control with the new charging state
    base_control.set_current_evcc_charging_state(evcc_interface.get_charging_state())
    base_control.set_current_evcc_charging_mode(evcc_interface.get_charging_mode())
    logger.info("[MAIN] EVCC Event - Charging state changed to: %s", new_state)
    change_control_state()


evcc_interface = EvccInterface(
    url=config_manager.config["evcc"]["url"],
    update_interval=10,
    on_charging_state_change=charging_state_callback,
)

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
    config_manager.config.get("battery", {}).get("max_charge_power_w", ""),
)

price_interface = PriceInterface(
    config_manager.config["price"]["source"],
    config_manager.config["price"]["token"],
    config_manager.config["price"]["feed_in_price"],
    config_manager.config["price"]["negative_price_switch"],
)


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


def get_summarized_pv_forecast(tgt_duration=24):
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
def create_optimize_request():
    """
    Creates an optimization request payload for energy management systems.

    Args:
        api_version (str): The API version to use for the request. Defaults to "new".

    Returns:
        dict: A dictionary containing the payload for the optimization request.
    """

    def get_ems_data():
        return {
            "pv_prognose_wh": get_summarized_pv_forecast(EOS_TGT_DURATION),
            "strompreis_euro_pro_wh": price_interface.get_current_prices(),
            "einspeiseverguetung_euro_pro_wh": price_interface.get_current_feedin_prices(),
            "preis_euro_pro_wh_akku": 0,
            "gesamtlast": load_interface.get_load_profile(EOS_TGT_DURATION),
        }

    def get_pv_akku_data():
        akku_object = {
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
            "initial_soc_percentage": round(
                battery_interface.battery_request_current_soc()
            ),
            "min_soc_percentage": config_manager.config["battery"][
                "min_soc_percentage"
            ],
            "max_soc_percentage": config_manager.config["battery"][
                "max_soc_percentage"
            ],
        }
        if eos_interface.get_eos_version() == ">=2025-04-09":
            akku_object = {"device_id": "battery1", **akku_object}
        return akku_object

    def get_wechselrichter_data():
        wechselrichter_object = {
            "max_power_wh": config_manager.config["inverter"]["max_pv_charge_rate"],
        }
        if eos_interface.get_eos_version() == ">=2025-04-09":
            wechselrichter_object = {
                "device_id": "inverter1",
                **wechselrichter_object,
            }  # at top
            wechselrichter_object["battery_id"] = "battery1"  # at the bottom
        return wechselrichter_object

    def get_eauto_data():
        eauto_object = {
            "capacity_wh": 27000,
            "charging_efficiency": 0.90,
            "discharging_efficiency": 0.95,
            "max_charge_power_w": 7360,
            "initial_soc_percentage": 50,
            "min_soc_percentage": 5,
            "max_soc_percentage": 100,
        }
        if eos_interface.get_eos_version() == ">=2025-04-09":
            eauto_object = {"device_id": "ev1", **eauto_object}
        return eauto_object

    def get_dishwasher_data():
        dishwaser_object = {"consumption_wh": 1, "duration_h": 1}
        if eos_interface.get_eos_version() == ">=2025-04-09":
            dishwaser_object = {"device_id": "dishwasher1", **dishwaser_object}
        return dishwaser_object

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
    logger.debug(
        "[Main] optimize request payload - startsolution: %s", payload["start_solution"]
    )
    return payload


class OptimizationScheduler:
    """
    A scheduler class that manages the periodic execution of an optimization process
    in a background thread. The class is responsible for starting, stopping, and
    managing the lifecycle of the optimization service.
    Attributes:
        update_interval (int): The interval in seconds between optimization runs.
        _update_thread (threading.Thread): The background thread running the optimization loop.
        _stop_event (threading.Event): An event used to signal the thread to stop.
    Methods:
        start_update_service():
        shutdown():
        _update_state_loop():
        run_optimization():
    """

    def __init__(self, update_interval):
        self.update_interval = update_interval
        self.last_request_response = {
            "request": json.dumps(
                {
                    "status": "Awaiting first optimization run",
                },
                indent=4,
            ),
            "response": json.dumps(
                {
                    "status": "starting up",
                    "message": (
                        "The first request has been sent to EOS and is now waiting for "
                        "the completion of the first optimization run."
                    ),
                },
                indent=4,
            ),
        }
        self.current_state = {
            "request_state": None,
            "last_request_timestamp": None,
            "last_response_timestamp": None,
            "next_run": None,
        }
        self._update_thread = None
        self._stop_event = threading.Event()
        self.start_update_service()

    def get_last_request_response(self):
        """
        Returns the last request response.
        """
        return self.last_request_response

    def get_current_state(self):
        """
        Returns the current state of the optimization scheduler.
        """
        return self.current_state

    def __set_state_request(self):
        """
        Sets the current state of the optimization scheduler.
        """
        self.current_state["request_state"] = "request send"
        self.current_state["last_request_timestamp"] = datetime.now(
            time_zone
        ).isoformat()

    def __set_state_response(self):
        """
        Sets the current state of the optimization scheduler.
        """
        self.current_state["request_state"] = "response received"
        self.current_state["last_response_timestamp"] = datetime.now(
            time_zone
        ).isoformat()

    def __set_state_next_run(self, next_run_time):
        """
        Sets the current state of the optimization scheduler.
        """
        self.current_state["next_run"] = next_run_time

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
            logger.info("[OPTIMIZATION] Update service stopped.")

    def _update_state_loop(self):
        """
        The loop that runs in the background thread to update the state.
        """
        while not self._stop_event.is_set():
            try:
                self.run_optimization()
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

    def run_optimization(self):
        """
        Executes the optimization process by creating an optimization request,
        sending it to the EOS interface, processing the response, and scheduling
        the next optimization run.
        The method performs the following steps:
        1. Logs the start of a new optimization run.
        2. Creates an optimization request in JSON format and saves it to a file.
        3. Sends the optimization request to the EOS interface and retrieves the response.
        4. Adds a timestamp to the response and saves it to a file.
        5. Extracts control data from the response and, if no error is detected,
           applies the control settings and updates the control state.
        6. Calculates the time for the next optimization run and logs the sleep duration.
        Raises:
            Any exceptions raised during file operations, JSON serialization,
            or EOS interface communication will propagate to the caller.
        Notes:
            - The method assumes the presence of global variables or objects such as
              `logger`, `base_path`, `eos_interface`, `config_manager`, and `time_zone`.
            - The `config_manager.config` dictionary is expected to contain the
              necessary configuration values for "eos.timeout" and "refresh_time".
        """
        logger.info("[Main] start new run")
        # update prices
        price_interface.update_prices(
            EOS_TGT_DURATION,
            datetime.now(time_zone).replace(hour=0, minute=0, second=0, microsecond=0),
        )
        # create optimize request
        json_optimize_input = create_optimize_request()
        self.__set_state_request()

        with open(
            base_path + "/json/optimize_request.json", "w", encoding="utf-8"
        ) as file:
            json.dump(json_optimize_input, file, indent=4)

        optimized_response = eos_interface.eos_set_optimize_request(
            json_optimize_input, config_manager.config["eos"]["timeout"]
        )

        json_optimize_input["timestamp"] = datetime.now(time_zone).isoformat()
        self.last_request_response["request"] = json.dumps(
            json_optimize_input, indent=4
        )
        optimized_response["timestamp"] = datetime.now(time_zone).isoformat()
        self.last_request_response["response"] = json.dumps(
            optimized_response, indent=4
        )
        self.__set_state_response()

        with open(
            base_path + "/json/optimize_response.json", "w", encoding="utf-8"
        ) as file:
            json.dump(optimized_response, file, indent=4)
        # +++++++++
        ac_charge_demand, dc_charge_demand, discharge_allowed, error = (
            eos_interface.examine_response_to_control_data(optimized_response)
        )
        if error is not True:
            setting_control_data(ac_charge_demand, dc_charge_demand, discharge_allowed)
            change_control_state()
        # +++++++++

        loop_now = datetime.now(time_zone)
        # Reset base to full minutes on the clock
        next_eval = loop_now.replace(microsecond=0)
        # Add the update interval to calculate the next evaluation time
        next_eval += timedelta(seconds=self.update_interval)
        sleeptime = (next_eval - loop_now).total_seconds()
        minutes, seconds = divmod(sleeptime, 60)
        self.__set_state_next_run(next_eval.astimezone(time_zone).isoformat())
        logger.info(
            "[Main] Next optimization at %s. Sleeping for %d min %.0f seconds\n",
            next_eval.strftime("%H:%M:%S"),
            minutes,
            seconds,
        )


optimization_scheduler = OptimizationScheduler(
    config_manager.config["refresh_time"] * 60  # convert to seconds
)


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
    # getting the current charging state from evcc
    base_control.set_current_evcc_charging_state(evcc_interface.get_charging_state())
    base_control.set_current_evcc_charging_mode(evcc_interface.get_charging_mode())


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

    current_overall_state = base_control.get_current_overall_state_number()
    current_overall_state_text = base_control.get_current_overall_state()

    # Check if the overall state of the inverter was changed recently
    if base_control.was_overall_state_changed_recently(180):
        logger.debug("[Main] Overall state changed recently")
        # MODE_CHARGE_FROM_GRID
        if current_overall_state == 0:
            # get the current ac charge demand and set it to the inverter according
            # to the max dynamic charge power of the battery based on SOC
            tgt_charge_power = min(
                base_control.get_current_ac_charge_demand(),
                round(battery_interface.get_max_charge_power_dyn()),
            )
            if inverter_en:
                inverter_interface.set_mode_force_charge(tgt_charge_power)
            logger.info(
                "[Main] Inverter mode set to %s with %s W (_____|||||_____)",
                current_overall_state_text,
                tgt_charge_power,
            )
        # MODE_AVOID_DISCHARGE
        elif current_overall_state == 1:
            if inverter_en:
                inverter_interface.set_mode_avoid_discharge()
            logger.info(
                "[Main] Inverter mode set to %s (_____-----_____)",
                current_overall_state_text,
            )
        # MODE_DISCHARGE_ALLOWED
        elif current_overall_state == 2:
            if inverter_en:
                inverter_interface.set_mode_allow_discharge()
            logger.info(
                "[Main] Inverter mode set to %s (_____+++++_____)",
                current_overall_state_text,
            )
        # MODE_AVOID_DISCHARGE_EVCC_FAST
        elif current_overall_state == 3:
            if inverter_en:
                inverter_interface.set_mode_avoid_discharge()
            logger.info(
                "[Main] Inverter mode set to %s (_____+---+_____)",
                current_overall_state_text,
            )
        # MODE_DISCHARGE_ALLOWED_EVCC_PV
        elif current_overall_state == 4:
            if inverter_en:
                inverter_interface.set_mode_allow_discharge()
            logger.info(
                "[Main] Inverter mode set to %s (_____-+++-_____)",
                current_overall_state_text,
            )
        # MODE_DISCHARGE_ALLOWED_EVCC_MIN_PV
        elif current_overall_state == 5:
            if inverter_en:
                inverter_interface.set_mode_allow_discharge()
            logger.info(
                "[Main] Inverter mode set to %s (_____+-+-+_____)",
                current_overall_state_text,
            )
        elif current_overall_state < 0:
            logger.warning("[Main] Inverter mode not initialized yet")
        return True
    # Log the current state if no recent changes were made

    logger.info(
        "[Main] Overall state not changed recently"
        + " - remaining in current state: %s  (_____OOOOO_____)",
        current_overall_state_text,
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


@app.route("/style.css", methods=["GET"])
def style_css():
    """
    Serves the CSS file for styling the web application.

    This function reads the content of the 'style.css' file located in the 'web' directory
    and returns it as a response with the appropriate content type.
    """
    with open(base_path + "/web/style.css", "r", encoding="utf-8") as css_file:
        return Response(css_file.read(), content_type="text/css")


@app.route("/json/optimize_request.json", methods=["GET"])
def get_optimize_request():
    """
    Retrieves the last optimization request and returns it as a JSON response.
    """
    return Response(
        optimization_scheduler.get_last_request_response()["request"],
        content_type="application/json",
    )


@app.route("/json/optimize_response.json", methods=["GET"])
def get_optimize_response():
    """
    Retrieves the last optimization response and returns it as a JSON response.
    """
    return Response(
        optimization_scheduler.get_last_request_response()["response"],
        content_type="application/json",
    )


@app.route("/json/current_controls.json", methods=["GET"])
def get_controls():
    """
    Returns the current demands for AC and DC charging as a JSON response.
    """
    current_ac_charge_demand = base_control.get_current_ac_charge_demand()
    current_dc_charge_demand = base_control.get_current_dc_charge_demand()
    current_discharge_allowed = base_control.get_current_discharge_allowed()
    current_battery_soc = battery_interface.get_current_soc()
    base_control.set_current_battery_soc(current_battery_soc)
    current_inverter_mode = base_control.get_current_overall_state()
    current_inverter_mode_num = base_control.get_current_overall_state_number()

    response_data = {
        "current_states": {
            "current_ac_charge_demand": current_ac_charge_demand,
            "current_dc_charge_demand": current_dc_charge_demand,
            "current_discharge_allowed": current_discharge_allowed,
            "inverter_mode": current_inverter_mode,
            "inverter_mode_num": current_inverter_mode_num,
        },
        "evcc": {
            "charging_state": base_control.get_current_evcc_charging_state(),
            "charging_mode": base_control.get_current_evcc_charging_mode(),
        },
        "battery": {
            "soc": current_battery_soc,
            "max_charge_power_dyn": battery_interface.get_max_charge_power_dyn(),
        },
        "state": optimization_scheduler.get_current_state(),
        "eos_connect_version": __version__,
        "timestamp": datetime.now(time_zone).isoformat(),
        "api_version": "0.0.1",
    }
    return Response(
        json.dumps(response_data, indent=4), content_type="application/json"
    )


if __name__ == "__main__":
    http_server = WSGIServer(
        ("0.0.0.0", config_manager.config["eos_connect_web_port"]),
        app,
        log=None,
        error_log=logger,
    )

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logger.info("[Main] Shutting down EOS connect")
        optimization_scheduler.shutdown()
        http_server.stop()
        logger.info("[Main] HTTP server stopped")

        # restore the old config
        if (
            config_manager.config["inverter"]["type"] == "fronius_gen24"
            and inverter_interface is not None
        ):
            inverter_interface.shutdown()
        evcc_interface.shutdown()
        battery_interface.shutdown()
        logger.info("[Main] Server stopped")
    finally:
        logger.info("[Main] Cleanup complete. Exiting.")
        sys.exit(0)
