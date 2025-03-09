# Configuration Guide

This document provides an overview of the configuration settings for the application. The configuration settings are stored in a `config.yaml` file.

## Configuration Sections

### Load Configuration

- **load.source**: Data source for load power. Possible values: `openhab`, `homeassistant`, `default` (default will using a primitive static consumption scheme).
- **load.url**: URL for load power data.

### EOS Server Configuration

- **eos.server**: Default EOS server address.
- **eos.port**: Default port for EOS server.

### Electricity Price Configuration

- **price.source**: Data source for electricity price. Possible values: `tibber`, `akkudoktor`.
- **price.token**: Token for electricity price.

### Battery Configuration
- **battery.source**: Data source for battery SOC. Possible values: openhab, homeassistant, default.
- **battery.url**: URL for battery SOC.
- **battery.capacity_wh**: Battery capacity in Wh.
- **battery.charge_efficiency**: Efficiency for charging the battery.
- **battery.discharge_efficiency**: Efficiency for discharging the battery.
- **battery.max_charge_power_w**: Maximum charging power in W.
- **battery.min_soc_percentage**: Minimum state of charge percentage.
- **battery.max_soc_percentage**: Maximum state of charge percentage.

### PV Forecast Configuration

The `pv_forecast` section allows you to define multiple PV forecast entries, each distinguished by a user-given name. Below is an example of a default PV forecast configuration:

```yaml
pv_forecast:
  default:
    lat: 47.5
    lon: 8.5
    azimuth: 10.0
    tilt: 30.0
    power: 4600
    powerInverter: 5000
    inverterEfficiency: 0.9
    horizont: "10,20,10,15"
```

Each PV forecast entry can have the following parameters:

- **lat**: Latitude for PV forecast @ Akkudoktor API.
- **lon**: Longitude for PV forecast @ Akkudoktor API.
- **azimuth**: Azimuth for PV forecast @ Akkudoktor API.
- **tilt**: Tilt for PV forecast @ Akkudoktor API.
- **power**: Power for PV forecast @ Akkudoktor API.
- **powerInverter**: Power Inverter for PV forecast @ Akkudoktor API.
- **inverterEfficiency**: Inverter Efficiency for PV forecast @ Akkudoktor API.
- **horizont**: optionial - Horizont to calculate shading up to 360 values to describe shading situation for your PV.

Feel free to add more PV forecast entries under the pv_forecast section by providing a unique name for each entry.

### Other Configuration Settings

**refresh_time**: Default refresh time in minutes.

**time_zone**: Default time zone.

**eos_connect_web_port**: Default port for EOS connect server.

## Notes
Ensure that the config.yaml file is located in the same directory as the application.

If the configuration file does not exist, the application will create one with default values and prompt you to restart the server after configuring the settings.

## Full Config Example

```yaml
oad:
  source: default  # Data source for load power - openhab or homeassistant
  url: http://<ip>:8080/rest/persistence/items/<load_item>  # URL for load power data

eos:
  server: 192.168.1.94  # Default EOS server address
  port: 8503  # Default port for EOS server

price:
  source: tibber  # Data source for electricity price
  token: tibberBearerToken  # Token for electricity price

battery:
  source: default  # Data source for battery SOC - openhab, homeassistant, default
  url: http://<ip>:8080:8080/rest/items/<soc_item>/state  # URL for battery SOC
  capacity_wh: 11059  # Battery capacity in Wh
  charge_efficiency: 0.88  # Efficiency for charging the battery
  discharge_efficiency: 0.88  # Efficiency for discharging the battery
  max_charge_power_w: 5000  # Maximum charging power in W
  min_soc_percentage: 5  # Minimum state of charge percentage
  max_soc_percentage: 100  # Maximum state of charge percentage

pv_forecast:
  roof_west:
    lat: 47.5  # Latitude for PV forecast @ Akkudoktor API
    lon: 8.5  # Longitude for PV forecast @ Akkudoktor API
    azimuth: 90.0  # Azimuth for PV forecast @ Akkudoktor API
    tilt: 30.0  # Tilt for PV forecast @ Akkudoktor API
    power: 4600  # Power for PV forecast @ Akkudoktor API
    powerInverter: 5000  # Power Inverter for PV forecast @ Akkudoktor API
    inverterEfficiency: 0.9  # Inverter Efficiency for PV forecast @ Akkudoktor API
    horizont: "10,20,10,15"  # Horizont to calculate shading up to 360 values to describe shading situation for your PV
  garden_south:
    lat: 47.5  # Latitude for PV forecast @ Akkudoktor API
    lon: 8.5  # Longitude for PV forecast @ Akkudoktor API
    azimuth: 0.0  # Azimuth for PV forecast @ Akkudoktor API
    tilt: 45.0  # Tilt for PV forecast @ Akkudoktor API
    power: 860  # Power for PV forecast @ Akkudoktor API
    powerInverter: 800  # Power Inverter for PV forecast @ Akkudoktor API
    inverterEfficiency: 0.9  # Inverter Efficiency for PV forecast @ Akkudoktor API
    horizont: ""  # Horizont to calculate shading up to 360 values to describe shading situation for your PV

refresh_time: 3  # Default refresh time in minutes
time_zone: Europe/Berlin  # Default time zone
eos_connect_web_port: 8081  # Default port for EOS connect server
```