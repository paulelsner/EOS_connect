# EOS Connect

EOS Connect is a tool designed to optimize energy usage by interacting with the EOS system. It fetches energy data, processes it, and displays the results dynamically on a webpage.

- [EOS Connect](#eos-connect)
  - [Features](#features)
  - [Current Status](#current-status)
    - [Compatibility Notes:](#compatibility-notes)
  - [Webpage Example](#webpage-example)
  - [Project Structure](#project-structure)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
    - [Using Docker](#using-docker)
    - [Running Locally](#running-locally)
  - [Configuration](#configuration)
  - [Usage](#usage)
  - [Contributing](#contributing)
  - [License](#license)




## Features
* Fetches energy or battery data from OpenHAB or HomeAssistant.
* Processes data to create a load profile.
* Interacts with the Tibber API and PV forecast API.
* Manages configurations via a user-friendly config.yaml file.
* Displays results dynamically on a webpage.
* Future plans include controlling FRONIUS inverters and battery charging systems interactively.

## Current Status
This project is in its early stages and is actively being developed and enhanced.

### Compatibility Notes:

* Hint 1: Compatible with the latest EOS (new API) by default.
* Hint 2: For older EOS versions [EOS commit e22388b](https://github.com/Akkudoktor-EOS/EOS/tree/e22388b7537af545a53d6cebef35d98a7ee30e1b), modify the create_optimize_request("old") function.

## Webpage Example

![webpage screenshot](doc/screenshot.PNG)

## Project Structure

```
EOS_connect
├── doc                             # aditional documentation stuff
├── src
│   ├── interfaces                  # needed interface modules for the different sources
│   │  ├── load_interface.py        # handles getting load history for openhab and homeassistant
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

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd EOS_connect
   ```

2. Install the required Python packages (for local usage):
   ```
   pip install -r requirements.txt
   ```

## Running the Application

### Using Docker

1. Build the Docker image:
   ```
   docker build -t eos_connect .
   ```

2. Run the application using Docker Compose:
   ```
   docker-compose up
   ```

or download the latest image at [latest release](https://github.com/ohAnd/eos_connect/releases/latest) and load to your docker environment

[![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/ohand/eos_connect/latest/total)](https://github.com/ohAnd/eos_connect/releases/latest)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ohand/eos_connect/docker-image.yml)


### Running Locally

If you prefer to run the application locally without Docker, you can execute the following command:
```
python src/eos_connect.py
```

## Configuration

Configuration is described here [CONFIG_README](src/CONFIG_README.md)

## Usage

The application will start fetching energy data from OpenHAB or HomeAssistant and processing it according to the defined logic in `src/eos_connect.py`. You can access the web interface at `http://localhost:8081`.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.