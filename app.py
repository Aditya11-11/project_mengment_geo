# from flask import Flask, request, jsonify, render_template
# from geopy.distance import geodesic
# from datetime import datetime, timedelta
# import os
# from flask_sqlalchemy import SQLAlchemy

# app = Flask(__name__)

# # Configure SQLAlchemy to use a SQLite database (adjust URI as needed)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employee_location.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)

# # Define the EmployeeLocation model
# class EmployeeLocation(db.Model):
#     __tablename__ = 'employee_locations'
#     id = db.Column(db.Integer, primary_key=True)
#     employeeID = db.Column(db.Text)
#     device_info = db.Column(db.Text)
#     date = db.Column(db.String(10))  # e.g., "YYYY-MM-DD"
#     inside_time = db.Column(db.String(8))  # e.g., "HH:MM:SS"
#     outside_time = db.Column(db.String(8))
#     total_time_spent_inside_geo_fence = db.Column(db.String(8))

# # Initialize the database (creates tables if not already present)
# with app.app_context():
#     db.create_all()

# # Global variables for geofence data
# geofence_data = {
#     'latitude_of_center': None,
#     'longitude_of_center': None,
#     'radius': None
# }

# # Global dictionaries for employee status and latest check result
# employee_status = {}
# last_check_result = {}

# def gephync(employee_latitude, employee_longitude):
#     if (geofence_data['latitude_of_center'] is None or 
#         geofence_data['longitude_of_center'] is None or 
#         geofence_data['radius'] is None):
#         return "Geofence has not been set yet."

#     center = (geofence_data['latitude_of_center'], geofence_data['longitude_of_center'])
#     employee_location = (employee_latitude, employee_longitude)
#     distance = geodesic(center, employee_location).meters

#     if distance <= geofence_data['radius']:
#         return "Employee is inside the area"
#     else:
#         return "Employee is outside the area"

# @app.route('/api/set_geofence', methods=['POST'])
# def set_geofence():
#     data = request.get_json()
#     latitude_of_center = data.get('lat')
#     longitude_of_center = data.get('lon')
#     radius = data.get('radius')

#     if latitude_of_center is None or longitude_of_center is None or radius is None:
#         return jsonify({"error": "Missing latitude, longitude or radius"}), 400

#     geofence_data['latitude_of_center'] = latitude_of_center
#     geofence_data['longitude_of_center'] = longitude_of_center
#     geofence_data['radius'] = radius

#     return jsonify({
#         "status": "success",
#         "message": f"Geofence set at ({latitude_of_center}, {longitude_of_center}) with radius of {radius} meters."
#     }), 200

# @app.route('/api/check_location', methods=['POST'])
# def check_location():
#     data = request.get_json()
#     # print(data)
#     employee_lat = data.get('lat')
#     employee_lon = data.get('lon')
#     device_info = data.get('topic')
#     timestamp = data.get('tst')
    
#     # Extract employee name from device_info (e.g., "owntask/user/emplynameid")
#     employeeID = "Unknown"
#     if device_info and '/' in device_info:
#         parts = device_info.split('/')
#         if len(parts) >= 3:
#             employeeID = parts[2]

#     # if not employee_lat or not employee_lon:
#     #     return jsonify({"error": "Missing latitude or longitude for employee"}), 400

#     # geofence check
#     result = gephync(employee_lat, employee_lon)

#     # Convert timestamp to datetime 
#     if timestamp:
#         try:
#             if len(str(int(timestamp))) > 10:  # milli
#                 timestamp_s = timestamp / 1000
#             else:
#                 timestamp_s = timestamp
#             dt_object = datetime.fromtimestamp(timestamp_s)
#             date = dt_object.strftime('%Y-%m-%d')
#             time_str = dt_object.strftime('%H:%M:%S')
#         except Exception as e:
#             print(f"Error processing timestamp: {e}")
#             dt_object = datetime.now()
#             date = dt_object.strftime('%Y-%m-%d')
#             time_str = dt_object.strftime('%H:%M:%S')
#     else:
#         dt_object = datetime.now()
#         date = dt_object.strftime('%Y-%m-%d')
#         time_str = dt_object.strftime('%H:%M:%S')

#     # Check if employee is inside based on the geofence check result
#     is_inside = "inside" in result.lower()

#     # Query for an "open" record (inside_time set, outside_time still NULL) for this employee and date
#     open_record = EmployeeLocation.query.filter(
#         EmployeeLocation.employeeID == employeeID,
#         EmployeeLocation.date == date,
#         EmployeeLocation.inside_time != None,
#         EmployeeLocation.outside_time == None
#     ).first()

