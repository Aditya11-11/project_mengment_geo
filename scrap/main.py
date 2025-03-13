from flask import Flask, request, jsonify
from geopy.distance import geodesic
from datetime import datetime

app = Flask(__name__)

# Global variable to store the geofence data
geofence_data = {
    'latitude_of_center': None,
    'longitude_of_center': None,
    'radius': None
}


def gephync(employee_latitude, employee_longitude):
    if geofence_data['latitude_of_center'] is None or geofence_data['longitude_of_center'] is None or geofence_data['radius'] is None:
        return "Geofence has not been set yet."

    center = (geofence_data['latitude_of_center'], geofence_data['longitude_of_center'])
    employee_location = (employee_latitude, employee_longitude)

    distance = geodesic(center, employee_location).meters

    if distance <= geofence_data['radius']:
        return "Employee is inside the area"
    else:
        return "Employee is outside the area"

@app.route('/api/set_geofence', methods=['POST'])
def set_geofence():
    data = request.get_json()

    latitude_of_center = data.get('lat')
    longitude_of_center = data.get('lon')
    radius = data.get('radius')

    if latitude_of_center is None or longitude_of_center is None or radius is None:
        return jsonify({"error": "Missing latitude, longitude or radius"}), 400

    geofence_data['latitude_of_center'] = latitude_of_center
    geofence_data['longitude_of_center'] = longitude_of_center
    geofence_data['radius'] = radius

    return jsonify({
        "status": "success",
        "message": f"Geofence set at ({latitude_of_center}, {longitude_of_center}) with radius of {radius} meters."
    }), 200

@app.route('/api/check_location', methods=['POST'])
def check_location():
    data = request.get_json()
    # print(data)

    employee_lat = data.get('lat')
    employee_lon = data.get('lon')
    device_info = data.get('topic')
    timestamp=data.get('tst')

    if not employee_lat or not employee_lon:
        return jsonify({"error": "Missing latitude or longitude for employee"})

    result = gephync(employee_lat, employee_lon)

# Convert milliseconds to seconds
    timestamp_s = timestamp / 1000

    # Convert to a datetime object
    dt_object = datetime.fromtimestamp(timestamp_s)

    # Extract date and time
    date = dt_object.strftime('%Y-%m-%d')  # Extracts date in 'YYYY-MM-DD' format
    time = dt_object.strftime('%H:%M:%S')  # Extracts time in 'HH:MM:SS' format

    print(result,device_info,date,time)

    return jsonify({
        "status": "success",
        "message": result,
        "device_info": device_info,
        "date": date,
        "time": time
    }), 200

@app.route('/api/total_employe _time')
def employee_time():
    return jsonify({
        "status": "success", 
        "message": "Employee time"
    }), 200
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)  # Change host and port as necessary
