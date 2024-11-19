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
# Initialize
init(autoreset=True)

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuration
BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN', 'YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo=')  
BLYNK_TDS_PIN = 'V0'
BLYNK_TEMPERATURE_PIN = 'V2'
BLYNK_HUMIDITY_PIN = 'V3'
BLYNK_EC_PIN = 'V7'
WEB_SERVER_PORT = int(os.environ.get('PORT', 10000))  

MAX_READINGS = 200
tds_readings = deque(maxlen=MAX_READINGS)
temperature_readings = deque(maxlen=MAX_READINGS)
humidity_readings = deque(maxlen=MAX_READINGS)
ec_readings = deque(maxlen=MAX_READINGS)
timestamps = deque(maxlen=MAX_READINGS)
data_lock = Lock()

# Flask App
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(24).hex()
CORS(app, resources={r"/*": {"origins": "*"}}) 

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Decode token if necessary (commented out if not Base64 encoded)
try:
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')
    logger.debug(f"Decoded Token: {decoded_token}")
except Exception as e:
    logger.warning(f"Failed to decode token: {e}")
    decoded_token = BLYNK_AUTH_TOKEN  # Use as is if not Base64

# Fetch API Data with Retry
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def fetch_api_data(url):
    """Fetch data from API with retry mechanism."""
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.text.strip()

def get_blynk_data():
    """Fetch data from Blynk API and update readings."""
    try:
        # API Endpoints
        tds_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_TDS_PIN}'
        temperature_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_TEMPERATURE_PIN}'
        humidity_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_HUMIDITY_PIN}'
        ec_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&vpin={BLYNK_EC_PIN}'
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Fetch data with retry
        tds_value = round(float(fetch_api_data(tds_url)), 3)
        temperature_value = round(float(fetch_api_data(temperature_url)), 3)
        humidity_value = round(float(fetch_api_data(humidity_url)), 3)
        ec_value = round(float(fetch_api_data(ec_url)), 3)

        # Update data
        with data_lock:
            tds_readings.append(tds_value)
            temperature_readings.append(temperature_value)
            humidity_readings.append(humidity_value)
            ec_readings.append(ec_value)
            timestamps.append(timestamp)

        # Emit data to clients
        socketio.emit('update_data', {
            'timestamps': list(timestamps),
            'tds_readings': list(tds_readings),
            'temperature_readings': list(temperature_readings),
            'humidity_readings': list(humidity_readings),
            'ec_readings': list(ec_readings)
        })
        logger.info("Data successfully emitted to clients.")

    except Exception as e:
        logger.error(f"Error retrieving data: {e}")

@app.route('/')
def home():
    global tds_readings, temperature_readings, humidity_readings, ec_readings, timestamps

    ip_address = socket.gethostbyname(socket.gethostname())

    # Calculate Statistics
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
    while True:
        try:
            get_blynk_data()
            time.sleep(3)
        except Exception as e:
            logger.error(f"Error in data fetcher thread: {e}")
            break

if __name__ == '__main__':
    try:
        logger.info("Starting Blynk data fetcher thread...")
        blynk_thread = Thread(target=blynk_data_fetcher)
        blynk_thread.daemon = True
        blynk_thread.start()

        logger.info(f"Starting server on port {WEB_SERVER_PORT}...")
        socketio.run(app, host='0.0.0.0', port=WEB_SERVER_PORT)

    except Exception as e:
        logger.critical(f"ERROR: {e}")