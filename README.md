# 🌦️ Weatherly — Python Weather Application

Weatherly is a Python-based desktop weather application that allows users to search for cities and view current weather conditions and forecasts.

The app stores search history locally and includes a basic admin view for monitoring user activity and logs.

This project was built as part of my Software Engineering learning journey and is intended to demonstrate backend logic, UI integration, API usage, and database handling.

# 📸 Screenshots

(Add screenshots of your app UI here)

![Main Dashboard](screenshots/dashboard.png)
![Forecast View](screenshots/forecast.png)

# Features

🔍 Search weather by city name

🌡️ Display current weather information

📅 Forecast support

🗃️ Search history stored in a local SQLite database

🛠️ Admin view for user activity and logs

⚠️ Error handling for invalid city names and API issues

🛠️ Tech Stack

## Language: Python

UI: Tkinter / CustomTkinter

API: OpenWeatherMap (or similar weather API)

Database: SQLite (local)

Libraries: requests

## 📂 Project Structure
weather-app

├── Weatherly.py

├── database.py

├── assets/

├── icons

├── weather.db

└── README.md

# ⚙️ How It Works

User enters a city name in the UI

The app sends a request to the weather API

Weather data is processed and displayed

Search history is saved in the database

Admin users can view logs and user activity

# 🧑‍💻 Setup Instructions

Admin Login: admin, password: admin123

1️⃣ Clone the repository
git clone https://github.com/chubbymaxwell41-commits/Weather-app-Weatherly.git

2️⃣ Install dependencies
pip install requests

3️⃣ Add your API key

Create a .env file or

Update the API key variable in the code

Replace:
YOUR_API_KEY_HERE

with your actual API key.

4️⃣ Run the application
python Weatherly.py

# 🎨 Design Credits

UI design inspired by existing weather app layouts and design concepts.
Implementation, logic, and functionality were developed by me.

# 🧠 Challenges & Learnings

Handling API errors and invalid user input

Debugging UI-to-backend communication

Structuring a Python project properly

Working with databases for logging and history

Learning debugging using print statements and logs

# 🔮 Future Improvements

User authentication

Exportable weather/search logs

Improved UI responsiveness

Better error messages

Deployment-ready version

# 📌 Notes

This project is learning-focused and will continue to improve as I gain more experience in software engineering and Python development.
