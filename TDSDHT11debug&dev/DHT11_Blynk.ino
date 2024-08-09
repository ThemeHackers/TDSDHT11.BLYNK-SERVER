#define BLYNK_TEMPLATE_NAME "TDSDHT11 Sensor"
#define BLYNK_TEMPLATE_ID "TMPL6P-Wygrt1"
#define BLYNK_AUTH_TOKEN "acPxQmZF_0swYPa7ANkaA9ZkzybGgcyj"
#define BLYNK_PRINT Serial

#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#include <ESP8266WebServer.h>
#include <DHT.h>

// Define pin and type for DHT sensor
#define DHTPIN D1
#define DHTTYPE DHT11

// Initialize DHT sensor
DHT dht(DHTPIN, DHTTYPE);

// WiFi credentials
char ssid[32] = "HackerTheme"; // Adjust the size according to your network's SSID length
char password[64] = "#!@Theme171149"; // Adjust the size according to your network's password length
// Blynk terminal widget on virtual pin V5
WidgetTerminal terminal(V5);

// Web server on port 80
ESP8266WebServer server(80);

// Handle root path
void handleRoot() {
  server.send(200, "text/plain", "Hello! Go to /reset to reset the device.");
}

// Handle reset path
void handleReset() {
  server.send(200, "text/plain", "Device is resetting...");
  delay(100);
  ESP.restart();
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
  dht.begin();

  // Initialize web server
  server.on("/", handleRoot);
  server.on("/reset", handleReset);
  server.begin();
  Serial.println("HTTP server started");

  // Connect to WiFi using default credentials
  connectToWiFi();

  // Initialize Blynk
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, password);

  // Print IP address to Blynk terminal after connecting to WiFi
  printIPAddress();
}

void loop() {
  Blynk.run();
  server.handleClient();

  // Read temperature and humidity from DHT sensor
  int temperature = dht.readTemperature();
  int humidity = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.print(" %\t");
  Serial.print("Temperature: ");
  Serial.println(temperature);

  // Send data to Blynk
  Blynk.virtualWrite(V2, temperature);
  Blynk.virtualWrite(V3, humidity);

  // Blink the built-in LED
  digitalWrite(LED_BUILTIN, HIGH);
  delay(150);
  digitalWrite(LED_BUILTIN, LOW);
  delay(300);

  // Check WiFi connection periodically
  checkWiFiConnection();
}

void connectToWiFi() {
  Serial.print("Connecting to WiFi with SSID: ");
  Serial.println(ssid);

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
    // You can add retry logic here or handle it in a different way based on your needs
  }
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
      Serial.println("\nWiFi reconnected");
    } else {
      Serial.println("\nWiFi reconnect failed");
    }
  }
}

void printIPAddress() {
  if (WiFi.status() == WL_CONNECTED) {
    String ipAddress = WiFi.localIP().toString();
    terminal.println("Device IP Address: " + ipAddress);
    terminal.flush();
  } else {
    terminal.println("Not connected to WiFi");
    terminal.flush();
  }
}

// Blynk function to handle terminal input
BLYNK_WRITE(V5) {
  String command = param.asStr();

  if (command == "ipconfig") {
    printIPAddress();
  } else if (command == "clear") {
    terminal.clear();
    terminal.println("Terminal cleared...");
    terminal.flush();
  } else if (command.startsWith("ssid:")) {
    command.remove(0, 5);
    strncpy(ssid, command.c_str(), sizeof(ssid) - 1);
    ssid[sizeof(ssid) - 1] = '\0'; // Ensure null termination
    terminal.println("SSID set to: " + String(ssid));
    terminal.flush();
  } else if (command.startsWith("pass:")) {
    command.remove(0, 5);
    strncpy(password, command.c_str(), sizeof(password) - 1);
    password[sizeof(password) - 1] = '\0'; // Ensure null termination
    terminal.println("Password set to: " + String(password));
    terminal.flush();
  } else if (command == "save") {
    terminal.println("Saving new WiFi credentials and restarting...");
    terminal.flush();
    delay(100);
    ESP.restart();
  } else {
    terminal.println("Unknown command: " + command);
    terminal.flush();
  }
}