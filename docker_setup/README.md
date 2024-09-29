
# easy-aso

This project is designed for running BACnet optimization and control strategies using Python and BACpypes. The `easy-aso` package can be installed locally or run inside a Docker container.

## Installation

### 1. Local Installation

To install the package locally, you can run:

```bash
pip install easy-aso
```

### 2. Running in Docker

If you'd like to run the project in a Docker container, follow the steps below.

## Docker Setup

### Step 1: Install Docker on Ubuntu

1. **Update the package list**:

   ```bash
   sudo apt update
   ```

2. **Install prerequisite packages**:

   ```bash
   sudo apt install apt-transport-https ca-certificates curl software-properties-common
   ```

3. **Add Docker’s official GPG key**:

   ```bash
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   ```

4. **Set up the stable Docker repository**:

   ```bash
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```

5. **Update the package list again to recognize Docker’s repository**:

   ```bash
   sudo apt update
   ```

6. **Install Docker**:

   ```bash
   sudo apt install docker-ce
   ```

7. **Check Docker service**:

   ```bash
   sudo systemctl status docker
   ```

### Step 2: Build the Docker Image

1. **Navigate to the project directory**:

   ```bash
   cd /path/to/your/easy-aso/scripts
   ```

2. **Build the Docker image**:

   ```bash
   sudo docker build -t easy-aso .
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

3. **Remove the container**:

   ```bash
   sudo docker rm easy-aso-container
   ```

   You can also delete the image with:

   ```bash
   sudo docker rmi easy-aso
   ```

## License

This project is licensed under the MIT License.
