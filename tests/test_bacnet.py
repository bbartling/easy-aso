import subprocess
import time
import pytest


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
    time.sleep(15)  # Run the test for 60 seconds of real time

    # Get the stdout from the client and server containers
    fake_easy_aso_logs = subprocess.run(
        ["docker", "logs", "fake-easy-aso"], capture_output=True, text=True
    ).stdout

    fake_bacnet_device_logs = subprocess.run(
        ["docker", "logs", "fake-bacnet-device"], capture_output=True, text=True
    ).stdout

    # Print logs for debugging
    print("fake_easy_aso_logs:\n", fake_easy_aso_logs)
    print("fake_bacnet_device_logss:\n", fake_bacnet_device_logs)

    # Ensure no errors occurred during the test
    assert "ModuleNotFoundError" not in fake_easy_aso_logs
    assert "Traceback" not in fake_easy_aso_logs
    assert "ModuleNotFoundError" not in fake_bacnet_device_logs
    assert "Traceback" not in fake_bacnet_device_logs

    # test kill switch is working good
    # gets written from fake bacnet device
    assert "Optimization status is True" in fake_easy_aso_logs
    assert "Optimization status is False" in fake_easy_aso_logs
    assert "Optimization re-enabled. Resuming normal operation." in fake_easy_aso_logs

    # test BACnet release is working on_stop
    assert "All BACnet overrides have been released." in fake_easy_aso_logs
