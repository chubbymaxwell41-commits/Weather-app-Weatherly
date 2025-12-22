# Weatherly.py
import customtkinter as ctk
import requests
from PIL import Image, ImageTk
import os
from datetime import datetime
import hashlib
import database  # local module, make sure database.py is in same folder
import sqlite3

# ---------- CONFIG ----------
API_KEY = "eac408cbe256621670200c5d87db8ac4"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

ICON_DIR = "icons"  # keep your existing icons here
# -----------------------------

# initialize DB
database.init_db()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_icon(name, size=(64, 64)):
    path = os.path.join(ICON_DIR, name)
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def map_weather_to_icon(weather_main, weather_id=None):
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

def background_for_weather(main):
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

        # ========== LEFT SIDE ==========
        left = ctk.CTkFrame(self, width=400, corner_radius=20, fg_color="#1f2630")
        left.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        # Load your custom welcome icon for the left side
        img_left = Image.open("welcome.png")
        img_left = img_left.resize((160, 160))  # you can increase or reduce this
        self.left_icon = ImageTk.PhotoImage(img_left)

        art_label = ctk.CTkLabel(left, image=self.left_icon, text="")
        art_label.place(relx=0.5, rely=0.5, anchor="center")

        # ========== RIGHT SIDE ==========
        self.right = ctk.CTkFrame(self, width=400, corner_radius=20, fg_color="#111111")
        self.right.pack(side="right", fill="y", padx=20, pady=20)
        self.right.pack_propagate(False)

        # Start with welcome content
        self.show_welcome_content()

    # ================== FIRST VIEW ==================
    def show_welcome_content(self):
        # clear right
        for w in self.right.winfo_children():
            w.destroy()

        # Load custom welcome icon
        img = Image.open("welcome.png")
        img = img.resize((120, 120))  # adjust size if you want
        self.welcome_icon = ImageTk.PhotoImage(img)

        icon = ctk.CTkLabel(self.right, image=self.welcome_icon, text="")
        icon.pack(pady=(80, 10))

        ctk.CTkLabel(self.right, text="Weatherly", font=("Arial", 28, "bold")).pack()
        ctk.CTkLabel(self.right, text="Weather App", font=("Arial", 14)).pack(pady=(0, 20))

        start_btn = ctk.CTkButton(
            self.right,
            text="Get Started",
            width=200,
            height=40,
            corner_radius=20,
            fg_color="#0d6efd",
            hover_color="#0953c8",
            command=self.show_login
        )
        start_btn.pack(pady=20)

    # ================== LOGIN VIEW (in right pane) ==================
    def show_login(self):
        for w in self.right.winfo_children():
            w.destroy()

        # login card
        card = ctk.CTkFrame(
            self.right,
            width=350,
            height=360,
            corner_radius=20,
            fg_color="#1a1a1a",
            border_width=2,
            border_color="#1f6eff"
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="Login", font=("Arial", 22, "bold")).pack(pady=(18, 14))

        # Username
        ctk.CTkLabel(card, text="Username").pack(anchor="w", padx=25)
        self.username_entry = ctk.CTkEntry(card, width=260, height=30,
                                           fg_color="#2b2b2b", border_color="#444")
        self.username_entry.pack(pady=(6, 12))

        # Password
        ctk.CTkLabel(card, text="Password").pack(anchor="w", padx=25)
        self.password_entry = ctk.CTkEntry(card, width=260, height=30,
                                           fg_color="#2b2b2b", border_color="#444",
                                           show="*")
        self.password_entry.pack(pady=(6, 6))

        # Show password
        self.show_pw = ctk.BooleanVar(value=False)
        show_pw_toggle = ctk.CTkSwitch(card, text="Show password", variable=self.show_pw, command=self.toggle_password)
        show_pw_toggle.pack(pady=(0, 8))

        # Error label
        self.error_label = ctk.CTkLabel(card, text="", text_color="red")
        self.error_label.pack(pady=(0, 6))

        # Login button
        login_btn = ctk.CTkButton(card, text="Log In", height=36, width=260,
                                  corner_radius=14, fg_color="#0d6efd", hover_color="#0953c8",
                                  command=self.login_user)
        login_btn.pack(pady=(6, 8))

        # Register button (opens register IN RIGHT PANE)
        register_btn = ctk.CTkButton(card, text="Register", height=36, width=260,
                                     corner_radius=14, fg_color="#444444", hover_color="#555555",
                                     command=self.show_register)
        register_btn.pack()

        # Enter = login
        self.password_entry.bind("<Return>", lambda e: self.login_user())

    # ========= Show / hide password =========
    def toggle_password(self):
        if self.show_pw.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    # ========= Login logic =========
    def login_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self.error_label.configure(text="Please fill in all fields")
            return

        pw_hash = hash_pw(password)
        role = database.verify_user(username, pw_hash)

        if role == "admin":
            # hide welcome (so the container is free) and go to admin
            self.pack_forget()
            self.app.show_admin_dashboard()
        elif role == "user":
            self.pack_forget()
            self.app.current_user = username
            self.app.show_main_for_user()
        else:
            self.error_label.configure(text="Invalid username or password")

    # ================== REGISTER VIEW (in right pane) ==================
    def show_register(self):
        for w in self.right.winfo_children():
            w.destroy()

        card = ctk.CTkFrame(
            self.right,
            width=380,
            height=420,
            corner_radius=20,
            fg_color="#1a1a1a",
            border_width=2,
            border_color="#1f6eff"
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="Create Account", font=("Arial", 20, "bold")).pack(pady=(18, 12))

        # Username
        ctk.CTkLabel(card, text="Username").pack(anchor="w", padx=25)
        self.reg_username = ctk.CTkEntry(card, width=300, height=30)
        self.reg_username.pack(pady=(6, 10))

        # Password
        ctk.CTkLabel(card, text="Password").pack(anchor="w", padx=25)
        self.reg_password = ctk.CTkEntry(card, width=300, height=30, show="*")
        self.reg_password.pack(pady=(6, 10))

        # Confirm
        ctk.CTkLabel(card, text="Confirm Password").pack(anchor="w", padx=25)
        self.reg_confirm = ctk.CTkEntry(card, width=300, height=30, show="*")
        self.reg_confirm.pack(pady=(6, 8))

        # Show password for register
        self.reg_show_pw = ctk.BooleanVar(value=False)
        reg_show = ctk.CTkSwitch(card, text="Show password", variable=self.reg_show_pw,
                                 command=self.toggle_register_password)
        reg_show.pack(pady=(0, 8))

        # Error label
        self.reg_error = ctk.CTkLabel(card, text="", text_color="red")
        self.reg_error.pack(pady=(0, 6))

        # Create account button
        create_btn = ctk.CTkButton(card, text="Create Account", height=36, width=300,
                                   fg_color="#0d6efd", hover_color="#0953c8",
                                   command=self.create_account)
        create_btn.pack(pady=(6, 8))

        # Back to welcome (not whole-screen back)
        back_btn = ctk.CTkButton(card, text="Back", height=34, width=160,
                                 fg_color="#444444", hover_color="#555555",
                                 command=self.show_welcome_content)
        back_btn.pack(pady=(6, 4))

        # Enter on confirm triggers create
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
        # hash pw and add user (normal user role)
        pw_hash = hash_pw(pw)
        ok = database.add_user(uname, pw_hash, role="user")
        if not ok:
            self.reg_error.configure(text="Username already taken")
            return

        # success: auto-login the new user and go to main UI
        self.pack_forget()
        self.app.current_user = uname
        self.app.show_main_for_user()



