
# easy-aso

This project is designed for running BACnet optimization and control strategies using Python and BACpypes. The `easy-aso` package can be installed locally or run inside a Docker container.

## Installation

**Setup Docker per Ubuntu documentation**:
* https://docs.docker.com/engine/install/ubuntu/

**Check Docker service**:

```bash
sudo systemctl status docker
```

### Step 2: Build the Docker Image

1. **Navigate to the project directory**:

   ```bash
   cd /path/to/your/easy-aso/scripts
   ```

2. **Build the Docker image**:
   From inside the project root directory run:

   ```bash
   sudo docker build -t easy-aso -f docker_setup/Dockerfile .
   ```

### Step 3: Run the Docker Container

1. **Run the Docker container**:

   ```bash
   sudo docker run --name easy-aso-container -d -p 47808:47808/udp easy-aso
   ```

2. **Verify the container is running**:

   ```bash
   sudo docker ps
   ```

### Step 4: View Logs from the Docker Container

1. **View real-time logs**:

   ```bash
   sudo docker logs -f easy-aso-container
   ```

2. **Stop viewing logs**:

   Press `Ctrl+C` to stop viewing the logs.

### Managing the Container

1. **Stop the container**:

   ```bash
   sudo docker stop easy-aso-container
   ```

2. **Restart the container**:

   ```bash
   sudo docker start easy-aso-container
   ```

2. **Restart the container**:

   ```bash
   sudo docker restart easy-aso-container
   ```

3. **Remove the container**: 

   ```bash
   sudo docker rm easy-aso-container
   ```

   You can also delete the image with:

   ```bash
   sudo docker rmi easy-aso
   ```

### TODO 
* Test a docker app on a UDP port other than 47808

```bash
# Use a Python base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install necessary packages and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

# Install BACpypes and other dependencies
RUN pip install bacpypes3 ifaddr

# Copy your Python package into the container
COPY easy_aso/ /app/easy_aso/

# Copy the make_write_request.py example script into the container
COPY examples/make_write_request.py /app/make_write_request.py

# Expose the default UDP port 47808 (you can expose other ports as needed)
EXPOSE 47808/udp
EXPOSE 47820/udp  # Expose additional port

# Set the default command to run the script, allowing arguments to be passed dynamically
CMD ["python3", "-u", "/app/make_write_request.py"]
```