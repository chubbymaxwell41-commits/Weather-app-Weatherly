# Weatherly.py
"""
Complete Weatherly application file (ready to copy/paste).

Features included:
- Welcome / Login / Register screens
- Admin dashboard (view/delete users, view logs)
- Main weather UI with search, favorites, recents
- Debounced autocomplete suggestions (local recents + favorites, plus background OpenWeather geocoding)
- Autocomplete does NOT steal focus; typing is not interrupted
- Search happens only when user clicks Search, presses Enter, or selects a suggestion
- Non-blocking network requests (threaded) and indeterminate progress bar while loading
- Settings screen (temperature unit, dynamic background) with "Settings saved" toast
- Robust image loading fallbacks and wind unit handling
- Uses local database.py for persistence (ensure database.py is present)
"""

import os
import threading
import time
import hashlib
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

import tkinter as tk
import customtkinter as ctk
import requests
from PIL import Image, ImageTk
from dotenv import load_dotenv

import database  # local module; ensure database.py is in same folder

# ---------- CONFIG ----------
load_dotenv()
API_KEY = os.getenv("OWM_API_KEY", "YOUR_API_KEY_HERE")
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODE_URL = "http://api.openweathermap.org/geo/1.0/direct"

ICON_DIR = "icons"  # keep your existing icon files here
GEOCODE_CACHE_TTL = 300  # seconds (5 minutes)
SEARCH_DEBOUNCE_MS = 600  # debounce delay for suggestion fetch in milliseconds
MIN_AUTOSUGGEST_CHARS = 3  # only fetch geocode suggestions for queries >= this
# -----------------------------

# initialize database (creates tables if necessary)
database.init_db()

# CTk appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def load_icon(name: str, size=(64, 64)) -> Optional[ImageTk.PhotoImage]:
    """Load an icon from ICON_DIR with safe fallback to None."""
    path = os.path.join(ICON_DIR, name)
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def map_weather_to_icon(weather_main: str, weather_id=None) -> str:
    main = (weather_main or "").lower()
    if main == "clear":
        return "sun.png"
    if main == "clouds":
        return "cloud.png"
    if main in ("rain", "drizzle"):
        return "rain.png"
    if main == "snow":
        return "snow.png"
    if main in ("thunderstorm",):
        return "thunder.png"
    return "cloud.png"


def background_for_weather(main: str) -> str:
    m = (main or "").lower()
    if m == "clear":
        return "#1E90FF"  # blue
    if m in ("clouds",):
        return "#6c7680"  # grey
    if m in ("rain", "drizzle"):
        return "#2b3a4a"  # dark blue
    if m in ("thunderstorm",):
        return "#1b2430"  # very dark
    if m == "snow":
        return "#9aa6b2"  # light grey
    return "#1f2630"  # default


# ------------------ Welcome Screen ------------------

class WelcomeScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(fg_color="#111111")

        # Left artwork
        left = ctk.CTkFrame(self, width=400, corner_radius=20, fg_color="#1f2630")
        left.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        try:
            img_left = Image.open("welcome.png")
            img_left = img_left.resize((160, 160))
            self.left_icon = ImageTk.PhotoImage(img_left)
            art_label = ctk.CTkLabel(left, image=self.left_icon, text="")
        except Exception:
            art_label = ctk.CTkLabel(left, text="Weatherly", font=("Arial", 20, "bold"))
        art_label.place(relx=0.5, rely=0.5, anchor="center")

        # Right container (login/register flows)
        self.right = ctk.CTkFrame(self, width=400, corner_radius=20, fg_color="#111111")
        self.right.pack(side="right", fill="y", padx=20, pady=20)
        self.right.pack_propagate(False)
        self.show_welcome_content()

    def show_welcome_content(self):
        for w in self.right.winfo_children():
            w.destroy()
        try:
            img = Image.open("welcome.png")
            img = img.resize((120, 120))
            self.welcome_icon = ImageTk.PhotoImage(img)
            icon = ctk.CTkLabel(self.right, image=self.welcome_icon, text="")
        except Exception:
            icon = ctk.CTkLabel(self.right, text="Weatherly", font=("Arial", 24, "bold"))
        icon.pack(pady=(80, 10))
        ctk.CTkLabel(self.right, text="Weatherly", font=("Arial", 28, "bold")).pack()
        ctk.CTkLabel(self.right, text="Weather App", font=("Arial", 14)).pack(pady=(0, 20))
        start_btn = ctk.CTkButton(self.right, text="Get Started", width=200, height=40, corner_radius=20,
                                  fg_color="#0d6efd", hover_color="#0953c8", command=self.show_login)
        start_btn.pack(pady=20)

    def show_login(self):
        for w in self.right.winfo_children():
            w.destroy()
        card = ctk.CTkFrame(self.right, width=350, height=360, corner_radius=20,
                            fg_color="#1a1a1a", border_width=2, border_color="#1f6eff")
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        ctk.CTkLabel(card, text="Login", font=("Arial", 22, "bold")).pack(pady=(18, 14))
        ctk.CTkLabel(card, text="Username").pack(anchor="w", padx=25)
        self.username_entry = ctk.CTkEntry(card, width=260, height=30, fg_color="#2b2b2b", border_color="#444")
        self.username_entry.pack(pady=(6, 12))
        ctk.CTkLabel(card, text="Password").pack(anchor="w", padx=25)
        self.password_entry = ctk.CTkEntry(card, width=260, height=30, fg_color="#2b2b2b", border_color="#444", show="*")
        self.password_entry.pack(pady=(6, 6))
        self.show_pw = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(card, text="Show password", variable=self.show_pw, command=self.toggle_password).pack(pady=(0, 8))
        self.error_label = ctk.CTkLabel(card, text="", text_color="red")
        self.error_label.pack(pady=(0, 6))
        ctk.CTkButton(card, text="Log In", height=36, width=260, corner_radius=14,
                      fg_color="#0d6efd", hover_color="#0953c8", command=self.login_user).pack(pady=(6, 8))
        ctk.CTkButton(card, text="Register", height=36, width=260, corner_radius=14,
                      fg_color="#444444", hover_color="#555555", command=self.show_register).pack()
        self.password_entry.bind("<Return>", lambda e: self.login_user())

    def toggle_password(self):
        if self.show_pw.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def login_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            self.error_label.configure(text="Please fill in all fields")
            return
        pw_hash = hash_pw(password)
        role = database.verify_user(username, pw_hash)
        if role == "admin":
            self.pack_forget()
            self.app.show_admin_dashboard()
        elif role == "user":
            self.pack_forget()
            self.app.current_user = username
            self.app.show_main_for_user()
        else:
            self.error_label.configure(text="Invalid username or password")

    def show_register(self):
        for w in self.right.winfo_children():
            w.destroy()
        card = ctk.CTkFrame(self.right, width=380, height=420, corner_radius=20,
                            fg_color="#1a1a1a", border_width=2, border_color="#1f6eff")
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)
        ctk.CTkLabel(card, text="Create Account", font=("Arial", 20, "bold")).pack(pady=(18, 12))
        ctk.CTkLabel(card, text="Username").pack(anchor="w", padx=25)
        self.reg_username = ctk.CTkEntry(card, width=300, height=30)
        self.reg_username.pack(pady=(6, 10))
        ctk.CTkLabel(card, text="Password").pack(anchor="w", padx=25)
        self.reg_password = ctk.CTkEntry(card, width=300, height=30, show="*")
        self.reg_password.pack(pady=(6, 10))
        ctk.CTkLabel(card, text="Confirm Password").pack(anchor="w", padx=25)
        self.reg_confirm = ctk.CTkEntry(card, width=300, height=30, show="*")
        self.reg_confirm.pack(pady=(6, 8))
        self.reg_show_pw = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(card, text="Show password", variable=self.reg_show_pw, command=self.toggle_register_password).pack(pady=(0, 8))
        self.reg_error = ctk.CTkLabel(card, text="", text_color="red")
        self.reg_error.pack(pady=(0, 6))
        ctk.CTkButton(card, text="Create Account", height=36, width=300, fg_color="#0d6efd", hover_color="#0953c8",
                      command=self.create_account).pack(pady=(6, 8))
        ctk.CTkButton(card, text="Back", height=34, width=160, fg_color="#444444", hover_color="#555555",
                      command=self.show_welcome_content).pack(pady=(6, 4))
        self.reg_confirm.bind("<Return>", lambda e: self.create_account())

    def toggle_register_password(self):
        if self.reg_show_pw.get():
            self.reg_password.configure(show="")
            self.reg_confirm.configure(show="")
        else:
            self.reg_password.configure(show="*")
            self.reg_confirm.configure(show="*")

    def create_account(self):
        uname = self.reg_username.get().strip()
        pw = self.reg_password.get().strip()
        confirm = self.reg_confirm.get().strip()
        if not uname or not pw or not confirm:
            self.reg_error.configure(text="All fields are required")
            return
        if pw != confirm:
            self.reg_error.configure(text="Passwords do not match")
            return
        pw_hash = hash_pw(pw)
        ok = database.add_user(uname, pw_hash, role="user")
        if not ok:
            self.reg_error.configure(text="Username already taken")
            return
        self.pack_forget()
        self.app.current_user = uname
        self.app.show_main_for_user()


