# TDSDHT11 Sensor with Blynk Integration

## Overview

This project uses an **ESP8266** microcontroller, a **Gravity TDS Sensor** (Total Dissolved Solids), and a **DHT11** sensor to monitor water quality parameters like TDS (ppm), EC (Electrical Conductivity), and temperature. The data is sent to the **Blynk IoT platform** for remote monitoring and control.

The system also includes an **LED RGB indicator** to visually represent the water quality status (Good, Normal, High TDS values). The device connects to a Wi-Fi network and has an HTTP server for diagnostics and device resets.

## Components

- **ESP8266** microcontroller
- **Gravity TDS Sensor**
- **DHT11 Temperature and Humidity Sensor**
- **RGB LED** for water quality indication
- **Blynk App** for real-time monitoring

## Libraries Required

1. **ESP8266WiFi**: For Wi-Fi connectivity.
2. **ESP8266mDNS**: For mDNS support.
3. **BlynkSimpleEsp8266**: For communication with the Blynk platform.
4. **GravityTDS**: To interface with the Gravity TDS sensor.

## Setup

### 1. Wiring

- **TDS Sensor** connected to **A0** (Analog input).
- **LED Pins** connected to **D2**, **D3**, and **D4** (for RGB LED).
- **DHT11** (optional) connected for temperature and humidity readings.

### 2. Blynk Setup

Create a Blynk project in the Blynk app and get the **Auth Token** for your ESP8266.

### 3. Wi-Fi Setup

Replace the Wi-Fi credentials in the code with your own:

```cpp
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
