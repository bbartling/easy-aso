import subprocess
import time
import pytest


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
