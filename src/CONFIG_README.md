# Configuration Guide

This document provides an overview of the configuration settings for the application. The configuration settings are stored in a `config.yaml` file.  
A default config file will be created with the first start, if there is no `config.yaml` in the `src` folder.

---

## Configuration Sections

### **Load Configuration**

- **`load.source`**:  
  Data source for load power. Possible values: `openhab`, `homeassistant`, `default` (default will use a primitive static consumption scheme).

- **`load.url`**:  
  URL for OpenHAB (e.g., `http://<ip>:8080`) or Home Assistant (e.g., `http://<ip>:8123`).

- **`load.load_sensor`**:  
  Item/entity name for load power data (OpenHAB item/Home Assistant sensor).  
  Must be in watts.  
  **Hint**: For Home Assistant, negative values are expected for persisted data.

- **`load.car_charge_load_sensor`**:  
  Item/entity name for wallbox power data.  
  Must be in watts or kilowatts (automatically checked).

- **`load.access_token`**:  
  Access token for Home Assistant (optional).

---

### **EOS Server Configuration**

- **`eos.server`**:  
  EOS server address (e.g., `192.168.1.94`).

- **`eos.port`**:  
  Port for the EOS server. Default: `8503`.

- **`timeout`**:  
  Timeout for EOS optimization requests, in seconds. Default: `180`.

---

### **Electricity Price Configuration**

- **`price.source`**:  
  Data source for electricity prices. Possible values: `tibber`, `default` (default uses akkudoktor API).

- **`price.token`**:  
  Token for accessing electricity price data.

- **`price.feed_in_price`**:  
  Feed-in price for the grid, in €/kWh.

- **`price.negative_price_switch`**:  
  Switch for handling negative electricity prices.  
  - `True`: Limits the feed-in price to `0` if there is a negative stock price for the hour.  
  - `False`: Ignores negative stock prices and uses the constant feed-in price.

---

### **Battery Configuration**

- **`battery.source`**:  
  Data source for battery SOC (State of Charge). Possible values: `openhab`, `homeassistant`, `default` (static data).

- **`battery.url`**:  
  URL for OpenHAB (e.g., `http://<ip>:8080`) or Home Assistant (e.g., `http://<ip>:8123`).

- **`battery.soc_sensor`**:  
  Item/entity name for the SOC sensor (OpenHAB item/Home Assistant sensor).

- **`battery.access_token`**:  
  Access token for Home Assistant (optional).

- **`battery.capacity_wh`**:  
  Total capacity of the battery, in watt-hours (Wh).

- **`battery.charge_efficiency`**:  
  Efficiency of charging the battery, as a decimal value between `0` and `1`.

- **`battery.discharge_efficiency`**:  
  Efficiency of discharging the battery, as a decimal value between `0` and `1`.

- **`battery.max_charge_power_w`**:  
  Maximum charging power for the battery, in watts (W).

- **`battery.min_soc_percentage`**:  
  Minimum state of charge for the battery, as a percentage.

- **`battery.max_soc_percentage`**:  
  Maximum state of charge for the battery, as a percentage.

---

### **PV Forecast Configuration**

The `pv_forecast` section allows you to define multiple PV forecast entries, each distinguished by a user-given name. Below is an example of a default PV forecast configuration:

```yaml
pv_forecast:
  - name: myPvInstallation1  # User-defined identifier for the PV installation, must be unique if you use multiple installations
    lat: 47.5  # Latitude for PV forecast @ Akkudoktor API
    lon: 8.5  # Longitude for PV forecast @ Akkudoktor API
    azimuth: 90.0  # Azimuth for PV forecast @ Akkudoktor API
    tilt: 30.0  # Tilt for PV forecast @ Akkudoktor API
    power: 4600  # Power for PV forecast @ Akkudoktor API
    powerInverter: 5000  # Power Inverter for PV forecast @ Akkudoktor API
    inverterEfficiency: 0.9  # Inverter Efficiency for PV forecast @ Akkudoktor API
    horizont: 10,20,10,15  # Horizont to calculate shading up to 360 values to describe shading situation for your PV.
```

