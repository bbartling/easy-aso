#!/usr/bin/env bash

# sudo apt update
# sudo apt install tcpdump
#
# capture_bacnet_pingpong.sh
#
# Capture BACnet/IP traffic while ping_pong_tester.py runs.
#
# Usage:
#   ./scripts//capture_bacnet_pingpong.sh eth0 60
#     -> capture on interface eth0 for 60 seconds
#
# Then open the resulting .pcap in Wireshark and confirm:
#   - You see ReadProperty / WriteProperty traffic
#   - You DO NOT see Who-Is spam for every HTTP request
#

IFACE="${1:-eth0}"
DURATION="${2:-60}"  # seconds
OUTDIR="pcaps"

mkdir -p "${OUTDIR}"

TS="$(date +'%Y%m%d_%H%M%S')"
PCAP_FILE="${OUTDIR}/bacnet_pingpong_${TS}.pcap"

echo "Capturing BACnet/IP on interface '${IFACE}' for ${DURATION}s..."
echo "Output file: ${PCAP_FILE}"
echo

# Requires sudo for most systems
sudo timeout "${DURATION}" tcpdump -i "${IFACE}" udp port 47808 -w "${PCAP_FILE}"

RET=$?

echo
if [ "${RET}" -eq 0 ]; then
  echo "Capture complete. PCAP saved to: ${PCAP_FILE}"
else
  echo "tcpdump exited with status ${RET} (maybe timeout or Ctrl+C)."
  echo "Partial capture (if any) saved to: ${PCAP_FILE}"
fi
