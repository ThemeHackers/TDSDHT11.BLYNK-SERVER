# TDSDHT11.BLYNK-SERVER
- This code is suitable for future water quality testing applications such as business, agriculture or home use.
- It also has many functions such as displaying graphs in Blynk cloud and displaying statistical values ​​via webapp.
> **Note :** You can use this code but please provide me with the source. Thank you for checking out my work.
# IoT Monitoring System with Flask

This project is a **web application for monitoring and visualizing IoT sensor data** connected via the Blynk platform. It uses **FastAPI** as the backend framework to fetch real-time data from various sensors and display the results efficiently. The system also stores sensor data for short-term analysis and computes statistical values such as mean, median, and standard deviation.

---

## Key Features

- **Real-Time Data Fetching**: Retrieves sensor data (TDS, EC, Temperature, and Humidity) from the Blynk platform in real time.
- **Automatic Statistical Computation**: Displays computed statistics like mean, median, and standard deviation for the collected data.
- **Data Storage**: Stores up to 200 data points per sensor for historical analysis.
- **Data Reset Functionality**: Allows the user to reset all stored data and statistics.
- **Hardware Connectivity Check**: Verifies the connection status of the IoT device via the Blynk API.
- **Network Usage Monitoring**: Tracks the network usage for requests and responses during data fetching.

---

## Technologies Used

- **FastAPI**: Backend framework for handling web requests.
- **Jinja2**: Templating engine used to render the HTML dashboard.
- **Blynk API**: Interface for connecting to IoT devices and fetching sensor data.
- **Asyncio**: Used for asynchronous tasks to fetch data and handle multiple requests concurrently.
- **Colorama**: Used for colored output in the terminal for better readability.
- **Statistics Module**: For calculating statistical values like mean, median, and standard deviation.
- **Uvicorn**: ASGI server for running the FastAPI application.

---