#### **Parameters**
- **`name`**:  
  A user-defined identifier for the PV installation. Must be unique if you use multiple installations.

- **`lat`**:  
  Latitude for the PV forecast.

- **`lon`**:  
  Longitude for the PV forecast.

- **`azimuth`**:  
  Azimuth angle for the PV forecast.

- **`tilt`**:  
  Tilt angle for the PV forecast.

- **`power`**:  
  The power of the PV installation, in watts (W).

- **`powerInverter`**:  
  The power of the inverter, in watts (W).

- **`inverterEfficiency`**:  
  The efficiency of the inverter, as a decimal value between `0` and `1`.

- **`horizont`**:  
  (Optional) A list of up to 360 values describing the shading situation for the PV installation.

---

### **Inverter Configuration**

- **`inverter.type`**:  
  Specifies the type of inverter. Possible values:  
  - `fronius_gen24`: Use the Fronius Gen24 inverter.  
  - `default`: Disable inverter control (only display the target state).

- **`inverter.address`**:  
  The IP address of the inverter.

- **`inverter.user`**:  
  The username for the inverter's local portal.

- **`inverter.password`**:  
  The password for the inverter's local portal.

- **`inverter.max_grid_charge_rate`**:  
  The maximum grid charge rate, in watts (W).

- **`inverter.max_pv_charge_rate`**:  
  The maximum PV charge rate, in watts (W).

- **`inverter.max_bat_discharge_rate`**:  
  The maximum battery discharge rate, in watts (W).

---

### **EVCC Configuration**

- **`evcc.url`**:  
  The URL for the EVCC instance (e.g., `http://<ip>:7070`).

---

### **MQTT Configuration**

The `mqtt` section allows you to configure the MQTT broker and Home Assistant MQTT Auto Discovery settings.

#### **Parameters**

- **`mqtt.enabled`**:  
  Enable or disable MQTT functionality.  
  - `true`: Enable MQTT.  
  - `false`: Disable MQTT.  

- **`mqtt.broker`**:  
  The address of the MQTT broker (e.g., `localhost` or `192.168.1.10`).

- **`mqtt.port`**:  
  The port of the MQTT broker. Default: `1883`.

- **`mqtt.user`**:  
  The username for authenticating with the MQTT broker (optional).

- **`mqtt.password`**:  
  The password for authenticating with the MQTT broker (optional).

- **`mqtt.tls`**:  
  Enable or disable TLS for secure MQTT connections.  
  - `true`: Use TLS for secure connections.  
  - `false`: Do not use TLS.  

- **`mqtt.ha_mqtt_auto_discovery`**:  
  Enable or disable Home Assistant MQTT Auto Discovery.  
  - `true`: Enable Auto Discovery.  
  - `false`: Disable Auto Discovery.  

- **`mqtt.ha_mqtt_auto_discovery_prefix`**:  
  The prefix for Home Assistant MQTT Auto Discovery topics. Default: `homeassistant`.

---

### **Other Configuration Settings**

- **`refresh_time`**:  
  Default refresh time for the application, in minutes.

- **`time_zone`**:  
  Default time zone for the application.

- **`eos_connect_web_port`**:  
  Default port for the EOS Connect server.

- **`log_level`**:  
  Log level for the application. Possible values: `debug`, `info`, `warning`, `error`.

---

## Notes

- Ensure that the `config.yaml` file is located in the same directory as the application.
- If the configuration file does not exist, the application will create one with default values and prompt you to restart the server after configuring the settings.

## Full Config Example (will be generated at first startup)

