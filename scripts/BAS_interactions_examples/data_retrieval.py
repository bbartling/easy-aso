import requests
import json

# Endpoint URL
url = 'http://192.168.0.102:8000/graphql'

def make_graphql_query(query: str):
    # Headers
    headers = {
        'Content-Type': 'application/json'
    }

    # Make the POST request
    response = requests.post(url, headers=headers, json={'query': query})

    # Parse and return the response
    if response.status_code == 200:
        return json.dumps(response.json(), indent=4)
    else:
        return f"Query failed with status code {response.status_code}. Query: {query}"

# Prepare and execute queries for each field
fields = [
    'averageZoneAirTemperatureSensor',
    'lowestZoneAirTemperatureSensorName',
    'lowestZoneAirTemperatureSensorReading',
    'highestZoneAirTemperatureSensorName',
    'highestZoneAirTemperatureSensorReading',
    'lowestZoneAirTemperatureSensorInfo',
    'highestZoneAirTemperatureSensorInfo',
    'averageAHUAirflowSensor',
    'averageChillerLoadSensor'
]

for field in fields:
    query = f'{{ {field} }}'
    print(f"\n{field.title()}:")
    print(make_graphql_query(query))
