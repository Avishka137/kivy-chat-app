from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import sqlite3
import os
from datetime import datetime
import hashlib

# --------------------------
#   GLOBAL UI COLORS
# --------------------------
PRIMARY = (0.1, 0.5, 0.8, 1)      # Blue
SECONDARY = (0.2, 0.7, 0.6, 1)    # Teal
BG_COLOR = (0.95, 0.95, 0.95, 1)  # Light Gray
BTN_TEXT = (1, 1, 1, 1)           # White text

Window.size = (400, 600)
Window.clearcolor = BG_COLOR

current_user = None
DB_FILE = 'app_data.db'


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def setup_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            phone TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            user_name TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            bio TEXT,
            join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(email) REFERENCES users(email)
        )''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False


def insert_user(name, email, password, phone):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        hashed_pass = hash_password(password)
        c.execute("INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)",
                  (name, email, hashed_pass, phone))
        conn.commit()
        conn.close()
        return True
    except:
        return False


def check_user(email, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, password FROM users WHERE email=?", (email,))
        result = c.fetchone()
        conn.close()
        if result and verify_password(password, result[1]):
            return result[0]
        return None
    except:
        return None


def get_users():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, email FROM users")
        users = c.fetchall()
        conn.close()
        return users
    except:
        return []


def save_message(user_name, message):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO messages (user_name, message, timestamp) VALUES (?, ?, ?)",
                  (user_name, message, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def get_messages():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_name, message, timestamp FROM messages ORDER BY timestamp DESC LIMIT 50")
        messages = c.fetchall()
        conn.close()
        return list(reversed(messages))
    except:
        return []


def get_profile(email):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT users.name, users.phone, profiles.bio, profiles.join_date FROM users LEFT JOIN profiles ON users.email = profiles.email WHERE users.email = ?", (email,))
        result = c.fetchone()
        conn.close()
        return result
    except:
        return None


def update_profile(email, bio):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO profiles (email, bio) VALUES (?, ?)", (email, bio))
        conn.commit()
        conn.close()
        return True
    except:
        return False


def get_user_email(name):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE name = ?", (name,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None


# --------------------------
#       SCREENS
# --------------------------

class HomeScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(text='User Management', font_size='26sp', bold=True, color=PRIMARY))
        layout.add_widget(Label(text='Chat + Profiles', font_size='14sp', color=(0, 0, 0, 1)))
        
        btn_layout = BoxLayout(orientation='vertical', spacing=10)
        
        def make_btn(text, action):
            btn = Button(text=text, size_hint_y=0.17,
                         background_color=PRIMARY, color=BTN_TEXT)
            btn.bind(on_press=action)
            return btn
        
        btn_layout.add_widget(make_btn('Register', self.go_register))
        btn_layout.add_widget(make_btn('Login', self.go_login))
        btn_layout.add_widget(make_btn('View Users', self.go_view))
        btn_layout.add_widget(make_btn('Chat Room', self.go_chat))
        
        profile_btn = Button(text='👤 My Profile',
                             size_hint_y=0.2,
                             background_color=SECONDARY,
                             color=BTN_TEXT)
        profile_btn.bind(on_press=self.go_profile)
        btn_layout.add_widget(profile_btn)
        
        layout.add_widget(btn_layout)
        self.add_widget(layout)
    
    def go_register(self, obj):
        self.manager.current = 'register'
    
    def go_login(self, obj):
        self.manager.current = 'login'
    
    def go_view(self, obj):
        self.manager.current = 'view'
    
    def go_chat(self, obj):
        if current_user:
            self.manager.current = 'chat'
    
    def go_profile(self, obj):
        if current_user:
            self.manager.current = 'profile'


class RegisterScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        layout.add_widget(Label(text='Register', font_size='22sp', bold=True, color=PRIMARY))

        def make_input(label):
            layout.add_widget(Label(text=label, color=(0, 0, 0, 1)))
            inp = TextInput(multiline=False, background_color=(1,1,1,1))
            layout.add_widget(inp)
            return inp

        self.name_input = make_input("Name:")
        self.email_input = make_input("Email:")
        self.pass_input = TextInput(password=True, multiline=False, background_color=(1,1,1,1))
        layout.add_widget(Label(text="Password:", color=(0,0,0,1)))
        layout.add_widget(self.pass_input)
        self.phone_input = make_input("Phone:")

        self.msg = Label(text='', color=(1, 0, 0, 1))
        layout.add_widget(self.msg)

        btn_row = BoxLayout(spacing=10)
        reg_btn = Button(text="Register", background_color=PRIMARY, color=BTN_TEXT)
        reg_btn.bind(on_press=self.register)
        back_btn = Button(text="Back", background_color=SECONDARY, color=BTN_TEXT)
        back_btn.bind(on_press=self.go_back)
        btn_row.add_widget(reg_btn)
        btn_row.add_widget(back_btn)

        layout.add_widget(btn_row)
        self.add_widget(layout)

    def register(self, obj):
        name = self.name_input.text.strip()
        email = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        phone = self.phone_input.text.strip()
        
        if not name or not email or not password:
            self.msg.text = 'Fill all fields!'
            return
        
        if '@' not in email:
            self.msg.text = 'Invalid email!'
            return
        
        if len(password) < 6:
            self.msg.text = 'Password must be 6+ chars!'
            return
        
        if insert_user(name, email, password, phone):
            self.msg.text = 'Registered successfully!'
            self.name_input.text = ''
            self.email_input.text = ''
            self.pass_input.text = ''
            self.phone_input.text = ''
        else:
            self.msg.text = 'Email already exists!'
    
    def go_back(self, obj):
        self.manager.current = 'home'


class LoginScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(text='Login', font_size='22sp', bold=True, color=PRIMARY))
        
        layout.add_widget(Label(text='Email:', color=(0,0,0,1)))
        self.email_input = TextInput(background_color=(1,1,1,1))
        layout.add_widget(self.email_input)
        
        layout.add_widget(Label(text='Password:', color=(0,0,0,1)))
        self.pass_input = TextInput(password=True, background_color=(1,1,1,1))
        layout.add_widget(self.pass_input)
        
        self.msg = Label(text='', color=(1, 0, 0, 1))
        layout.add_widget(self.msg)
        
        btn_row = BoxLayout(spacing=10)
        login_btn = Button(text='Login', background_color=PRIMARY, color=BTN_TEXT)
        login_btn.bind(on_press=self.login)
        back_btn = Button(text='Back', background_color=SECONDARY, color=BTN_TEXT)
        back_btn.bind(on_press=self.go_back)
        btn_row.add_widget(login_btn)
        btn_row.add_widget(back_btn)
        
        layout.add_widget(btn_row)
        self.add_widget(layout)
    
    def login(self, obj):
        global current_user
        email = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        
        name = check_user(email, password)
        if name:
            current_user = name
            self.msg.text = f'Welcome {name}!'
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'home'), 1)
        else:
            self.msg.text = 'Wrong credentials!'
    
    def go_back(self, obj):
        self.manager.current = 'home'


class ViewUsersScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text='All Users', font_size='22sp', bold=True, color=PRIMARY))
        
        users = get_users()
        
        scroll = ScrollView(size_hint_y=0.75)
        user_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        user_layout.bind(minimum_height=user_layout.setter('height'))
        
        if users:
            for user in users:
                lbl = Label(text=f"{user[0]} - {user[1]}", size_hint_y=None, height=40, font_size='12sp')
                user_layout.add_widget(lbl)
        else:
            user_layout.add_widget(Label(text='No users!', size_hint_y=None, height=40))
        
        scroll.add_widget(user_layout)
        layout.add_widget(scroll)
        
        btn_back = Button(text='Back', size_hint_y=0.1, background_color=SECONDARY, color=BTN_TEXT)
        btn_back.bind(on_press=self.go_back)
        layout.add_widget(btn_back)
        
        self.add_widget(layout)
    
    def go_back(self, obj):
        self.manager.current = 'home'


class ChatScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        header = BoxLayout(size_hint_y=0.1)
        header.add_widget(Label(text='💬 Chat Room', font_size='20sp', color=PRIMARY))
        header.add_widget(Label(text=f'User: {current_user}', font_size='12sp'))
        layout.add_widget(header)
        
        self.scroll = ScrollView(size_hint_y=0.7)
        self.chat_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8)
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        self.scroll.add_widget(self.chat_layout)
        layout.add_widget(self.scroll)
        
        input_row = BoxLayout(size_hint_y=0.15, spacing=8)
        self.msg_input = TextInput(background_color=(1,1,1,1))
        send_btn = Button(text='Send', background_color=PRIMARY, color=BTN_TEXT)
        send_btn.bind(on_press=self.send_message)
        
        input_row.add_widget(self.msg_input)
        input_row.add_widget(send_btn)
        layout.add_widget(input_row)
        
        back_btn = Button(text='Back', background_color=SECONDARY, color=BTN_TEXT)
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def on_enter(self):
        self.load_messages()
        Clock.schedule_interval(self.load_messages, 1)
    
    def on_leave(self):
        try:
            Clock.unschedule(self.load_messages)
        except:
            pass
    
    def load_messages(self, *args):
        self.chat_layout.clear_widgets()
        messages = get_messages()
        
        for user_name, message, timestamp in messages:
            time_str = str(timestamp)[11:16]
            
            color = PRIMARY if user_name == current_user else SECONDARY
            lbl = Label(text=f"{user_name}: {message}\n[{time_str}]",
                        size_hint_y=None, height=60,
                        color=color)
            self.chat_layout.add_widget(lbl)
        
        self.scroll.scroll_y = 0
    
    def send_message(self, obj):
        message = self.msg_input.text.strip()
        
        if not message:
            return
        
        if save_message(current_user, message):
            self.msg_input.text = ''
            self.load_messages()
    
    def go_back(self, obj):
        global current_user
        current_user = None
        self.manager.current = 'home'


class ProfileScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(text='👤 My Profile', font_size='22sp', bold=True, color=PRIMARY))
        
        scroll = ScrollView()
        info_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        info_layout.bind(minimum_height=info_layout.setter('height'))
        
        self.name_label = Label(text='Name:', size_hint_y=None, height=40)
        self.email_label = Label(text='Email:', size_hint_y=None, height=40)
        self.phone_label = Label(text='Phone:', size_hint_y=None, height=40)
        self.join_label = Label(text='Joined:', size_hint_y=None, height=40)
        
        info_layout.add_widget(self.name_label)
        info_layout.add_widget(self.email_label)
        info_layout.add_widget(self.phone_label)
        info_layout.add_widget(self.join_label)
        
        info_layout.add_widget(Label(text='Bio:', height=30, size_hint_y=None))
        
        self.bio_input = TextInput(height=100, size_hint_y=None, background_color=(1,1,1,1))
        info_layout.add_widget(self.bio_input)
        
        scroll.add_widget(info_layout)
        layout.add_widget(scroll)
        
        btn_row = BoxLayout(size_hint_y=0.15, spacing=10)
        
        save_btn = Button(text='Save Bio', background_color=PRIMARY, color=BTN_TEXT)
        save_btn.bind(on_press=self.save_bio)
        
        back_btn = Button(text='Back', background_color=SECONDARY, color=BTN_TEXT)
        back_btn.bind(on_press=self.go_back)
        
        btn_row.add_widget(save_btn)
        btn_row.add_widget(back_btn)
        
        layout.add_widget(btn_row)
        
        self.add_widget(layout)
    
    def on_enter(self):
        email = get_user_email(current_user)
        profile = get_profile(email)
        
        if profile:
            name, phone, bio, join_date = profile
            self.name_label.text = f'Name: {name}'
            self.email_label.text = f'Email: {email}'
            self.phone_label.text = f'Phone: {phone if phone else "Not set"}'
            self.join_label.text = f'Joined: {str(join_date)[:10]}'
            self.bio_input.text = bio if bio else ''
    
    def save_bio(self, obj):
        email = get_user_email(current_user)
        bio = self.bio_input.text.strip()
        
        if update_profile(email, bio):
            self.bio_input.hint_text = 'Saved!'
        else:
            self.bio_input.hint_text = 'Error'
    
    def go_back(self, obj):
        self.manager.current = 'home'


class MyApp(App):
    def build(self):
        setup_db()
        self.title = 'User Management + Chat + Profiles'
        
        sm = ScreenManager()
        
        screens = [
            (HomeScreen, 'home'),
            (RegisterScreen, 'register'),
            (LoginScreen, 'login'),
            (ViewUsersScreen, 'view'),
            (ChatScreen, 'chat'),
            (ProfileScreen, 'profile')
        ]

        for scr, name in screens:
            s = scr(name=name)
            s.build()
            sm.add_widget(s)
        
        return sm


if __name__ == '__main__':
    MyApp().run()
