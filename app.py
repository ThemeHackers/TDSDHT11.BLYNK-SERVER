import requests
import numpy as np
from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Thread, Lock
import time
from datetime import datetime
from scipy.stats import skew, kurtosis
import socket
import warnings
import base64
from collections import deque
from flask_cors import CORS
import os

warnings.simplefilter("ignore", category=RuntimeWarning)

# Configuration
BLYNK_AUTH_TOKEN = 'YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo='
BLYNK_TDS_PIN = 'V0'
BLYNK_TEMPERATURE_PIN = 'V2'
BLYNK_HUMIDITY_PIN = 'V3'
BLYNK_EC_PIN = 'V7'
WEB_SERVER_PORT = int(os.environ.get('PORT', 5000))
TARGET_SERVER_URL = 'https://tdsdht11-blynk-server.onrender.com/'

# Data storage
MAX_READINGS = 50
tds_readings = deque(maxlen=MAX_READINGS)
temperature_readings = deque(maxlen=MAX_READINGS)
humidity_readings = deque(maxlen=MAX_READINGS)
ec_readings = deque(maxlen=MAX_READINGS)
timestamps = deque(maxlen=MAX_READINGS)

data_lock = Lock()
decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')

# Flask app and WebSocket
app = Flask(__name__)
app.config['DEBUG'] = False
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app)
CORS(app)

class StatisticalValues:
    @staticmethod
    def mean(data):
        return np.mean(data) if data else None

    @staticmethod
    def standard_deviation(data):
        return np.std(data) if data else None

    @staticmethod
    def skewness(data):
        return skew(data) if len(data) > 3 else None

    @staticmethod
    def kurtosis(data):
        return kurtosis(data) if len(data) > 3 else None

def send_data_to_server():
    """Send collected data to the external server."""
    global tds_readings, temperature_readings, humidity_readings, ec_readings, timestamps

    with data_lock:
        data_payload = {
            'timestamps': list(timestamps),
            'tds_readings': list(tds_readings),
            'temperature_readings': list(temperature_readings),
            'humidity_readings': list(humidity_readings),
            'ec_readings': list(ec_readings),
        }

    try:
        response = requests.post(TARGET_SERVER_URL, json=data_payload)
        if response.status_code == 200:
            print("Data sent successfully!")
        else:
            print(f"Failed to send data. Status Code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending data to server: {e}")

def get_blynk_data():
    """Fetch data from Blynk and send to the WebSocket and external server."""
    global tds_readings, temperature_readings, humidity_readings, ec_readings, timestamps

    try:
        # Fetch data from Blynk API
        tds_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}')
        temperature_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}')
        humidity_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}')
        ec_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}')

        timestamp = datetime.now().strftime('%H:%M:%S')

        # Parse and append data
        if tds_response.status_code == 200 and tds_response.text.strip('[]'):
            tds_value = float(tds_response.text.strip('[]'))
            with data_lock:
                tds_readings.append(tds_value)
                timestamps.append(timestamp)

        if temperature_response.status_code == 200 and temperature_response.text.strip('[]'):
            temperature_value = float(temperature_response.text.strip('[]'))
            with data_lock:
                temperature_readings.append(temperature_value)

        if humidity_response.status_code == 200 and humidity_response.text.strip('[]'):
            humidity_value = float(humidity_response.text.strip('[]'))
            with data_lock:
                humidity_readings.append(humidity_value)

        if ec_response.status_code == 200 and ec_response.text.strip('[]'):
            ec_value = float(ec_response.text.strip('[]'))
            with data_lock:
                ec_readings.append(ec_value)

        # Emit data via WebSocket
        socketio.emit('update_data', {
            'timestamps': list(timestamps),
            'tds_readings': list(tds_readings),
            'temperature_readings': list(temperature_readings),
            'humidity_readings': list(humidity_readings),
            'ec_readings': list(ec_readings)
        })

        # Send data to external server
        send_data_to_server()
    except Exception as e:
        print(f"Error retrieving data from Blynk API: {e}")

@app.route('/')
def home():
    """Render the dashboard with statistics."""
    global timestamps

    ip_address = socket.gethostbyname(socket.gethostname())

    tds_stats = {
        'mean': StatisticalValues.mean(tds_readings),
        'std_dev': StatisticalValues.standard_deviation(tds_readings),
    }

    temperature_stats = {
        'mean': StatisticalValues.mean(temperature_readings),
        'std_dev': StatisticalValues.standard_deviation(temperature_readings),
    }

    humidity_stats = {
        'mean': StatisticalValues.mean(humidity_readings),
        'std_dev': StatisticalValues.standard_deviation(humidity_readings),
    }

    ec_stats = {
        'mean': StatisticalValues.mean(ec_readings),
        'std_dev': StatisticalValues.standard_deviation(ec_readings),
    }

    return render_template('dashboard.html', ip_address=ip_address,
                           tds_stats=tds_stats, temperature_stats=temperature_stats,
                           humidity_stats=humidity_stats, ec_stats=ec_stats,
                           tds_readings=list(tds_readings), temperature_readings=list(temperature_readings),
                           humidity_readings=list(humidity_readings), ec_readings=list(ec_readings),
                           timestamps=list(timestamps))

def blynk_data_fetcher():
    """Background thread for fetching Blynk data."""
    while True:
        try:
            get_blynk_data()
            time.sleep(3)
        except Exception as e:
            print(f"Error in background thread: {e}")
            break

if __name__ == '__main__':
    blynk_thread = Thread(target=blynk_data_fetcher)
    blynk_thread.daemon = True
    blynk_thread.start()

    socketio.run(app, port=WEB_SERVER_PORT)
