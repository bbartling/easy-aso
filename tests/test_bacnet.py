import subprocess
import time
import shutil
import pytest


def _docker_available() -> bool:
    # integration test: requires docker + compose
    docker_path = shutil.which("docker")
    if docker_path is None:
        return False
    try:
        subprocess.run([docker_path, "info"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    docker_compose_path = shutil.which("docker-compose")
    if docker_compose_path is not None:
        return True
    try:
        subprocess.run([docker_path, "compose", "version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@pytest.fixture(scope="module")
def run_docker_compose():
    if not _docker_available():
        pytest.skip("integration test requires docker + docker compose")
    # Prefer compose v2, fall back to docker-compose
    docker_compose_path = shutil.which("docker-compose")
    if docker_compose_path is not None:
        cmd = [docker_compose_path, "-f", "tests/docker-compose.yml"]
    else:
        docker_path = shutil.which("docker")
        cmd = [docker_path, "compose", "-f", "tests/docker-compose.yml"]
    subprocess.run(cmd + ["up", "-d"], check=True)
    time.sleep(10)
    yield
    subprocess.run(cmd + ["down"], check=True)


def test_bacnet_client_server(run_docker_compose):
    time.sleep(15)
    fake_easy_aso_logs = subprocess.run(["docker", "logs", "fake-easy-aso"], capture_output=True, text=True).stdout
    fake_bacnet_device_logs = subprocess.run(["docker", "logs", "fake-bacnet-device"], capture_output=True, text=True).stdout
    print("fake_easy_aso_logs:\n", fake_easy_aso_logs)
    print("fake_bacnet_device_logs:\n", fake_bacnet_device_logs)
    assert "ModuleNotFoundError" not in fake_easy_aso_logs
    assert "Traceback" not in fake_easy_aso_logs
    assert "ModuleNotFoundError" not in fake_bacnet_device_logs
    assert "Traceback" not in fake_bacnet_device_logs
    assert "Optimization status is True" in fake_easy_aso_logs
    assert "Optimization status is False" in fake_easy_aso_logs
    assert "Optimization re-enabled. Resuming normal operation." in fake_easy_aso_logs
    assert "All BACnet overrides have been released." in fake_easy_aso_logs
