# Weather Application (Python)

A Python-based weather application that allows users to search for cities and view current weather conditions and forecasts.  
The app stores search history and includes basic admin functionality.

This project was built as part of my software engineering learning journey and is intended to demonstrate backend logic, UI integration, API usage, and database handling.

---

## Features

- Search weather by city name
- Displays current weather information
- Forecast support
- Search history stored in a local database
- Admin view for user activity/logs
- Error handling for invalid city names or API issues

---

## Tech Stack

- Python
- Weather API (e.g. OpenWeatherMap)
- SQLite (local database)
- Tkinter / CustomTkinter (UI)  
  *(update this if different)*
- Requests library

---

## Project Structure

weather-app/
│
├── Weatherly.py
├── database.py
├── assets/
├── weather.db
└── README.md


*(Structure may vary depending on implementation)*

---

## How It Works (High-Level)

1. User enters a city name in the UI
2. The app sends a request to the weather API
3. Weather data is processed and displayed
4. Search history is saved in the database
5. Admin users can view logs and user activity

---

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/chubbymaxwell41-commits/Weather-app-Weatherly.git
2. Install dependencies:

pip install requests

3. Add your API key:

Create a .env file or update the API key variable in the code

Replace YOUR_API_KEY_HERE with your actual key

4. Run the application:

python main.py

## Design Credits

UI design inspired by existing weather app layouts and design concepts.
Implementation, logic, and functionality were developed by me.

## Challenges & Learnings

Handling API errors and invalid user input
Debugging UI-to-backend communication
Structuring a Python project properly
Working with databases for logging and history
Learning how to debug using print statements and logs

## Future Improvements

User authentication
Exportable weather/search logs
Improved UI responsiveness
Better error messages
Deployment-ready version

## Notes

This project is a learning-focused application and will continue to improve as I gain more experience.
