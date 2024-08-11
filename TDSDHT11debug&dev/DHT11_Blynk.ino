#define BLYNK_TEMPLATE_NAME "TDSDHT11 Sensor"
#define BLYNK_TEMPLATE_ID "TMPL6P-Wygrt1"
#define BLYNK_AUTH_TOKEN "acPxQmZF_0swYPa7ANkaA9ZkzybGgcyj"
#define BLYNK_PRINT Serial

#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#include <DHT.h>

#define DHTPIN D1
#define DHTTYPE DHT11

WidgetTerminal terminal(V4);

DHT dht(DHTPIN, DHTTYPE);

char ssid[32] = "HackerTheme"; 
char password[64] = "#!@Theme171149"; 

void setup() {
  dht.begin();
  connectToWiFi();
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, password);
}

void loop() {
  Blynk.run();
  int temperature = dht.readTemperature();
  int humidity = dht.readHumidity();

  if (!isnan(temperature) && !isnan(humidity)) {
    Blynk.virtualWrite(V2, temperature);
    Blynk.virtualWrite(V3, humidity);
  }

  checkWiFiConnection();
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    attempts++;
  }
}

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      attempts++;
    }
  }
}

String logEntries = "";


void addLogEntry(String entry) {
  logEntries += entry + "\n";
}

BLYNK_WRITE(V4) {
  String command = param.asStr();

  if (command == "status") {
    terminal.println("Current Status:");
    terminal.println("TDS Value: " + String(tdsValue) + " ppm");
    terminal.println("EC Value: " + String(ecValue));
    terminal.flush();
  } else if (command == "temperature") {
    terminal.println("Current Temperature Setting: " + String(temperature) + " °C");
    terminal.flush();
  } else if (command == "tds") {
    terminal.println("Current TDS Value: " + String(tdsValue) + " ppm");
    terminal.flush();
  } else if (command == "ec") {
    terminal.println("Current EC Value: " + String(ecValue));
    terminal.flush();
  } else if (command == "wifi") {
    if (WiFi.status() == WL_CONNECTED) {
      terminal.println("WiFi is connected");
      terminal.println("IP Address: " + WiFi.localIP().toString());
      terminal.println("Signal Strength: " + String(WiFi.RSSI()) + " dBm");
    } else {
      terminal.println("WiFi is not connected");
    }
    terminal.flush();
  } else if (command == "uptime") {
    unsigned long uptime = millis() / 1000; // Convert milliseconds to seconds
    unsigned long hours = uptime / 3600;
    unsigned long minutes = (uptime % 3600) / 60;
    unsigned long seconds = uptime % 60;
    terminal.println("Uptime: " + String(hours) + " hours, " + String(minutes) + " minutes, " + String(seconds) + " seconds");
    terminal.flush();
  } else if (command == "resetWiFi") {
    WiFi.disconnect();
    WiFi.reconnect();
    terminal.println("WiFi connection reset.");
    terminal.flush();
  } else if (command == "sensor") {
    terminal.println("TDS Sensor Data:");
    terminal.println("Temperature: " + String(temperature) + " °C");
    terminal.println("TDS Value: " + String(tdsValue) + " ppm");
    terminal.println("EC Value: " + String(ecValue));
    terminal.flush();
  } else if (command == "log") {
    terminal.println("Recent log entries:");
    terminal.println(logEntries);
    terminal.flush();
  } else if (command == "clear") {
    terminal.clear(); 
    terminal.flush();
  } else if (command == "ipconfig") {
    if (WiFi.status() == WL_CONNECTED) {
      terminal.println("IP Address: " + WiFi.localIP().toString());
      terminal.println("Subnet Mask: " + WiFi.subnetMask().toString());
      terminal.println("Gateway: " + WiFi.gatewayIP().toString());
    } else {
      terminal.println("WiFi is not connected");
    }
    terminal.flush();
  } else if (command == "ipconfig/reset") {
    if (WiFi.status() == WL_CONNECTED) {
      terminal.println("Access URL: http://" + WiFi.localIP().toString() + "/reset");
    } else {
      terminal.println("WiFi is not connected");
    }
    terminal.flush();
  } else if (command == "reset") {
    terminal.println("System is resetting...");
    terminal.flush();
    delay(100);
    ESP.restart();  
  } else if (command == "help") {
    terminal.println("Available commands:");
    terminal.println("status          - Show current TDS and EC values");
    terminal.println("temperature     - Show current temperature setting");
    terminal.println("tds             - Show current TDS value");
    terminal.println("ec              - Show current EC value");
    terminal.println("wifi            - Show WiFi connection status");
    terminal.println("uptime          - Show system uptime");
    terminal.println("resetWiFi       - Disconnect and reconnect WiFi");
    terminal.println("sensor          - Show TDS sensor data");
    terminal.println("log             - Show recent log entries");
    terminal.println("clear           - Clear terminal output");
    terminal.println("ipconfig        - Show IP configuration");
    terminal.println("ipconfig/reset  - Show reset URL");
    terminal.println("reset           - Reset the device");
    terminal.println("help            - Show this help message");
    terminal.flush();
  } else {
    terminal.println("Unknown command: " + command);
    terminal.flush();
  }
}

