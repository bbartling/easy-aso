# Use the latest python slim image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install dependencies (if any)
# For example, system-level packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install BACpypes and any other required dependencies
RUN pip install bacpypes3 ifaddr

# Copy your Python package into the container
COPY easy_aso/ /app/easy_aso/

# Copy the make_write_request.py example script into the container
COPY examples/make_write_request.py /app/make_write_request.py

# Expose the UDP port 47808 for BACnet
EXPOSE 47808/udp

# Set the default command to run your Python script with unbuffered output
CMD ["python", "-u", "/app/make_write_request.py"]

# Optional bacpypes args
#CMD ["python3", "-u", "/app/make_write_request.py", "--name", "BensBot", "--instance", "999999"]