# ------------------ Admin Dashboard ------------------

class AdminDashboard(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(fg_color="#101010")
        ctk.CTkLabel(self, text="Admin Dashboard", font=("Arial", 28, "bold")).pack(pady=20)
        stats = ctk.CTkFrame(self, fg_color="#1b1b1b", corner_radius=12)
        stats.pack(fill="x", padx=20, pady=(0, 15))
        self.total_label = ctk.CTkLabel(stats, text=f"Total Users: {database.get_user_count()}", font=("Arial", 16, "bold"))
        self.total_label.pack(padx=12, pady=10)
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20)
        left = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=16)
        left.pack(side="left", fill="both", expand=True, padx=10)
        ctk.CTkLabel(left, text="Users", font=("Arial", 20, "bold")).pack(pady=10)
        self.user_list = ctk.CTkScrollableFrame(left, fg_color="#222222", corner_radius=10)
        self.user_list.pack(fill="both", expand=True, padx=15, pady=10)
        self.selected_user = None
        self.load_users()
        ubtns = ctk.CTkFrame(left, fg_color="transparent")
        ubtns.pack(pady=10)
        ctk.CTkButton(ubtns, text="View User", width=120, command=self.view_user).pack(side="left", padx=6)
        ctk.CTkButton(ubtns, text="Delete User", width=120, fg_color="#c62828", hover_color="#8e0000", command=self.delete_user).pack(side="left", padx=6)
        right = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=16)
        right.pack(side="right", fill="both", expand=True, padx=10)
        ctk.CTkLabel(right, text="User Search Logs", font=("Arial", 20, "bold")).pack(pady=10)
        logs_top = ctk.CTkFrame(right, fg_color="transparent")
        logs_top.pack(pady=10)
        self.log_username = ctk.CTkEntry(logs_top, placeholder_text="Enter username", width=200)
        self.log_username.pack(side="left", padx=6)
        ctk.CTkButton(logs_top, text="Load Logs", width=120, command=self.load_logs).pack(side="left", padx=6)
        self.logs_list = ctk.CTkScrollableFrame(right, fg_color="#222222", corner_radius=10)
        self.logs_list.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkButton(self, text="Logout", fg_color="#444444", hover_color="#666", width=150, command=self.logout).pack(pady=15)

    def load_users(self):
        for w in self.user_list.winfo_children():
            w.destroy()
        users = database.get_all_users()
        self.user_rows = {}
        self.selected_user = None
        for username, role in users:
            row = ctk.CTkFrame(self.user_list, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)
            label = ctk.CTkLabel(row, text=f"{username} ({role})", font=("Arial", 14))
            label.pack(side="left", padx=10, pady=8)
            row.bind("<Button-1>", lambda e, u=username, r=row: self.select_user(u, r))
            label.bind("<Button-1>", lambda e, u=username, r=row: self.select_user(u, r))
            self.user_rows[username] = row

    def select_user(self, username, row_widget):
        self.selected_user = username
        for user, row in self.user_rows.items():
            row.configure(fg_color="#444444" if user == username else "#2b2b2b")
        try:
            self.log_username.delete(0, "end")
            self.log_username.insert(0, username)
        except Exception:
            pass

    def view_user(self):
        if not self.selected_user:
            return
        try:
            self.log_username.delete(0, "end")
            self.log_username.insert(0, self.selected_user)
        except Exception:
            pass
        logs = database.get_logs_for_user(self.selected_user)
        for w in self.logs_list.winfo_children():
            w.destroy()
        if not logs:
            ctk.CTkLabel(self.logs_list, text="No logs found").pack(pady=10)
            return
        for timestamp, city, temp in logs:
            row = ctk.CTkFrame(self.logs_list, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=f"{timestamp} — {city} ({temp}°C)", font=("Arial", 13)).pack(padx=10, pady=6)

    def delete_user(self):
        if not self.selected_user or self.selected_user == "admin":
            return
        database.delete_user(self.selected_user)
        self.selected_user = None
        self.total_label.configure(text=f"Total Users: {database.get_user_count()}")
        self.load_users()

    def load_logs(self):
        username = self.log_username.get().strip()
        for w in self.logs_list.winfo_children():
            w.destroy()
        logs = database.get_logs_for_user(username)
        if not logs:
            ctk.CTkLabel(self.logs_list, text="No logs found").pack(pady=10)
            return
        for timestamp, city, temp in logs:
            row = ctk.CTkFrame(self.logs_list, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=f"{timestamp} — {city} ({temp}°C)", font=("Arial", 13)).pack(padx=10, pady=6)

    def logout(self):
        self.app.current_user = None
        self.pack_forget()
        self.app.welcome = WelcomeScreen(self.app.container, self.app)
        self.app.welcome.pack(fill="both", expand=True)


