import requests
import time
import json

# Set the base URL
base_url = "http://localhost:5000"

# Step 1: Set up the geofence
geofence_data = {
    "lat": 40.7128,
    "lon": -74.0060,
    "radius": 1000
}
response = requests.post(f"{base_url}/api/set_geofence", json=geofence_data)
print("Geofence setup response:", response.json())

# Step 2: Simulate employee entering geofence
enter_data = {
    "lat": 40.7130,
    "lon": -74.0062,
    "topic": "owntask/user/john",
    "tst": int(time.time())  # Current time in seconds
}
print(f"Sending enter data with timestamp: {enter_data['tst']}")
response = requests.post(f"{base_url}/api/check_location", json=enter_data)
try:
    print("Enter geofence response:", response.json())
except json.JSONDecodeError:
    print("Error decoding JSON response:", response.text)
    print("Status code:", response.status_code)

# Wait for a few seconds
print("Waiting 10 seconds...")
time.sleep(10)

# Step 3: Simulate employee exiting geofence
exit_data = {
    "lat": 40.7500,
    "lon": -74.1000,
    "topic": "owntask/user/john",
    "tst": int(time.time())  # Current time in seconds
}
print(f"Sending exit data with timestamp: {exit_data['tst']}")
response = requests.post(f"{base_url}/api/check_location", json=exit_data)
try:
    print("Exit geofence response:", response.json())
except json.JSONDecodeError:
    print("Error decoding JSON response:", response.text)
    print("Status code:", response.status_code)

# Step 4: Retrieve the data to verify
response = requests.get(f"{base_url}/api/get_location_data")
try:
    data = response.json()
    print("Retrieved data:", json.dumps(data, indent=2))
except json.JSONDecodeError:
    print("Error decoding JSON response:", response.text)
    print("Status code:", response.status_code)