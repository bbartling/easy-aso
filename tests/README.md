## Contributing:

PRs, git issues, and discussions are highly encouraged! The requirements for contributions are that the app remains easy to use, configurable, and avoids unnecessary complexity.

Currently, the project includes two unit tests:

1. **Abstract Base Class (ABC) Validation:**: This test ensures that the EasyASO abstract base class is functioning as intended. Specifically, it verifies that any EasyASO application implements the required methods: on_start, on_stop, and on_step.

2. **BACnet Integration Test:** This test sets up a sample EasyASO client application and a simulated BACnet server device, both running in Docker containers. The test verifies that these applications can successfully communicate over the BACnet protocol for **60 seconds**. If the client and server can exchange data as expected, the test passes.

### Development Setup:

To get started with development, you'll need to:

1. **Local pip install**: Develop in a local Python package environment.
   ```bash
   pip uninstall easy-aso
   pip install .
   ```

2. **Setup Docker**: 
    Since the project relies on Docker and Docker Compose to simulate BACnet environments for testing, it's important to ensure these tools are properly installed. Simply follow the instructions in the `easy-aso/docker_setup` directory. These will guide you through setting up Docker and Docker Compose so you can run the necessary tests seamlessly.

3. **Run tests**: 
    With everything in place, you can verify your setup by running the test suite. Use the following command to run unit tests, including those that interact with the BACnet simulation:
    ```bash
    # run both tests
    pytest

    # or individual test
    pytest tests/test_bacnet.py
    ```
    The tests will check that everything works as expected and that your development environment is configured correctly.


      
