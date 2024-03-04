#!/bin/bash

# Define the interface to listen on, e.g., eth0, wlan0, etc.
INTERFACE="eth0"

# Define the BACnet port
PORT=47808

# Run tcpdump to capture BACnet traffic
sudo tcpdump -i $INTERFACE udp port $PORT -w bacnet_capture.pcap
