# EOS Connect Energy Data Processing

This project is designed to fetch energy data from OpenHAB, process it, and create a load profile. It includes functionalities for interacting with APIs, managing configurations, and handling energy data.

Finally to request an optimization through EOS https://github.com/Akkudoktor-EOS and get the feedback and display this on dynamic webpage.

current usage with commit https://github.com/Akkudoktor-EOS/EOS/tree/e22388b7537af545a53d6cebef35d98a7ee30e1b approved (old API)

## Project Structure

```
EOS_connect
├── src
│   ├── eos_optimize_request.py  # Main logic for fetching and processing energy data
├── Dockerfile                     # Docker configuration for the project
├── docker-compose.yml             # Docker Compose configuration for multi-container setup
├── requirements.txt               # Python dependencies for the project
└── README.md                      # Project documentation
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

2. Install the required Python packages:
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
python src/eos_optimize_request.py
```

## Usage

The application will start fetching energy data from OpenHAB and processing it according to the defined logic in `src/eos_optimize_request.py`. You can access the web interface at `http://localhost:8081`.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.