# ------------------ Login / Register Screens ------------------

class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="#111111")
        self.app = app

        # Center container
        container = ctk.CTkFrame(
            self,
            width=350,
            height=390,   # <-- increased height
            corner_radius=20,
            fg_color="#1a1a1a",
            border_width=2,
            border_color="#1f6eff"
        )
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.pack_propagate(False)

        # Title
        title = ctk.CTkLabel(container, text="Login", font=("Arial", 20, "bold"))
        title.pack(pady=(20, 10))

        # Username
        user_label = ctk.CTkLabel(container, text="Username:")
        user_label.pack(anchor="w", padx=25)

        self.username_entry = ctk.CTkEntry(
            container,
            width=260,
            height=30,
            fg_color="#2b2b2b",
            border_color="#444"
        )
        self.username_entry.pack(pady=(5, 15))

        # Password
        pass_label = ctk.CTkLabel(container, text="Password:")
        pass_label.pack(anchor="w", padx=25)

        self.password_entry = ctk.CTkEntry(
            container,
            width=260,
            height=30,
            fg_color="#2b2b2b",
            border_color="#444",
            show="*"
        )
        self.password_entry.pack(pady=(5, 5))

        # Show / Hide password
        self.show_pw = ctk.BooleanVar(value=False)

        show_pw_toggle = ctk.CTkSwitch(
            container,
            text="Show password",
            variable=self.show_pw,
            command=self.toggle_password
        )
        show_pw_toggle.pack(pady=(0, 10))

        # Error message
        self.error = ctk.CTkLabel(container, text="", text_color="#ff4d4d")
        self.error.pack(pady=(0, 10))

        # Login button (blue)
        login_btn = ctk.CTkButton(
            container,
            text="Log In",
            height=35,
            width=260,
            corner_radius=12,
            fg_color="#0d6efd",
            hover_color="#0953c8",
            command=self.attempt_login
        )
        login_btn.pack(pady=(5, 10))

        # Register button (grey)
        register_btn = ctk.CTkButton(
            container,
            text="Register",
            height=35,
            width=260,
            corner_radius=12,
            fg_color="#3a3a3a",
            hover_color="#4a4a4a",
            command=self.show_register
        )
        register_btn.pack()

        # Press Enter to login
        self.password_entry.bind("<Return>", lambda e: self.attempt_login())

    # ===== Show / hide password =====
    def toggle_password(self):
        if self.show_pw.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    # ====== LOGIN ACTION ======
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

    # ====== GO TO REGISTER ======
    def show_register(self):
        self.pack_forget()
        register_screen = RegisterScreen(self.master, self.app)
        register_screen.pack(fill="both", expand=True)


class RegisterScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(corner_radius=12)

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

        # only normal users allowed by registration flow
        pw_hash = hash_pw(pw)
        ok = database.add_user(username, pw_hash, role="user")
        if not ok:
            self.error.configure(text="Username taken")
            return

        # success -> auto-login user and go to main app
        self.app.current_user = username
        self.pack_forget()
        self.app.show_main_for_user()

    def back_to_login(self):
        self.pack_forget()
        ls = LoginScreen(self.master, self.app)
        ls.pack(fill="both", expand=True, padx=12, pady=12)


# ------------------ Admin Dashboard ------------------

class AdminDashboard(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(fg_color="#101010")

        # ================= HEADER ================
        ctk.CTkLabel(
            self,
            text="Admin Dashboard",
            font=("Arial", 28, "bold")
        ).pack(pady=20)

        # ================= STATS BAR ================
        stats = ctk.CTkFrame(self, fg_color="#1b1b1b", corner_radius=12)
        stats.pack(fill="x", padx=20, pady=(0, 15))

        self.total_label = ctk.CTkLabel(
            stats,
            text=f"Total Users: {database.get_user_count()}",
            font=("Arial", 16, "bold")
        )
        self.total_label.pack(padx=12, pady=10)

        # ================= MAIN SPLIT (LEFT + RIGHT) ================
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20)

        # ============================================================
        #                     LEFT PANEL (USERS)
        # ============================================================
        left = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=16)
        left.pack(side="left", fill="both", expand=True, padx=10)

        ctk.CTkLabel(left, text="Users", font=("Arial", 20, "bold")).pack(pady=10)

        self.user_list = ctk.CTkScrollableFrame(left, fg_color="#222222", corner_radius=10)
        self.user_list.pack(fill="both", expand=True, padx=15, pady=10)

        self.selected_user = None
        self.load_users()

        # === user control buttons ===
        ubtns = ctk.CTkFrame(left, fg_color="transparent")
        ubtns.pack(pady=10)

        ctk.CTkButton(
            ubtns, text="View User", width=120,
            command=self.view_user
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            ubtns, text="Delete User", width=120,
            fg_color="#c62828", hover_color="#8e0000",
            command=self.delete_user
        ).pack(side="left", padx=6)

        # ============================================================
        #                      RIGHT PANEL (LOGS)
        # ============================================================
        right = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=16)
        right.pack(side="right", fill="both", expand=True, padx=10)

        ctk.CTkLabel(right, text="User Search Logs", font=("Arial", 20, "bold")).pack(pady=10)

        # search logs controls
        logs_top = ctk.CTkFrame(right, fg_color="transparent")
        logs_top.pack(pady=10)

        self.log_username = ctk.CTkEntry(logs_top, placeholder_text="Enter username", width=200)
        self.log_username.pack(side="left", padx=6)

        ctk.CTkButton(
            logs_top, text="Load Logs", width=120,
            command=self.load_logs
        ).pack(side="left", padx=6)

        # logs display
        self.logs_list = ctk.CTkScrollableFrame(right, fg_color="#222222", corner_radius=10)
        self.logs_list.pack(fill="both", expand=True, padx=15, pady=10)

        # ================= LOGOUT =================
        ctk.CTkButton(
            self,
            text="Logout",
            fg_color="#444444",
            hover_color="#666",
            width=150,
            command=self.logout
        ).pack(pady=15)

    # ============================================================
    #                     LOAD USERS
    # ============================================================
    def load_users(self):
        # clear list first
        for w in self.user_list.winfo_children():
            w.destroy()

        users = database.get_all_users()  # [(username, role)]

        self.user_rows = {}  # store rows so we can highlight one later
        self.selected_user = None

        for username, role in users:
            row = ctk.CTkFrame(self.user_list, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)

            label = ctk.CTkLabel(row, text=f"{username} ({role})", font=("Arial", 14))
            label.pack(side="left", padx=10, pady=8)

            # make both row and label clickable
            row.bind("<Button-1>", lambda e, u=username, r=row: self.select_user(u, r))
            label.bind("<Button-1>", lambda e, u=username, r=row: self.select_user(u, r))

            self.user_rows[username] = row

    def select_user(self, username, row_widget):
        self.selected_user = username

        # highlight clicked row, un-highlight others
        for user, row in self.user_rows.items():
            if user == username:
                row.configure(fg_color="#444444")
            else:
                row.configure(fg_color="#2b2b2b")

        # auto-fill log search field
        try:
            self.log_username.delete(0, "end")
            self.log_username.insert(0, username)
        except:
            pass

    # ============================================================
    #                     VIEW USER DETAILS
    # ============================================================
    def view_user(self):
        if not self.selected_user:
            return

        # Put the username in the logs input (optional)
        try:
            self.log_username.delete(0, "end")
            self.log_username.insert(0, self.selected_user)
        except:
            pass

        # Load logs for selected user
        logs = database.get_logs_for_user(self.selected_user)

        # Clear current logs
        for w in self.logs_list.winfo_children():
            w.destroy()

        if not logs:
            ctk.CTkLabel(self.logs_list, text="No logs found").pack(pady=10)
            return

        # Show logs in the right panel
        for timestamp, city, temp in logs:
            row = ctk.CTkFrame(self.logs_list, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)

            ctk.CTkLabel(
                row,
                text=f"{timestamp} — {city} ({temp}°C)",
                font=("Arial", 13)
            ).pack(padx=10, pady=6)

    # ============================================================
    #                     DELETE USER
    # ============================================================
    def delete_user(self):
        if not self.selected_user:
            return

        if self.selected_user == "admin":
            return  # prevent deleting admin

        database.delete_user(self.selected_user)
        self.selected_user = None
        self.total_label.configure(text=f"Total Users: {database.get_user_count()}")
        self.load_users()

    # ============================================================
    #                     LOAD SEARCH LOGS
    # ============================================================
    def load_logs(self):
        username = self.log_username.get().strip()

        for w in self.logs_list.winfo_children():
            w.destroy()

        logs = database.get_logs_for_user(username)
        # logs must be like: [(timestamp, city, temp), ...]

        if not logs:
            ctk.CTkLabel(self.logs_list, text="No logs found").pack(pady=10)
            return

        for timestamp, city, temp in logs:
            row = ctk.CTkFrame(self.logs_list, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)

            ctk.CTkLabel(
                row,
                text=f"{timestamp} — {city} ({temp}°C)",
                font=("Arial", 13)
            ).pack(padx=10, pady=6)

    # ============================================================
    #                     LOGOUT
    # ============================================================
    def logout(self):
        self.app.current_user = None
        self.pack_forget()
        self.app.welcome = WelcomeScreen(self.app.container, self.app)
        self.app.welcome.pack(fill="both", expand=True)




