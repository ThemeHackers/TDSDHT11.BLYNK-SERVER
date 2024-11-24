from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
import asyncio
import requests
import os
import base64
import logging
import time
from statistics import mean, median, stdev
from colorama import Fore, init
import threading

init(autoreset=True)

app = FastAPI()

env = Environment(loader=FileSystemLoader("templates"))

BLYNK_AUTH_TOKEN = os.getenv("BLYNK_AUTH_TOKEN", "YWNQeFFtWkZfMHN3WVBhN0FOa2FBOVprenliR2djeWo=")
BLYNK_TDS_PIN = "V0"
BLYNK_EC_PIN = "V7"
BLYNK_TEMPERATURE_PIN = "V2"
BLYNK_HUMIDITY_PIN = "V3"
WEB_SERVER_PORT = int(os.getenv("PORT", 10000))

data_storage = {"TDS": [], "EC": [], "Temperature": [], "Humidity": []}
MAX_DATA_POINTS = 200
data_send_count = 0

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    decoded_token = base64.b64decode(BLYNK_AUTH_TOKEN).decode("utf-8")
except Exception as e:
    logger.warning(f"Failed to decode token: {e}")
    decoded_token = BLYNK_AUTH_TOKEN

tds_url = f"https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TDS_PIN}"
ec_url = f"https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_EC_PIN}"
temperature_url = f"https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_TEMPERATURE_PIN}"
humidity_url = f"https://blynk.cloud/external/api/get?token={decoded_token}&{BLYNK_HUMIDITY_PIN}"


async def fetch_data(url):
    try:
        async with asyncio.Semaphore(10):  
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.get, url)
            response.raise_for_status()
            return float(response.text.strip())
    except (requests.RequestException, ValueError) as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return None


async def fetch_all_data():
    return await asyncio.gather(
        fetch_data(tds_url),
        fetch_data(ec_url),
        fetch_data(temperature_url),
        fetch_data(humidity_url),
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    global data_send_count
    data = await fetch_all_data()
    tds_value, ec_value, temperature_value, humidity_value = data

    for value, key in zip(data, data_storage.keys()):
        if value is not None:
            data_storage[key].append(value)
            if len(data_storage[key]) > MAX_DATA_POINTS:
                data_storage[key].pop(0)

    calculating = any(len(values) < MAX_DATA_POINTS for values in data_storage.values())

    stats = (
        {
            sensor: {
                "mean": mean(values) if values else 0,
                "median": median(values) if values else 0,
                "stdev": stdev(values) if len(values) > 1 else 0,
            }
            for sensor, values in data_storage.items()
        }
        if not calculating
        else None
    )

    data_send_count += 1
    template = env.get_template("dashboard.html")
    content = template.render(
        tds=tds_value,
        ec=ec_value,
        temperature=temperature_value,
        humidity=humidity_value,
        stats=stats,
        calculating=calculating,
        data_count={sensor: len(values) for sensor, values in data_storage.items()},
        data_send_count=data_send_count,
    )
    return HTMLResponse(content)


@app.post("/reset")
async def reset_data():
    global data_send_count
    try:
        for key in data_storage.keys():
            data_storage[key].clear()
        data_send_count = 0
        return RedirectResponse("/", status_code=303)
    except Exception as e:
        logger.error(f"Error resetting data: {e}")
        return RedirectResponse("/", status_code=500)


async def network_usage_monitor():
    while True:
        try:
            total_usage = await measure_network_usage(tds_url, ec_url, temperature_url, humidity_url)
            logger.info(f"Network usage: {total_usage:.2f} MB")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error in network usage monitor: {e}")
            break


async def measure_network_usage(*urls):
    total_request_size = 0
    total_response_size = 0
    for url in urls:
        try:
            request_size = len(url.encode("utf-8"))
            total_request_size += request_size
            response = await asyncio.to_thread(requests.get, url)
            response.raise_for_status()
            response_size = len(response.content)
            total_response_size += response_size
        except requests.RequestException as e:
            logger.error(f"Error fetching URL: {url}, Error: {e}")

    total_size = total_request_size + total_response_size
    total_size_mb = total_size / (1024 * 1024)  
    return total_size_mb


def is_hardware_connected():
    url = f"https://blynk.cloud/external/api/isHardwareConnected?token={decoded_token}"
    try:
        response = requests.get(url)
        return response.text.strip().lower() == "false"
    except requests.RequestException as e:
        logger.error(f"Error checking hardware connection: {e}")
        return False


if __name__ == "__main__":
    import uvicorn

    try:
        if is_hardware_connected():
            print(Fore.GREEN + "The hardware device is connected.")
            threading.Thread(target=asyncio.run, args=(network_usage_monitor(),), daemon=True).start()
            uvicorn.run(app, host="0.0.0.0", port=WEB_SERVER_PORT)
        else:
            print(Fore.RED + "The hardware device is not connected.")
    except KeyboardInterrupt:
        print(Fore.RED + "Server stopped.")
