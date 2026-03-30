from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp
import sqlite3
import os
from datetime import datetime
import hashlib
import shutil

# ── Palette ───────────────────────────────────────────────────────────────────
PRIMARY      = (0.13, 0.37, 0.71, 1)   # deep blue
PRIMARY_DARK = (0.08, 0.25, 0.52, 1)
ACCENT       = (0.06, 0.73, 0.62, 1)   # teal
ACCENT2      = (0.98, 0.57, 0.25, 1)   # warm amber
BG_LIGHT     = (0.97, 0.97, 0.98, 1)
CARD_BG      = (1,    1,    1,    1)
TEXT_DARK    = (0.12, 0.12, 0.18, 1)
TEXT_MUTED   = (0.50, 0.52, 0.58, 1)
WHITE        = (1,    1,    1,    1)
DANGER       = (0.85, 0.25, 0.25, 1)
SUCCESS      = (0.15, 0.68, 0.38, 1)

Window.size = (400, 700)
Window.clearcolor = BG_LIGHT

current_user = None
DB_FILE = os.path.join(os.path.expanduser('~'), 'Documents', 'user_app_database.db')
PROFILE_PICS_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'user_app_profile_pics')

if not os.path.exists(PROFILE_PICS_DIR):
    os.makedirs(PROFILE_PICS_DIR)