#     if is_inside:
#         if open_record:
#             # Employee already recorded as inside
#             employee_status[employeeID] = "inside"
#         else:
#             # New entrycreate a new record with inside_time
#             employee_status[employeeID] = "inside"
#             new_record = EmployeeLocation(
#                 employeeID=employeeID,
#                 device_info=device_info,
#                 date=date,
#                 inside_time=time_str,
#                 outside_time=None,
#                 total_time_spent_inside_geo_fence="00:00:00"
#             )
#             db.session.add(new_record)
#             db.session.commit()
#     else:
#         if open_record:
#             # Employee was inside andleft update the record
#             inside_time = open_record.inside_time
#             record_date = open_record.date
#             try:
#                 inside_dt = datetime.strptime(f"{record_date} {inside_time}", "%Y-%m-%d %H:%M:%S")
#                 outside_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
#                 diff = outside_dt - inside_dt
#                 total_seconds = int(diff.total_seconds())
#                 hours, remainder = divmod(total_seconds, 3600)
#                 minutes, seconds = divmod(remainder, 60)
#                 total_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
#             except Exception as e:
#                 print(f"Error calculating time difference: {e}")
#                 total_time_str = "00:00:00"
            
#             open_record.outside_time = time_str
#             open_record.total_time_spent_inside_geo_fence = total_time_str
#             db.session.commit()
#             employee_status[employeeID] = "outside"
#         else:
#             employee_status[employeeID] = "outside"

#     result_json = {
#         "status": "success",
#         "message": result,
#         "device_info": device_info,
#         "employeeID": employeeID,
#         "date": date,
#         "time": time_str,
#         "status_changed": True
#     }
    
#     # Save the latest result for retrieval
#     last_check_result[employeeID] = result_json
#     # print(result_json)

#     return jsonify(result_json), 200

# @app.route('/api/get_location_data', methods=['GET'])
# def get_location_data():
#     filter_date = request.args.get('date')
    
#     if filter_date:
#         records = EmployeeLocation.query.filter_by(date=filter_date).all()
#     else:
#         records = EmployeeLocation.query.all()
    
#     result = []
#     for record in records:
#         result.append({
#             'id': record.id,
#             'employeeID': record.employeeID,
#             'device_info': record.device_info,
#             'date': record.date,
#             'inside_time': record.inside_time,
#             'outside_time': record.outside_time,
#             'total_time_spent_inside_geo_fence': record.total_time_spent_inside_geo_fence
#         })
#         # print(result)
    
#     return jsonify({
#         "status": "success",
#         "data": result
#     }), 200

# @app.route('/api/delete_location_data/<int:id>', methods=['DELETE'])
# def delete_location_data(id):
#     record = EmployeeLocation.query.get(id)
#     if not record:
#         return jsonify({
#             "status": "error",
#             "message": f"Record with ID {id} not found"
#         }), 404
#     db.session.delete(record)
#     db.session.commit()
#     return jsonify({
#         "status": "success",
#         "message": f"Record with ID {id} deleted successfully"
#     }), 200

# @app.route('/api/get_employee_statuses', methods=['GET'])
# def get_employee_statuses():
#     employeeID = request.args.get('employeeID')
#     date_filter = request.args.get('date')  #formatYYYY-MM-DD
#     id_filter=request.args.get('id')

#     if not employeeID:
#         return jsonify({"error": "Employee name is required as query parameter"}), 400

#     if date_filter:
#         records = EmployeeLocation.query.filter_by(employeeID=employeeID, date=date_filter).all()
#     if id_filter:
#         records = EmployeeLocation.query.filter_by(id=id_filter).all()
#     else:
#         records = EmployeeLocation.query.filter_by(employeeID=employeeID).all()
    
#     results = []
#     for record in records:
#         results.append({
#             'id': record.id,
#             'employeeID': record.employeeID,
#             'device_info': record.device_info,
#             'date': record.date,
#             'inside_time': record.inside_time,
#             'outside_time': record.outside_time,
#             'total_time_spent_inside_geo_fence': record.total_time_spent_inside_geo_fence
#         })
    
#     return jsonify({
#         "status": "success",
#         "data": results
#     }), 200

