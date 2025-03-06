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
                        "source": "openhab",  # data source for load power
                        "url": "http://192.168.1.30:8080/rest/persistence/items/Fronius_Load_Power",
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
                        "source": "tibber",  # data source for electricity price
                        "token": "tibberBearerToken",  # token for electricity price
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

        config.yaml_set_comment_before_after_key("load", before="Load configuration")
        config["load"].yaml_set_comment_before_after_key(
            "source", before="Data source for load power - openhab or homeassistant"
        )
        config["load"].yaml_set_comment_before_after_key(
            "url", before="URL for load power data"
        )

        config.yaml_set_comment_before_after_key(
            "eos", before="EOS server configuration"
        )
        config["eos"].yaml_set_comment_before_after_key(
            "server", before="Default EOS server address"
        )
        config["eos"].yaml_set_comment_before_after_key(
            "port", before="Default port for EOS server"
        )

        config.yaml_set_comment_before_after_key(
            "price", before="Electricity price configuration"
        )
        config["price"].yaml_set_comment_before_after_key(
            "source", before="Data source for electricity price"
        )
        config["price"].yaml_set_comment_before_after_key(
            "token", before="Token for electricity price"
        )

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
            before="horizont to calculate shading up to 360 values to describe shading sitiation for your pv.",
        )

        config.yaml_set_comment_before_after_key(
            "refresh_time", before="Default refresh time in minutes"
        )
        config.yaml_set_comment_before_after_key(
            "time_zone", before="Default time zone"
        )
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

    def set_load_source(self, load_source):
        """
        Updates the configuration file with the new load source.
        Possible values: openhab, homeassistant
        """
        valid_sources = ["openhab", "homeassistant"]
        if load_source not in valid_sources:
            logger.error("[Config] invalid load source: %s", load_source)
            raise ValueError(
                f"Invalid load source: {load_source}. Valid options are: {valid_sources}"
            )

        logger.info("[Config] setting load source to %s", load_source)
        self.config["load"]["source"] = load_source
        self.write_config()

    def set_load_url(self, load_url):
        """
        Updates the configuration file with the new load URL.
        """
        logger.info("[Config] setting load URL to %s", load_url)
        self.config["load"]["url"] = load_url
        self.write_config()

    def set_eos_server(self, eos_server):
        """
        Updates the configuration file with the new EOS server address.
        """
        logger.info("[Config] setting EOS server to %s", eos_server)
        self.config["eos"]["server"] = eos_server
        self.write_config()

    def set_eos_port(self, eos_port):
        """
        Updates the configuration file with the new EOS server port.
        """
        logger.info("[Config] setting EOS port to %s", eos_port)
        self.config["eos"]["port"] = eos_port
        self.write_config()

    def set_price_source(self, price_source):
        """
        Updates the configuration file with the new price source.
        Possible values: tibber, custom
        """
        valid_sources = ["tibber", "akkudoktor"]
        if price_source not in valid_sources:
            logger.error("[Config] invalid price source: %s", price_source)
            raise ValueError(
                f"Invalid price source: {price_source}. Valid options are: {valid_sources}"
            )

        logger.info("[Config] setting price source to %s", price_source)
        self.config["price"]["source"] = price_source
        self.write_config()

    def set_price_source_token(self, price_source_token):
        """
        Updates the configuration file with the new price source token.
        """
        logger.info("[Config] setting price source token to %s", price_source_token)
        self.config["price"]["token"] = price_source_token
        self.write_config()

    def set_refresh_time(self, refresh_time):
        """
        Updates the configuration file with the new refresh time.
        """
        logger.info("[Config] setting refresh time to %s", refresh_time)
        self.config["refresh_time"] = refresh_time
        self.write_config()

    def set_time_zone(self, time_zone):
        """
        Updates the configuration file with the new time zone.
        """
        logger.info("[Config] setting time zone to %s", time_zone)
        self.config["time_zone"] = time_zone
        self.write_config()

    def set_eos_connect_web_port(self, eos_connect_web_port):
        """
        Updates the configuration file with the new EOS connect server port.
        """
        logger.info(
            "[Config] setting EOS connect server port to %s", eos_connect_web_port
        )
        self.config["eos_connect_web_port"] = eos_connect_web_port
        self.write_config()
