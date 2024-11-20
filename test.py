from flask import Flask, render_template
import requests
import os
import base64
import logging
from statistics import mean, median, stdev
from colorama import Fore , Style ,init 
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential
init(autoreset=True)
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
MAX_DATA_POINTS = 10 
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return float(response.text.strip())  
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
def check_server_connection():
    """Check if the server is connected, with up to 5 retries."""
    max_retries = 5  
    retry_count = 0  

    while retry_count < max_retries:
        try:
            url = f'https://blynk.cloud/external/api/isHardwareConnected?token={decoded_token}'
            response = fetch_data(url)
            
            if response == 'true':
                logger.info(Fore.GREEN + "Server is connected.")
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

@app.route("/")
def index():
    tds_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}'
    ec_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}'
    temperature_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}'
    humidity_url = f'https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}'
    tds_value = fetch_data(tds_url)
    ec_value = fetch_data(ec_url)
    temperature_value = fetch_data(temperature_url)
    humidity_value = fetch_data(humidity_url)
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

    calculating = any(len(values) < MAX_DATA_POINTS for values in data_storage.values())

    if not calculating:

        stats = {
            sensor: {
                "mean": mean(values),
                "median": median(values),
                "stdev": stdev(values) if len(values) > 1 else 0
            }
            for sensor, values in data_storage.items()
        }
    else:
        stats = None
    data_count = {sensor: len(values) for sensor, values in data_storage.items()}

    return render_template(
        "index.html",
        tds=tds_value,
        ec=ec_value,
        temperature=temperature_value,
        humidity=humidity_value,
        stats=stats,
        calculating=calculating,
        data_count=data_count  
    )


if __name__ == "__main__":
    app.run(debug=True)
