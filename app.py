from flask import Flask, request, jsonify, render_template
from geopy.distance import geodesic
from datetime import datetime, timedelta
import os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure SQLAlchemy to use a SQLite database (adjust URI as needed)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employee_location.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the EmployeeLocation model
class EmployeeLocation(db.Model):
    __tablename__ = 'employee_locations'
    id = db.Column(db.Integer, primary_key=True)
    employname = db.Column(db.Text)
    device_info = db.Column(db.Text)
    date = db.Column(db.String(10))  # e.g., "YYYY-MM-DD"
    inside_time = db.Column(db.String(8))  # e.g., "HH:MM:SS"
    outside_time = db.Column(db.String(8))
    total_time_spent_inside_geo_fence = db.Column(db.String(8))

# Initialize the database (creates tables if not already present)
with app.app_context():
    db.create_all()

# Global variables for geofence data
geofence_data = {
    'latitude_of_center': None,
    'longitude_of_center': None,
    'radius': None
}

# Global dictionaries for employee status and latest check result
employee_status = {}
last_check_result = {}

def gephync(employee_latitude, employee_longitude):
    if (geofence_data['latitude_of_center'] is None or 
        geofence_data['longitude_of_center'] is None or 
        geofence_data['radius'] is None):
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
    
    # Extract employee name from device_info (e.g., "owntask/user/emplynameid")
    employname = "Unknown"
    if device_info and '/' in device_info:
        parts = device_info.split('/')
        if len(parts) >= 3:
            employname = parts[2]

    if not employee_lat or not employee_lon:
        return jsonify({"error": "Missing latitude or longitude for employee"}), 400

    # geofence check
    result = gephync(employee_lat, employee_lon)

    # Convert timestamp to datetime 
    if timestamp:
        try:
            if len(str(int(timestamp))) > 10:  # milli
                timestamp_s = timestamp / 1000
            else:
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

    # Check if employee is inside based on the geofence check result
    is_inside = "inside" in result.lower()

    # Query for an "open" record (inside_time set, outside_time still NULL) for this employee and date
    open_record = EmployeeLocation.query.filter(
        EmployeeLocation.employname == employname,
        EmployeeLocation.date == date,
        EmployeeLocation.inside_time != None,
        EmployeeLocation.outside_time == None
    ).first()

    if is_inside:
        if open_record:
            # Employee already recorded as inside
            employee_status[employname] = "inside"
        else:
            # New entrycreate a new record with inside_time
            employee_status[employname] = "inside"
            new_record = EmployeeLocation(
                employname=employname,
                device_info=device_info,
                date=date,
                inside_time=time_str,
                outside_time=None,
                total_time_spent_inside_geo_fence="00:00:00"
            )
            db.session.add(new_record)
            db.session.commit()
    else:
        if open_record:
            # Employee was inside andleft update the record
            inside_time = open_record.inside_time
            record_date = open_record.date
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
            
            open_record.outside_time = time_str
            open_record.total_time_spent_inside_geo_fence = total_time_str
            db.session.commit()
            employee_status[employname] = "outside"
        else:
            employee_status[employname] = "outside"

    result_json = {
        "status": "success",
        "message": result,
        "device_info": device_info,
        "employname": employname,
        "date": date,
        "time": time_str,
        "status_changed": True
    }
    
    # Save the latest result for retrieval
    last_check_result[employname] = result_json

    return jsonify(result_json), 200

@app.route('/api/get_location_data', methods=['GET'])
def get_location_data():
    filter_date = request.args.get('date')
    
    if filter_date:
        records = EmployeeLocation.query.filter_by(date=filter_date).all()
    else:
        records = EmployeeLocation.query.all()
    
    result = []
    for record in records:
        result.append({
            'id': record.id,
            'employname': record.employname,
            'device_info': record.device_info,
            'date': record.date,
            'inside_time': record.inside_time,
            'outside_time': record.outside_time,
            'total_time_spent_inside_geo_fence': record.total_time_spent_inside_geo_fence
        })
    
    return jsonify({
        "status": "success",
        "data": result
    }), 200

@app.route('/api/delete_location_data/<int:id>', methods=['DELETE'])
def delete_location_data(id):
    record = EmployeeLocation.query.get(id)
    if not record:
        return jsonify({
            "status": "error",
            "message": f"Record with ID {id} not found"
        }), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": "success",
        "message": f"Record with ID {id} deleted successfully"
    }), 200

@app.route('/api/get_employee_statuses', methods=['GET'])
def get_employee_statuses():
    employname = request.args.get('employname')
    date_filter = request.args.get('date')  #formatYYYY-MM-DD

    if not employname:
        return jsonify({"error": "Employee name is required as query parameter"}), 400

    if date_filter:
        records = EmployeeLocation.query.filter_by(employname=employname, date=date_filter).all()
    else:
        records = EmployeeLocation.query.filter_by(employname=employname).all()
    
    results = []
    for record in records:
        results.append({
            'id': record.id,
            'employname': record.employname,
            'device_info': record.device_info,
            'date': record.date,
            'inside_time': record.inside_time,
            'outside_time': record.outside_time,
            'total_time_spent_inside_geo_fence': record.total_time_spent_inside_geo_fence
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
    result = last_check_result.get(employname)
    if result:
        return jsonify(result), 200
    else:
        return jsonify({"error": f"No live data found for employee {employname}"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