# ------------------ Main Weather UI ------------------

class WeatherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Weatherly - Weather App")
        self.geometry("900x550")
        self.minsize(900, 500)
        self.container = ctk.CTkFrame(self, corner_radius=0)
        self.container.pack(fill="both", expand=True, padx=12, pady=12)

        # app state
        self.icon_cache: Dict[str, Any] = {}
        self.current_user = None
        self.settings = database.get_settings()
        self.temp_unit = self.settings["unit"]
        self.dynamic_bg = self.settings["dynamic_bg"]

        self.is_loading = False
        self._search_debounce_job = None
        self._suggest_win: Optional[tk.Toplevel] = None
        self._suggest_listbox: Optional[tk.Listbox] = None
        self._geocode_cache: Dict[str, Tuple[float, List[str]]] = {}  # q->(ts, results)

        # show welcome (first screen)
        self.welcome = WelcomeScreen(self.container, self)
        self.welcome.pack(fill="both", expand=True)

        # placeholders
        self.login_frame = None
        self.settings_frame = None
        self.main_frame = None
        self.admin_frame = None
        self.register_frame = None

    # --------------- screen flow helpers ----------------
    def show_login(self):
        try:
            self.welcome.pack_forget()
        except Exception:
            pass
        if self.login_frame is None or not getattr(self.login_frame, "winfo_exists", lambda: False)():
            self.login_frame = LoginScreen(self.container, app=self)
        self.login_frame.pack(fill="both", expand=True, padx=12, pady=12)

    def show_register_screen(self):
        try:
            if getattr(self, "welcome", None) and self.welcome.winfo_exists():
                self.welcome.pack_forget()
        except Exception:
            pass
        try:
            if getattr(self, "login_frame", None) and self.login_frame.winfo_exists():
                self.login_frame.pack_forget()
        except Exception:
            pass
        try:
            if getattr(self, "main_frame", None) and self.main_frame.winfo_exists():
                self.main_frame.pack_forget()
        except Exception:
            pass
        try:
            if getattr(self, "admin_frame", None) and self.admin_frame.winfo_exists():
                self.admin_frame.pack_forget()
        except Exception:
            pass
        if getattr(self, "register_frame", None) is None or not getattr(self.register_frame, "winfo_exists", lambda: False)():
            self.register_frame = RegisterScreen(self.container, self)
        self.register_frame.pack(fill="both", expand=True, padx=12, pady=12)

    def show_main_for_user(self):
        self.current_user = getattr(self, "current_user", None)
        if self.login_frame:
            self.login_frame.pack_forget()
        self.geometry("1200x720")
        self.build_main_ui()

    def show_admin_dashboard(self):
        if self.login_frame:
            self.login_frame.pack_forget()
        self.geometry("1200x720")
        if self.admin_frame is None or not getattr(self.admin_frame, "winfo_exists", lambda: False)():
            self.admin_frame = AdminDashboard(self.container, app=self)
        self.admin_frame.pack(fill="both", expand=True, padx=12, pady=12)

    # ---------------- Build main UI ----------------
    def build_main_ui(self):
        try:
            if self.main_frame:
                self.main_frame.destroy()
        except Exception:
            pass

        self.main_frame = ctk.CTkFrame(self.container, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        # left sidebar
        sidebar = ctk.CTkFrame(self.main_frame, width=90, corner_radius=12)
        sidebar.pack(side="left", fill="y", padx=(0, 12), pady=0)
        logo = ctk.CTkLabel(sidebar, text="🌬", font=("Arial", 20))
        logo.pack(pady=(18, 6))
        for name in ("Weather", "Settings"):
            if name == "Settings":
                btn = ctk.CTkButton(sidebar, text=name, width=80, corner_radius=12, command=self.show_settings)
            else:
                btn = ctk.CTkButton(sidebar, text=name, width=80, corner_radius=12, command=self.show_weather)
            btn.pack(pady=8)

        logout_btn = ctk.CTkButton(sidebar, text="Logout", width=80, corner_radius=12, fg_color="#b91c1c",
                                   hover_color="#7f1d1d", command=self.logout_user)
        logout_btn.pack(pady=20)

        # center area
        self.center = ctk.CTkFrame(self.main_frame, corner_radius=12)
        self.center.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=0)

        # search bar row
        search_row = ctk.CTkFrame(self.center, corner_radius=8)
        search_row.pack(fill="x", pady=(12, 6), padx=12)

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(search_row, textvariable=self.search_var, placeholder_text="Search for city e.g. London, Tokyo", width=380)
        self.search_entry.bind("<KeyRelease>", self._on_search_keyrelease)
        self.search_entry.bind("<Return>", lambda e: self._immediate_search_from_entry())
        self.search_entry.bind("<Down>", self._on_search_down_pressed)
        self.search_entry.pack(side="left", padx=(8, 6), pady=8)

        self.search_btn = ctk.CTkButton(search_row, text="Search", width=90, command=self.search_and_update)
        self.search_btn.pack(side="left", padx=(6, 6), pady=8)

        # indeterminate progress bar (hidden by default)
        self.loading_bar = ctk.CTkProgressBar(search_row, orientation="horizontal", mode="indeterminate", width=120)
        self.loading_bar.pack_forget()

        fav_btn = ctk.CTkButton(search_row, text="★", width=40, command=self.open_favorites_window)
        fav_btn.pack(side="right", padx=(4, 6), pady=8)
        recent_btn = ctk.CTkButton(search_row, text="🕒", width=40, command=self.open_recents_window)
        recent_btn.pack(side="right", padx=(6, 4), pady=8)

        # top info / main weather area
        top_info = ctk.CTkFrame(self.center, corner_radius=12)
        top_info.pack(fill="x", padx=12, pady=(6, 12))

        left_top = ctk.CTkFrame(top_info, corner_radius=8)
        left_top.pack(side="left", fill="both", expand=True, padx=(8, 6), pady=10)

        city_row = ctk.CTkFrame(left_top, corner_radius=8)
        city_row.pack(anchor="w", padx=12, pady=(6, 0))

        self.city_label = ctk.CTkLabel(city_row, text="Welcome", font=("Arial", 26, "bold"))
        self.city_label.pack(side="left")

        self.favorite_btn = ctk.CTkButton(city_row, text="☆", width=40, height=34, corner_radius=8, command=self.toggle_favorite)
        self.favorite_btn.pack(side="left", padx=(12, 0))

        self.chance_label = ctk.CTkLabel(left_top, text="Chance of rain: --", font=("Arial", 12))
        self.chance_label.pack(anchor="w", padx=12, pady=(6, 6))

        self.temp_label = ctk.CTkLabel(left_top, text="--°", font=("Arial", 56, "bold"))
        self.temp_label.pack(anchor="w", padx=12, pady=(6, 12))

        right_top = ctk.CTkFrame(top_info, width=220, corner_radius=8)
        right_top.pack(side="right", padx=(6, 8), pady=10)

        self.big_icon_label = ctk.CTkLabel(right_top, text="", font=("Arial", 14))
        self.big_icon_label.pack(padx=10, pady=10)

        hourly_frame = ctk.CTkFrame(self.center, corner_radius=12)
        hourly_frame.pack(fill="x", padx=12, pady=(6, 12))
        self.hourly_container = hourly_frame

        lower_frame = ctk.CTkFrame(self.center, corner_radius=12)
        lower_frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        self.info_real = ctk.CTkLabel(lower_frame, text="Real Feel: --°", font=("Arial", 14))
        self.info_real.pack(anchor="w", padx=12, pady=6)
        self.info_wind = ctk.CTkLabel(lower_frame, text="Wind: --", font=("Arial", 14))
        self.info_wind.pack(anchor="w", padx=12, pady=6)
        self.info_uv = ctk.CTkLabel(lower_frame, text="UV Index: --", font=("Arial", 14))
        self.info_uv.pack(anchor="w", padx=12, pady=6)

        # right column forecast
        self.right_col = ctk.CTkFrame(self.main_frame, width=320, corner_radius=12)
        self.right_col.pack(side="right", fill="y", padx=(12, 0), pady=0)

        heading = ctk.CTkLabel(self.right_col, text="5-DAY FORECAST", font=("Arial", 14, "bold"))
        heading.pack(pady=(12, 6))

        self.days_container = ctk.CTkScrollableFrame(self.right_col, corner_radius=8)
        self.days_container.pack(fill="both", expand=True, padx=10, pady=8)

        self.days_widgets = []
        for i in range(5):
            frame = ctk.CTkFrame(self.days_container, corner_radius=8, height=60)
            frame.pack(fill="x", pady=6, padx=6)
            lbl_day = ctk.CTkLabel(frame, text="", width=80, anchor="w", font=("Arial", 12))
            lbl_day.pack(side="left", padx=(8, 6))
            icon_lbl = ctk.CTkLabel(frame, text="")
            icon_lbl.pack(side="left", padx=6)
            temp_lbl = ctk.CTkLabel(frame, text="", anchor="e")
            temp_lbl.pack(side="right", padx=10)
            self.days_widgets.append((lbl_day, icon_lbl, temp_lbl))

        self.error_label = ctk.CTkLabel(self.center, text="", text_color="#ff4d4d", font=("Arial", 12))
        self.error_label.pack(anchor="w", padx=20, pady=(0, 6))

    # ---------------- Autocomplete & Debounce ----------------
    def _on_search_keyrelease(self, event):
        text = self.search_var.get().strip()
        if text:
            self._show_suggestions_local(text)
        else:
            self._hide_suggestions()
        # debounce schedule: only used to fetch/merge suggestions, not to auto-search
        try:
            if self._search_debounce_job:
                self.after_cancel(self._search_debounce_job)
        except Exception:
            pass
        self._search_debounce_job = self.after(SEARCH_DEBOUNCE_MS, lambda: self._debounce_fetch_suggestions(text))

    def _debounce_fetch_suggestions(self, text: str):
        """
        After debounce, fetch geocode suggestions (in background) if useful.
        This does not trigger a search and does not disable the entry, so typing will not be interrupted.
        """
        try:
            current = self.search_var.get().strip()
            if current == text and current:
                if len(current) >= MIN_AUTOSUGGEST_CHARS:
                    self._schedule_geocode_fetch(current)
        except Exception:
            pass

    def _immediate_search_from_entry(self):
        try:
            if self._search_debounce_job:
                self.after_cancel(self._search_debounce_job)
                self._search_debounce_job = None
        except Exception:
            pass
        self._hide_suggestions()
        self.search_and_update()

    def _gather_local_candidates(self) -> List[str]:
        candidates = []
        try:
            recents = database.get_recents(50)
            for _id, city, temp, time_s in recents:
                if city:
                    candidates.append(city)
        except Exception:
            pass
        try:
            favs = database.get_favorites()
            for city, temp, cond, date in favs:
                if city:
                    candidates.append(city)
        except Exception:
            pass
        seen = set()
        result = []
        for c in candidates:
            k = c.strip()
            if k and k.lower() not in seen:
                seen.add(k.lower())
                result.append(k)
        return result

    def _show_suggestions_local(self, query: str):
        ql = query.lower()
        candidates = self._gather_local_candidates()
        matches = [c for c in candidates if c.lower().startswith(ql)]
        if not matches:
            matches = [c for c in candidates if ql in c.lower()]
        self._show_suggestions(matches)
        if len(query) >= MIN_AUTOSUGGEST_CHARS:
            self._schedule_geocode_fetch(query)

    def _show_suggestions(self, items: List[str]):
        if not items:
            self._hide_suggestions()
            return
        if self._suggest_win and tk.Toplevel.winfo_exists(self._suggest_win):
            lb = self._suggest_listbox
            lb.delete(0, tk.END)
        else:
            self._suggest_win = tk.Toplevel(self)
            self._suggest_win.overrideredirect(True)
            self._suggest_win.attributes("-topmost", True)
            frame = tk.Frame(self._suggest_win, bg="#2b2b2b")
            frame.pack(fill="both", expand=True)
            lb = tk.Listbox(frame, bg="#2b2b2b", fg="#ffffff", highlightthickness=0, bd=0, activestyle="none")
            lb.pack(side="left", fill="both", expand=True)
            sb = tk.Scrollbar(frame, command=lb.yview)
            sb.pack(side="right", fill="y")
            lb.config(yscrollcommand=sb.set)
            lb.bind("<Double-Button-1>", lambda e: self._apply_selected_suggestion_and_search())
            lb.bind("<Return>", lambda e: self._apply_selected_suggestion_and_search())
            lb.bind("<Escape>", lambda e: self._hide_suggestions())
            self._suggest_listbox = lb
        for m in items:
            try:
                self._suggest_listbox.insert(tk.END, m)
            except Exception:
                pass
        try:
            self.update_idletasks()
            x = self.search_entry.winfo_rootx()
            y = self.search_entry.winfo_rooty() + self.search_entry.winfo_height()
            width = self.search_entry.winfo_width() + (self.search_btn.winfo_width() if hasattr(self, "search_btn") else 0) + 10
            self._suggest_win.geometry(f"{width}x150+{x}+{y}")
            # Do NOT force focus onto the popup — keep typing uninterrupted
        except Exception:
            pass

    def _hide_suggestions(self):
        try:
            if self._suggest_win:
                self._suggest_win.destroy()
        except Exception:
            pass
        self._suggest_win = None
        self._suggest_listbox = None

    def _apply_selected_suggestion_and_search(self):
        try:
            lb = self._suggest_listbox
            if not lb:
                return
            sel = lb.curselection()
            if not sel:
                return
            val = lb.get(sel[0])
            self.search_var.set(val)
            self._hide_suggestions()
            self.search_and_update()
        except Exception:
            pass

    def _on_search_down_pressed(self, event):
        # Move focus into suggestion list without stealing focus initially
        if self._suggest_listbox and self._suggest_listbox.size() > 0:
            try:
                self._suggest_listbox.focus_set()
                self._suggest_listbox.selection_clear(0, tk.END)
                self._suggest_listbox.selection_set(0)
                self._suggest_listbox.activate(0)
            except Exception:
                pass
            return "break"
        return None

    # ---------------- Geocoding thread + cache ----------------
    def _schedule_geocode_fetch(self, query: str):
        ql = query.lower()
        cached = self._geocode_cache.get(ql)
        if cached and (time.time() - cached[0]) < GEOCODE_CACHE_TTL:
            self._merge_geocode_suggestions(cached[1])
            return
        thread = threading.Thread(target=self._geocode_thread, args=(query,), daemon=True)
        thread.start()

    def _geocode_thread(self, query: str):
        ql = query.lower()
        params = {"q": query, "limit": 6, "appid": API_KEY}
        results: List[str] = []
        try:
            r = requests.get(GEOCODE_URL, params=params, timeout=8)
            r.raise_for_status()
            data = r.json()
            for item in data:
                name = item.get("name", "")
                state = item.get("state", "")
                country = item.get("country", "")
                display = name
                if state:
                    display += f", {state}"
                if country:
                    display += f", {country}"
                results.append(display)
        except Exception as e:
            print("Geocode error:", e)
        self._geocode_cache[ql] = (time.time(), results)
        try:
            self.after(0, lambda: self._merge_geocode_suggestions(results))
        except Exception:
            pass

    def _merge_geocode_suggestions(self, geocode_list: List[str]):
        try:
            existing = []
            if self._suggest_listbox:
                existing = [self._suggest_listbox.get(i) for i in range(self._suggest_listbox.size())]
            merged = []
            seen = set()
            for s in existing + geocode_list:
                k = s.strip()
                if k and k.lower() not in seen:
                    seen.add(k.lower())
                    merged.append(k)
            if merged:
                self._show_suggestions(merged)
        except Exception:
            pass

    # ------------- Networking & UI (search, update) ----------------
    def search_and_update(self):
        city = self.search_var.get().strip()
        if not city:
            return
        if self.is_loading:
            return
        self._hide_suggestions()
        self.start_loading()
        thread = threading.Thread(target=self._fetch_weather_thread, args=(city,), daemon=True)
        thread.start()

    def _fetch_weather_thread(self, city: str):
        units = "metric" if self.temp_unit == "C" else "imperial"
        params = {"q": city, "appid": API_KEY, "units": units}
        current_data = None
        forecast_data = None
        error = None
        try:
            r = requests.get(WEATHER_URL, params=params, timeout=12)
            try:
                current_json = r.json()
            except Exception:
                current_json = None
            if r.status_code != 200:
                msg = current_json.get("message") if isinstance(current_json, dict) else r.text
                if r.status_code == 404:
                    error = "not_found"
                else:
                    error = f"HTTP {r.status_code}: {msg}"
            else:
                current_data = current_json
            r2 = requests.get(FORECAST_URL, params=params, timeout=12)
            try:
                forecast_json = r2.json()
            except Exception:
                forecast_json = None
            if r2.status_code != 200:
                msg = forecast_json.get("message") if isinstance(forecast_json, dict) else r2.text
                error = error or f"Forecast HTTP {r2.status_code}: {msg}"
            else:
                forecast_data = forecast_json
        except requests.exceptions.RequestException as e:
            error = str(e)
        except Exception as e:
            error = str(e)
        self.after(0, lambda: self.on_fetch_complete(city, current_data, forecast_data, error))

    def on_fetch_complete(self, city, current_data, forecast_data, error):
        self.stop_loading()
        if error:
            if error == "not_found":
                self.city_label.configure(text="Not found")
                self.error_label.configure(text="City not found. Check spelling.")
            else:
                self.error_label.configure(text="Network/API error. See console.")
                print("Weather API error:", error)
            return
        if not current_data or (str(current_data.get("cod", "")) not in ("200", "200.0")):
            msg = current_data.get("message") if isinstance(current_data, dict) else None
            if msg:
                self.error_label.configure(text=f"API: {msg}")
            else:
                self.error_label.configure(text="City not found or invalid response.")
            self.city_label.configure(text="Not found")
            return
        if not forecast_data or (str(forecast_data.get("cod", "")) not in ("200", "200.0")):
            print("Forecast payload invalid; continuing with current weather only.")
            forecast_data = {"list": []}
        try:
            self.update_ui_with_data(current_data, forecast_data)
            self.error_label.configure(text="")
        except Exception as e:
            print("Update UI error:", e)
            self.error_label.configure(text="Error displaying weather.")
        # DB logging
        try:
            database.add_recent(current_data.get("name", city), int(round(current_data["main"]["temp"])))
        except Exception as e:
            print("Recent log error:", e)
        if self.current_user:
            try:
                database.log_user_search(self.current_user, current_data.get("name", city), int(round(current_data["main"]["temp"])))
            except Exception as e:
                print("User log error:", e)

    def start_loading(self):
        self.is_loading = True
        try:
            self.search_entry.configure(state="disabled")
        except Exception:
            pass
        try:
            self.search_btn.configure(state="disabled")
        except Exception:
            pass
        try:
            self.loading_bar.pack(side="left", padx=(6, 6))
            self.loading_bar.start()
        except Exception:
            pass
        try:
            self.error_label.configure(text="")
        except Exception:
            pass

    def stop_loading(self):
        self.is_loading = False
        try:
            self.search_entry.configure(state="normal")
        except Exception:
            pass
        try:
            self.search_btn.configure(state="normal")
        except Exception:
            pass
        try:
            self.loading_bar.stop()
            self.loading_bar.pack_forget()
        except Exception:
            pass

    def update_ui_with_data(self, current: Dict[str, Any], forecast: Dict[str, Any]):
        if not current or not isinstance(current, dict):
            self.error_label.configure(text="No weather data to display.")
            return
        city_name = current.get("name", "Unknown")
        temp = current.get("main", {}).get("temp")
        humidity = current.get("main", {}).get("humidity")
        wind_speed = current.get("wind", {}).get("speed")
        weather = current.get("weather", [{}])[0]
        desc = weather.get("description", "").title()
        main = weather.get("main", "")
        wid = weather.get("id", None)

        self.city_label.configure(text=city_name)
        self.chance_label.configure(text=f"Condition: {desc}")

        if getattr(self, "temp_unit", "C") == "C":
            self.temp_label.configure(text=f"{int(round(temp))}°C" if temp is not None else "--°C")
        else:
            self.temp_label.configure(text=f"{int(round(temp))}°F" if temp is not None else "--°F")

        try:
            if self.temp_unit == "C":
                if wind_speed is not None:
                    kmh = round(wind_speed * 3.6, 1)
                    self.info_wind.configure(text=f"Wind Speed: {kmh} km/h")
                else:
                    self.info_wind.configure(text="Wind Speed: --")
            else:
                if wind_speed is not None:
                    self.info_wind.configure(text=f"Wind Speed: {wind_speed} mph")
                else:
                    self.info_wind.configure(text="Wind Speed: --")
        except Exception:
            self.info_wind.configure(text="Wind Speed: --")

        self.info_uv.configure(text=f"Humidity: {humidity}%" if humidity is not None else "Humidity: --")
        pressure = current.get("main", {}).get("pressure")
        self.info_real.configure(text=f"Pressure: {pressure} hPa" if pressure is not None else "Pressure: --")

        try:
            if database.is_favorite(city_name):
                self.favorite_btn.configure(text="★")
            else:
                self.favorite_btn.configure(text="☆")
        except Exception:
            self.favorite_btn.configure(text="☆")

        icon_name = map_weather_to_icon(main, wid)
        big_icon = self.get_cached_icon(icon_name, size=(120, 120))
        if big_icon:
            self.big_icon_label.configure(image=big_icon, text="")
            self.big_icon_label.image = big_icon
        else:
            self.big_icon_label.configure(text=desc)

        if getattr(self, "dynamic_bg", True):
            color = background_for_weather(main)
        else:
            color = "#1f2630"
        try:
            self.center.configure(fg_color=color)
            for child in self.right_col.winfo_children():
                try:
                    child.configure(fg_color=color)
                except Exception:
                    pass
        except Exception:
            pass

        # hourly and 5-day update
        for widget in self.hourly_container.winfo_children():
            widget.destroy()
        hours = forecast.get("list", [])[:7]
        hr_frame = ctk.CTkFrame(self.hourly_container, corner_radius=8)
        hr_frame.pack(fill="x", padx=6, pady=8)
        for hr in hours:
            dt_txt = hr.get("dt_txt", "")
            tstr = dt_txt.split(" ")[1][:5] if dt_txt else ""
            temp_h = int(round(hr.get("main", {}).get("temp", 0)))
            w = hr.get("weather", [{}])[0]
            iconn = map_weather_to_icon(w.get("main", ""), w.get("id"))
            ic = self.get_cached_icon(iconn, size=(40, 40))
            cell = ctk.CTkFrame(hr_frame, corner_radius=8, width=110, height=120)
            cell.pack(side="left", padx=10, pady=6)
            cell.pack_propagate(False)
            ctk.CTkLabel(cell, text=tstr, font=("Arial", 11)).pack(padx=6, pady=(6, 2))
            if ic:
                lbl = ctk.CTkLabel(cell, image=ic, text="")
                lbl.image = ic
                lbl.pack()
            else:
                ctk.CTkLabel(cell, text=w.get("main", "")).pack()
            ctk.CTkLabel(cell, text=f"{temp_h}°", font=("Arial", 12, "bold")).pack(pady=(4, 8))

        days = {}
        conditions = {}
        for item in forecast.get("list", []):
            date = item.get("dt_txt", "").split(" ")[0]
            if not date:
                continue
            days.setdefault(date, []).append(item.get("main", {}).get("temp", 0))
            conditions.setdefault(date, item.get("weather", [{}])[0].get("main", "").lower())
        day_items = list(days.items())[:5]
        for label, icon_lbl, temp_lbl in self.days_widgets:
            label.configure(text="")
            icon_lbl.configure(text="", image=None)
            try:
                icon_lbl.image = None
            except Exception:
                pass
            temp_lbl.configure(text="")
        for i, (day, temps) in enumerate(day_items):
            label, icon_lbl, temp_lbl = self.days_widgets[i]
            dt = datetime.strptime(day, "%Y-%m-%d")
            label.configure(text=dt.strftime("%a"))
            tmax = int(round(max(temps))) if temps else 0
            tmin = int(round(min(temps))) if temps else 0
            temp_lbl.configure(text=f"{tmax}° / {tmin}°")
            cond = conditions.get(day, "clouds")
            icon_file = map_weather_to_icon(cond)
            icon_img = self.get_cached_icon(icon_file, size=(32, 32))
            if icon_img:
                icon_lbl.configure(image=icon_img, text="")
                icon_lbl.image = icon_img
            else:
                icon_lbl.configure(text=cond.title())

        self._last_city = city_name
        self._last_condition = main
        self._last_temp = int(round(temp)) if temp is not None else None

    def get_cached_icon(self, filename: str, size=(64, 64)):
        key = f"{filename}_{size[0]}x{size[1]}"
        if key in self.icon_cache:
            return self.icon_cache[key]
        img = load_icon(filename, size=size)
        if img:
            self.icon_cache[key] = img
            return img
        return None

    # favorites / recents windows, toggle, settings, toast...
    def open_favorites_window(self):
        try:
            win = ctk.CTkToplevel(self)
            win.title("Favorite Cities")
            win.geometry("420x420")
            win.lift(); win.focus_force(); win.attributes("-topmost", True); win.after(200, lambda: win.attributes("-topmost", False))
            ctk.CTkLabel(win, text="⭐ Favorite Cities", font=("Arial", 18, "bold")).pack(pady=(12, 6))
            fav_frame = ctk.CTkScrollableFrame(win)
            fav_frame.pack(fill="both", expand=True, padx=12, pady=12)
            favs = database.get_favorites()
            if not favs:
                ctk.CTkLabel(fav_frame, text="No favorites yet").pack(padx=8, pady=8)
            else:
                for city, temp, cond, date in favs:
                    row = ctk.CTkFrame(fav_frame)
                    row.pack(fill="x", pady=6, padx=6)
                    ctk.CTkLabel(row, text=city, anchor="w").pack(side="left", padx=6)
                    ctk.CTkLabel(row, text=f"{temp}°", anchor="e").pack(side="left", padx=6)
                    open_btn = ctk.CTkButton(row, text="Open", width=60, command=lambda c=city: (self.search_from_recents(c), win.destroy()))
                    open_btn.pack(side="right", padx=4)
                    remove_btn = ctk.CTkButton(row, text="Remove", width=70, command=lambda c=city: (database.remove_favorite(c), win.destroy(), self.open_favorites_window()))
                    remove_btn.pack(side="right", padx=4)
        except Exception as e:
            print("Open favorites window error:", e)

    def open_recents_window(self):
        try:
            win = ctk.CTkToplevel(self)
            win.title("Recent Searches")
            win.geometry("420x500")
            win.lift(); win.focus_force(); win.attributes("-topmost", True); win.after(200, lambda: win.attributes("-topmost", False))
            ctk.CTkLabel(win, text="🕒 Recent Searches", font=("Arial", 18, "bold")).pack(pady=(12, 6))
            rec_frame = ctk.CTkScrollableFrame(win)
            rec_frame.pack(fill="both", expand=True, padx=12, pady=12)
            recs = database.get_recents(20)
            if not recs:
                ctk.CTkLabel(rec_frame, text="No recents yet").pack(padx=8, pady=8)
            else:
                for _id, city, temp, time_s in recs:
                    row = ctk.CTkFrame(rec_frame)
                    row.pack(fill="x", pady=6, padx=6)
                    ctk.CTkLabel(row, text=city, anchor="w").pack(side="left", padx=6)
                    ctk.CTkLabel(row, text=f"{temp}°", anchor="e").pack(side="left", padx=6)
                    btn_research = ctk.CTkButton(row, text="Open", width=80, command=lambda c=city: (win.destroy(), self.search_from_recents(c)))
                    btn_research.pack(side="right", padx=6)
            ctk.CTkButton(win, text="Clear Recents", command=lambda: (database.clear_recents(), win.destroy(), self.open_recents_window())).pack(pady=10)
        except Exception as e:
            print("Open recents window error:", e)

    def search_from_recents(self, city_name: str):
        self.search_var.set(city_name)
        self.search_and_update()

    def toggle_favorite(self):
        try:
            city = getattr(self, "_last_city", None)
            if not city:
                return
            city = city.strip()
            if database.is_favorite(city):
                database.remove_favorite(city)
                self.favorite_btn.configure(text="☆")
            else:
                database.add_favorite(city, self._last_temp or 0, self._last_condition or "")
                self.favorite_btn.configure(text="★")
        except Exception as e:
            print("Favorite toggle error:", e)

    def show_settings(self):
        try:
            if self.center:
                self.center.pack_forget()
        except Exception:
            pass
        try:
            if self.right_col:
                self.right_col.pack_forget()
        except Exception:
            pass
        if self.settings_frame is None or not getattr(self.settings_frame, "winfo_exists", lambda: False)():
            self.settings_frame = SettingsScreen(self.main_frame, back_cb=self.show_weather, app=self)
        self.settings_frame.pack(side="left", fill="both", expand=True, padx=12, pady=12)

    def show_weather(self):
        try:
            if self.settings_frame:
                self.settings_frame.pack_forget()
        except Exception:
            pass
        try:
            self.center.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=0)
            self.right_col.pack(side="right", fill="y", padx=(12, 0), pady=0)
        except Exception:
            pass

    def rebuild_main(self):
        if self.main_frame:
            self.main_frame.destroy()
            self.build_main_ui()

    def logout_user(self):
        self.current_user = None
        try:
            self.main_frame.pack_forget()
        except Exception:
            pass
        self.welcome = WelcomeScreen(self.container, self)
        self.welcome.pack(fill="both", expand=True)

    def show_toast(self, message: str, duration: int = 1400):
        try:
            toast = ctk.CTkToplevel(self)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            lbl = ctk.CTkLabel(toast, text=message, fg_color="#2b2b2b", text_color="#ffffff",
                               corner_radius=10, padx=12, pady=8, font=("Arial", 11))
            lbl.pack()
            self.update_idletasks()
            w = lbl.winfo_reqwidth()
            h = lbl.winfo_reqheight()
            x = self.winfo_rootx() + max(10, self.winfo_width() - w - 30)
            y = self.winfo_rooty() + max(10, self.winfo_height() - h - 40)
            toast.geometry(f"+{x}+{y}")
            toast.after(duration, toast.destroy)
        except Exception as e:
            print("Toast error:", e)