# ------------------ Main Weather UI (untouched layout) ------------------

class WeatherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Weatherly - Weather App")
        # start small for welcome/login
        self.geometry("900x550")
        self.minsize(900, 500)

        self.container = ctk.CTkFrame(self, corner_radius=0)
        self.container.pack(fill="both", expand=True, padx=12, pady=12)

        # app state
        self.icon_cache = {}
        self.current_user = None   # username string when logged in
        # load saved settings
        self.settings = database.get_settings()
        self.temp_unit = self.settings["unit"]
        self.dynamic_bg = self.settings["dynamic_bg"]

        # show welcome (Get Started -> shows login)
        self.welcome = WelcomeScreen(self.container, self)
        self.welcome.pack(fill="both", expand=True)

        # frames placeholders
        self.login_frame = None
        self.settings_frame = None
        self.main_frame = None
        self.admin_frame = None

    # ----------------- screen flow -----------------
    def show_login(self):
        # hide welcome
        self.welcome.pack_forget()
        # create login frame
        if self.login_frame is None or not self.login_frame.winfo_exists():
            self.login_frame = LoginScreen(self.container, app=self)
        self.login_frame.pack(fill="both", expand=True, padx=12, pady=12)

    def show_register_screen(self):
        """
        Show the RegisterScreen inside the main container.
        This hides other screens (welcome/login/main/admin) so the register UI displays correctly.
        """
        # Hide welcome / login / main / admin if visible
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

        # Create or reuse the register screen
        if getattr(self, "register_frame", None) is None or not getattr(self.register_frame, "winfo_exists",
                                                                        lambda: False)():
            # RegisterScreen class exists in this file
            self.register_frame = RegisterScreen(self.container, self)

        # show it
        self.register_frame.pack(fill="both", expand=True, padx=12, pady=12)

    def show_main_for_user(self):
        # called after normal user logs in
        self.current_user = getattr(self, "current_user", None)
        # remove login screen
        if self.login_frame:
            self.login_frame.pack_forget()
        # restore window size for main UI
        self.geometry("1200x720")
        # build main UI (uses existing build_main_ui that stays mostly unchanged)
        self.build_main_ui()

    def show_admin_dashboard(self):
        # remove login screen
        if self.login_frame:
            self.login_frame.pack_forget()
        # restore window size
        self.geometry("1200x720")
        # create admin frame
        if self.admin_frame is None or not getattr(self.admin_frame, "winfo_exists", lambda: False)():
            self.admin_frame = AdminDashboard(self.container, app=self)
        self.admin_frame.pack(fill="both", expand=True, padx=12, pady=12)

    # When settings or other flows are used, you can add show_settings etc...
    # ---------------- Build main UI (keeps your previous main app layout but adapted) ----------------

    def build_main_ui(self):
        # if main_frame exists, destroy to rebuild cleanly
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

        # Sidebar buttons (Settings and Weather wired)
        for name in ("Weather", "Settings"):
            if name == "Settings":
                btn = ctk.CTkButton(
                    sidebar,
                    text=name,
                    width=80,
                    corner_radius=12,
                    command=self.show_settings
                )
            elif name == "Weather":
                btn = ctk.CTkButton(
                    sidebar,
                    text=name,
                    width=80,
                    corner_radius=12,
                    command=self.show_weather
                )
            else:
                btn = ctk.CTkButton(sidebar, text=name, width=80, corner_radius=12)
            btn.pack(pady=8)

        # Logout button for normal users
        logout_btn = ctk.CTkButton(
            sidebar,
            text="Logout",
            width=80,
            corner_radius=12,
            fg_color="#b91c1c",
            hover_color="#7f1d1d",
            command=self.logout_user
        )
        logout_btn.pack(pady=20)

        # center area
        self.center = ctk.CTkFrame(self.main_frame, corner_radius=12)
        self.center.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=0)

        # search bar
        search_row = ctk.CTkFrame(self.center, corner_radius=8)
        search_row.pack(fill="x", pady=(12, 6), padx=12)

        self.search_entry = ctk.CTkEntry(search_row, placeholder_text="Search for city e.g. London, Tokyo", width=380)
        self.search_entry.bind("<Return>", lambda event: self.search_and_update())
        self.search_entry.pack(side="left", padx=(8, 6), pady=8)

        # search button
        search_btn = ctk.CTkButton(search_row, text="Search", width=90, command=self.search_and_update)
        search_btn.pack(side="left", padx=(6, 6), pady=8)

        # favorites and recents as separate buttons on right
        fav_btn = ctk.CTkButton(search_row, text="★", width=40, command=self.open_favorites_window)
        fav_btn.pack(side="right", padx=(4, 6), pady=8)
        recent_btn = ctk.CTkButton(search_row, text="🕒", width=40, command=self.open_recents_window)
        recent_btn.pack(side="right", padx=(6, 4), pady=8)

        # top info and rest of layout (kept similar to your original layout)
        top_info = ctk.CTkFrame(self.center, corner_radius=12)
        top_info.pack(fill="x", padx=12, pady=(6, 12))

        left_top = ctk.CTkFrame(top_info, corner_radius=8)
        left_top.pack(side="left", fill="both", expand=True, padx=(8, 6), pady=10)

        city_row = ctk.CTkFrame(left_top, corner_radius=8)
        city_row.pack(anchor="w", padx=12, pady=(6, 0))

        self.city_label = ctk.CTkLabel(city_row, text="Welcome", font=("Arial", 26, "bold"))
        self.city_label.pack(side="left")

        self.favorite_btn = ctk.CTkButton(city_row, text="☆", width=40, height=34, corner_radius=8,
                                          command=self.toggle_favorite)
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
        self.info_wind = ctk.CTkLabel(lower_frame, text="Wind: -- m/s", font=("Arial", 14))
        self.info_wind.pack(anchor="w", padx=12, pady=6)
        self.info_uv = ctk.CTkLabel(lower_frame, text="UV Index: --", font=("Arial", 14))
        self.info_uv.pack(anchor="w", padx=12, pady=6)

        # right col
        self.right_col = ctk.CTkFrame(self.main_frame, width=320, corner_radius=12)
        self.right_col.pack(side="right", fill="y", padx=(12, 0), pady=0)

        heading = ctk.CTkLabel(self.right_col, text="5-DAY FORECAST", font=("Arial", 14, "bold"))
        heading.pack(pady=(12, 6))

        self.days_container = ctk.CTkScrollableFrame(self.right_col, corner_radius=8)
        self.days_container.pack(fill="both", expand=True, padx=10, pady=8)

        # Save references for updating (5 rows)
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

        # error label under search
        self.error_label = ctk.CTkLabel(self.center, text="", text_color="#ff4d4d", font=("Arial", 12))
        self.error_label.pack(anchor="w", padx=20, pady=(0, 6))

        # default nothing searched
        # we DO NOT auto search on start anymore
        # self.search_entry.insert(0, "Madrid")
        # self.search_and_update()

    # ------------- Networking & UI (search, update) ----------------
    def search_and_update(self):
        city = self.search_entry.get().strip()
        if not city:
            return

        self.error_label.configure(text="")
        self.city_label.configure(text="Fetching weather...")
        self.update()

        try:
            units = "metric" if self.temp_unit == "C" else "imperial"
            params = {"q": city, "appid": API_KEY, "units": units}

            r = requests.get(WEATHER_URL, params=params, timeout=10)
            r.raise_for_status()
            current_data = r.json()

            r2 = requests.get(FORECAST_URL, params=params, timeout=10)
            r2.raise_for_status()
            forecast_data = r2.json()

            # ✅ ONLY UI UPDATE HERE
            self.update_ui_with_data(current_data, forecast_data)

        except requests.exceptions.HTTPError:
            self.city_label.configure(text="Not found")
            self.error_label.configure(text="City not found. Check spelling.")
            return

        except Exception as e:
            print("Weather error:", e)
            self.error_label.configure(text="Network error. Try again.")
            return

        # ===== DATABASE STUFF (separate, safe) =====
        try:
            database.add_recent(
                current_data.get("name", city),
                int(round(current_data["main"]["temp"]))
            )
        except Exception as e:
            print("Recent log error:", e)

        if self.current_user:
            try:
                database.log_user_search(
                    self.current_user,
                    current_data.get("name", city),
                    int(round(current_data["main"]["temp"]))
                )
            except Exception as e:
                print("User log error:", e)

    def update_ui_with_data(self, current, forecast):
        city_name = current.get("name", "Unknown")
        temp = current.get("main", {}).get("temp")
        feels = current.get("main", {}).get("feels_like")
        humidity = current.get("main", {}).get("humidity")
        wind_speed = current.get("wind", {}).get("speed")
        weather = current.get("weather", [{}])[0]
        desc = weather.get("description", "").title()
        main = weather.get("main", "")
        wid = weather.get("id", None)

        self.city_label.configure(text=city_name)
        self.chance_label.configure(text=f"Condition: {desc}")
        # temp presentation depends on unit
        # Temperature
        if getattr(self, "temp_unit", "C") == "C":
            self.temp_label.configure(text=f"{int(round(temp))}°C" if temp is not None else "--°C")
        else:
            self.temp_label.configure(text=f"{int(round(temp))}°F" if temp is not None else "--°F")

        # Wind Speed
        self.info_wind.configure(text=f"Wind Speed: {wind_speed} km/h" if wind_speed is not None else "Wind Speed: --")

        # Humidity
        self.info_uv.configure(text=f"Humidity: {humidity}%" if humidity is not None else "Humidity: --")

        # Pressure
        pressure = current.get("main", {}).get("pressure")
        self.info_real.configure(text=f"Pressure: {pressure} hPa" if pressure is not None else "Pressure: --")

        try:
            if database.is_favorite(city_name):
                self.favorite_btn.configure(text="★")
            else:
                self.favorite_btn.configure(text="☆")
        except Exception:
            self.favorite_btn.configure(text="☆")

        # big icon
        icon_name = map_weather_to_icon(main, wid)
        big_icon = self.get_cached_icon(icon_name, size=(120, 120))
        if big_icon:
            self.big_icon_label.configure(image=big_icon, text="")
            self.big_icon_label.image = big_icon
        else:
            self.big_icon_label.configure(text=desc)

        # dynamic background gating
        # dynamic background gating
        if getattr(self, "dynamic_bg", True):
            color = background_for_weather(main)
        else:
            color = "#1f2630"
        try:
            self.center.configure(fg_color=color)

            # DO NOT resize or redraw right_col layout, only recolor children
            for child in self.right_col.winfo_children():
                try:
                    child.configure(fg_color=color)
                except:
                    pass

        except Exception:
            pass

        # hourly
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

        # 5 day with icons
        days = {}
        conditions = {}
        for item in forecast.get("list", []):
            date = item.get("dt_txt", "").split(" ")[0]
            if not date:
                continue
            if date not in days:
                days[date] = []
            days[date].append(item.get("main", {}).get("temp", 0))
            if date not in conditions:
                conditions[date] = item.get("weather", [{}])[0].get("main", "").lower()

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

        # remember last search for favorites and settings
        self._last_city = city_name
        self._last_condition = main
        self._last_temp = int(round(temp)) if temp is not None else None

    def get_cached_icon(self, filename, size=(64, 64)):
        key = f"{filename}_{size[0]}x{size[1]}"
        if key in self.icon_cache:
            return self.icon_cache[key]
        img = load_icon(filename, size=size)
        if img:
            self.icon_cache[key] = img
            return img
        return None

    # Favorites / Recents windows (kept separate)
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
                for _id, city, temp, time in recs:
                    row = ctk.CTkFrame(rec_frame)
                    row.pack(fill="x", pady=6, padx=6)
                    ctk.CTkLabel(row, text=city, anchor="w").pack(side="left", padx=6)
                    ctk.CTkLabel(row, text=f"{temp}°", anchor="e").pack(side="left", padx=6)
                    btn_research = ctk.CTkButton(row, text="Open", width=80, command=lambda c=city: (win.destroy(), self.search_from_recents(c)))
                    btn_research.pack(side="right", padx=6)

            ctk.CTkButton(win, text="Clear Recents", command=lambda: (database.clear_recents(), win.destroy(), self.open_recents_window())).pack(pady=10)
        except Exception as e:
            print("Open recents window error:", e)

    def search_from_recents(self, city_name):
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, city_name)
        self.search_and_update()

    # Favorites toggle
    def toggle_favorite(self):
        try:
            city = getattr(self, "_last_city", None)
            if not city:
                return
            if database.is_favorite(city):
                database.remove_favorite(city)
                self.favorite_btn.configure(text="☆")
            else:
                database.add_favorite(city, self._last_temp or 0, self._last_condition or "")
                self.favorite_btn.configure(text="★")
        except Exception as e:
            print("Favorite toggle error:", e)

    # ---------------- Settings screen integration ----------------
    def show_settings(self):
        # hide only the center frame
        try:
            if self.center:
                self.center.pack_forget()
        except Exception:
            pass

        # hide right col too
        try:
            if self.right_col:
                self.right_col.pack_forget()
        except Exception:
            pass

        # show settings frame
        if self.settings_frame is None or not getattr(self.settings_frame, "winfo_exists", lambda: False)():
            self.settings_frame = SettingsScreen(self.main_frame, back_cb=self.show_weather, app=self)

        self.settings_frame.pack(side="left", fill="both", expand=True, padx=12, pady=12)

    def show_weather(self):
        # remove settings frame
        try:
            if self.settings_frame:
                self.settings_frame.pack_forget()
        except Exception:
            pass

        # restore main weather UI panels
        try:
            self.center.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=0)
            self.right_col.pack(side="right", fill="y", padx=(12, 0), pady=0)
        except Exception:
            pass

    # ----------------- helper to rebuild main UI if needed -----------------
    def rebuild_main(self):
        # helper to rebuild UI when toggles/settings change
        if self.main_frame:
            self.main_frame.destroy()
            self.build_main_ui()

    def logout_user(self):
        self.current_user = None
        # hide main UI
        try:
            self.main_frame.pack_forget()
        except Exception:
            pass

        # show welcome screen
        self.welcome = WelcomeScreen(self.container, self)
        self.welcome.pack(fill="both", expand=True)


