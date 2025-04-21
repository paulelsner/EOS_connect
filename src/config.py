"""
This module provides the ConfigManager class for managing configuration settings
of the application. The configuration settings are stored in a 'config.yaml' file.
"""

import os
import sys
import logging
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

logger = logging.getLogger("__main__")
logger.info("[Config] loading module ")


class ConfigManager:
    """
    Manages the configuration settings for the application.

    This class handles loading, updating, and saving configuration settings from a 'config.yaml'
    file. If the configuration file does not exist, it creates one with default values and
    prompts the user to restart the server.
    """

    def __init__(self, given_dir):
        self.current_dir = given_dir
        self.config_file = os.path.join(self.current_dir, "config.yaml")
        self.yaml = YAML()
        self.yaml.default_flow_style = False
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.preserve_quotes = True
        self.default_config = self.create_default_config()
        self.config = self.default_config.copy()
        self.load_config()

    def create_default_config(self):
        """
        Creates the default configuration with comments.
        """
        config = CommentedMap(
            {
                "load": CommentedMap(
                    {
                        "source": "default",  # data source for load power
                        "url": "http://homeassistant:8123",  # URL for openhab or homeassistant
                        "load_sensor": "Load_Power",  # item / entity for load power data
                        "car_charge_load_sensor": "Wallbox_Power",  # item / entity wallbox power
                        "access_token": "abc123",  # access token for homeassistant
                    }
                ),
                "eos": CommentedMap(
                    {
                        "server": "192.168.1.94",  # Default EOS server address
                        "port": 8503,  # Default port for EOS server
                        "timeout": 180,  # Default timeout for EOS optimize request
                    }
                ),
                "price": CommentedMap(
                    {
                        "source": "default",
                        "token": "tibberBearerToken",  # token for electricity price
                        "feed_in_price": 0.0,  # feed in price for the grid
                        "negative_price_switch": False,  # switch for negative price
                    }
                ),
                "battery": CommentedMap(
                    {
                        "source": "default",  # data source for battery soc
                        "url": "http://homeassistant:8123",  # URL for openhab or homeassistant
                        "soc_sensor": "battery_SOC",  # item / entity for battery SOC data
                        "access_token": "abc123",  # access token for homeassistant
                        "capacity_wh": 11059,
                        "charge_efficiency": 0.88,
                        "discharge_efficiency": 0.88,
                        "max_charge_power_w": 5000,
                        "min_soc_percentage": 5,
                        "max_soc_percentage": 100,
                    }
                ),
                "pv_forecast": [
                    CommentedMap(
                        {
                            "name": "myPvInstallation1",  # Placeholder for user-defined
                            # configuration name
                            "lat": 47.5,  # Latitude for PV forecast @ Akkudoktor API
                            "lon": 8.5,  # Longitude for PV forecast @ Akkudoktor API
                            "azimuth": 90.0,  # Azimuth for PV forecast @ Akkudoktor API
                            "tilt": 30.0,  # Tilt for PV forecast @ Akkudoktor API
                            "power": 4600,  # Power of PV system in Wp
                            "powerInverter": 5000,  # Inverter Power
                            "inverterEfficiency": 0.9,  # Inverter Efficiency for
                            # PV forecast @ Akkudoktor API
                            "horizont": "10,20,10,15",  # Horizont to calculate shading
                        }
                    )
                ],
                "inverter": CommentedMap(
                    {
                        "type": "default",
                        "address": "192.168.1.12",
                        "user": "customer",
                        "password": "abc123",
                        "max_grid_charge_rate": 5000,
                        "max_pv_charge_rate": 5000,
                        "max_bat_discharge_rate": 5000,
                    }
                ),
                "evcc": CommentedMap(
                    {
                        "url": "http://yourEVCCserver:7070",  # URL for EVCC server
                    }
                ),
                "refresh_time": 3,  # Default refresh time in minutes
                "time_zone": "Europe/Berlin",  # Add default time zone
                "eos_connect_web_port": 8081,  # Default port for EOS connect server
                "log_level": "info",  # Default log level
            }
        )
        # load configuration
        config.yaml_set_comment_before_after_key("load", before="Load configuration")
        config["load"].yaml_add_eol_comment(
            "Data source for load power - openhab, homeassistant,"+
            " default (using a static load profile)",
            "source",
        )
        config["load"].yaml_add_eol_comment(
            "URL for openhab or homeassistant"+
            " (e.g. http://openhab:7070 or http://homeassistant:8123)",
            "url",
        )
        config["load"].yaml_add_eol_comment(
            "item / entity for load power data in watts", "load_sensor"
        )
        config["load"].yaml_add_eol_comment(
            "item / entity for wallbox power data in watts or kilowatts",
            "car_charge_load_sensor",
        )
        config["load"].yaml_add_eol_comment(
            "access token for homeassistant (optional)", "access_token"
        )
        # eos configuration
        config.yaml_set_comment_before_after_key(
            "eos", before="EOS server configuration"
        )
        config["eos"].yaml_add_eol_comment("EOS server address", "server")
        config["eos"].yaml_add_eol_comment(
            "port for EOS server - default: 8503", "port"
        )
        config["eos"].yaml_add_eol_comment(
            "timeout for EOS optimize request in seconds - default: 180", "timeout"
        )
        # price configuration
        config.yaml_set_comment_before_after_key(
            "price", before="Electricity price configuration"
        )
        config["price"].yaml_add_eol_comment(
            "data source for electricity price tibber, default (default uses akkudoktor)",
            "source",
        )
        config["price"].yaml_add_eol_comment("Token for electricity price", "token")
        config["price"].yaml_add_eol_comment(
            "feed in price for the grid in €/kWh", "feed_in_price"
        )
        config["price"].yaml_add_eol_comment(
            "switch for no payment if negative stock price is given",
            "negative_price_switch",
        )
        # battery configuration
        config.yaml_set_comment_before_after_key(
            "battery", before="battery configuration"
        )
        config["battery"].yaml_add_eol_comment(
            "Data source for battery soc - openhab, homeassistant, default", "source"
        )
        config["battery"].yaml_add_eol_comment(
            "URL for openhab or homeassistant"+
            " (e.g. http://openhab:7070 or http://homeassistant:8123)",
            "url",
        )
        config["battery"].yaml_add_eol_comment(
            "item / entity for battery SOC data in [0..1]", "soc_sensor"
        )
        config["battery"].yaml_add_eol_comment(
            "access token for homeassistant (optional)", "access_token"
        )
        config["battery"].yaml_add_eol_comment("battery capacity in Wh", "capacity_wh")
        config["battery"].yaml_add_eol_comment(
            "efficiency for charging the battery in [0..1]", "charge_efficiency"
        )
        config["battery"].yaml_add_eol_comment(
            "efficiency for discharging the battery in [0..1]", "discharge_efficiency"
        )
        config["battery"].yaml_add_eol_comment(
            "max charging power in W", "max_charge_power_w"
        )
        config["battery"].yaml_add_eol_comment(
            "URL for battery soc in %", "min_soc_percentage"
        )
        config["battery"].yaml_add_eol_comment(
            "URL for battery soc in %", "max_soc_percentage"
        )
        # pv forecast configuration
        config.yaml_set_comment_before_after_key(
            "pv_forecast",
            before="List of PV forecast configurations."
            + " Add multiple entries as needed.\nSee Akkudoktor API "
            + "(https://api.akkudoktor.net/#/pv%20generation%20calculation/getForecast) "
            + "for more details.",
        )
        for index, pv_config in enumerate(config["pv_forecast"]):
            config["pv_forecast"][index].yaml_add_eol_comment(
                "User-defined identifier for the PV installation,"
                + " have to be unique if you use more installations",
                "name",
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Latitude for PV forecast @ Akkudoktor API", "lat"
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Longitude for PV forecast @ Akkudoktor API", "lon"
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Azimuth for PV forecast @ Akkudoktor API", "azimuth"
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Tilt for PV forecast @ Akkudoktor API", "tilt"
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Power for PV forecast @ Akkudoktor API", "power"
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Power Inverter for PV forecast @ Akkudoktor API", "powerInverter"
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Inverter Efficiency for PV forecast @ Akkudoktor API",
                "inverterEfficiency",
            )
            config["pv_forecast"][index].yaml_add_eol_comment(
                "Horizont to calculate shading up to 360 values"+
                " to describe shading situation for your PV.",
                "horizont",
            )
        # inverter configuration
        config.yaml_set_comment_before_after_key(
            "inverter", before="Inverter configuration"
        )
        config["inverter"].yaml_add_eol_comment(
            "Type of inverter - fronius_gen24, default (default will disable inverter control -"+
            " only displaying the target state) - preset: default",
            "type",
        )
        config["inverter"].yaml_add_eol_comment("Address of the inverter", "address")
        config["inverter"].yaml_add_eol_comment("Username for the inverter", "user")
        config["inverter"].yaml_add_eol_comment("Password for the inverter", "password")
        config["inverter"].yaml_add_eol_comment(
            "Max grid charge rate in W - default: 5000", "max_grid_charge_rate"
        )
        config["inverter"].yaml_add_eol_comment(
            "Max PV charge rate in W - default: 5000", "max_pv_charge_rate"
        )
        config["inverter"].yaml_add_eol_comment(
            "Max battery discharge rate in W (currently not used) - default: 5000",
            "max_bat_discharge_rate",
        )
        # evcc configuration
        config.yaml_set_comment_before_after_key("evcc", before="EVCC configuration")
        config["evcc"].yaml_add_eol_comment(
            "URL for EVCC server - default: http://yourEVCCserver:7070",
            "url",
        )
        # refresh time configuration
        config.yaml_add_eol_comment(
            "Default refresh time of EOS connect in minutes - default: 3",
            "refresh_time",
        )
        # time zone configuration
        config.yaml_add_eol_comment(
            "Default time zone - default: Europe/Berlin", "time_zone"
        )
        # eos connect web port configuration
        config.yaml_add_eol_comment(
            "Default port for EOS connect server - default: 8081",
            "eos_connect_web_port",
        )
        # loglevel configuration
        config.yaml_add_eol_comment(
            "Log level for the application : debug, info, warning, error - default: info",
            "log_level",
        )
        return config

    def load_config(self):
        """
        Reads the configuration from 'config.yaml' file located in the current directory.
        If the file exists, it loads the configuration values.
        If the file does not exist, it creates a new 'config.yaml' file with default values and
        prompts the user to restart the server after configuring the settings.
        """
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config.update(self.yaml.load(f))
            self.check_eos_timeout_and_refreshtime()
        else:
            self.write_config()
            print("Config file not found. Created a new one with default values.")
            print(
                "Please restart the server after configuring the settings in config.yaml"
            )
            sys.exit(0)

    def write_config(self):
        """
        Writes the configuration to 'config.yaml' file located in the current directory.
        """
        logger.info("[Config] writing config file")
        with open(self.config_file, "w", encoding="utf-8") as config_file_handle:
            self.yaml.dump(self.config, config_file_handle)

    def check_eos_timeout_and_refreshtime(self):
        """
        Check if the eos timeout is smaller than the refresh time
        """
        eos_timeout_seconds = self.config["eos"]["timeout"]
        refresh_time_seconds = self.config["refresh_time"] * 60

        if eos_timeout_seconds > refresh_time_seconds:
            logger.error(
                (
                    "[Config] EOS timeout (%s s) is greater than the refresh time (%s s)."
                    " Please adjust the settings."
                ),
                eos_timeout_seconds,
                refresh_time_seconds,
            )
            sys.exit(0)
