from flask import Flask, render_template, redirect, flash
import requests
import os
import base64
import logging
import time
from statistics import mean, median, stdev
from colorama import Fore, Style, init
import threading

# Initialize and setup
init(autoreset=True)
app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Constants and environment variables
BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN', 'YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo=') 
WEB_SERVER_PORT = int(os.getenv('PORT', 10000))
MAX_DATA_POINTS = 10

# Data storage and threading setup
data_storage = {
    "TDS": [],
    "EC": [],
    "Temperature": [],
    "Humidity": []
}
data_lock = threading.Lock()
stop_monitoring = threading.Event()

# Logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Decode Blynk token
try:
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')
except Exception as e:
    logger.warning(f"Failed to decode token: {e}")
    decoded_token = BLYNK_AUTH_TOKEN

# Consolidated API endpoint
blynk_url = f'https://blynk.cloud/external/api/get?token={decoded_token}'
sensor_pins = {
    "TDS": "V0",
    "EC": "V2",
    "Temperature": "V3",
    "Humidity": "V7"
}


def fetch_all_data():
    """Fetch all sensor data in a single request."""
    try:
        pins = ",".join(sensor_pins.values())
        response = requests.get(f"{blynk_url}&{pins}", timeout=5)
        response.raise_for_status()
        data = response.json()

        with data_lock:
            for sensor, pin in sensor_pins.items():
                if pin in data:
                    value = float(data[pin])
                    data_storage[sensor].append(value)
                    if len(data_storage[sensor]) > MAX_DATA_POINTS:
                        data_storage[sensor].pop(0)
        return data
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}")
        return None


def calculate_statistics():
    """Calculate statistics for all sensors."""
    with data_lock:
        stats = {
            sensor: {
                "mean": mean(values),
                "median": median(values),
                "stdev": stdev(values) if len(values) > 1 else 0
            }
            for sensor, values in data_storage.items()
            if len(values) >= MAX_DATA_POINTS
        }
    return stats


def measure_network_usage():
    """Measure the total network usage."""
    try:
        total_request_size = len(blynk_url.encode('utf-8'))
        response = requests.get(blynk_url)
        response.raise_for_status()
        total_response_size = len(response.content)
        total_usage_mb = (total_request_size + total_response_size) / (1024 * 1024)
        logger.info(f"Network usage: {total_usage_mb:.2f} MB")
        return total_usage_mb
    except requests.exceptions.RequestException as e:
        logger.error(f"Error measuring network usage: {e}")
        return 0


def network_usage_monitor():
    """Thread to monitor network usage periodically."""
    while not stop_monitoring.is_set():
        measure_network_usage()
        time.sleep(5)


@app.route("/")
def index():
    # Fetch sensor data
    fetch_all_data()
    calculating = any(len(values) < MAX_DATA_POINTS for values in data_storage.values())
    
    # Prepare stats if data is sufficient
    stats = calculate_statistics() if not calculating else None
    data_count = {sensor: len(values) for sensor, values in data_storage.items()}

    return render_template(
        "index.html",
        stats=stats,
        calculating=calculating,
        data_count=data_count,
        data_storage=data_storage
    )


@app.route("/reset", methods=["POST"])
def reset_data():
    with data_lock:
        for key in data_storage:
            data_storage[key] = []
    flash("Data has been reset successfully!", "success")
    return redirect("/")


@app.route("/shutdown", methods=["POST"])
def shutdown_monitor():
    stop_monitoring.set()
    flash("Network monitoring stopped.", "success")
    return redirect("/")


@app.before_first_request
def initialize():
    monitor_thread = threading.Thread(target=network_usage_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=WEB_SERVER_PORT, debug=True)