# ── DB helpers (unchanged) ────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def setup_db():
    db_files = [DB_FILE, f"{DB_FILE}-shm", f"{DB_FILE}-wal", f"{DB_FILE}-journal"]
    database_valid = False
    if os.path.exists(DB_FILE):
        try:
            test_conn = sqlite3.connect(DB_FILE, timeout=5)
            test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            test_conn.close()
            database_valid = True
        except Exception as e:
            database_valid = False
    if not database_valid:
        for db_file in db_files:
            try:
                if os.path.exists(db_file):
                    os.remove(db_file)
            except:
                pass
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, phone TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL, message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL, bio TEXT,
            profile_pic TEXT, join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(email) REFERENCES users(email))''')
        c.execute('''CREATE TABLE IF NOT EXISTS timeline_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL, post_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(email) REFERENCES users(email))''')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB setup error: {e}")
        return False

def insert_user(name, email, password, phone):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)",
                  (name, email, hash_password(password), phone))
        conn.commit(); conn.close(); return True
    except: return False

def check_user(email, password):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT name, password FROM users WHERE email=?", (email,))
        result = c.fetchone(); conn.close()
        if result and verify_password(password, result[1]):
            return result[0]
        return None
    except: return None

def get_users():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT name, email FROM users")
        users = c.fetchall(); conn.close(); return users
    except: return []

def save_message(user_name, message):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("INSERT INTO messages (user_name, message, timestamp) VALUES (?, ?, ?)",
                  (user_name, message, datetime.now()))
        conn.commit(); conn.close(); return True
    except: return False

def get_messages():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT user_name, message, timestamp FROM messages ORDER BY timestamp DESC LIMIT 50")
        msgs = c.fetchall(); conn.close(); return list(reversed(msgs))
    except: return []

def get_profile(email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("""SELECT users.name, users.phone, profiles.bio, profiles.join_date, profiles.profile_pic
                     FROM users LEFT JOIN profiles ON users.email = profiles.email
                     WHERE users.email = ?""", (email,))
        result = c.fetchone(); conn.close(); return result
    except: return None

def update_profile(email, bio, profile_pic=None):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        if profile_pic:
            c.execute("INSERT OR REPLACE INTO profiles (email, bio, profile_pic) VALUES (?, ?, ?)",
                      (email, bio, profile_pic))
        else:
            c.execute("INSERT OR REPLACE INTO profiles (email, bio) VALUES (?, ?)", (email, bio))
        conn.commit(); conn.close(); return True
    except: return False

def get_user_email(name):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE name = ?", (name,))
        result = c.fetchone(); conn.close()
        return result[0] if result else None
    except: return None

def save_timeline_post(email, post_text):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("INSERT INTO timeline_posts (email, post_text, timestamp) VALUES (?, ?, ?)",
                  (email, post_text, datetime.now()))
        conn.commit(); conn.close(); return True
    except: return False

def get_timeline_posts(email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT post_text, timestamp FROM timeline_posts WHERE email = ? ORDER BY timestamp DESC", (email,))
        posts = c.fetchall(); conn.close(); return posts
    except: return []


# ── UI Helpers ────────────────────────────────────────────────────────────────
def make_rounded_button(text, bg_color, text_color=WHITE, height=50, radius=12):
    """Button with rounded corners drawn on canvas."""
    btn = Button(
        text=text,
        size_hint_y=None, height=dp(height),
        background_normal='', background_color=(0, 0, 0, 0),
        color=text_color, font_size='15sp', bold=True
    )
    with btn.canvas.before:
        Color(*bg_color)
        btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(radius)])
    btn.bind(pos=lambda w, v: setattr(w._bg_rect, 'pos', v),
             size=lambda w, v: setattr(w._bg_rect, 'size', v))
    return btn

def make_card(padding=16, spacing=10):
    """White card with subtle shadow simulation."""
    card = BoxLayout(orientation='vertical',
                     padding=dp(padding), spacing=dp(spacing),
                     size_hint_y=None)
    with card.canvas.before:
        # Shadow layer
        Color(0, 0, 0, 0.05)
        card._shadow = RoundedRectangle(pos=(card.x + dp(2), card.y - dp(2)),
                                        size=card.size, radius=[dp(14)])
        Color(*CARD_BG)
        card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(14)])
    card.bind(
        pos=lambda w, v: (setattr(w._shadow, 'pos', (v[0]+dp(2), v[1]-dp(2))),
                          setattr(w._bg, 'pos', v)),
        size=lambda w, v: (setattr(w._shadow, 'size', v),
                           setattr(w._bg, 'size', v))
    )
    return card

def styled_input(hint, is_password=False):
    inp = TextInput(
        hint_text=hint,
        password=is_password,
        multiline=False,
        size_hint_y=None, height=dp(48),
        background_color=(0.95, 0.96, 0.98, 1),
        foreground_color=TEXT_DARK,
        hint_text_color=(*TEXT_MUTED[:3], 0.7),
        cursor_color=PRIMARY,
        padding=[dp(14), dp(12)],
        font_size='14sp'
    )
    return inp

def icon_label(icon, text, color=TEXT_MUTED):
    lbl = Label(text=f'{icon}  {text}', font_size='13sp',
                color=color, size_hint_y=None, height=dp(28),
                halign='left', valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


# ── Decorative Header Widget ──────────────────────────────────────────────────
class HeroHeader(Widget):
    """
    Draws a rich decorative header with:
    - solid color background gradient simulation
    - floating circles for depth
    - large emoji/icon in the center
    - title + subtitle text labels
    """
    def __init__(self, icon='👤', title='', subtitle='', bg1=PRIMARY, bg2=PRIMARY_DARK,
                 height=220, **kwargs):
        super().__init__(size_hint_y=None, height=dp(height), **kwargs)
        self.icon = icon
        self.title_text = title
        self.subtitle_text = subtitle
        self.bg1 = bg1
        self.bg2 = bg2
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Background — dark layer + lighter overlay to fake gradient
            Color(*self.bg2)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[0, 0, dp(32), dp(32)])
            Color(*self.bg1, 0.6)
            RoundedRectangle(pos=(self.x, self.y + self.height * 0.4),
                             size=(self.width, self.height * 0.6),
                             radius=[0, 0, dp(32), dp(32)])

            # Decorative floating circles
            Color(1, 1, 1, 0.07)
            Ellipse(pos=(self.x - dp(40), self.y + self.height * 0.3),
                    size=(dp(160), dp(160)))
            Color(1, 1, 1, 0.05)
            Ellipse(pos=(self.x + self.width - dp(80), self.y + self.height * 0.5),
                    size=(dp(120), dp(120)))
            Color(1, 1, 1, 0.04)
            Ellipse(pos=(self.x + self.width * 0.3, self.y - dp(20)),
                    size=(dp(100), dp(100)))

            # Icon circle backdrop
            Color(1, 1, 1, 0.15)
            cx = self.x + self.width / 2 - dp(40)
            cy = self.y + self.height * 0.42
            Ellipse(pos=(cx, cy), size=(dp(80), dp(80)))

        # Icon label — centered
        if not hasattr(self, '_icon_lbl'):
            self._icon_lbl = Label(font_size='36sp',
                                   color=WHITE, bold=True)
            self.add_widget(self._icon_lbl)
        self._icon_lbl.text = self.icon
        self._icon_lbl.pos = (self.x, self.y + self.height * 0.38)
        self._icon_lbl.size = (self.width, dp(80))
        self._icon_lbl.halign = 'center'
        self._icon_lbl.valign = 'middle'
        self._icon_lbl.text_size = self._icon_lbl.size

        # Title
        if not hasattr(self, '_title_lbl'):
            self._title_lbl = Label(font_size='22sp', bold=True, color=WHITE)
            self.add_widget(self._title_lbl)
        self._title_lbl.text = self.title_text
        self._title_lbl.pos = (self.x, self.y + dp(52))
        self._title_lbl.size = (self.width, dp(34))
        self._title_lbl.halign = 'center'
        self._title_lbl.text_size = self._title_lbl.size

        # Subtitle
        if not hasattr(self, '_sub_lbl'):
            self._sub_lbl = Label(font_size='13sp', color=(1, 1, 1, 0.75))
            self.add_widget(self._sub_lbl)
        self._sub_lbl.text = self.subtitle_text
        self._sub_lbl.pos = (self.x, self.y + dp(26))
        self._sub_lbl.size = (self.width, dp(28))
        self._sub_lbl.halign = 'center'
        self._sub_lbl.text_size = self._sub_lbl.size


class StatBadge(Widget):
    """Small colored pill badge, e.g. for member count."""
    def __init__(self, text='', color=ACCENT, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(120), dp(32)), **kwargs)
        self._text = text
        self._color = color
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*self._color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        if not hasattr(self, '_lbl'):
            self._lbl = Label(font_size='12sp', color=WHITE, bold=True)
            self.add_widget(self._lbl)
        self._lbl.text = self._text
        self._lbl.pos = self.pos
        self._lbl.size = self.size
        self._lbl.halign = 'center'
        self._lbl.text_size = self._lbl.size


# ── Screens ───────────────────────────────────────────────────────────────────

class HomeScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        # ── Hero header ──
        hero = HeroHeader(
            icon='🌐',
            title='User Hub',
            subtitle='Connect · Chat · Share',
            bg1=PRIMARY, bg2=PRIMARY_DARK,
            height=230
        )
        root.add_widget(hero)

        # ── Login status strip ──
        self.status_bar = BoxLayout(size_hint_y=None, height=dp(36),
                                    padding=[dp(20), dp(4)])
        with self.status_bar.canvas.before:
            Color(*ACCENT, 0.12)
            self.status_bar._bg = Rectangle(pos=self.status_bar.pos,
                                            size=self.status_bar.size)
        self.status_bar.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v)
        )
        self.status_lbl = Label(text='👋  Not logged in', font_size='12sp',
                                color=TEXT_MUTED, halign='left', valign='middle')
        self.status_lbl.bind(size=self.status_lbl.setter('text_size'))
        self.status_bar.add_widget(self.status_lbl)
        root.add_widget(self.status_bar)

        # ── Button grid ──
        scroll = ScrollView(size_hint_y=1)
        inner = BoxLayout(orientation='vertical', padding=dp(20),
                          spacing=dp(12), size_hint_y=None)
        inner.bind(minimum_height=inner.setter('height'))

        # Section: account
        inner.add_widget(self._section_label('Account'))
        row1 = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(52))
        b_reg = make_rounded_button('✏️  Register', PRIMARY, height=52)
        b_log = make_rounded_button('🔑  Login', ACCENT, height=52)
        b_reg.bind(on_press=lambda *_: setattr(self.manager, 'current', 'register'))
        b_log.bind(on_press=lambda *_: setattr(self.manager, 'current', 'login'))
        row1.add_widget(b_reg); row1.add_widget(b_log)
        inner.add_widget(row1)

        # Section: explore
        inner.add_widget(self._section_label('Explore'))
        b_view = make_rounded_button('👥  Community Members', (0.22, 0.22, 0.30, 1), height=52)
        b_view.bind(on_press=lambda *_: setattr(self.manager, 'current', 'view'))
        inner.add_widget(b_view)

        b_chat = make_rounded_button('💬  Chat Room', ACCENT2, height=52)
        b_chat.bind(on_press=self.go_chat)
        inner.add_widget(b_chat)

        # Section: profile
        inner.add_widget(self._section_label('You'))
        b_prof = make_rounded_button('🪪  My Profile', PRIMARY_DARK, height=52)
        b_prof.bind(on_press=self.go_profile)
        inner.add_widget(b_prof)

        self.logout_btn = make_rounded_button('🚪  Logout', DANGER, height=44)
        self.logout_btn.bind(on_press=self.do_logout)
        self.logout_btn.opacity = 0
        self.logout_btn.disabled = True
        inner.add_widget(self.logout_btn)

        scroll.add_widget(inner)
        root.add_widget(scroll)

        self.add_widget(root)

    def _section_label(self, text):
        lbl = Label(text=text.upper(), font_size='10sp', color=TEXT_MUTED,
                    size_hint_y=None, height=dp(28),
                    halign='left', valign='middle', bold=True)
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def on_enter(self):
        if current_user:
            self.status_lbl.text = f'✅  Logged in as  {current_user}'
            self.logout_btn.opacity = 1
            self.logout_btn.disabled = False
        else:
            self.status_lbl.text = '👋  Not logged in'
            self.logout_btn.opacity = 0
            self.logout_btn.disabled = True

    def go_chat(self, *_):
        if current_user:
            self.manager.current = 'chat'
        else:
            self.status_lbl.text = '⚠️  Please login first'

    def go_profile(self, *_):
        if current_user:
            self.manager.current = 'profile'
        else:
            self.status_lbl.text = '⚠️  Please login first'

    def do_logout(self, *_):
        global current_user
        current_user = None
        self.on_enter()


class RegisterScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        hero = HeroHeader(
            icon='✏️',
            title='Create Account',
            subtitle='Join the community today',
            bg1=(0.15, 0.52, 0.44, 1), bg2=(0.08, 0.35, 0.30, 1),
            height=200
        )
        root.add_widget(hero)

        scroll = ScrollView(size_hint_y=1)
        form = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12),
                         size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        # Decorative icon row
        icon_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        for icon, label in [('👤', 'Name'), ('📧', 'Email'), ('🔒', 'Pass'), ('📱', 'Phone')]:
            col = BoxLayout(orientation='vertical')
            col.add_widget(Label(text=icon, font_size='20sp', size_hint_y=None, height=dp(26)))
            col.add_widget(Label(text=label, font_size='9sp', color=TEXT_MUTED,
                                 size_hint_y=None, height=dp(14)))
            icon_row.add_widget(col)
        form.add_widget(icon_row)

        # Divider
        form.add_widget(self._divider())

        self.name_input  = styled_input('👤  Full Name')
        self.email_input = styled_input('📧  Email Address')
        self.pass_input  = styled_input('🔒  Password (min 6 chars)', is_password=True)
        self.phone_input = styled_input('📱  Phone Number')

        for w in [self.name_input, self.email_input, self.pass_input, self.phone_input]:
            form.add_widget(w)

        self.msg = Label(text='', color=DANGER, size_hint_y=None, height=dp(28),
                         font_size='12sp', halign='center')
        self.msg.bind(size=self.msg.setter('text_size'))
        form.add_widget(self.msg)

        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(52))
        b_reg  = make_rounded_button('✅  Register', ACCENT, height=52)
        b_back = make_rounded_button('← Back', (0.7, 0.7, 0.7, 1), height=52)
        b_reg.bind(on_press=self.register)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        btn_row.add_widget(b_reg); btn_row.add_widget(b_back)
        form.add_widget(btn_row)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def _divider(self):
        w = Widget(size_hint_y=None, height=dp(1))
        with w.canvas:
            Color(0.85, 0.85, 0.90, 1)
            Rectangle(pos=w.pos, size=w.size)
        w.bind(pos=lambda wi, v: setattr(wi.canvas.children[-1], 'pos', v),
               size=lambda wi, v: setattr(wi.canvas.children[-1], 'size', v))
        return w

    def register(self, *_):
        name     = self.name_input.text.strip()
        email    = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        phone    = self.phone_input.text.strip()

        if not name or not email or not password:
            self.msg.text = '⚠️  Please fill in all required fields'
            return
        if '@' not in email:
            self.msg.text = '⚠️  Please enter a valid email address'
            return
        if len(password) < 6:
            self.msg.text = '⚠️  Password must be at least 6 characters'
            return

        if insert_user(name, email, password, phone):
            self.msg.color = SUCCESS
            self.msg.text = '🎉  Welcome! Registration successful'
            for inp in [self.name_input, self.email_input,
                        self.pass_input, self.phone_input]:
                inp.text = ''
            Clock.schedule_once(
                lambda dt: setattr(self.manager, 'current', 'login'), 1.5)
        else:
            self.msg.color = DANGER
            self.msg.text = '⚠️  This email is already registered'


class LoginScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        hero = HeroHeader(
            icon='🔑',
            title='Welcome Back',
            subtitle='Sign in to your account',
            bg1=PRIMARY, bg2=(0.06, 0.20, 0.46, 1),
            height=210
        )
        root.add_widget(hero)

        scroll = ScrollView(size_hint_y=1)
        form = BoxLayout(orientation='vertical', padding=dp(24), spacing=dp(14),
                         size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        # Illustration row — lock icons
        art_row = BoxLayout(size_hint_y=None, height=dp(50))
        art_lbl = Label(text='🔐  Secure · Private · Trusted',
                        font_size='14sp', color=(*PRIMARY[:3], 0.7),
                        halign='center')
        art_lbl.bind(size=art_lbl.setter('text_size'))
        art_row.add_widget(art_lbl)
        form.add_widget(art_row)

        self.email_input = styled_input('📧  Email Address')
        self.pass_input  = styled_input('🔒  Password', is_password=True)
        form.add_widget(self.email_input)
        form.add_widget(self.pass_input)

        self.msg = Label(text='', color=DANGER, size_hint_y=None,
                         height=dp(28), font_size='12sp', halign='center')
        self.msg.bind(size=self.msg.setter('text_size'))
        form.add_widget(self.msg)

        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(52))
        b_login = make_rounded_button('🔑  Login', PRIMARY, height=52)
        b_back  = make_rounded_button('← Back', (0.7, 0.7, 0.7, 1), height=52)
        b_login.bind(on_press=self.login)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        btn_row.add_widget(b_login); btn_row.add_widget(b_back)
        form.add_widget(btn_row)

        no_account = Label(
            text="Don't have an account?  Register →",
            font_size='12sp', color=(*PRIMARY[:3], 0.8),
            size_hint_y=None, height=dp(36), halign='center'
        )
        no_account.bind(size=no_account.setter('text_size'))
        form.add_widget(no_account)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def login(self, *_):
        global current_user
        email    = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        name = check_user(email, password)
        if name:
            current_user = name
            self.msg.color = SUCCESS
            self.msg.text = f'✅  Welcome back, {name}!'
            Clock.schedule_once(
                lambda dt: setattr(self.manager, 'current', 'home'), 1)
        else:
            self.msg.color = DANGER
            self.msg.text = '⚠️  Invalid email or password'


class ViewUsersScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        hero = HeroHeader(
            icon='👥',
            title='Community',
            subtitle='All registered members',
            bg1=(0.35, 0.20, 0.65, 1), bg2=(0.22, 0.10, 0.45, 1),
            height=190
        )
        root.add_widget(hero)

        inner = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))

        # Stats row
        self.stats_lbl = Label(text='', font_size='12sp', color=TEXT_MUTED,
                               size_hint_y=None, height=dp(28), halign='left')
        self.stats_lbl.bind(size=self.stats_lbl.setter('text_size'))
        inner.add_widget(self.stats_lbl)

        self.scroll = ScrollView(size_hint_y=1)
        self.user_layout = BoxLayout(orientation='vertical', size_hint_y=None,
                                     spacing=dp(8))
        self.user_layout.bind(minimum_height=self.user_layout.setter('height'))
        self.scroll.add_widget(self.user_layout)
        inner.add_widget(self.scroll)

        b_back = make_rounded_button('← Back to Home', PRIMARY, height=48)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        inner.add_widget(b_back)

        root.add_widget(inner)
        self.add_widget(root)

    def on_enter(self):
        self.user_layout.clear_widgets()
        users = get_users()
        self.stats_lbl.text = f'👥  {len(users)} member{"s" if len(users) != 1 else ""} found'

        avatars = ['🧑', '👩', '🧔', '👱', '🧕', '👲', '🧑‍💻', '👩‍💼', '🧑‍🎨', '👩‍🔬']

        if users:
            for i, (name, email) in enumerate(users):
                card = make_card(padding=12, spacing=6)
                card.size_hint_y = None
                card.height = dp(68)

                row = BoxLayout(spacing=dp(12))

                # Avatar circle
                av = Label(text=avatars[i % len(avatars)], font_size='22sp',
                           size_hint=(None, None), size=(dp(44), dp(44)))
                with av.canvas.before:
                    Color(*PRIMARY, 0.12)
                    Ellipse(pos=av.pos, size=av.size)
                av.bind(pos=lambda w, v: setattr(w.canvas.before.children[-1], 'pos', v))

                info = BoxLayout(orientation='vertical')
                n_lbl = Label(text=name, font_size='14sp', bold=True,
                              color=TEXT_DARK, halign='left', valign='middle')
                n_lbl.bind(size=n_lbl.setter('text_size'))
                e_lbl = Label(text=email, font_size='11sp', color=TEXT_MUTED,
                              halign='left', valign='middle')
                e_lbl.bind(size=e_lbl.setter('text_size'))
                info.add_widget(n_lbl); info.add_widget(e_lbl)

                row.add_widget(av); row.add_widget(info)
                card.add_widget(row)
                self.user_layout.add_widget(card)
        else:
            self.user_layout.add_widget(
                Label(text='No members yet. Be the first!', color=TEXT_MUTED,
                      size_hint_y=None, height=dp(60)))


class ChatScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        hero = HeroHeader(
            icon='💬',
            title='Chat Room',
            subtitle='Live community messages',
            bg1=ACCENT2, bg2=(0.65, 0.32, 0.08, 1),
            height=160
        )
        root.add_widget(hero)

        inner = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))

        # Online indicator
        top_row = BoxLayout(size_hint_y=None, height=dp(28))
        top_row.add_widget(Label(text='🟢  Live · auto-refreshes every 2s',
                                 font_size='11sp', color=SUCCESS,
                                 halign='left', valign='middle'))
        inner.add_widget(top_row)

        self.scroll = ScrollView(size_hint_y=1)
        self.chat_layout = BoxLayout(orientation='vertical',
                                     size_hint_y=None, spacing=dp(8))
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        self.scroll.add_widget(self.chat_layout)
        inner.add_widget(self.scroll)

        # Input area
        input_card = make_card(padding=10, spacing=8)
        input_card.size_hint_y = None
        input_card.height = dp(56)
        input_row = BoxLayout(spacing=dp(8))
        self.msg_input = TextInput(
            hint_text='Type a message…',
            multiline=False,
            background_color=(0.95, 0.96, 0.98, 1),
            foreground_color=TEXT_DARK,
            hint_text_color=(*TEXT_MUTED[:3], 0.6),
            padding=[dp(12), dp(10)],
            font_size='13sp'
        )
        send_btn = make_rounded_button('Send ▶', PRIMARY, height=40, radius=8)
        send_btn.size_hint_x = 0.28
        send_btn.bind(on_press=self.send_message)
        input_row.add_widget(self.msg_input)
        input_row.add_widget(send_btn)
        input_card.add_widget(input_row)
        inner.add_widget(input_card)

        b_back = make_rounded_button('← Back', (0.6, 0.6, 0.6, 1), height=44)
        b_back.bind(on_press=self.go_back)
        inner.add_widget(b_back)

        root.add_widget(inner)
        self.add_widget(root)

    def on_enter(self):
        self.load_messages()
        Clock.schedule_interval(self.load_messages, 2)

    def on_leave(self):
        try: Clock.unschedule(self.load_messages)
        except: pass

    def load_messages(self, *_):
        self.chat_layout.clear_widgets()
        messages = get_messages()
        bubble_colors = {
            'self': (PRIMARY[0], PRIMARY[1], PRIMARY[2], 0.12),
            'other': (ACCENT[0], ACCENT[1], ACCENT[2], 0.10)
        }
        for user_name, message, timestamp in messages:
            is_me = (user_name == current_user)
            time_str = str(timestamp)[11:16]

            bubble = BoxLayout(orientation='vertical',
                               size_hint_y=None, padding=dp(10))
            bubble.height = dp(66)
            bg_col = bubble_colors['self'] if is_me else bubble_colors['other']
            with bubble.canvas.before:
                Color(*bg_col)
                bubble._bg = RoundedRectangle(pos=bubble.pos,
                                              size=bubble.size, radius=[dp(10)])
            bubble.bind(
                pos=lambda w, v: setattr(w._bg, 'pos', v),
                size=lambda w, v: setattr(w._bg, 'size', v)
            )

            name_color = PRIMARY if is_me else ACCENT
            name_lbl = Label(
                text=f"{'🟦' if is_me else '🟩'} {user_name}",
                font_size='11sp', bold=True, color=name_color,
                size_hint_y=None, height=dp(20),
                halign='left', valign='middle'
            )
            name_lbl.bind(size=name_lbl.setter('text_size'))

            msg_lbl = Label(
                text=f"{message}  [{time_str}]",
                font_size='13sp', color=TEXT_DARK,
                size_hint_y=None, height=dp(26),
                halign='left', valign='middle'
            )
            msg_lbl.bind(size=msg_lbl.setter('text_size'))

            bubble.add_widget(name_lbl)
            bubble.add_widget(msg_lbl)
            self.chat_layout.add_widget(bubble)

        self.scroll.scroll_y = 0

    def send_message(self, *_):
        msg = self.msg_input.text.strip()
        if msg and save_message(current_user, msg):
            self.msg_input.text = ''
            self.load_messages()

    def go_back(self, *_):
        self.manager.current = 'home'


class ProfileScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        self.hero = HeroHeader(
            icon='🪪',
            title='My Profile',
            subtitle='Your personal space',
            bg1=PRIMARY, bg2=PRIMARY_DARK,
            height=200
        )
        root.add_widget(self.hero)

        scroll = ScrollView(size_hint_y=1)
        form = BoxLayout(orientation='vertical', padding=dp(16),
                         spacing=dp(10), size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        # ── Info card ──
        info_card = make_card()
        info_card.size_hint_y = None
        info_card.height = dp(110)

        top_row = BoxLayout(spacing=dp(14), size_hint_y=None, height=dp(70))

        # Profile image or placeholder
        self.profile_image = Image(source='', size_hint=(None, None),
                                   size=(dp(64), dp(64)))
        self.avatar_placeholder = Label(text='👤', font_size='34sp',
                                        size_hint=(None, None),
                                        size=(dp(64), dp(64)))
        with self.avatar_placeholder.canvas.before:
            Color(*PRIMARY, 0.12)
            self.av_bg = Ellipse(pos=self.avatar_placeholder.pos,
                                 size=self.avatar_placeholder.size)
        self.avatar_placeholder.bind(
            pos=lambda w, v: setattr(self.av_bg, 'pos', v),
            size=lambda w, v: setattr(self.av_bg, 'size', v)
        )
        top_row.add_widget(self.avatar_placeholder)

        details = BoxLayout(orientation='vertical', spacing=dp(2))
        self.name_label  = Label(text='—', font_size='16sp', bold=True,
                                 color=TEXT_DARK, halign='left', valign='middle')
        self.email_label = Label(text='—', font_size='11sp', color=TEXT_MUTED,
                                 halign='left', valign='middle')
        self.name_label.bind(size=self.name_label.setter('text_size'))
        self.email_label.bind(size=self.email_label.setter('text_size'))
        details.add_widget(self.name_label)
        details.add_widget(self.email_label)
        top_row.add_widget(details)

        upload_btn = make_rounded_button('📷', PRIMARY, height=36, radius=8)
        upload_btn.size_hint = (None, None)
        upload_btn.size = (dp(44), dp(36))
        upload_btn.bind(on_press=self.choose_profile_pic)
        top_row.add_widget(upload_btn)

        info_card.add_widget(top_row)

        meta_row = BoxLayout(spacing=dp(16), size_hint_y=None, height=dp(26))
        self.phone_label = icon_label('📞', 'Not set')
        self.join_label  = icon_label('📅', 'Member since —')
        meta_row.add_widget(self.phone_label)
        meta_row.add_widget(self.join_label)
        info_card.add_widget(meta_row)

        form.add_widget(info_card)

        # ── Bio card ──
        bio_card = make_card()
        bio_card.size_hint_y = None
        bio_card.height = dp(140)

        bio_lbl = Label(text='📝  Bio', font_size='13sp', bold=True,
                        color=PRIMARY, size_hint_y=None, height=dp(28),
                        halign='left', valign='middle')
        bio_lbl.bind(size=bio_lbl.setter('text_size'))
        bio_card.add_widget(bio_lbl)

        self.bio_input = TextInput(
            hint_text='Tell the community about yourself…',
            background_color=(0.95, 0.96, 0.98, 1),
            foreground_color=TEXT_DARK,
            size_hint_y=None, height=dp(68),
            padding=[dp(10), dp(8)],
            font_size='13sp'
        )
        bio_card.add_widget(self.bio_input)

        save_bio_btn = make_rounded_button('💾  Save Bio', ACCENT, height=38, radius=8)
        save_bio_btn.bind(on_press=self.save_bio)
        bio_card.add_widget(save_bio_btn)

        form.add_widget(bio_card)

        # ── Timeline card ──
        tl_card = make_card()
        tl_card.size_hint_y = None
        tl_card.height = dp(300)

        tl_header = Label(text='📋  My Timeline', font_size='14sp', bold=True,
                          color=PRIMARY, size_hint_y=None, height=dp(30),
                          halign='left', valign='middle')
        tl_header.bind(size=tl_header.setter('text_size'))
        tl_card.add_widget(tl_header)

        post_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.timeline_input = TextInput(
            hint_text='✨  Share something with the world…',
            multiline=False,
            background_color=(0.95, 0.96, 0.98, 1),
            foreground_color=TEXT_DARK,
            hint_text_color=(*TEXT_MUTED[:3], 0.6),
            padding=[dp(10), dp(10)],
            font_size='13sp'
        )
        post_btn = make_rounded_button('Post', ACCENT2, height=44, radius=8)
        post_btn.size_hint_x = 0.28
        post_btn.bind(on_press=self.post_timeline)
        post_row.add_widget(self.timeline_input)
        post_row.add_widget(post_btn)
        tl_card.add_widget(post_row)

        self.tl_scroll = ScrollView(size_hint_y=1)
        self.tl_layout = BoxLayout(orientation='vertical',
                                   size_hint_y=None, spacing=dp(6))
        self.tl_layout.bind(minimum_height=self.tl_layout.setter('height'))
        self.tl_scroll.add_widget(self.tl_layout)
        tl_card.add_widget(self.tl_scroll)

        form.add_widget(tl_card)

        b_back = make_rounded_button('← Back to Home', PRIMARY, height=50)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        form.add_widget(b_back)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self):
        email = get_user_email(current_user)
        if not email:
            return
        profile = get_profile(email)
        if profile:
            name, phone, bio, join_date, profile_pic = profile
            self.hero.title_text = name
            self.hero._draw()
            self.name_label.text  = name
            self.email_label.text = email
            self.phone_label.text = f'📞  {phone if phone else "Not set"}'
            self.join_label.text  = f'📅  Since {str(join_date)[:10] if join_date else "—"}'
            self.bio_input.text   = bio if bio else ''
            if profile_pic and os.path.exists(profile_pic):
                self.profile_image.source = profile_pic
                self.avatar_placeholder.text = ''
        self.load_timeline()

    def choose_profile_pic(self, *_):
        content = BoxLayout(orientation='vertical', spacing=dp(10))
        fc = FileChooserIconView(filters=['*.png', '*.jpg', '*.jpeg'])
        content.add_widget(fc)
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        sel_btn = make_rounded_button('✅  Select', ACCENT, height=46)
        can_btn = make_rounded_button('Cancel', (0.6, 0.6, 0.6, 1), height=46)
        btn_box.add_widget(sel_btn); btn_box.add_widget(can_btn)
        content.add_widget(btn_box)
        popup = Popup(title='Choose Profile Picture', content=content,
                      size_hint=(0.9, 0.9))
        def select_file(*_):
            if fc.selection:
                src = fc.selection[0]
                email = get_user_email(current_user)
                dst = os.path.join(PROFILE_PICS_DIR,
                                   f"{email}_{os.path.basename(src)}")
                try:
                    shutil.copy(src, dst)
                    update_profile(email, self.bio_input.text, dst)
                    self.profile_image.source = dst
                    popup.dismiss()
                except Exception as e:
                    print(f"Copy error: {e}")
        sel_btn.bind(on_press=select_file)
        can_btn.bind(on_press=popup.dismiss)
        popup.open()

    def save_bio(self, *_):
        email = get_user_email(current_user)
        if update_profile(email, self.bio_input.text.strip()):
            self.bio_input.hint_text = '✅  Bio saved!'

    def post_timeline(self, *_):
        email = get_user_email(current_user)
        text  = self.timeline_input.text.strip()
        if text and save_timeline_post(email, text):
            self.timeline_input.text = ''
            self.load_timeline()

    def load_timeline(self):
        self.tl_layout.clear_widgets()
        email = get_user_email(current_user)
        if not email:
            return
        posts = get_timeline_posts(email)
        if posts:
            post_icons = ['✨', '💡', '🎯', '🌟', '💬', '🔥', '🎨', '📌']
            for i, (text, timestamp) in enumerate(posts):
                time_str = str(timestamp)[:16]
                row = BoxLayout(size_hint_y=None, height=dp(54),
                                spacing=dp(8), padding=[dp(4), dp(4)])
                with row.canvas.before:
                    Color(*ACCENT, 0.07)
                    row._bg = RoundedRectangle(pos=row.pos, size=row.size,
                                               radius=[dp(8)])
                row.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                         size=lambda w, v: setattr(w._bg, 'size', v))

                icon_lbl = Label(text=post_icons[i % len(post_icons)],
                                 font_size='16sp', size_hint=(None, 1),
                                 width=dp(28))
                col = BoxLayout(orientation='vertical')
                t_lbl = Label(text=text, font_size='13sp', color=TEXT_DARK,
                              halign='left', valign='middle',
                              size_hint_y=None, height=dp(26))
                t_lbl.bind(size=t_lbl.setter('text_size'))
                d_lbl = Label(text=time_str, font_size='10sp', color=TEXT_MUTED,
                              halign='left', valign='middle',
                              size_hint_y=None, height=dp(18))
                d_lbl.bind(size=d_lbl.setter('text_size'))
                col.add_widget(t_lbl); col.add_widget(d_lbl)
                row.add_widget(icon_lbl); row.add_widget(col)
                self.tl_layout.add_widget(row)
        else:
            self.tl_layout.add_widget(
                Label(text='No posts yet — share your first thought! ✨',
                      color=TEXT_MUTED, font_size='12sp',
                      size_hint_y=None, height=dp(50)))


# ── App ───────────────────────────────────────────────────────────────────────
class MyApp(App):
    def build(self):
        setup_db()
        self.title = 'User Hub — Connect & Share'
        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        for cls, name in [
            (HomeScreen,      'home'),
            (RegisterScreen,  'register'),
            (LoginScreen,     'login'),
            (ViewUsersScreen, 'view'),
            (ChatScreen,      'chat'),
            (ProfileScreen,   'profile'),
        ]:
            s = cls(name=name)
            s.build()
            sm.add_widget(s)
        return sm

if __name__ == '__main__':
    MyApp().run()
