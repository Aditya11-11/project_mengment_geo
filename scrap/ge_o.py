from geopy.distance import geodesic

# Define geofence center and radius (in meters)

def gephync(employee_latitude, employee_longitude):
    center = (latitude_of_center, longitude_of_center)
    radius = 100  # in meters

    # Employee's current location
    employee_location = (employee_latitude, employee_longitude)

    # Calculate the distance between employee and geofence center
    distance = geodesic(center, employee_location).meters

    # Check if the employee is inside the geofence
    if distance <= radius:
        print("Employee is inside the area")
    else:
        print("Employee is outside the area")



