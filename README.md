# EOS Connect

EOS Connect is a tool designed to optimize energy usage by interacting with the EOS system. It fetches energy data, processes it, and displays the results dynamically on a webpage.

- [EOS Connect](#eos-connect)
  - [Features](#features)
  - [Current Status](#current-status)
  - [Webpage Example](#webpage-example)
  - [Configuration](#configuration)
  - [Useful Information](#useful-information)
    - [Getting historical values](#getting-historical-values)
      - [Homeassistant](#homeassistant)
      - [Openhab](#openhab)
  - [Usage](#usage)
  - [Project Structure](#project-structure)
  - [Requirements](#requirements)
  - [Installation and Running](#installation-and-running)
  - [Running the Application](#running-the-application)
    - [Using Docker](#using-docker)
    - [Using in Home Assistant with an Add On](#using-in-home-assistant-with-an-add-on)
    - [Local](#local)
      - [Installation](#installation)
      - [Running Locally](#running-locally)
  - [Contributing](#contributing)
  - [License](#license)




## Features
* Fetches energy or battery data from OpenHAB or HomeAssistant.
* Processes data to create a load profile.
* Interacts with the Tibber API and PV forecast API.
* Manages configurations via a user-friendly config.yaml file.
* Displays results dynamically on a webpage.
* Controlling FRONIUS inverters and battery charging systems interactively.

## Current Status
This project is in its early stages and is actively being developed and enhanced.

## Webpage Example

![webpage screenshot](doc/screenshot.PNG)

## Configuration

Configuration is described here [CONFIG_README](src/CONFIG_README.md)

## Useful Information

### Getting historical values

#### Homeassistant

The tool will use historical data from Home Assistant's local database. By default, this database is configured with a retention period of **10 days**.

To improve the accuracy of load forecasts, it is recommended to use data from the last **2 weeks**. 

You can extend the retention period by modifying the `recorder` configuration in Home Assistant's `configuration.yaml` file. If the `recorder` section is not already present, you can add it as shown below:

```yaml
recorder:
  purge_keep_days: 15  # Keep data for 15 days
```

After making this change, restart Home Assistant for the new retention period to take effect.

**Note**: Increasing the retention period will require more storage space, depending on the number of entities being recorded.

If you do not change the retention period, the tool will still work, but it will use the available 10 days of data, which may result in less accurate load forecasts.

#### Openhab

No specific info yet.

## Usage

The application will start fetching energy data from OpenHAB or HomeAssistant and processing it according to the defined logic in `src/eos_connect.py`. You can access the web interface at `http://localhost:8081`. For local usage the port is configurable see [CONFIG_README](src/CONFIG_README.md). For docker usage change the mapped port in docker-compose.yml.

## Project Structure

```
EOS_connect
├── doc                             # aditional documentation stuff
├── src
│   ├── interfaces                  # needed interface modules for the different sources
│   │  ├── load_interface.py        # handles getting load history from openhab and homeassistant
│   │  ├── battery_interface.py     # handles getting soc data from openhab and homeassistant
│   ├── json
│   │  ├── optimize_request.json    # will be created/ rewritten with every new optimization request
│   │  ├── optimize_response.json   # will be created/ rewritten after the feedback of EOS
│   ├── web
│   │  ├── index.html               # served webpage to dynamically showing the current state and response from EOS
│   ├── eos_connect.py              # Main logic for fetching and processing energy data
│   ├── config.py                   # config handling
│   ├── config.yaml                 # config file - default will be created with first start
│   ├── CONFIG_README.md            # config documentation
├── Dockerfile                      # Docker configuration for the project
├── docker-compose.yml              # Docker Compose configuration for multi-container setup
├── requirements.txt                # Python dependencies for the project
└── README.md                       # Project documentation
```

## Requirements

To run this project, you need to have the following installed:

- Python 3.x
- Docker
- Docker Compose

## Installation and Running

## Running the Application

### Using Docker

Pull existing latest snapshot and run the application in the background using Docker Compose (`--pull always` ensures the latest image is pulled):
   ```
   docker-compose up --pull always -d
   ```
[![latest](https://ghcr-badge.egpl.dev/ohand/eos_connect/latest_tag?color=%2344cc11&ignore=latest&label=latest+version&trim=)](https://github.com/ohAnd/EOS_connect/pkgs/container/eos_connect)

[![image tags](https://ghcr-badge.egpl.dev/ohand/eos_connect/tags?color=%2344cc11&ignore=latest&n=3&label=latest+image+tags&trim=)](https://github.com/ohAnd/EOS_connect/pkgs/container/eos_connect)

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ohand/eos_connect/docker-image.yml)

### Using in Home Assistant with an Add On

see https://github.com/ohAnd/ha_addons

### Local

#### Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd EOS_connect
   ```

2. Install the required Python packages (for local usage):
   ```
   pip install -r requirements.txt
   ```
#### Running Locally

Run the application locally without Docker, you can execute the following command:
```
python src/eos_connect.py
```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.