
# Use an Alpine Linux base image for Raspberry Pi
FROM arm32v7/alpine:latest

# Set the working directory in the container
WORKDIR /app

# Install necessary packages and dependencies
RUN apk --no-cache add python3 python3-dev py3-pip

# Install BACpypes and any other required dependencies
RUN pip3 install bacpypes3

# Copy your Python package into the container
COPY easy_aso/ /app/easy_aso/

# Copy an example script to run (optional)
COPY examples/main.py /app/main.py

# Expose the UDP port 47808 for BACnet
EXPOSE 47808/udp

# Set the default command to run your Python script
CMD ["python3", "/app/main.py"]
