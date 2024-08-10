#define BLYNK_TEMPLATE_NAME "TDSDHT11 Sensor"
#define BLYNK_TEMPLATE_ID "TMPL6P-Wygrt1"
#define BLYNK_AUTH_TOKEN "acPxQmZF_0swYPa7ANkaA9ZkzybGgcyj"
#define BLYNK_PRINT Serial

#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#include <ESP8266WebServer.h>
#include "GravityTDS.h"


const char* ssid = "HOME65_2.4Gz";
const char* password = "59454199";

#define TdsSensorPin A0
#define redPin D0
#define greenPin D1
#define bluePin D2


GravityTDS gravityTds;


float temperature = 25.0;
float tdsValue = 0.0;
float ecValue = 0.0;
unsigned long previousMillis = 0;
const long interval = 1000; 


WidgetTerminal terminal(V4);


ESP8266WebServer server(80);


unsigned long buttonPressTime[3] = {0, 0, 0};
const unsigned long buttonResetDelay = 5000; 

void setup() {
 
  Serial.begin(115200);


  pinMode(redPin, OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);

 
  gravityTds.setPin(TdsSensorPin);
  gravityTds.setAref(5.0);
  gravityTds.setAdcRange(1024);

  gravityTds.setUsageMode(3); 

  
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, password);

 
  server.on("/", handleRoot);
  server.on("/reset", handleReset);
  server.begin();
  Serial.println("HTTP server started...");
}

void loop() {
  Blynk.run();
  server.handleClient();

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

   
    gravityTds.setTemperature(temperature);
    gravityTds.update();
    ecValue = gravityTds.getEcValue();
    tdsValue = gravityTds.getTdsValue();

   
    String tdsSeverity;
    if (tdsValue < 300) {
      tdsSeverity = "GOOD";
    } else if (tdsValue >= 300 && tdsValue < 500) {
      tdsSeverity = "NORMAL";
    } else {
      tdsSeverity = "HIGH";
    }

    // Serial.print("TDS: ");
    // Serial.print(tdsValue, 0);
    // Serial.println(" ppm");
    // Serial.print("EC Value: ");
    // Serial.println(ecValue);

    
    if (tdsValue > 18) {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(250);
      digitalWrite(LED_BUILTIN, LOW);
      delay(250);
    }

    if (tdsValue > 500) {
      digitalWrite(redPin, HIGH);
      digitalWrite(greenPin, LOW);
      digitalWrite(bluePin, LOW);
    } else {
      digitalWrite(redPin, LOW);
      digitalWrite(greenPin, HIGH);
      digitalWrite(bluePin, LOW);
    }

    
    Blynk.virtualWrite(V0, tdsValue);
    Blynk.virtualWrite(V7, ecValue);
    Blynk.virtualWrite(V5, tdsSeverity);
  }

  
  checkWiFiConnection();

  
  if (currentMillis - buttonPressTime[0] >= buttonResetDelay && buttonPressTime[0] > 0) {
    Blynk.virtualWrite(V8, 0); 
    buttonPressTime[0] = 0; 
  }
  if (currentMillis - buttonPressTime[1] >= buttonResetDelay && buttonPressTime[1] > 0) {
    Blynk.virtualWrite(V9, 0); 
    buttonPressTime[1] = 0; 
  }
  if (currentMillis - buttonPressTime[2] >= buttonResetDelay && buttonPressTime[2] > 0) {
    Blynk.virtualWrite(V10, 0); 
    buttonPressTime[2] = 0;
  }
}

void handleRoot() {
  server.send(200, "text/plain", "Hello! Go to /reset to reset the device.");
}

void handleReset() {
  server.send(200, "text/plain", "Device is resetting...");
  delay(100);
  ESP.restart();
}

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi connection lost. Reconnecting...");

    
    WiFi.begin(ssid, password);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi connected");
    } else {
      Serial.println("\nWiFi connection failed");
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

BLYNK_WRITE(V8) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    gravityTds.setUsageMode(1); 
    terminal.println("Mode set to: Industrial");
    buttonPressTime[0] = millis(); 
  }
  terminal.flush();
}

BLYNK_WRITE(V9) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    gravityTds.setUsageMode(2); 
    terminal.println("Mode set to: Agriculture");
    buttonPressTime[1] = millis(); 
  }
  terminal.flush();
}

BLYNK_WRITE(V10) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    gravityTds.setUsageMode(3); 
    terminal.println("Mode set to: Household");
    buttonPressTime[2] = millis(); 
  }
  terminal.flush();
}

BLYNK_WRITE(V11) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    terminal.println("Rebooting the main processor...");
    terminal.flush();
    delay(100);
    ESP.restart();  
  }
}

