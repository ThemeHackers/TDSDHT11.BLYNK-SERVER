from flask import Flask, render_template
import requests
import os
import base64
import logging
from statistics import mean, median, stdev

app = Flask(__name__)

# Environment variables and Blynk setup
BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN', 'YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo=') 
BLYNK_TDS_PIN = "V0"
BLYNK_EC_PIN = "V2"
BLYNK_TEMPERATURE_PIN = "V3"
BLYNK_HUMIDITY_PIN = "V7"

data_storage = {
    "TDS": [],
    "EC": [],
    "Temperature": [],
    "Humidity": []
}
MAX_DATA_POINTS = 10  # Threshold for storing data

def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return float(response.text.strip())  # Ensure numeric conversion
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None
    except ValueError:
        print(f"Invalid data format received from {url}")
        return None

try:
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')
    logging.debug(f"Decoded Token: {decoded_token}")
except Exception as e:
    logging.warning(f"Failed to decode token: {e}")
    decoded_token = BLYNK_AUTH_TOKEN

@app.route("/")
def index():
    # URLs to fetch data
    tds_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}'
    ec_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}'
    temperature_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}'
    humidity_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}'

    # Fetch sensor values
    tds_value = fetch_data(tds_url)
    ec_value = fetch_data(ec_url)
    temperature_value = fetch_data(temperature_url)
    humidity_value = fetch_data(humidity_url)

    # Add new data to storage, removing the oldest if storage exceeds MAX_DATA_POINTS
    if tds_value is not None:
        data_storage["TDS"].append(tds_value)
        if len(data_storage["TDS"]) > MAX_DATA_POINTS:
            data_storage["TDS"].pop(0)

    if ec_value is not None:
        data_storage["EC"].append(ec_value)
        if len(data_storage["EC"]) > MAX_DATA_POINTS:
            data_storage["EC"].pop(0)

    if temperature_value is not None:
        data_storage["Temperature"].append(temperature_value)
        if len(data_storage["Temperature"]) > MAX_DATA_POINTS:
            data_storage["Temperature"].pop(0)

    if humidity_value is not None:
        data_storage["Humidity"].append(humidity_value)
        if len(data_storage["Humidity"]) > MAX_DATA_POINTS:
            data_storage["Humidity"].pop(0)

    # Check if we have enough data for calculation (10 data points)
    calculating = any(len(values) < MAX_DATA_POINTS for values in data_storage.values())

    if not calculating:
        # Calculate statistics for each sensor once we have 10 data points
        stats = {
            sensor: {
                "mean": mean(values),
                "median": median(values),
                "stdev": stdev(values) if len(values) > 1 else 0
            }
            for sensor, values in data_storage.items()
        }
    else:
        stats = None  # Not enough data yet for calculations

    # Count the number of data points stored for each sensor
    data_count = {sensor: len(values) for sensor, values in data_storage.items()}

    return render_template(
        "index.html",
        tds=tds_value,
        ec=ec_value,
        temperature=temperature_value,
        humidity=humidity_value,
        stats=stats,
        calculating=calculating,
        data_count=data_count  # Pass data count to template
    )


if __name__ == "__main__":
    app.run(debug=True)
