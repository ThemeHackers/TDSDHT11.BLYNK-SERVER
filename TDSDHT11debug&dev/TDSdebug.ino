#define BLYNK_TEMPLATE_NAME "TDSDHT11 Sensor"
#define BLYNK_TEMPLATE_ID "TMPL6P-Wygrt1"
#define BLYNK_AUTH_TOKEN "acPxQmZF_0swYPa7ANkaA9ZkzybGgcyj"
#define BLYNK_PRINT Serial

#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#include <ESP8266WebServer.h>
#include "GravityTDS.h"

// New WiFi credentials
const char* ssid = "HackerTheme";
const char* password = "#!@Theme171149";

// Pin definitions
#define TdsSensorPin A0
#define redPin D0
#define greenPin D1
#define bluePin D2

// GravityTDS instance
GravityTDS gravityTds;

// Variables
float temperature = 25.0;
float tdsValue = 0.0;
float ecValue = 0.0;
unsigned long previousMillis = 0;
const long interval = 1000; // Interval for updating TDS value and Blynk

// Blynk terminal widget on virtual pin V4
WidgetTerminal terminal(V4);

// Web server on port 80
ESP8266WebServer server(80);

// Declare global variables for button handling
unsigned long buttonPressTime[3] = {0, 0, 0};
const unsigned long buttonResetDelay = 5000; // 5 seconds

void setup() {
  // Initialize serial communication
  Serial.begin(115200);

  // Configure pin modes
  pinMode(redPin, OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);

  // Initialize GravityTDS sensor
  gravityTds.setPin(TdsSensorPin);
  gravityTds.setAref(5.0);
  gravityTds.setAdcRange(1024);

  // Set default usage mode
  gravityTds.setUsageMode(3); // Default to Household

  // Initialize Blynk
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, password);

  // Initialize web server
  server.on("/", handleRoot);
  server.on("/reset", handleReset);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  Blynk.run();
  server.handleClient();

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    
    // Update the TDS sensor reading
    gravityTds.setTemperature(temperature);
    gravityTds.update();
    ecValue = gravityTds.getEcValue();
    tdsValue = gravityTds.getTdsValue();

    // Print TDS and EC values to serial monitor
    // Serial.print("TDS: ");
    // Serial.print(tdsValue, 0);
    // Serial.println(" ppm");
    // Serial.print("EC Value: ");
    // Serial.println(ecValue);

    // Control LED based on TDS value
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

    // Send TDS and EC values to Blynk
    Blynk.virtualWrite(V0, tdsValue);
    Blynk.virtualWrite(V7, ecValue);
  }

  // Check WiFi connection periodically
  checkWiFiConnection();

  // Check if button reset is needed
  if (currentMillis - buttonPressTime[0] >= buttonResetDelay && buttonPressTime[0] > 0) {
    Blynk.virtualWrite(V8, 0); // Reset button state to 0
    buttonPressTime[0] = 0; // Reset the time tracking
  }
  if (currentMillis - buttonPressTime[1] >= buttonResetDelay && buttonPressTime[1] > 0) {
    Blynk.virtualWrite(V9, 0); // Reset button state to 0
    buttonPressTime[1] = 0; // Reset the time tracking
  }
  if (currentMillis - buttonPressTime[2] >= buttonResetDelay && buttonPressTime[2] > 0) {
    Blynk.virtualWrite(V10, 0); // Reset button state to 0
    buttonPressTime[2] = 0; // Reset the time tracking
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
    
    // Try to reconnect to the specified WiFi network
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

// Blynk function to handle terminal input
BLYNK_WRITE(V4) {
  String command = param.asStr();

  if (command == "ipconfig") {
    String ipAddress = WiFi.localIP().toString();
    terminal.println("IP Address to reset: http://" + ipAddress + "/reset");
    terminal.flush();
  } else if (command == "clear") {
    terminal.clear();
    terminal.println("Terminal cleared...");
    terminal.flush();
  } else if (command.startsWith("ssid:")) {
    terminal.println("SSID setting is now fixed and cannot be changed.");
    terminal.flush();
  } else if (command.startsWith("pass:")) {
    terminal.println("Password setting is now fixed and cannot be changed.");
    terminal.flush();
  } else if (command == "save") {
    terminal.println("Saving new WiFi credentials is not applicable.");
    terminal.flush();
  } else if (command.startsWith("mode:")) {
    int mode = command.substring(5).toInt();
    if (mode >= 1 && mode <= 3) {
      gravityTds.setUsageMode(mode);
      terminal.println("Mode set to: " + String(mode));
    } else {
      terminal.println("Invalid mode. Use 1 for Industrial, 2 for Agriculture, or 3 for Household.");
    }
    terminal.flush();
  } else {
    terminal.println("Unknown command: " + command);
    terminal.flush();
  }
}

// Blynk function to handle button presses for mode selection
BLYNK_WRITE(V8) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    gravityTds.setUsageMode(1); // Set mode to Industrial
    terminal.println("Mode set to: Industrial");
    buttonPressTime[0] = millis(); // Track button press time
  }
  terminal.flush();
}

BLYNK_WRITE(V9) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    gravityTds.setUsageMode(2); // Set mode to Agriculture
    terminal.println("Mode set to: Agriculture");
    buttonPressTime[1] = millis(); // Track button press time
  }
  terminal.flush();
}

BLYNK_WRITE(V10) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    gravityTds.setUsageMode(3); // Set mode to Household
    terminal.println("Mode set to: Household");
    buttonPressTime[2] = millis(); // Track button press time
  }
  terminal.flush();
}
BLYNK_WRITE(V11) {
  int buttonState = param.asInt();
  if (buttonState == 1) {
    terminal.println("Rebooting the main processor...");
    terminal.flush();
    delay(100);
    ESP.restart();  // Restart the ESP8266
  }
}
