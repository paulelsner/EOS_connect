# EOS Connect

Request optimization at an [EOS](https://github.com/Akkudoktor-EOS) and handle the response to display the result on a dynamic webpage.

Currently, the project is designed to fetch energy data from OpenHAB, process it, and create a load profile. It includes functionalities for interacting with the Tibber API and PV forecast API, managing configurations, and handling energy data.

Next step:
Using the feedback to interactively control a FRONIUS inverter and battery charging system.

*Hint 1: usage approved with latest EOS (new API) - default*

*Hint 2: usage approved with commit https://github.com/Akkudoktor-EOS/EOS/tree/e22388b7537af545a53d6cebef35d98a7ee30e1b (old API) - have to be changed at function create_optimize_request("old")*

## Project Structure

```
EOS_connect
├── src
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

### Running Locally

If you prefer to run the application locally without Docker, you can execute the following command:
```
python src/eos_connect.py
```

## Configuration

Configuration is described here [CONFIG_README](src/CONFIG_README.md)

## Usage

The application will start fetching energy data from OpenHAB and processing it according to the defined logic in `src/eos_connect.py`. You can access the web interface at `http://localhost:8081`.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.