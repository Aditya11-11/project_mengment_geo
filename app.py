from flask import Flask, request, jsonify, render_template
from geopy.distance import geodesic
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

# Database setup
DB_PATH = 'employee_location.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employee_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employname TEXT,
        device_info TEXT,
        date TEXT,
        inside_time TEXT,
        outside_time TEXT,
        total_time_spent_inside_geo_fence TEXT
    )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Global variable to store the geofence data
geofence_data = {
    'latitude_of_center': None,
    'longitude_of_center': None,
    'radius': None
}

# Dictionary to track employee status (inside/outside)
employee_status = {}
# Global dictionary to store the latest result per employee
last_check_result = {}


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

    employee_lat = data.get('lat')
    employee_lon = data.get('lon')
    device_info = data.get('topic')
    timestamp = data.get('tst')
    
    # Extract employee name from device_info (format: owntask/user/employname/employee_id)
    employname = "Unknown"
    if device_info and '/' in device_info:
        parts = device_info.split('/')
        if len(parts) >= 3:
            employname = parts[2]

    if not employee_lat or not employee_lon:
        return jsonify({"error": "Missing latitude or longitude for employee"})

    # Check geofence status
    result = gephync(employee_lat, employee_lon)

    # Convert timestamp to datetime
    if timestamp:
        try:
            if len(str(int(timestamp))) > 10:  # in milliseconds
                timestamp_s = timestamp / 1000
            else:  # already in seconds
                timestamp_s = timestamp
            dt_object = datetime.fromtimestamp(timestamp_s)
            date = dt_object.strftime('%Y-%m-%d')
            time_str = dt_object.strftime('%H:%M:%S')
        except Exception as e:
            print(f"Error processing timestamp: {e}")
            dt_object = datetime.now()
            date = dt_object.strftime('%Y-%m-%d')
            time_str = dt_object.strftime('%H:%M:%S')
    else:
        dt_object = datetime.now()
        date = dt_object.strftime('%Y-%m-%d')
        time_str = dt_object.strftime('%H:%M:%S')

    # Check if the employee is inside or outside
    is_inside = "inside" in result.lower()

    # Query DB for an "open" record for the current date (inside_time set, outside_time still NULL)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, inside_time, date 
        FROM employee_locations 
        WHERE employname = ? AND date = ? AND inside_time IS NOT NULL AND outside_time IS NULL
        ''', (employname, date))
    open_record = cursor.fetchone()
    conn.close()

    if is_inside:
        # Employee is inside
        if open_record:
            # Already has an open record – do not insert a new one.
            employee_status[employname] = "inside"
        else:
            # New entry: Employee is entering; create a new record with inside_time.
            employee_status[employname] = "inside"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO employee_locations 
                (employname, device_info, date, inside_time, outside_time, total_time_spent_inside_geo_fence)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (employname, device_info, date, time_str, None, "00:00:00"))
            conn.commit()
            conn.close()
    else:
        # Employee is outside
        if open_record:
            # Employee was inside and now left: update the open record.
            inside_time = open_record['inside_time']
            record_date = open_record['date']
            try:
                inside_dt = datetime.strptime(f"{record_date} {inside_time}", "%Y-%m-%d %H:%M:%S")
                outside_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
                diff = outside_dt - inside_dt
                total_seconds = int(diff.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                total_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except Exception as e:
                print(f"Error calculating time difference: {e}")
                total_time_str = "00:00:00"
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE employee_locations 
                SET outside_time = ?, total_time_spent_inside_geo_fence = ?
                WHERE id = ?
                ''', (time_str, total_time_str, open_record['id']))
            conn.commit()
            conn.close()
            employee_status[employname] = "outside"
        else:
            # Employee is outside and no open record exists: do nothing.
            employee_status[employname] = "outside"

    # Prepare the result JSON
    result_json = {
        "status": "success",
        "message": result,
        "device_info": device_info,
        "employname": employname,
        "date": date,
        "time": time_str,
        "status_changed": True  # You can further customize this flag if needed.
    }
    
    # Store the result by employee name in the global dictionary for live data retrieval
    last_check_result[employname] = result_json

    return jsonify(result_json), 200


@app.route('/api/get_location_data', methods=['GET'])
def get_location_data():
    # Get filter date from query parameters if provided
    filter_date = request.args.get('date')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    if filter_date:
        # Filter by date if provided
        cursor.execute('SELECT * FROM employee_locations WHERE date = ?', (filter_date,))
    else:  
        # Get all records if no date filter
        cursor.execute('SELECT * FROM employee_locations')
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert rows to list of dictionaries
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'employname': row['employname'],
            'device_info': row['device_info'],
            'date': row['date'],
            'inside_time': row['inside_time'],
            'outside_time': row['outside_time'],
            'total_time_spent_inside_geo_fence': row['total_time_spent_inside_geo_fence']
        })
    
    return jsonify({
        "status": "success",
        "data": result
    }), 200

@app.route('/api/delete_location_data/<int:id>', methods=['DELETE'])
def delete_location_data(id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the record exists
        cursor.execute('SELECT id FROM employee_locations WHERE id = ?', (id,))
        record = cursor.fetchone()
        
        if not record:
            conn.close()
            return jsonify({
                "status": "error",
                "message": f"Record with ID {id} not found"
            }), 404
        
        # Delete the record
        cursor.execute('DELETE FROM employee_locations WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Record with ID {id} deleted successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error deleting record: {str(e)}"
        }), 500

@app.route('/api/get_employee_statuses', methods=['GET'])
def get_employee_statuses():
    employname = request.args.get('employname')
    date_filter = request.args.get('date')  # optional, format: YYYY-MM-DD

    if not employname:
        return jsonify({"error": "Employee name is required as query parameter"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()
    
    if date_filter:
        # Retrieve records for the employee on the given date
        cursor.execute('SELECT * FROM employee_locations WHERE employname = ? AND date = ?', (employname, date_filter))
    else:
        # Retrieve all records for the employee
        cursor.execute('SELECT * FROM employee_locations WHERE employname = ?', (employname,))
        
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        results.append({
            'id': row['id'],
            'employname': row['employname'],
            'device_info': row['device_info'],
            'date': row['date'],
            'inside_time': row['inside_time'],
            'outside_time': row['outside_time'],
            'total_time_spent_inside_geo_fence': row['total_time_spent_inside_geo_fence']
        })
    
    return jsonify({
        "status": "success",
        "data": results
    }), 200


@app.route('/api/latest_location', methods=['GET'])
def latest_location():
    employname = request.args.get('employname')
    if not employname:
        return jsonify({"error": "Employee name is required as query parameter"}), 400
    # Retrieve the latest result for that employee
    result = last_check_result.get(employname)
    if result:
        return jsonify(result), 200
    else:
        return jsonify({"error": f"No live data found for employee {employname}"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Change host and port as necessary































