```yaml
# Load configuration
load:
  source: default  # Data source for load power - openhab, homeassistant, default (using a static load profile)
  url: http://homeassistant:8123 # URL for openhab or homeassistant (e.g. http://openhab:7070 or http://homeassistant:8123)
  load_sensor: Load_Power # item / entity for load power data in watts
  car_charge_load_sensor: Wallbox_Power # item / entity for wallbox power data in watts or kilowatts
  access_token: abc123 # access token for homeassistant (optional)
# EOS server configuration
eos:
  server: 192.168.1.94  # EOS server address
  port: 8503 # port for EOS server - default: 8503
  timeout: 180 # timeout for EOS optimize request in seconds - default: 180
# Electricity price configuration
price:
  source: default  # data source for electricity price tibber, default (default uses akkudoktor)
  token: tibberBearerToken # Token for electricity price
  feed_in_price: 0.0 # feed in price for the grid in €/kWh
  negative_price_switch: false # switch for no payment if negative stock price is given
# battery configuration
battery:
  source: default  # Data source for battery soc - openhab, homeassistant, default
  url: http://homeassistant:8123 # URL for openhab or homeassistant (e.g. http://openhab:7070 or http://homeassistant:8123)
  soc_sensor: battery_SOC # item / entity for battery SOC data in [0..1]
  access_token: abc123 # access token for homeassistant (optional)
  capacity_wh: 11059 # battery capacity in Wh
  charge_efficiency: 0.88 # efficiency for charging the battery in [0..1]
  discharge_efficiency: 0.88 # efficiency for discharging the battery in [0..1]
  max_charge_power_w: 5000 # max charging power in W
  min_soc_percentage: 5 # URL for battery soc in %
  max_soc_percentage: 100 # URL for battery soc in %
# List of PV forecast configurations. Add multiple entries as needed.
# See Akkudoktor API (https://api.akkudoktor.net/#/pv%20generation%20calculation/getForecast) for more details.
pv_forecast:
  - name: myPvInstallation1  # User-defined identifier for the PV installation, have to be unique if you use more installations
    lat: 47.5 # Latitude for PV forecast @ Akkudoktor API
    lon: 8.5 # Longitude for PV forecast @ Akkudoktor API
    azimuth: 90.0 # Azimuth for PV forecast @ Akkudoktor API
    tilt: 30.0 # Tilt for PV forecast @ Akkudoktor API
    power: 4600 # Power for PV forecast @ Akkudoktor API
    powerInverter: 5000 # Power Inverter for PV forecast @ Akkudoktor API
    inverterEfficiency: 0.9 # Inverter Efficiency for PV forecast @ Akkudoktor API
    horizont: 10,20,10,15 # Horizont to calculate shading up to 360 values to describe shading situation for your PV.
# Inverter configuration
inverter:
  type: default  # Type of inverter - fronius_gen24, default (default will disable inverter control - only displaying the target state) - preset: default
  address: 192.168.1.12 # Address of the inverter
  user: customer # Username for the inverter
  password: abc123 # Password for the inverter
  max_grid_charge_rate: 5000 # Max grid charge rate in W - default: 5000
  max_pv_charge_rate: 5000 # Max PV charge rate in W - default: 5000
  max_bat_discharge_rate: 5000 # Max battery discharge rate in W (currently not used) - default: 5000
# EVCC configuration
evcc:
  url: http://yourEVCCserver:7070  # URL for EVCC server - default: http://yourEVCCserver:7070
mqtt:
  enabled: false # Enable MQTT - default: false
  broker: localhost # URL for MQTT server - default: mqtt://yourMQTTserver
  port: 1883 # Port for MQTT server - default: 1883
  user: mqtt_user # Username for MQTT server - default: mqtt
  password: mqtt_password # Password for MQTT server - default: mqtt
  tls: false # Use TLS for MQTT server - default: false
  ha_mqtt_auto_discovery: true # Enable Home Assistant MQTT auto discovery - default: true
  ha_mqtt_auto_discovery_prefix: homeassistant # Prefix for Home Assistant MQTT auto discovery - default: homeassistant
refresh_time: 3 # Default refresh time of EOS connect in minutes - default: 3
time_zone: Europe/Berlin # Default time zone - default: Europe/Berlin
eos_connect_web_port: 8081 # Default port for EOS connect server - default: 8081
log_level: info # Log level for the application : debug, info, warning, error - default: info

```