# ----------------- SettingsScreen -----------------

class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, back_cb, app):
        super().__init__(parent)
        self.back_cb = back_cb
        self.app = app
        self.configure(corner_radius=20)
        ctk.CTkLabel(self, text="Settings", font=("Arial", 28, "bold")).pack(pady=30)
        self.unit_var = ctk.StringVar(value=self.app.settings.get("unit", "C"))
        unit_frame = ctk.CTkFrame(self, corner_radius=12)
        unit_frame.pack(pady=10, padx=40, fill="x")
        ctk.CTkLabel(unit_frame, text="Temperature Unit").pack(side="left", padx=10)
        ctk.CTkRadioButton(unit_frame, text="°C", variable=self.unit_var, value="C", command=self.set_unit).pack(side="left", padx=10)
        ctk.CTkRadioButton(unit_frame, text="°F", variable=self.unit_var, value="F", command=self.set_unit).pack(side="left", padx=10)
        bg_frame = ctk.CTkFrame(self, corner_radius=12)
        bg_frame.pack(pady=10, padx=40, fill="x")
        ctk.CTkLabel(bg_frame, text="Dynamic Background").pack(side="left", padx=10)
        self.bg_var = ctk.BooleanVar(value=self.app.settings.get("dynamic_bg", True))
        ctk.CTkSwitch(bg_frame, text="On / Off", variable=self.bg_var, command=self.toggle_bg).pack(side="right", padx=10)
        clear_frame = ctk.CTkFrame(self, corner_radius=12)
        clear_frame.pack(pady=20, padx=40, fill="x")
        ctk.CTkButton(clear_frame, text="Clear Recents", command=self.clear_recents).pack(pady=10, fill="x")
        ctk.CTkButton(clear_frame, text="Clear Favorites", command=self.clear_favorites).pack(pady=10, fill="x")

    def set_unit(self):
        new_unit = self.unit_var.get()
        self.app.temp_unit = new_unit
        database.save_settings(new_unit, self.bg_var.get())
        self.app.settings = database.get_settings()
        self.app.rebuild_main()
        try:
            self.app.show_toast("Settings saved")
        except Exception:
            pass

    def toggle_bg(self):
        database.save_settings(self.unit_var.get(), self.bg_var.get())
        self.app.settings = database.get_settings()
        self.app.rebuild_main()
        try:
            self.app.show_toast("Settings saved")
        except Exception:
            pass

    def clear_recents(self):
        database.clear_recents()

    def clear_favorites(self):
        for city, *_ in database.get_favorites():
            database.remove_favorite(city)


