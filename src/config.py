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
                        "url": "http://<ip>:8080", # URL for openhab or homeassistant
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
                    }
                ),
                "battery": CommentedMap(
                    {
                        "source": "default",  # data source for battery soc
                        "url": "http://<ip>:8080", # URL for openhab or homeassistant
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
                            "name": "<user defined config>",  # Placeholder for user-defined 
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
                        "type": "fronius_gen24",
                        "address": "192.168.1.12",
                        "user": "customer",
                        "password": "abc123",
                        "max_grid_charge_rate": 5000,
                        "max_pv_charge_rate": 5000,
                        "max_bat_discharge_rate": 5000
                    }
                ),
                "evcc": CommentedMap(
                    {
                        "url": "http://<ip>:7070",  # URL for EVCC server
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
        config["load"].yaml_set_comment_before_after_key(
            "source", before="Data source for load power - openhab, homeassistant, default"
        )
        config["load"].yaml_set_comment_before_after_key(
            "url", before="URL for openhab or homeassistant"
        )
        config["load"].yaml_set_comment_before_after_key(
            "load_sensor", before="item / entity for load power data"
        )
        config["load"].yaml_set_comment_before_after_key(
            "car_charge_load_sensor", before="item / entity for wallbox power data"
        )
        config["load"].yaml_set_comment_before_after_key(
            "access_token", before="access token for homeassistant (optional)"
        )
        # eos configuration
        config.yaml_set_comment_before_after_key(
            "eos", before="EOS server configuration"
        )
        config["eos"].yaml_set_comment_before_after_key(
            "server", before="EOS server address"
        )
        config["eos"].yaml_set_comment_before_after_key(
            "port", before="port for EOS server - default: 8503"
        )
        config["eos"].yaml_set_comment_before_after_key(
            "timeout", before="timeout for EOS optimize request in seconds - default: 180"
        )
        # price configuration
        config.yaml_set_comment_before_after_key(
            "price", before="Electricity price configuration"
        )
        config["price"].yaml_set_comment_before_after_key(
            "source", before="data source for electricity price tibber, default (akkudoktor)"
        )
        config["price"].yaml_set_comment_before_after_key(
            "token", before="Token for electricity price"
        )
        # battery configuration
        config.yaml_set_comment_before_after_key("battery", before="battery configuration")
        config["battery"].yaml_set_comment_before_after_key(
            "source", before="Data source for battery soc - openhab, homeassistant, default"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "url", before="URL for openhab or homeassistant"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "soc_sensor", before="item / entity for battery SOC data"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "access_token", before="access token for homeassistant (optional)"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "capacity_wh", before="battery cpaacity in Wh"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "charge_efficiency", before="efficiency for charging the battery"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "discharge_efficiency", before="efficiency for discharging the battery"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "max_charge_power_w", before="max charging power in W"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "min_soc_percentage", before="URL for battery soc"
        )
        config["battery"].yaml_set_comment_before_after_key(
            "max_soc_percentage", before="URL for battery soc"
        )
        # pv forecast configuration
        config.yaml_set_comment_before_after_key(
            "pv_forecast", before="List of PV forecast configurations."+
            " Add multiple entries as needed."
        )
        for index, pv_config in enumerate(config["pv_forecast"]):
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "lat", before="Latitude for PV forecast @ Akkudoktor API"
            )
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "lon", before="Longitude for PV forecast @ Akkudoktor API"
            )
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "azimuth", before="Azimuth for PV forecast @ Akkudoktor API"
            )
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "tilt", before="Tilt for PV forecast @ Akkudoktor API"
            )
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "power", before="Power for PV forecast @ Akkudoktor API"
            )
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "powerInverter", before="Power Inverter for PV forecast @ Akkudoktor API"
            )
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "inverterEfficiency", before="Inverter Efficiency for PV forecast @ Akkudoktor API"
            )
            config["pv_forecast"][index].yaml_set_comment_before_after_key(
            "horizont", before="Horizont to calculate shading up to 360 values to describe" +
            " shading situation for your PV."
            )
        # inverter configuration
        config.yaml_set_comment_before_after_key(
            "inverter", before="Inverter configuration"
        )
        config["inverter"].yaml_set_comment_before_after_key(
            "type", before="Type of inverter - fronius_gen24, fronius_solar_api"
        )
        config["inverter"].yaml_set_comment_before_after_key(
            "address", before="Address of the inverter"
        )
        config["inverter"].yaml_set_comment_before_after_key(
            "user", before="Username for the inverter"
        )
        config["inverter"].yaml_set_comment_before_after_key(
            "password", before="Password for the inverter"
        )
        config["inverter"].yaml_set_comment_before_after_key(
            "max_grid_charge_rate", before="Max grid charge rate in W"
        )
        config["inverter"].yaml_set_comment_before_after_key(
            "max_pv_charge_rate", before="Max PV charge rate in W"
        )
        config["inverter"].yaml_set_comment_before_after_key(
            "max_bat_discharge_rate", before="Max battery discharge rate in W"
        )
        # evcc configuration
        config.yaml_set_comment_before_after_key(
            "evcc", before="EVCC configuration"
        )
        config["evcc"].yaml_set_comment_before_after_key(
            "url", before="URL for EVCC server"
        )
        # refresh time configuration
        config.yaml_set_comment_before_after_key(
            "refresh_time", before="Default refresh time in minutes"
        )
        # time zone configuration
        config.yaml_set_comment_before_after_key(
            "time_zone", before="Default time zone"
        )
        # eos connect web port configuration
        config.yaml_set_comment_before_after_key(
            "eos_connect_web_port", before="Default port for EOS connect server"
        )
        # loglevel configuration
        config.yaml_set_comment_before_after_key(
            "log_level", before="Log level for the application : debug, info, warning, error"
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
            ("[Config] EOS timeout (%s s) is greater than the refresh time (%s s)."
            " Please adjust the settings."), eos_timeout_seconds, refresh_time_seconds
            )
            sys.exit(0)
