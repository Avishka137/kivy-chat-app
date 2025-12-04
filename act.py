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

Window.size = (400, 600)

current_user = None
DB_FILE = 'app_data.db'


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
        c.execute("INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)",
                  (name, email, password, phone))
        conn.commit()
        conn.close()
        return True
    except:
        return False


def check_user(email, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name FROM users WHERE email=? AND password=?", (email, password))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
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


class HomeScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(text='User Management', size_hint_y=0.15, font_size='24sp', bold=True))
        layout.add_widget(Label(text='With Chat Room', size_hint_y=0.05, font_size='12sp'))
        
        btn_layout = BoxLayout(orientation='vertical', size_hint_y=0.7, spacing=10)
        
        btn1 = Button(text='Register', size_hint_y=0.25)
        btn1.bind(on_press=self.go_register)
        btn_layout.add_widget(btn1)
        
        btn2 = Button(text='Login', size_hint_y=0.25)
        btn2.bind(on_press=self.go_login)
        btn_layout.add_widget(btn2)
        
        btn3 = Button(text='View Users', size_hint_y=0.25)
        btn3.bind(on_press=self.go_view)
        btn_layout.add_widget(btn3)
        
        btn4 = Button(text='Chat Room', size_hint_y=0.25)
        btn4.bind(on_press=self.go_chat)
        btn_layout.add_widget(btn4)
        
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


class RegisterScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text='Register', font_size='20sp', bold=True, size_hint_y=0.1))
        
        layout.add_widget(Label(text='Name:', size_hint_y=0.08))
        self.name_input = TextInput(multiline=False, size_hint_y=0.08)
        layout.add_widget(self.name_input)
        
        layout.add_widget(Label(text='Email:', size_hint_y=0.08))
        self.email_input = TextInput(multiline=False, size_hint_y=0.08)
        layout.add_widget(self.email_input)
        
        layout.add_widget(Label(text='Password:', size_hint_y=0.08))
        self.pass_input = TextInput(password=True, multiline=False, size_hint_y=0.08)
        layout.add_widget(self.pass_input)
        
        layout.add_widget(Label(text='Phone:', size_hint_y=0.08))
        self.phone_input = TextInput(multiline=False, size_hint_y=0.08)
        layout.add_widget(self.phone_input)
        
        self.msg = Label(text='', size_hint_y=0.1, font_size='12sp')
        layout.add_widget(self.msg)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        btn_submit = Button(text='Register')
        btn_submit.bind(on_press=self.register)
        btn_layout.add_widget(btn_submit)
        
        btn_back = Button(text='Back')
        btn_back.bind(on_press=self.go_back)
        btn_layout.add_widget(btn_back)
        
        layout.add_widget(btn_layout)
        layout.add_widget(Label(size_hint_y=0.15))
        
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
        
        if insert_user(name, email, password, phone):
            self.msg.text = 'Registered!'
            self.name_input.text = ''
            self.email_input.text = ''
            self.pass_input.text = ''
            self.phone_input.text = ''
        else:
            self.msg.text = 'Email exists!'
    
    def go_back(self, obj):
        self.manager.current = 'home'


class LoginScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text='Login', font_size='20sp', bold=True, size_hint_y=0.1))
        
        layout.add_widget(Label(text='Email:', size_hint_y=0.1))
        self.email_input = TextInput(multiline=False, size_hint_y=0.1)
        layout.add_widget(self.email_input)
        
        layout.add_widget(Label(text='Password:', size_hint_y=0.1))
        self.pass_input = TextInput(password=True, multiline=False, size_hint_y=0.1)
        layout.add_widget(self.pass_input)
        
        self.msg = Label(text='', size_hint_y=0.2, font_size='12sp')
        layout.add_widget(self.msg)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        btn_login = Button(text='Login')
        btn_login.bind(on_press=self.login)
        btn_layout.add_widget(btn_login)
        
        btn_back = Button(text='Back')
        btn_back.bind(on_press=self.go_back)
        btn_layout.add_widget(btn_back)
        
        layout.add_widget(btn_layout)
        layout.add_widget(Label(size_hint_y=0.15))
        
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
        layout.add_widget(Label(text='All Users', font_size='20sp', bold=True, size_hint_y=0.1))
        
        users = get_users()
        
        scroll = ScrollView(size_hint_y=0.75)
        user_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        user_layout.bind(minimum_height=user_layout.setter('height'))
        
        if users:
            for user in users:
                lbl = Label(text=f"{user[0]} - {user[1]}", size_hint_y=None, height=40, font_size='10sp')
                user_layout.add_widget(lbl)
        else:
            user_layout.add_widget(Label(text='No users!', size_hint_y=None, height=40))
        
        scroll.add_widget(user_layout)
        layout.add_widget(scroll)
        
        btn_back = Button(text='Back', size_hint_y=0.1)
        btn_back.bind(on_press=self.go_back)
        layout.add_widget(btn_back)
        
        self.add_widget(layout)
    
    def go_back(self, obj):
        self.manager.current = 'home'


class ChatScreen(Screen):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        header = BoxLayout(size_hint_y=0.08, spacing=10)
        header.add_widget(Label(text=f'Chat - {current_user}', font_size='16sp', bold=True))
        layout.add_widget(header)
        
        self.scroll = ScrollView(size_hint_y=0.7)
        self.chat_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        self.scroll.add_widget(self.chat_layout)
        layout.add_widget(self.scroll)
        
        input_layout = BoxLayout(size_hint_y=0.15, spacing=5)
        self.msg_input = TextInput(multiline=False, hint_text='Type message...')
        input_layout.add_widget(self.msg_input)
        
        send_btn = Button(text='Send', size_hint_x=0.2)
        send_btn.bind(on_press=self.send_message)
        input_layout.add_widget(send_btn)
        
        layout.add_widget(input_layout)
        
        btn_back = Button(text='Exit Chat', size_hint_y=0.07)
        btn_back.bind(on_press=self.go_back)
        layout.add_widget(btn_back)
        
        self.add_widget(layout)
    
    def on_enter(self):
        self.load_messages()
        Clock.schedule_interval(self.load_messages, 2)
    
    def on_leave(self):
        Clock.unschedule(self.load_messages)
    
    def load_messages(self, *args):
        self.chat_layout.clear_widgets()
        messages = get_messages()
        
        for msg in messages:
            user_name, message, timestamp = msg
            time_str = str(timestamp)[11:16] if timestamp else ''
            text = f"{user_name} ({time_str}): {message}"
            lbl = Label(text=text, size_hint_y=None, height=40, font_size='10sp')
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


class MyApp(App):
    def build(self):
        setup_db()
        self.title = 'User Management + Chat'
        
        sm = ScreenManager()
        
        home = HomeScreen(name='home')
        home.build()
        sm.add_widget(home)
        
        register = RegisterScreen(name='register')
        register.build()
        sm.add_widget(register)
        
        login = LoginScreen(name='login')
        login.build()
        sm.add_widget(login)
        
        view = ViewUsersScreen(name='view')
        view.build()
        sm.add_widget(view)
        
        chat = ChatScreen(name='chat')
        chat.build()
        sm.add_widget(chat)
        
        return sm


if __name__ == '__main__':
    MyApp().run()
