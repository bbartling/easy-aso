## Contributing:

PRs, git issues, and discussions are highly encouraged! The requirements for contributions are that the app remains easy to use, configurable, and avoids unnecessary complexity.

Currently, the project includes two unit tests:

1. **Abstract Base Class (ABC) Validation:**: This test ensures that the EasyASO abstract base class is functioning as intended. Specifically, it verifies that any EasyASO application implements the required methods: on_start, on_stop, and on_step.

2. **BACnet Integration Test:** This test sets up a sample EasyASO application and a simulated BACnet device, both running in Docker containers. The test verifies that these applications can successfully communicate over the BACnet protocol for **15 seconds**. If the client and server can exchange data as expected, the test passes as well as the `easy-aso` BACnet server point for `"Optimization status is True"` or `False` which operates as a kill-switch if an `easy-aso` instance was integrated via BACnet into a BAS.

### Development Setup:

To get started with development, you'll need to:

1. **Local pip install**: Develop in a local Python package environment.
   ```bash
   pip uninstall easy-aso
   pip install .
   ```

2. **Setup Docker**: 
    Since the project relies on Docker and Docker Compose to simulate BACnet environments for testing, it's important to ensure these tools are properly installed. Simply follow the instructions in the `easy-aso/docker_setup` directory. These will guide you through setting up Docker and Docker Compose so you can run the necessary tests seamlessly.

    You can manually test the docker containers within the `easy-aso/tests` dir by running these commands below where you can then view the logs manually which is what the unit tests depend on.

    ```bash
    docker-compose up
    ```
    Followed by

    ```bash
    docker-compose build
    ```
3. **Run tests**: 
    With everything in place, you can verify your setup by running the test suite. Use the following command to run unit tests, including those that interact with the BACnet simulation:
    ```bash
    # run both tests
    pytest

    # or individual test
    pytest tests/test_bacnet.py
    ```
    The tests will check that everything works as expected and that your development environment is configured correctly. On the BACnet communications tests inside the `test_bacnet.py` a `subprocess.run()` commands in the script use Docker Compose to orchestrate two Docker containers (BACnet server and client) defined in the `tests/docker-compose.yml` file. The first `docker-compose up` command starts the containers in detached mode, ensuring they communicate over a shared network defined in the Compose file. The `bridge` network configuration allows the containers to communicate using their container names as hostnames. Specifically, these containers are set up to communicate over the BACnet port (47808), which is commonly used for BACnet/IP traffic. The `time.sleep(10)` ensures enough time for the containers to initialize before the test logic runs. After the test, `docker-compose down` is used to stop and remove the containers, cleaning up the environment.


      
