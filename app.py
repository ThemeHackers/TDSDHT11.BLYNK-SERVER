from flask import Flask, render_template, redirect, flash
import requests
import os
import base64
import logging
import time
from statistics import mean, median, stdev
from colorama import Fore, Style, init
import threading

init(autoreset=True)
app = Flask(__name__)
app.secret_key = os.urandom(24).hex()  

BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN', 'YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo=') 
BLYNK_TDS_PIN = "V0"
BLYNK_EC_PIN = "V7"
BLYNK_TEMPERATURE_PIN = "V2"
BLYNK_HUMIDITY_PIN = "V3"
WEB_SERVER_PORT = int(os.environ.get('PORT', 10000))

data_storage = {
    "TDS": [],
    "EC": [],
    "Temperature": [],
    "Humidity": []
}
MAX_DATA_POINTS = 200
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()])
logger = logging.getLogger(__name__)


data_lock = threading.Lock()
log_lock = threading.Lock()
data_send_count = 0
def fetch_data(url, sensor_name):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = float(response.text.strip())
     
        if data < 0 or data > 1000: 
            raise ValueError(f"Invalid data value for {sensor_name}: {data}")
        
        return data
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"Error fetching data from {sensor_name}: {e}")
        return None

def network_usage_monitor():
    while True:
        try:
            with log_lock:
                measure_network_usage(tds_url, ec_url, temperature_url, humidity_url)
            time.sleep(5)
        except Exception as e:
            with log_lock:
                logger.error(f"Error in network usage monitor: {e}")
            break

def measure_network_usage(*urls):
    total_request_size = 0
    total_response_size = 0
    for url in urls:
        try:
            request_size = len(url.encode('utf-8'))
            total_request_size += request_size
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            response_size = len(response.content)
            total_response_size += response_size
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL: {url}, Error: {e}")

    total_size = total_request_size + total_response_size
    total_size_mb = total_size / (1024 * 1024) 
    return total_size_mb

def calculate_stats(sensor_data):
    if len(sensor_data) > 1:
        return {
            "mean": mean(sensor_data),
            "median": median(sensor_data),
            "stdev": stdev(sensor_data)
        }
    else:
        return {
            "mean": mean(sensor_data),
            "median": median(sensor_data),
            "stdev": 0
        }

def c_hardware():
    url = 'https://blynk.cloud/external/api/isHardwareConnected?token='
    retries = 3
    for _ in range(retries):
        response = requests.get(url + decoded_token)
        if response.text == "false":
            print(Fore.GREEN + "The hardware device is connected.......")
            start_network_monitoring()
            app.run(host='0.0.0.0', port=WEB_SERVER_PORT, debug=False)
            return
        else:
            print(Fore.RED + f"Attempt {_ + 1}: The hardware device is not connected......")
            time.sleep(5)
    exit(1)

def start_network_monitoring():
    monitor_thread = threading.Thread(target=network_usage_monitor)
    monitor_thread.daemon = True 
    monitor_thread.start()


def update_data_storage(sensor, value):
    with data_lock:
        data_storage[sensor].append(value)
        if len(data_storage[sensor]) > MAX_DATA_POINTS:
            data_storage[sensor].pop(0)

@app.route("/")
def index():
    global data_send_count
    tds_value = fetch_data(tds_url, "TDS")
    ec_value = fetch_data(ec_url, "EC")
    temperature_value = fetch_data(temperature_url, "Temperature")
    humidity_value = fetch_data(humidity_url, "Humidity")
    
    if tds_value is not None:
        update_data_storage("TDS", tds_value)

    if ec_value is not None:
        update_data_storage("EC", ec_value)

    if temperature_value is not None:
        update_data_storage("Temperature", temperature_value)

    if humidity_value is not None:
        update_data_storage("Humidity", humidity_value)

    calculating = any(len(values) < MAX_DATA_POINTS for values in data_storage.values())

    if not calculating:
        stats = {
            sensor: calculate_stats(values)
            for sensor, values in data_storage.items()
        }
    else:
        stats = None
    data_send_count += 1

    return render_template(
        "dashboard.html",
        tds=tds_value,
        ec=ec_value,
        temperature=temperature_value,
        humidity=humidity_value,
        stats=stats,
        calculating=calculating,
        data_count={sensor: len(values) for sensor, values in data_storage.items()},
        data_send_count=data_send_count
    )

@app.route("/reset", methods=["POST"])
def reset_data():
    try:
        with data_lock:
            data_storage["TDS"] = []
            data_storage["EC"] = []
            data_storage["Temperature"] = []
            data_storage["Humidity"] = []
            global data_send_count
            data_send_count = 0
        flash("Data has been reset successfully!", "success")
        return redirect("/")
    except Exception as e:
        flash(f"An error occurred while processing: {str(e)}", "error")
        return redirect("/")

if __name__ == "__main__":
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')
    tds_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}'
    ec_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}'
    temperature_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}'
    humidity_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}'
    c_hardware()
