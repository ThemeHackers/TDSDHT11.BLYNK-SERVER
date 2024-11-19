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

init(autoreset=True)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BLYNK_AUTH_TOKEN = os.getenv('BLYNK_AUTH_TOKEN', 'YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo=')
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

tds_readings = deque(maxlen=MAX_READINGS)
ec_readings = deque(maxlen=MAX_READINGS)
temperature_readings = deque(maxlen=MAX_READINGS)
humidity_readings = deque(maxlen=MAX_READINGS)
timestamps = deque(maxlen=MAX_READINGS)
data_lock = Lock()

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(24).hex()
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

try:
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode('utf-8')
    logger.debug(f"Decoded Token: {decoded_token}")
except Exception as e:
    logger.warning(f"Failed to decode token: {e}")
    decoded_token = BLYNK_AUTH_TOKEN

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
    """Check if the server is connected, with up to 5 retries."""
    max_retries = 5  
    retry_count = 0  

    while retry_count < max_retries:
        try:
            status_url = f'https://blynk.cloud/external/api/isHardwareConnected?token={decoded_token}'
            response = fetch_api_data(status_url)
            
            if response == 'true':
                logger.info(Fore.RED + "Server is connected.")
                return True  
            else:
                logger.error(Fore.RED + "Server is not connected.")

        except Exception as e:
            logger.error(Fore.RED + f"Failed to check server connection: {e}")
        
        retry_count += 1
        if retry_count < max_retries:
            logger.info(Fore.YELLOW + f"Retrying connection in 15 seconds... (Attempt {retry_count}/{max_retries})")
            time.sleep(15)
        else:
            logger.error(Fore.RED + "Maximum retry attempts reached. Shutting down server.")
            exit(1)
            
def network_usage_monitor():
    """Periodically measure network usage."""
    while True:
        try:
            measure_network_usage(tds_url, ec_url, temperature_url, humidity_url)
            time.sleep(10)      
        except Exception as e:
            logger.error(Fore.RED + f"Error in network usage monitor: {e}")
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

            print(Fore.GREEN + f"URL: {url}")
            print(Fore.YELLOW + f"Request Size: {request_size} bytes")
            print(Fore.YELLOW + f"Response Size: {response_size} bytes")
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Error fetching URL: {url}, Error: {e}")

    
    total_size = total_request_size + total_response_size
    total_size_mb = total_size / (1024 * 1024)  

 
    print(Fore.BLUE + f"Total Request Size: {total_request_size} bytes")
    print(Fore.BLUE + f"Total Response Size: {total_response_size} bytes")
    print(Fore.BLUE + f"Total Data Usage: {total_size} bytes")
    print(Fore.MAGENTA + f"Total Data Usage: {total_size_mb:.10f} MB")
    return total_size_mb

tds_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}'
ec_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}'
temperature_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}'
humidity_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}'

data_usage_mb = measure_network_usage(tds_url, ec_url, temperature_url, humidity_url)
print("")
print(Fore.MAGENTA + f"Total Data Used: {data_usage_mb:.10f} MB")
print("")


def get_blynk_data():
    """Fetch data from Blynk API and update readings."""
    try:
        tds_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}'
        ec_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}'
        temperature_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}'
        humidity_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}'
        measure_network_usage(tds_url, ec_url, temperature_url, humidity_url)
        timestamp = datetime.now().strftime('%H:%M:%S')

        try:
            tds_value = round(float(fetch_api_data(tds_url)), 3)
            ec_value = round(float(fetch_api_data(ec_url)), 3)
            temperature_value = round(float(fetch_api_data(temperature_url)), 3)
            humidity_value = round(float(fetch_api_data(humidity_url)), 3)
        except Exception:
            logger.warning(Fore.RED + f'Using fallback data.')
            tds_value, ec_value = FALLBACK_DATA["tds"], FALLBACK_DATA["ec"]
            temperature_value, humidity_value = FALLBACK_DATA["temperature"], FALLBACK_DATA["humidity"]
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
            logger.info(Fore.GREEN + "Data successfully emitted to clients.")
        else:
            logger.warning(Fore.RED + f"Skipping data update. TDS: {tds_status}, EC: {ec_status}")

    except Exception as e:
        logger.error(Fore.RED + f"Error retrieving data: {e}")

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
            logger.error(Fore.RED + f"Error in data fetcher thread: {e}")
            break

if __name__ == '__main__':
    try:
        logger.info(Fore.GREEN + "Checking server connection...")
        if not check_server_connection():
            logger.error(Fore.RED + "Server is not connected. Exiting...")
            exit(1)

        logger.info(Fore.GREEN + "Starting Blynk data fetcher thread...")
        blynk_thread = Thread(target=blynk_data_fetcher)
        blynk_thread.daemon = True
        blynk_thread.start()

        logger.info(Fore.GREEN + "Starting network usage monitor thread...")
        network_thread = Thread(target=network_usage_monitor)
        network_thread.daemon = True
        network_thread.start()

        logger.info(f"Starting server on port {WEB_SERVER_PORT}...")
        socketio.run(app, host='0.0.0.0', port=WEB_SERVER_PORT)

    except KeyboardInterrupt:
        logger.info("Shutting down server gracefully.")
    except Exception as e:
        logger.critical(f"ERROR: {e}")
