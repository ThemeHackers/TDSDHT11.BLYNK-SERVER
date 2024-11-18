import requests
import numpy as np
from flask import Flask, render_template
from flask_socketio import SocketIO 
from threading import Thread, Lock
from flask_cors import CORS
import time

from datetime import datetime
import socket
import warnings
import base64
from collections import deque
import os
from colorama import Fore, Style, init
import uvicorn

init(autoreset=True)
from modules.statistics import StatisticalValues

warnings.simplefilter("ignore", category=RuntimeWarning)

# Blynk and server configurations
BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN', 'YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo=')  
BLYNK_TDS_PIN = 'V0'
BLYNK_TEMPERATURE_PIN = 'V2'
BLYNK_HUMIDITY_PIN = 'V3'
BLYNK_EC_PIN = 'V7'
WEB_SERVER_PORT = int(os.environ.get('PORT', 5000))  

# Data buffers and lock
MAX_READINGS = 200
tds_readings = deque(maxlen=MAX_READINGS)
temperature_readings = deque(maxlen=MAX_READINGS)
humidity_readings = deque(maxlen=MAX_READINGS)
ec_readings = deque(maxlen=MAX_READINGS)
timestamps = deque(maxlen=MAX_READINGS)
data_lock = Lock()


app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(24).hex()
CORS(app, resources={r"/*": {"origins": "*"}})  
socketio = SocketIO(app, cors_allowed_origins="*")

decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')


def get_blynk_data():
    """Fetch data from Blynk API and update readings."""
    global tds_readings, temperature_readings, humidity_readings, ec_readings, timestamps
    try:
        tds_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}')
        temperature_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}')
        humidity_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}')
        ec_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}')
        timestamp = datetime.now().strftime('%H:%M:%S')

        if tds_response.status_code == 200 and tds_response.text.strip('[]'):
            tds_value = round(float(tds_response.text.strip('[]')), 3)
            with data_lock:
                tds_readings.append(tds_value)
                timestamps.append(timestamp)

        if temperature_response.status_code == 200 and temperature_response.text.strip('[]'):
            temperature_value = round(float(temperature_response.text.strip('[]')), 3)
            with data_lock:
                temperature_readings.append(temperature_value)

        if humidity_response.status_code == 200 and humidity_response.text.strip('[]'):
            humidity_value = round(float(humidity_response.text.strip('[]')), 3)
            with data_lock:
                humidity_readings.append(humidity_value)

        if ec_response.status_code == 200 and ec_response.text.strip('[]'):
            ec_value = round(float(ec_response.text.strip('[]')), 3)
            with data_lock:
                ec_readings.append(ec_value)

        socketio.emit('update_data', {
            'timestamps': list(timestamps),
            'tds_readings': list(tds_readings),
            'temperature_readings': list(temperature_readings),
            'humidity_readings': list(humidity_readings),
            'ec_readings': list(ec_readings)
        })
        print("Emitted data:", {
            'timestamps': list(timestamps),
            'tds_readings': list(tds_readings),
            'temperature_readings': list(temperature_readings),
            'humidity_readings': list(humidity_readings),
            'ec_readings': list(ec_readings)
        })

    except Exception as e:
        print(f"Error retrieving data from Blynk API: {e}")
        print("TDS Response:", tds_response.text if 'tds_response' in locals() else "No response")
        print("Temperature Response:", temperature_response.text if 'temperature_response' in locals() else "No response")
        print("Humidity Response:", humidity_response.text if 'humidity_response' in locals() else "No response")
        print("EC Response:", ec_response.text if 'ec_response' in locals() else "No response")



@app.route('/')
def home():
    global tds_readings, temperature_readings, humidity_readings, ec_readings, timestamps

    tds_readings = tds_readings or []
    temperature_readings = temperature_readings or []
    humidity_readings = humidity_readings or []
    ec_readings = ec_readings or []
    timestamps = timestamps or []

    ip_address = socket.gethostbyname(socket.gethostname())


    tds_mean = StatisticalValues.mean(tds_readings)
    tds_std_dev = StatisticalValues.standard_deviation(tds_readings)
    tds_range = StatisticalValues.range(tds_readings)
    tds_variance = StatisticalValues.variance(tds_readings)
    tds_iqr = StatisticalValues.interquartile_range(tds_readings)

    temperature_mean = StatisticalValues.mean(temperature_readings)
    temperature_std_dev = StatisticalValues.standard_deviation(temperature_readings)

    humidity_mean = StatisticalValues.mean(humidity_readings)
    humidity_std_dev = StatisticalValues.standard_deviation(humidity_readings)

    ec_mean = StatisticalValues.mean(ec_readings)
    ec_std_dev = StatisticalValues.standard_deviation(ec_readings)

    return render_template('dashboard.html', ip_address=ip_address,
                           tds_stats={
                               'mean': round(tds_mean, 2) if tds_mean is not None else 0,
                               'std_dev': round(tds_std_dev, 2) if tds_std_dev is not None else 0,
                               'range': round(tds_range, 2) if tds_range is not None else 0,
                               'variance': round(tds_variance, 2) if tds_variance is not None else 0,
                               'iqr': round(tds_iqr, 2) if tds_iqr is not None else 0
                           },
                           temperature_stats={
                               'mean': round(temperature_mean, 2) if temperature_mean is not None else 0,
                               'std_dev': round(temperature_std_dev, 2) if temperature_std_dev is not None else 0
                           },
                           humidity_stats={
                               'mean': round(humidity_mean, 2) if humidity_mean is not None else 0,
                               'std_dev': round(humidity_std_dev, 2) if humidity_std_dev is not None else 0
                           },
                           ec_stats={
                               'mean': round(ec_mean, 2) if ec_mean is not None else 0,
                               'std_dev': round(ec_std_dev, 2) if ec_std_dev is not None else 0
                           },
                           timestamps=list(timestamps),  
                           tds_readings=list(tds_readings),  
                           temperature_readings=list(temperature_readings),  
                           humidity_readings=list(humidity_readings),  
                           ec_readings=list(ec_readings))  


def blynk_data_fetcher():
    """Background thread for fetching Blynk data."""
    while True:
        try:
            get_blynk_data()
            time.sleep(3)
        except Exception as e:
            print(Fore.RED + f"Error in data fetcher thread: {e}")
            break
if __name__ == '__main__':
    try:
        print(Fore.GREEN + "Starting Blynk data fetcher thread...")
        blynk_thread = Thread(target=blynk_data_fetcher)
        blynk_thread.daemon = True
        blynk_thread.start()

        print(Fore.GREEN + f"Starting server on port {WEB_SERVER_PORT}...")
        socketio.run(app, host="0.0.0.0", port=WEB_SERVER_PORT, log_output=True)
    except Exception as e:
        print(Fore.RED + f"ERROR: {e}")

