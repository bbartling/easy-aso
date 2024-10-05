import subprocess
import time
import pytest

"""
Developer Note:

To run the BACnet client and server Docker containers individually NOT in a pytest environment and view their logs:

1. Build the Docker containers:

    Run the following command to build the Docker images for the client and server:
    
    $ docker-compose build

2. Run both containers together:

    To run both the BACnet client and server containers together and view their logs in real-time:
    
    $ docker-compose up

    * Press **Ctrl + C** to stop the containers when done. This will gracefully stop both containers.

3. View logs for individual containers:

    To view logs for the individual containers after running them, use the following commands:

    - Client logs:
      $ docker-compose logs bacnet-client
    
    - Server logs:
      $ docker-compose logs bacnet-server

4. Run the containers individually:

    If you want to run the server or client containers individually:

    - To run only the server container:
      $ docker-compose run bacnet-server

    - To run only the client container:
      $ docker-compose run bacnet-client

5. Stop the containers:

    To stop and remove the containers that are running in detached mode, use:
    
    $ docker-compose down
"""


# Run docker-compose, reduce the step interval for faster cycles
@pytest.fixture(scope="module")
def run_docker_compose():
    # Start the Docker Compose setup
    subprocess.run(
        ["docker-compose", "-f", "tests/docker-compose.yml", "up", "-d"], check=True
    )
    time.sleep(10)  # Give some time for the containers to start
    yield
    # Cleanup after test
    subprocess.run(
        ["docker-compose", "-f", "tests/docker-compose.yml", "down"], check=True
    )


def test_bacnet_client_server(run_docker_compose):

    time.sleep(120)  # Run the test for 120 seconds of real time

    # Get the stdout from the client and server containers
    client_logs = subprocess.run(
        ["docker", "logs", "tests-bacnet-client-1"], capture_output=True, text=True
    ).stdout
    server_logs = subprocess.run(
        ["docker", "logs", "tests-bacnet-server-1"], capture_output=True, text=True
    ).stdout

    # Ensure no errors occurred during the test
    assert "ModuleNotFoundError" not in client_logs
    assert "Traceback" not in client_logs
    assert "ModuleNotFoundError" not in server_logs
    assert "Traceback" not in server_logs

    # Check for key outputs in the logs to verify proper operation
    assert "Current power reading" in client_logs
    assert "CustomBot started" in client_logs
    assert "Updated DAP-P" in server_logs