# ----------------- LoginScreen and RegisterScreen used in flows -----------------

class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="#111111")
        self.app = app
        container = ctk.CTkFrame(self, width=350, height=390, corner_radius=20, fg_color="#1a1a1a", border_width=2, border_color="#1f6eff")
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.pack_propagate(False)
        ctk.CTkLabel(container, text="Login", font=("Arial", 20, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(container, text="Username:").pack(anchor="w", padx=25)
        self.username_entry = ctk.CTkEntry(container, width=260, height=30, fg_color="#2b2b2b", border_color="#444")
        self.username_entry.pack(pady=(5, 15))
        ctk.CTkLabel(container, text="Password:").pack(anchor="w", padx=25)
        self.password_entry = ctk.CTkEntry(container, width=260, height=30, fg_color="#2b2b2b", border_color="#444", show="*")
        self.password_entry.pack(pady=(5, 5))
        self.show_pw = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(container, text="Show password", variable=self.show_pw, command=self.toggle_password).pack(pady=(0, 10))
        self.error = ctk.CTkLabel(container, text="", text_color="#ff4d4d")
        self.error.pack(pady=(0, 10))
        ctk.CTkButton(container, text="Log In", height=35, width=260, corner_radius=12, fg_color="#0d6efd", hover_color="#0953c8", command=self.attempt_login).pack(pady=(5, 10))
        ctk.CTkButton(container, text="Register", height=35, width=260, corner_radius=12, fg_color="#3a3a3a", hover_color="#4a4a4a", command=self.show_register).pack()
        self.password_entry.bind("<Return>", lambda e: self.attempt_login())

    def toggle_password(self):
        if self.show_pw.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            self.error.configure(text="Enter username and password")
            return
        password_hash = hash_pw(password)
        role = database.verify_user(username, password_hash)
        if role:
            self.app.current_user = username
            if role == "admin":
                self.app.show_admin_dashboard()
            else:
                self.app.show_main_for_user()
        else:
            self.error.configure(text="Invalid username or password")

    def show_register(self):
        self.pack_forget()
        register_screen = RegisterScreen(self.master, self.app)
        register_screen.pack(fill="both", expand=True)


class RegisterScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        ctk.CTkLabel(self, text="Register", font=("Arial", 24, "bold")).pack(pady=(30, 8))
        form = ctk.CTkFrame(self, corner_radius=8)
        form.pack(padx=40, pady=8)
        ctk.CTkLabel(form, text="Username").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.username_entry = ctk.CTkEntry(form, width=260)
        self.username_entry.grid(row=0, column=1, padx=6, pady=6)
        ctk.CTkLabel(form, text="Password").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.password_entry = ctk.CTkEntry(form, show="*", width=260)
        self.password_entry.grid(row=1, column=1, padx=6, pady=6)
        self.error = ctk.CTkLabel(self, text="", text_color="#ff4d4d")
        self.error.pack(pady=(4, 6))
        btn_row = ctk.CTkFrame(self)
        btn_row.pack(pady=12)
        ctk.CTkButton(btn_row, text="Create account", width=140, command=self.create_account).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Back to Login", width=140, command=self.back_to_login).pack(side="left", padx=8)

    def create_account(self):
        username = self.username_entry.get().strip()
        pw = self.password_entry.get().strip()
        if not username or not pw:
            self.error.configure(text="Enter username and password")
            return
        pw_hash = hash_pw(pw)
        ok = database.add_user(username, pw_hash, role="user")
        if not ok:
            self.error.configure(text="Username taken")
            return
        self.app.current_user = username
        self.pack_forget()
        self.app.show_main_for_user()

    def back_to_login(self):
        self.pack_forget()
        ls = LoginScreen(self.master, self.app)
        ls.pack(fill="both", expand=True, padx=12, pady=12)


# ----------------- App entrypoint -----------------

if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()

