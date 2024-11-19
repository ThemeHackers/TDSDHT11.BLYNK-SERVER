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
from tenacity import retry, stop_after_attempt, wait_exponential
import base64
import json

# Initialize
init(autoreset=True)

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuration
BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN')
if not BLYNK_AUTH_TOKEN:
    logger.critical("BLYNK_AUTH_TOKEN not set in environment variables.")
    exit(1)

BLYNK_TDS_PIN = 'V0'
BLYNK_TEMPERATURE_PIN = 'V2'
BLYNK_HUMIDITY_PIN = 'V3'
BLYNK_EC_PIN = 'V7'
WEB_SERVER_PORT = int(os.environ.get('PORT', 10000))
MAX_READINGS = 200
FALLBACK_DATA = {"tds": 0.0, "ec": 0.0, "temperature": 0.0, "humidity": 0.0}

# Initialize storage
tds_readings = deque(maxlen=MAX_READINGS)
ec_readings = deque(maxlen=MAX_READINGS)
temperature_readings = deque(maxlen=MAX_READINGS)
humidity_readings = deque(maxlen=MAX_READINGS)
timestamps = deque(maxlen=MAX_READINGS)
data_lock = Lock()

# Flask App
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(24).hex()
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Decode token if necessary
try:
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')
    logger.debug(f"Decoded Token: {decoded_token}")
except Exception as e:
    logger.warning(f"Failed to decode token: {e}")
    decoded_token = BLYNK_AUTH_TOKEN

# Fetch API Data with Retry
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def fetch_api_data(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        logger.warning(f"API fetch failed: {e}")
        raise

def check_server_connection():
    """Check if the server is connected."""
    try:
        status_url = f'https://blynk.cloud/external/api/isHardwareConnected?token={decoded_token}'
        response = fetch_api_data(status_url)
        if response == 'true':
            logger.info("Server is connected.")
            return True
        else:
            logger.error("Server is not connected.")
            return False
    except Exception as e:
        logger.error(f"Failed to check server connection: {e}")
        return False

def get_blynk_data():
    """Fetch data from Blynk API and update readings."""
    try:
        tds_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_TDS_PIN}'
        ec_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_EC_PIN}'
        temperature_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_TEMPERATURE_PIN}'
        humidity_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_HUMIDITY_PIN}'
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Fetch data with fallback
        try:
            tds_value = round(float(fetch_api_data(tds_url)), 3)
            ec_value = round(float(fetch_api_data(ec_url)), 3)
            temperature_value = round(float(fetch_api_data(temperature_url)), 3)
            humidity_value = round(float(fetch_api_data(humidity_url)), 3)
        except Exception:
            logger.warning("Using fallback data.")
            tds_value, ec_value = FALLBACK_DATA["tds"], FALLBACK_DATA["ec"]
            temperature_value, humidity_value = FALLBACK_DATA["temperature"], FALLBACK_DATA["humidity"]

        # Sensor status
        tds_status = "Active" if tds_value > 18 else "Inactive"
        ec_status = "Active" if ec_value > 6.28 else "Inactive"

        if tds_status == "Active" and ec_status == "Active":
            with data_lock:
                tds_readings.append(tds_value)
                ec_readings.append(ec_value)
                temperature_readings.append(temperature_value)
                humidity_readings.append(humidity_value)
                timestamps.append(timestamp)

            socketio.emit('update_data', {
                'timestamps': list(timestamps),
                'tds_readings': list(tds_readings),
                'ec_readings': list(ec_readings),
                'temperature_readings': list(temperature_readings),
                'humidity_readings': list(humidity_readings)
            })
            logger.info("Data successfully emitted to clients.")
        else:
            logger.warning(f"Skipping data update. TDS: {tds_status}, EC: {ec_status}")

    except Exception as e:
        logger.error(f"Error retrieving data: {e}")

@app.route('/')
def home():
    ip_address = socket.gethostbyname(socket.gethostname())
    tds_mean = StatisticalValues.mean(tds_readings)
    ec_mean = StatisticalValues.mean(ec_readings)
    temperature_mean = StatisticalValues.mean(temperature_readings)
    humidity_mean = StatisticalValues.mean(humidity_readings)

    return render_template('dashboard.html', ip_address=ip_address,
                           tds_stats={'mean': round(tds_mean, 2) if tds_mean else 0},
                           ec_stats={'mean': round(ec_mean, 2) if ec_mean else 0},
                           temperature_stats={'mean': round(temperature_mean, 2) if temperature_mean else 0},
                           humidity_stats={'mean': round(humidity_mean, 2) if humidity_mean else 0},
                           timestamps=list(timestamps),
                           tds_readings=list(tds_readings),
                           ec_readings=list(ec_readings),
                           temperature_readings=list(temperature_readings),
                           humidity_readings=list(humidity_readings))

def blynk_data_fetcher():
    while True:
        try:
            get_blynk_data()
            time.sleep(3)
        except Exception as e:
            logger.error(f"Error in data fetcher thread: {e}")
            break

if __name__ == '__main__':
    try:
        logger.info("Checking server connection...")
        if not check_server_connection():
            logger.error("Server is not connected. Exiting...")
            exit(1)

        logger.info("Starting Blynk data fetcher thread...")
        blynk_thread = Thread(target=blynk_data_fetcher)
        blynk_thread.daemon = True
        blynk_thread.start()

        logger.info(f"Starting server on port {WEB_SERVER_PORT}...")
        socketio.run(app, host='0.0.0.0', port=WEB_SERVER_PORT)

    except KeyboardInterrupt:
        logger.info("Shutting down server gracefully.")
    except Exception as e:
        logger.critical(f"ERROR: {e}")