# ----------------- SettingsScreen (keeps and hooks into database.save_settings) -----------------

class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, back_cb, app):
        super().__init__(parent)
        self.back_cb = back_cb
        self.app = app

        self.configure(corner_radius=20)

        ctk.CTkLabel(self, text="Settings", font=("Arial", 28, "bold")).pack(pady=30)

        # Temperature unit toggle
        self.unit_var = ctk.StringVar(value=self.app.settings.get("unit", "C"))
        unit_frame = ctk.CTkFrame(self, corner_radius=12)
        unit_frame.pack(pady=10, padx=40, fill="x")

        ctk.CTkLabel(unit_frame, text="Temperature Unit").pack(side="left", padx=10)

        ctk.CTkRadioButton(unit_frame, text="°C", variable=self.unit_var,
                           value="C", command=self.set_unit).pack(side="left", padx=10)
        ctk.CTkRadioButton(unit_frame, text="°F", variable=self.unit_var,
                           value="F", command=self.set_unit).pack(side="left", padx=10)

        # Dynamic Background
        bg_frame = ctk.CTkFrame(self, corner_radius=12)
        bg_frame.pack(pady=10, padx=40, fill="x")
        ctk.CTkLabel(bg_frame, text="Dynamic Background").pack(side="left", padx=10)

        self.bg_var = ctk.BooleanVar(value=self.app.settings.get("dynamic_bg", True))
        ctk.CTkSwitch(bg_frame, text="On / Off", variable=self.bg_var, command=self.toggle_bg).pack(side="right", padx=10)

        # Clear buttons
        clear_frame = ctk.CTkFrame(self, corner_radius=12)
        clear_frame.pack(pady=20, padx=40, fill="x")

        ctk.CTkButton(clear_frame, text="Clear Recents", command=self.clear_recents).pack(pady=10, fill="x")
        ctk.CTkButton(clear_frame, text="Clear Favorites", command=self.clear_favorites).pack(pady=10, fill="x")

        # Real Back Button
        ctk.CTkButton(
            self,
            text="Back to Weather",
            width=200,
            fg_color="#3a3a3a",
            hover_color="#555",
            command=self.app.show_weather
        ).pack(pady=20)

    def set_unit(self):
        new_unit = self.unit_var.get()
        self.app.temp_unit = new_unit
        database.save_settings(new_unit, self.bg_var.get())
        self.app.settings = database.get_settings()
        self.app.rebuild_main()

    def toggle_bg(self):
        database.save_settings(self.unit_var.get(), self.bg_var.get())
        self.app.settings = database.get_settings()
        self.app.rebuild_main()

    def clear_recents(self):
        database.clear_recents()

    def clear_favorites(self):
        for city, *_ in database.get_favorites():
            database.remove_favorite(city)



if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()
