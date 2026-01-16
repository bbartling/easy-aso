import subprocess
import time
import os
import pytest

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
SERVICE_NAME = "diy-bacnet-server-test"


def get_compose_command():
    """
    Determines if the system uses 'docker compose' (V2) or 'docker-compose' (V1).
    Returns the command list prefix to use in subprocess calls.
    """
    # 1. Try the modern 'docker compose' (V2 plugin)
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("\n[Test Setup] Using modern 'docker compose' (V2)")
        return ["docker", "compose"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 2. Fallback to legacy 'docker-compose' (V1 standalone)
    print("\n[Test Setup] Falling back to legacy 'docker-compose' (V1)")
    return ["docker-compose"]


@pytest.fixture(scope="module")
def run_docker_compose():
    """Start the BACnet server container for the duration of the test module."""
    
    # DYNAMICALLY GET THE COMMAND HERE
    compose_cmd = get_compose_command()

    # Build the full command: ['docker', 'compose', '-f', ...] or ['docker-compose', '-f', ...]
    up_cmd = compose_cmd + ["-f", COMPOSE_FILE, "up", "-d"]
    down_cmd = compose_cmd + ["-f", COMPOSE_FILE, "down", "-v"]

    print(f"[Test Setup] Running command: {' '.join(up_cmd)}")

    subprocess.run(up_cmd, check=True)

    # give container some time to start BACnet stack and JSON-RPC API
    print("[Test Setup] Waiting 15s for BACnet stack boot...")
    time.sleep(15)
    
    yield

    print(f"[Test Teardown] Running command: {' '.join(down_cmd)}")
    subprocess.run(down_cmd, check=True)


def _get_container_logs(name: str) -> str:
    proc = subprocess.run(
        ["docker", "logs", name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.stdout


def test_bacnet_server_startup(run_docker_compose):
    """Basic smoke test that container starts and BACnet/JSON-RPC boot without exceptions."""
    logs = _get_container_logs(SERVICE_NAME)

    # Helpful debug print if the test fails in CI
    print("===== diy-bacnet-server container logs =====")
    print(logs)
    print("===========================================")

    # Ensure the BACpypes application initialized
    assert "BACnet application initialized." in logs

    # Ensure the JSON-RPC API came up
    assert "JSON-RPC API ready at" in logs

    # No unhandled tracebacks or import errors allowed in logs
    assert "Traceback (most recent call last)" not in logs
    assert "ModuleNotFoundError" not in logs
    assert "ImportError" not in logs