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
                        "url": "http://<ip>:8080/rest/persistence/items/<load_item>",
                    }
                ),
                "eos": CommentedMap(
                    {
                        "server": "192.168.1.94",  # Default EOS server address
                        "port": 8503,  # Default port for EOS server
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
                        "url": "http://<ip>:8080:8080/rest/items/<soc_item>/state",
                        "capacity_wh": 11059,
                        "charge_efficiency": 0.88,
                        "discharge_efficiency": 0.88,
                        "max_charge_power_w": 5000,
                        "min_soc_percentage": 5,
                        "max_soc_percentage": 100,
                    }
                ),
                "pv_forecast": CommentedMap(
                    {
                        "default": CommentedMap(
                            {
                                "lat": 47.5,
                                "lon": 8.5,
                                "azimuth": 10.0,
                                "tilt": 30.0,
                                "power": 4600,
                                "powerInverter": 5000,
                                "inverterEfficiency": 0.9,
                                "horizont": "10,20,10,15",
                            }
                        )
                    }
                ),
                "refresh_time": 3,  # Default refresh time in minutes
                "time_zone": "Europe/Berlin",  # Add default time zone
                "eos_connect_web_port": 8081,  # Default port for EOS connect server
            }
        )
        # load configuration
        config.yaml_set_comment_before_after_key("load", before="Load configuration")
        config["load"].yaml_set_comment_before_after_key(
            "source", before="Data source for load power - openhab, homeassistant, default"
        )
        config["load"].yaml_set_comment_before_after_key(
            "url", before="URL for load power data"
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
            "url", before="URL for battery soc"
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
        config["pv_forecast"].yaml_set_comment_before_after_key(
            "default", before="Default PV forecast configuration"
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "lat", before="Latitude for PV forecast @ Akkudoktor API"
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "lon", before="Longitude for PV forecast @ Akkudoktor API"
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "azimuth", before="Azimuth for PV forecast @ Akkudoktor API"
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "tilt", before="Tilt for PV forecast @ Akkudoktor API"
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "power", before="Power for PV forecast @ Akkudoktor API"
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "powerInverter", before="Power Inverter for PV forecast @ Akkudoktor API"
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "inverterEfficiency",
            before="Inverter Efficiency for PV forecast @ Akkudoktor API",
        )
        config["pv_forecast"]["default"].yaml_set_comment_before_after_key(
            "horizont",
            before="horizont to calculate shading up to 360 values to describe shading" +
                    "sitiation for your pv.",
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
