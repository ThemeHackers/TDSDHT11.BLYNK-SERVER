from flask import Flask, render_template
from flask_socketio import SocketIO
import os
import time
from threading import Thread, Lock
import requests
import socket
from datetime import datetime
from collections import deque
from colorama import Fore, init
from flask_cors import CORS
from modules.statistics import StatisticalValues
import logging
import base64

# Initialize
init(autoreset=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN', 'default_token')  
BLYNK_TDS_PIN = 'V0'
BLYNK_TEMPERATURE_PIN = 'V2'
BLYNK_HUMIDITY_PIN = 'V3'
BLYNK_EC_PIN = 'V7'
WEB_SERVER_PORT = int(os.environ.get('PORT', 10000))  
FETCH_INTERVAL = 3  # seconds
MAX_READINGS = 200

# Shared Data
tds_readings = deque(maxlen=MAX_READINGS)
temperature_readings = deque(maxlen=MAX_READINGS)
humidity_readings = deque(maxlen=MAX_READINGS)
ec_readings = deque(maxlen=MAX_READINGS)
timestamps = deque(maxlen=MAX_READINGS)
data_lock = Lock()
should_stop = False  # Flag to safely stop the thread

# Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
CORS(app, resources={r"/*": {"origins": ["https://your-trusted-domain.com"]}})  # Secure CORS settings
socketio = SocketIO(app, cors_allowed_origins="https://your-trusted-domain.com", async_mode="eventlet")

# Decode token if necessary
try:
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')
    logger.info("Decoded Blynk Auth Token successfully.")
except Exception as e:
    logger.warning(f"Using raw token: {e}")
    decoded_token = BLYNK_AUTH_TOKEN


def get_blynk_data():
    """Fetch data from Blynk API and update readings."""
    try:
        # API Requests
        tds_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_TDS_PIN}')
        tds_response.raise_for_status()
        temperature_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_TEMPERATURE_PIN}')
        temperature_response.raise_for_status()
        humidity_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_HUMIDITY_PIN}')
        humidity_response.raise_for_status()
        ec_response = requests.get(f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_EC_PIN}')
        ec_response.raise_for_status()
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Process API Data
        with data_lock:
            if tds_response.text.strip():
                tds_readings.append(round(float(tds_response.text.strip()), 3))
                timestamps.append(timestamp)

            if temperature_response.text.strip():
                temperature_readings.append(round(float(temperature_response.text.strip()), 3))

            if humidity_response.text.strip():
                humidity_readings.append(round(float(humidity_response.text.strip()), 3))

            if ec_response.text.strip():
                ec_readings.append(round(float(ec_response.text.strip()), 3))

        # Emit data to clients
        socketio.emit('update_data', {
            'timestamps': list(timestamps),
            'tds_readings': list(tds_readings),
            'temperature_readings': list(temperature_readings),
            'humidity_readings': list(humidity_readings),
            'ec_readings': list(ec_readings)
        })
        logger.info("Data successfully emitted to clients.")

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request failed: {e}")
    except Exception as e:
        logger.error(f"Error retrieving data: {e}")


@app.route('/')
def home():
    """Render the main dashboard."""
    ip_address = socket.gethostbyname(socket.gethostname())

    # Calculate Statistics
    tds_stats = {
        'mean': round(StatisticalValues.mean(tds_readings) or 0, 2),
        'std_dev': round(StatisticalValues.standard_deviation(tds_readings) or 0, 2),
        'range': round(StatisticalValues.range(tds_readings) or 0, 2),
        'variance': round(StatisticalValues.variance(tds_readings) or 0, 2),
        'iqr': round(StatisticalValues.interquartile_range(tds_readings) or 0, 2)
    }

    temperature_stats = {
        'mean': round(StatisticalValues.mean(temperature_readings) or 0, 2),
        'std_dev': round(StatisticalValues.standard_deviation(temperature_readings) or 0, 2)
    }

    humidity_stats = {
        'mean': round(StatisticalValues.mean(humidity_readings) or 0, 2),
        'std_dev': round(StatisticalValues.standard_deviation(humidity_readings) or 0, 2)
    }

    ec_stats = {
        'mean': round(StatisticalValues.mean(ec_readings) or 0, 2),
        'std_dev': round(StatisticalValues.standard_deviation(ec_readings) or 0, 2)
    }

    return render_template('dashboard.html', ip_address=ip_address,
                           tds_stats=tds_stats,
                           temperature_stats=temperature_stats,
                           humidity_stats=humidity_stats,
                           ec_stats=ec_stats,
                           timestamps=list(timestamps),
                           tds_readings=list(tds_readings),
                           temperature_readings=list(temperature_readings),
                           humidity_readings=list(humidity_readings),
                           ec_readings=list(ec_readings))


def blynk_data_fetcher():
    """Thread to fetch data periodically."""
    global should_stop
    while not should_stop:
        get_blynk_data()
        time.sleep(FETCH_INTERVAL)


if __name__ == '__main__':
    try:
        logger.info("Starting Blynk data fetcher thread...")
        blynk_thread = Thread(target=blynk_data_fetcher)
        blynk_thread.daemon = True
        blynk_thread.start()

        logger.info(f"Starting server on port {WEB_SERVER_PORT}...")
        socketio.run(app, host='0.0.0.0', port=WEB_SERVER_PORT)

    except KeyboardInterrupt:
        should_stop = True
        logger.info("Stopping server...")
    except Exception as e:
        logger.critical(f"Critical error: {e}")
