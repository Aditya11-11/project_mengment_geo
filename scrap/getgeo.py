from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/location', methods=['POST'])
def track_location():
    # Log the headers and the raw request body for debugging
    print(f"Received Headers: {request.headers}")
    print(f"Received Raw JSON Data: {request.data}")
    data = request.get_json()

    # Log the parsed JSON data for debugging
    print(f"Parsed JSON Data: {data}")

    # Process all fields
    latitude = data.get('lat')
    longitude = data.get('lon')
    timestamp = data.get('tst')

    # Optionally, store the data in the database or process further
    print(f"Received location data: Latitude={latitude}, Longitude={longitude}, Timestamp={timestamp}")

    # Return a success response
    return jsonify({
        "status": "success",
        "message": "Location data received",
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Change host and port as necessary