# @app.route('/api/latest_location', methods=['GET'])
# def latest_location():
#     employeeID = request.args.get('employeeID')
#     if not employeeID:
#         return jsonify({"error": "Employee name is required as query parameter"}), 400
#     result = last_check_result.get(employeeID)
#     if result:
#         return jsonify(result), 200
#     else:
#         return jsonify({"error": f"No live data found for employee {employeeID}"}), 404

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)
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
    employeeID = db.Column(db.Text)
    device_info = db.Column(db.Text)
    date = db.Column(db.String(10))  # e.g., "YYYY-MM-DD"
    inside_time = db.Column(db.String(8))  # e.g., "HH:MM:SS"
    outside_time = db.Column(db.String(8))
    # This field is a string in HH:MM:SS format representing the cumulative time
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
    
    # Extract employeeID from device_info (e.g., "owntask/user/emplynameid")
    employeeID = "Unknown"
    if device_info and '/' in device_info:
        parts = device_info.split('/')
        if len(parts) >= 3:
            employeeID = parts[2]

    # geofence check
    result = gephync(employee_lat, employee_lon)

    # Convert timestamp to datetime
    if timestamp:
        try:
            # If timestamp is in milliseconds, convert to seconds
            if len(str(int(timestamp))) > 10:
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

    is_inside = "inside" in result.lower()

    # Query for an "open" record for this employee and date (record where outside_time is still NULL)
    open_record = EmployeeLocation.query.filter(
        EmployeeLocation.employeeID == employeeID,
        EmployeeLocation.date == date,
        EmployeeLocation.inside_time != None,
        EmployeeLocation.outside_time == None
    ).first()

    if is_inside:
        if not open_record:
            # Create a new record if none exists
            new_record = EmployeeLocation(
                employeeID=employeeID,
                device_info=device_info,
                date=date,
                inside_time=time_str,
                outside_time=None,
                total_time_spent_inside_geo_fence="00:00:00"
            )
            db.session.add(new_record)
            db.session.commit()
        employee_status[employeeID] = "inside"
    else:
        if open_record:
            try:
                inside_dt = datetime.strptime(f"{open_record.date} {open_record.inside_time}", "%Y-%m-%d %H:%M:%S")
                outside_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
                diff = outside_dt - inside_dt
                total_seconds = int(diff.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                session_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except Exception as e:
                print(f"Error calculating time difference: {e}")
                session_time_str = "00:00:00"
            
            # Update the record: mark outside_time and update cumulative total
            # First, convert existing total (if any) from HH:MM:SS to seconds.
            def time_to_seconds(t_str):
                try:
                    h, m, s = map(int, t_str.split(':'))
                    return h * 3600 + m * 60 + s
                except Exception:
                    return 0

            existing_seconds = time_to_seconds(open_record.total_time_spent_inside_geo_fence)
            new_total_seconds = existing_seconds + total_seconds
            aggregated_time = f"{new_total_seconds // 3600:02d}:{(new_total_seconds % 3600) // 60:02d}:{new_total_seconds % 60:02d}"
            
            open_record.outside_time = time_str
            open_record.total_time_spent_inside_geo_fence = aggregated_time
            db.session.commit()
            employee_status[employeeID] = "outside"
        else:
            employee_status[employeeID] = "outside"

    result_json = {
        "status": "success",
        "message": result,
        "device_info": device_info,
        "employeeID": employeeID,
        "date": date,
        "time": time_str,
        "status_changed": True
    }
    
    last_check_result[employeeID] = result_json
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
            'employeeID': record.employeeID,
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

# --- New Aggregated Endpoint for Employee Statuses ---
@app.route('/api/get_employee_statuses', methods=['GET'])
def get_employee_statuses():
    """
    Retrieve location records for an employee. If a date is provided, the endpoint
    calculates the aggregated total inside time (summing all records' total_time_spent_inside_geo_fence)
    for that employee on that day.
    
    Query parameters:
      - employeeID (required)
      - date (optional, format "YYYY-MM-DD")
      - id (optional, for a specific record)
    """
    employeeID = request.args.get('employeeID')
    date_filter = request.args.get('date')  # e.g., "2025-03-25"
    id_filter = request.args.get('id')

    if not employeeID:
        return jsonify({"error": "Employee name is required as query parameter"}), 400

    # If id_filter is provided, ignore date_filter and fetch by record id.
    if id_filter:
        records = EmployeeLocation.query.filter_by(id=id_filter).all()
    elif date_filter:
        records = EmployeeLocation.query.filter_by(employeeID=employeeID, date=date_filter).all()
    else:
        records = EmployeeLocation.query.filter_by(employeeID=employeeID).all()
    
    # Aggregate total time for the provided date (if date_filter is provided)
    aggregated_total = "00:00:00"
    if date_filter:
        total_seconds = 0
        def time_to_seconds(t_str):
            try:
                h, m, s = map(int, t_str.split(':'))
                return h * 3600 + m * 60 + s
            except Exception:
                return 0
        # Sum the total_time_spent_inside_geo_fence for all records for that day.
        for record in records:
            total_seconds += time_to_seconds(record.total_time_spent_inside_geo_fence)
        aggregated_total = f"{total_seconds // 3600:02d}:{(total_seconds % 3600) // 60:02d}:{total_seconds % 60:02d}"

    results = []
    for record in records:
        results.append({
            'id': record.id,
            'employeeID': record.employeeID,
            'device_info': record.device_info,
            'date': record.date,
            'inside_time': record.inside_time,
            'outside_time': record.outside_time,
            'total_time_spent_inside_geo_fence': record.total_time_spent_inside_geo_fence
        })
    
    response_data = {
        "status": "success",
        "records": results
    }
    if date_filter:
        response_data["aggregated_total_inside_time"] = aggregated_total

    return jsonify(response_data), 200

@app.route('/api/latest_location', methods=['GET'])
def latest_location():
    employeeID = request.args.get('employeeID')
    if not employeeID:
        return jsonify({"error": "Employee name is required as query parameter"}), 400
    result = last_check_result.get(employeeID)
    if result:
        return jsonify(result), 200
    else:
        return jsonify({"error": f"No live data found for employee {employeeID}"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
