import requests
import random
import time
import csv


"""
This script posts ALL commandable BACnet points every 0.1s to the FastAPI endpoint,
randomizing AVs as floats and BVs as true/false. It then reads back from the server
to verify the current writable point values.

$ python3 -m venv env
$ . env/bin/activate
$ pip install requests
$ python3 client_tester.py
"""


csv_path = "./csv_file/chiller_points.csv"
post_url = "http://localhost:8080/update"
get_url = "http://localhost:8080/read"

# Load only points with Commandable = N
points = {}  # name: "AV" or "BV"

with open(csv_path, newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    count = 0
    for row in reader:
        print(row)  # DEBUG: print every row
        name = row.get("Name", "").strip()
        point_type = row.get("PointType", "").strip().upper()
        commandable = row.get("Commandable", "").strip().upper()

        # Only include Commandable=N and valid AV/BV
        if name and commandable == "N" and point_type in {"AV", "BV"}:
            points[name] = point_type
            count += 1

    print(f"Found {count} non-commandable points")
print(f"Loaded {len(points)} non-commandable points")


while True:
    payload = {}

    for name, point_type in points.items():
        if point_type == "AV":
            payload[name] = round(random.uniform(0, 100), 2)
        elif point_type == "BV":
            payload[name] = random.choice([True, False])

    try:
        post_response = requests.post(post_url, json=payload)
        print(
            f"[POST] Status: {post_response.status_code} | Sent {len(payload)} points"
        )

        get_response = requests.get(get_url)
        print(f"[GET]  BACnet Writeables: {get_response.text}")
    except Exception as e:
        print(f"Error communicating with server: {e}")

    time.sleep(0.1)
