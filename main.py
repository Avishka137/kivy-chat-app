from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line, Ellipse
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.animation import Animation
import sqlite3
from datetime import datetime
import hashlib

# ─────────────────────────────────────────
#   DESIGN TOKENS
# ─────────────────────────────────────────
C_BG        = (0.06, 0.07, 0.10, 1)   # Near-black background
C_SURFACE   = (0.11, 0.13, 0.17, 1)   # Card surface
C_SURFACE2  = (0.15, 0.17, 0.23, 1)   # Elevated surface
C_ACCENT    = (0.22, 0.72, 0.58, 1)   # Mint green accent
C_ACCENT2   = (0.94, 0.42, 0.38, 1)   # Coral accent
C_TEXT      = (0.92, 0.93, 0.95, 1)   # Primary text
C_MUTED     = (0.55, 0.58, 0.65, 1)   # Muted text
C_WHITE     = (1,    1,    1,    1)
C_ERROR     = (0.94, 0.36, 0.36, 1)
C_SUCCESS   = (0.28, 0.84, 0.60, 1)

RADIUS      = dp(14)
BTN_RADIUS  = dp(12)
INPUT_H     = dp(48)
BTN_H       = dp(50)

Window.size         = (400, 700)
Window.clearcolor   = C_BG

current_user  = None
current_email = None
DB_FILE       = 'app_data.db'


# ─────────────────────────────────────────
#   DATABASE LAYER  (unchanged logic)
# ─────────────────────────────────────────
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def verify_password(p, h):
    return hash_password(p) == h

def setup_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, name TEXT,
        email TEXT UNIQUE, password TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY, user_name TEXT,
        message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY, email TEXT UNIQUE, bio TEXT,
        join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(email) REFERENCES users(email))''')
    conn.commit(); conn.close()

def insert_user(name, email, password, phone):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.cursor().execute(
            "INSERT INTO users (name,email,password,phone) VALUES (?,?,?,?)",
            (name, email, hash_password(password), phone))
        conn.commit(); conn.close(); return True
    except: return False

def check_user(email, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        r = conn.cursor().execute(
            "SELECT name,password FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        return r[0] if r and verify_password(password, r[1]) else None
    except: return None

def get_users():
    try:
        conn = sqlite3.connect(DB_FILE)
        u = conn.cursor().execute("SELECT name,email FROM users").fetchall()
        conn.close(); return u
    except: return []

def save_message(user_name, message):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.cursor().execute(
            "INSERT INTO messages (user_name,message,timestamp) VALUES (?,?,?)",
            (user_name, message, datetime.now()))
        conn.commit(); conn.close(); return True
    except: return False

def get_messages():
    try:
        conn = sqlite3.connect(DB_FILE)
        rows = conn.cursor().execute(
            "SELECT user_name,message,timestamp FROM messages "
            "ORDER BY timestamp DESC LIMIT 50").fetchall()
        conn.close(); return list(reversed(rows))
    except: return []

def get_profile(email):
    try:
        conn = sqlite3.connect(DB_FILE)
        r = conn.cursor().execute(
            "SELECT users.name,users.phone,profiles.bio,profiles.join_date "
            "FROM users LEFT JOIN profiles ON users.email=profiles.email "
            "WHERE users.email=?", (email,)).fetchone()
        conn.close(); return r
    except: return None

def update_profile(email, bio):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.cursor().execute(
            "INSERT OR REPLACE INTO profiles (email,bio) VALUES (?,?)", (email, bio))
        conn.commit(); conn.close(); return True
    except: return False

def get_user_email(name):
    try:
        conn = sqlite3.connect(DB_FILE)
        r = conn.cursor().execute(
            "SELECT email FROM users WHERE name=?", (name,)).fetchone()
        conn.close(); return r[0] if r else None
    except: return None


# ─────────────────────────────────────────
#   CUSTOM WIDGETS
# ─────────────────────────────────────────

class Card(FloatLayout):
    """Rounded card widget with canvas background."""
    def __init__(self, bg=C_SURFACE, radius=RADIUS, **kw):
        super().__init__(**kw)
        self._bg    = bg
        self._rad   = radius
        self._rect  = None
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self._rad])

    def on_size(self, *_): self._update()


class ModernButton(Button):
    """Pill-shaped button with accent fill and hover glow."""
    def __init__(self, accent=C_ACCENT, text_color=C_BG,
                 outline=False, **kw):
        super().__init__(**kw)
        self._accent     = accent
        self._txt_color  = text_color
        self._outline    = outline
        self.background_normal   = ''
        self.background_down     = ''
        self.background_color    = (0, 0, 0, 0)
        self.color               = text_color
        self.bold                = True
        self.font_size           = dp(14)
        self.size_hint_y         = None
        self.height              = BTN_H
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            if self._outline:
                Color(*self._accent)
                Line(rounded_rectangle=(self.x+1, self.y+1,
                                        self.width-2, self.height-2,
                                        BTN_RADIUS), width=1.5)
            else:
                Color(*self._accent)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[BTN_RADIUS])

    def on_press(self):
        anim = Animation(opacity=0.7, duration=0.08)
        anim += Animation(opacity=1.0, duration=0.08)
        anim.start(self)

    def on_size(self, *_): self._draw()


class ModernInput(TextInput):
    """Dark-themed input with rounded border."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal    = ''
        self.background_active    = ''
        self.background_color     = (0, 0, 0, 0)
        self.foreground_color     = C_TEXT
        self.cursor_color         = C_ACCENT
        self.hint_text_color      = list(C_MUTED)
        self.font_size            = dp(14)
        self.padding              = [dp(14), dp(12), dp(14), dp(12)]
        self.multiline            = False
        self.size_hint_y          = None
        self.height               = INPUT_H
        self.bind(pos=self._draw, size=self._draw,
                  focus=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*C_SURFACE2)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[dp(10)])
            if self.focus:
                Color(*C_ACCENT)
                Line(rounded_rectangle=(self.x+1, self.y+1,
                                        self.width-2, self.height-2,
                                        dp(10)), width=1.4)

    def on_size(self, *_): self._draw()


class FieldLabel(Label):
    def __init__(self, **kw):
        kw.setdefault('color', C_MUTED)
        kw.setdefault('font_size', dp(11))
        kw.setdefault('bold', True)
        kw.setdefault('halign', 'left')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(22))
        super().__init__(**kw)
        self.bind(size=lambda *_: setattr(self, 'text_size', (self.width, None)))


class StatusLabel(Label):
    def __init__(self, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(20))
        kw.setdefault('font_size', dp(12))
        super().__init__(**kw)
        self.text = ''

    def show(self, text, ok=False):
        self.text  = text
        self.color = C_SUCCESS if ok else C_ERROR


class Divider(Widget):
    def __init__(self, **kw):
        kw.setdefault('size_hint_y', None)
        kw.setdefault('height', dp(1))
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*C_SURFACE2)
            Rectangle(pos=self.pos, size=self.size)


class Avatar(Widget):
    """Circular avatar with initials."""
    def __init__(self, initials='?', color=C_ACCENT, size_dp=48, **kw):
        kw['size_hint'] = (None, None)
        kw['size'] = (dp(size_dp), dp(size_dp))
        super().__init__(**kw)
        self._initials = initials
        self._color    = color
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*self._color, 0.25)
            Ellipse(pos=self.pos, size=self.size)
            Color(*self._color)
            Line(ellipse=(*self.pos, *self.size), width=1.5)

        lbl = Label(text=self._initials, color=self._color,
                    font_size=dp(16), bold=True,
                    pos=self.pos, size=self.size)
        self.add_widget(lbl)


class ChatBubble(BoxLayout):
    """Modern chat bubble."""
    def __init__(self, name, message, time_str, is_me=False, **kw):
        super().__init__(orientation='horizontal', **kw)
        self.size_hint_y = None
        self.padding     = [dp(6), dp(4)]
        self.spacing     = dp(8)

        bubble_color = C_ACCENT  if is_me else C_SURFACE2
        text_color   = C_BG      if is_me else C_TEXT
        name_color   = C_ACCENT  if is_me else C_MUTED

        inner = BoxLayout(orientation='vertical',
                          size_hint_x=None, spacing=dp(2))

        name_lbl = Label(text=name if not is_me else 'You',
                         color=name_color, font_size=dp(10),
                         bold=True, size_hint_y=None, height=dp(16),
                         halign='left' if not is_me else 'right')
        name_lbl.bind(size=lambda *_: setattr(name_lbl, 'text_size', (name_lbl.width, None)))

        msg_lbl = Label(text=message, color=text_color,
                        font_size=dp(13), size_hint_y=None,
                        halign='left', valign='middle')
        msg_lbl.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1] + dp(4)))
        msg_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))

        time_lbl = Label(text=time_str, color=C_MUTED,
                         font_size=dp(9), size_hint_y=None, height=dp(14),
                         halign='right' if is_me else 'left')
        time_lbl.bind(size=lambda *_: setattr(time_lbl, 'text_size', (time_lbl.width, None)))

        inner.add_widget(name_lbl)
        inner.add_widget(msg_lbl)
        inner.add_widget(time_lbl)
        inner.bind(minimum_height=inner.setter('height'))

        # Bubble sizing: max 70% width
        max_w = Window.width * 0.68
        inner.width = max_w

        bubble_wrap = FloatLayout(size_hint=(None, None),
                                  width=max_w + dp(24),
                                  height=dp(1))
        inner.bind(height=lambda inst, h: setattr(bubble_wrap, 'height', h + dp(20)))

        def _draw_bubble(*_):
            bubble_wrap.canvas.before.clear()
            with bubble_wrap.canvas.before:
                Color(*bubble_color)
                RoundedRectangle(pos=(bubble_wrap.x, bubble_wrap.y),
                                 size=(bubble_wrap.width, bubble_wrap.height),
                                 radius=[dp(14)])

        bubble_wrap.bind(pos=_draw_bubble, size=_draw_bubble)
        inner.pos = (bubble_wrap.x + dp(12), bubble_wrap.y + dp(10))
        inner.bind(pos=lambda *_: None)
        bubble_wrap.add_widget(inner)

        spacer = Widget()
        if is_me:
            self.add_widget(spacer)
            self.add_widget(bubble_wrap)
        else:
            self.add_widget(bubble_wrap)
            self.add_widget(spacer)

        self.bind(minimum_height=self.setter('height'))
        bubble_wrap.bind(height=lambda inst, h: setattr(self, 'height', h + dp(8)))


# ─────────────────────────────────────────
#   SCREEN BASE
# ─────────────────────────────────────────

class BaseScreen(Screen):
    """Adds dark background canvas to every screen."""
    def on_add_widget(self, widget, *args):
        self._set_bg()

    def _set_bg(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*C_BG)
            Rectangle(pos=self.pos, size=self.size)

    def on_size(self, *_): self._set_bg()
    def on_pos(self,  *_): self._set_bg()


# ─────────────────────────────────────────
#   HOME SCREEN
# ─────────────────────────────────────────

class HomeScreen(BaseScreen):
    def build(self):
        root = BoxLayout(orientation='vertical',
                         padding=[dp(24), dp(40), dp(24), dp(30)],
                         spacing=dp(10))

        # ── Header ──
        hdr = BoxLayout(orientation='vertical', size_hint_y=None,
                        height=dp(120), spacing=dp(6))
        dot_row = BoxLayout(size_hint_y=None, height=dp(10), spacing=dp(6))
        for col in [C_ACCENT, C_ACCENT2, (0.4, 0.5, 1, 1)]:
            d = Widget(size_hint=(None, None), size=(dp(8), dp(8)))
            with d.canvas:
                Color(*col)
                Ellipse(pos=d.pos, size=d.size)
            d.bind(pos=lambda inst, p, col=col: (
                inst.canvas.clear(),
                inst.canvas.__enter__(),
                Color(*col).__init__(*col),
                Ellipse(pos=p, size=inst.size),
            ))
            dot_row.add_widget(d)
        dot_row.add_widget(Widget())

        title = Label(text='NEXUS', font_size=dp(38), bold=True,
                      color=C_TEXT, size_hint_y=None, height=dp(50),
                      halign='left')
        title.bind(size=lambda *_: setattr(title, 'text_size', (title.width, None)))

        sub = Label(text='Chat · Connect · Profiles',
                    font_size=dp(13), color=C_MUTED,
                    size_hint_y=None, height=dp(22), halign='left')
        sub.bind(size=lambda *_: setattr(sub, 'text_size', (sub.width, None)))

        hdr.add_widget(dot_row)
        hdr.add_widget(title)
        hdr.add_widget(sub)
        root.add_widget(hdr)

        # ── Status chip ──
        self.status_chip = Label(
            text='● Not logged in', color=C_MUTED, font_size=dp(12),
            size_hint_y=None, height=dp(28), halign='left')
        self.status_chip.bind(size=lambda *_: setattr(
            self.status_chip, 'text_size', (self.status_chip.width, None)))
        root.add_widget(self.status_chip)
        root.add_widget(Divider())

        # ── Nav buttons ──
        btn_data = [
            ('Register',   self.go_register, C_ACCENT,  False),
            ('Login',      self.go_login,    C_ACCENT,  True),
            ('View Users', self.go_view,     C_SURFACE2, False),
            ('Chat Room',  self.go_chat,     C_ACCENT2, False),
            ('My Profile', self.go_profile,  C_SURFACE2, False),
        ]
        for label, cb, color, outline in btn_data:
            btn = ModernButton(text=label, accent=color,
                               text_color=C_TEXT if outline or color == C_SURFACE2 else C_BG,
                               outline=outline)
            btn.bind(on_press=cb)
            root.add_widget(btn)

        root.add_widget(Widget())   # spacer

        self.add_widget(root)

    def on_enter(self):
        if current_user:
            self.status_chip.text  = f'● Logged in as  {current_user}'
            self.status_chip.color = C_SUCCESS
        else:
            self.status_chip.text  = '● Not logged in'
            self.status_chip.color = C_MUTED

    def go_register(self, *_): self.manager.current = 'register'
    def go_login(self,    *_): self.manager.current = 'login'
    def go_view(self,     *_): self.manager.current = 'view'
    def go_chat(self,     *_):
        if current_user: self.manager.current = 'chat'
    def go_profile(self,  *_):
        if current_user: self.manager.current = 'profile'


# ─────────────────────────────────────────
#   REGISTER SCREEN
# ─────────────────────────────────────────

class RegisterScreen(BaseScreen):
    def build(self):
        root = BoxLayout(orientation='vertical',
                         padding=[dp(24), dp(32), dp(24), dp(20)],
                         spacing=dp(14))

        root.add_widget(Label(text='Create Account', font_size=dp(26),
                              bold=True, color=C_TEXT,
                              size_hint_y=None, height=dp(40),
                              halign='left'))
        root.add_widget(Label(text='Join Nexus today',
                              font_size=dp(13), color=C_MUTED,
                              size_hint_y=None, height=dp(22), halign='left'))
        root.add_widget(Widget(size_hint_y=None, height=dp(6)))

        def field(label, pw=False):
            root.add_widget(FieldLabel(text=label))
            inp = ModernInput(password=pw)
            root.add_widget(inp)
            return inp

        self.name_in  = field('FULL NAME')
        self.email_in = field('EMAIL')
        self.pass_in  = field('PASSWORD', pw=True)
        self.phone_in = field('PHONE  (optional)')

        self.status = StatusLabel()
        root.add_widget(self.status)

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(12))
        reg_btn  = ModernButton(text='Create Account', accent=C_ACCENT,
                                text_color=C_BG)
        reg_btn.bind(on_press=self.register)
        back_btn = ModernButton(text='Back', accent=C_SURFACE2,
                                text_color=C_TEXT)
        back_btn.bind(on_press=self.go_back)
        btn_row.add_widget(reg_btn)
        btn_row.add_widget(back_btn)
        root.add_widget(btn_row)

        self.add_widget(root)

    def register(self, *_):
        name  = self.name_in.text.strip()
        email = self.email_in.text.strip()
        pw    = self.pass_in.text.strip()
        phone = self.phone_in.text.strip()
        if not name or not email or not pw:
            self.status.show('Please fill all required fields.')
            return
        if '@' not in email:
            self.status.show('Invalid email address.')
            return
        if len(pw) < 6:
            self.status.show('Password must be at least 6 characters.')
            return
        if insert_user(name, email, pw, phone):
            self.status.show('Account created!  You can log in now.', ok=True)
            for f in [self.name_in, self.email_in, self.pass_in, self.phone_in]:
                f.text = ''
        else:
            self.status.show('Email already registered.')

    def go_back(self, *_): self.manager.current = 'home'


# ─────────────────────────────────────────
#   LOGIN SCREEN
# ─────────────────────────────────────────

class LoginScreen(BaseScreen):
    def build(self):
        root = BoxLayout(orientation='vertical',
                         padding=[dp(24), dp(50), dp(24), dp(24)],
                         spacing=dp(14))

        root.add_widget(Label(text='Welcome back', font_size=dp(26),
                              bold=True, color=C_TEXT,
                              size_hint_y=None, height=dp(40)))
        root.add_widget(Label(text='Sign in to Nexus',
                              font_size=dp(13), color=C_MUTED,
                              size_hint_y=None, height=dp(26)))

        root.add_widget(FieldLabel(text='EMAIL'))
        self.email_in = ModernInput()
        root.add_widget(self.email_in)

        root.add_widget(FieldLabel(text='PASSWORD'))
        self.pass_in = ModernInput(password=True)
        root.add_widget(self.pass_in)

        self.status = StatusLabel()
        root.add_widget(self.status)

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(12))
        login_btn = ModernButton(text='Sign In', accent=C_ACCENT, text_color=C_BG)
        login_btn.bind(on_press=self.login)
        back_btn  = ModernButton(text='Back', accent=C_SURFACE2, text_color=C_TEXT)
        back_btn.bind(on_press=self.go_back)
        btn_row.add_widget(login_btn)
        btn_row.add_widget(back_btn)
        root.add_widget(btn_row)

        root.add_widget(Widget())
        self.add_widget(root)

    def login(self, *_):
        global current_user, current_email
        email = self.email_in.text.strip()
        pw    = self.pass_in.text.strip()
        name  = check_user(email, pw)
        if name:
            current_user  = name
            current_email = email
            self.status.show(f'Welcome back, {name}!', ok=True)
            Clock.schedule_once(
                lambda dt: setattr(self.manager, 'current', 'home'), 1.2)
        else:
            self.status.show('Incorrect email or password.')

    def go_back(self, *_): self.manager.current = 'home'


# ─────────────────────────────────────────
#   VIEW USERS SCREEN
# ─────────────────────────────────────────

class ViewUsersScreen(BaseScreen):
    def build(self):
        root = BoxLayout(orientation='vertical',
                         padding=[dp(20), dp(30), dp(20), dp(20)],
                         spacing=dp(12))

        root.add_widget(Label(text='Members', font_size=dp(26),
                              bold=True, color=C_TEXT,
                              size_hint_y=None, height=dp(40)))
        root.add_widget(Divider())

        scroll = ScrollView()
        self.list_layout = BoxLayout(orientation='vertical',
                                     size_hint_y=None, spacing=dp(8))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        root.add_widget(scroll)

        back_btn = ModernButton(text='Back', accent=C_SURFACE2, text_color=C_TEXT,
                                size_hint_y=None)
        back_btn.bind(on_press=self.go_back)
        root.add_widget(back_btn)
        self.add_widget(root)

    def on_enter(self):
        self.list_layout.clear_widgets()
        users = get_users()
        if not users:
            self.list_layout.add_widget(
                Label(text='No users yet.', color=C_MUTED,
                      size_hint_y=None, height=dp(50)))
            return
        for name, email in users:
            row = BoxLayout(orientation='horizontal',
                            size_hint_y=None, height=dp(64),
                            padding=[dp(14), dp(10)], spacing=dp(12))
            with row.canvas.before:
                Color(*C_SURFACE)
                RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(10)])
            row.bind(pos=lambda inst, _: self._redraw_row(inst),
                     size=lambda inst, _: self._redraw_row(inst))

            init = (name[0] + (name.split()[-1][0] if ' ' in name else '')).upper()
            av = Avatar(initials=init, color=C_ACCENT, size_dp=40)
            row.add_widget(av)

            info = BoxLayout(orientation='vertical', spacing=dp(2))
            n_lbl = Label(text=name, color=C_TEXT, font_size=dp(14),
                          bold=True, halign='left')
            n_lbl.bind(size=lambda inst, _: setattr(inst, 'text_size', (inst.width, None)))
            e_lbl = Label(text=email, color=C_MUTED, font_size=dp(11),
                          halign='left')
            e_lbl.bind(size=lambda inst, _: setattr(inst, 'text_size', (inst.width, None)))
            info.add_widget(n_lbl)
            info.add_widget(e_lbl)
            row.add_widget(info)
            self.list_layout.add_widget(row)

    def _redraw_row(self, row):
        row.canvas.before.clear()
        with row.canvas.before:
            Color(*C_SURFACE)
            RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(10)])

    def go_back(self, *_): self.manager.current = 'home'


# ─────────────────────────────────────────
#   CHAT SCREEN
# ─────────────────────────────────────────

class ChatScreen(BaseScreen):
    def build(self):
        root = BoxLayout(orientation='vertical',
                         padding=[dp(12), dp(16), dp(12), dp(10)],
                         spacing=dp(8))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        back_btn = ModernButton(text='‹', accent=C_SURFACE2, text_color=C_TEXT,
                                size_hint_x=None, width=dp(46))
        back_btn.bind(on_press=self.go_back)
        title = Label(text='Chat Room', font_size=dp(18), bold=True,
                      color=C_TEXT, halign='left')
        title.bind(size=lambda *_: setattr(title, 'text_size', (title.width, None)))
        self.user_pill = Label(text='', font_size=dp(11), color=C_ACCENT,
                               halign='right')
        self.user_pill.bind(size=lambda *_: setattr(
            self.user_pill, 'text_size', (self.user_pill.width, None)))
        hdr.add_widget(back_btn)
        hdr.add_widget(title)
        hdr.add_widget(self.user_pill)
        root.add_widget(hdr)
        root.add_widget(Divider())

        # Messages area
        self.scroll = ScrollView()
        self.chat_layout = BoxLayout(orientation='vertical',
                                     size_hint_y=None, spacing=dp(6),
                                     padding=[dp(4), dp(8)])
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        self.scroll.add_widget(self.chat_layout)
        root.add_widget(self.scroll)

        # Input bar
        bar = BoxLayout(size_hint_y=None, height=INPUT_H + dp(8),
                        spacing=dp(8), padding=[0, dp(4)])
        self.msg_in = ModernInput(hint_text='Type a message…')
        self.msg_in.height = INPUT_H
        send_btn = ModernButton(text='Send', accent=C_ACCENT, text_color=C_BG,
                                size_hint_x=None, width=dp(72))
        send_btn.bind(on_press=self.send_message)
        bar.add_widget(self.msg_in)
        bar.add_widget(send_btn)
        root.add_widget(bar)

        self.add_widget(root)

    def on_enter(self):
        self.user_pill.text = f'● {current_user}'
        self.load_messages()
        Clock.schedule_interval(self.load_messages, 2)

    def on_leave(self):
        Clock.unschedule(self.load_messages)

    def load_messages(self, *_):
        self.chat_layout.clear_widgets()
        for name, msg, ts in get_messages():
            time_str = str(ts)[11:16]
            is_me = (name == current_user)
            bubble = ChatBubble(name, msg, time_str, is_me=is_me)
            self.chat_layout.add_widget(bubble)
        self.scroll.scroll_y = 0

    def send_message(self, *_):
        msg = self.msg_in.text.strip()
        if msg and save_message(current_user, msg):
            self.msg_in.text = ''
            self.load_messages()

    def go_back(self, *_):
        global current_user, current_email
        current_user = current_email = None
        self.manager.current = 'home'


# ─────────────────────────────────────────
#   PROFILE SCREEN
# ─────────────────────────────────────────

class ProfileScreen(BaseScreen):
    def build(self):
        root = BoxLayout(orientation='vertical',
                         padding=[dp(20), dp(28), dp(20), dp(20)],
                         spacing=dp(10))

        # Avatar row
        av_row = BoxLayout(size_hint_y=None, height=dp(80),
                           spacing=dp(16))
        self.avatar = Widget(size_hint=(None, None), size=(dp(64), dp(64)))
        self._av_name = ''
        av_row.add_widget(self.avatar)

        info = BoxLayout(orientation='vertical', spacing=dp(4))
        self.name_lbl = Label(text='', font_size=dp(18), bold=True,
                              color=C_TEXT, halign='left')
        self.name_lbl.bind(size=lambda *_: setattr(
            self.name_lbl, 'text_size', (self.name_lbl.width, None)))
        self.join_lbl = Label(text='', font_size=dp(11), color=C_MUTED,
                              halign='left')
        self.join_lbl.bind(size=lambda *_: setattr(
            self.join_lbl, 'text_size', (self.join_lbl.width, None)))
        info.add_widget(self.name_lbl)
        info.add_widget(self.join_lbl)
        av_row.add_widget(info)
        root.add_widget(av_row)
        root.add_widget(Divider())

        # Info pills
        self.email_lbl = Label(text='', font_size=dp(12), color=C_MUTED,
                               size_hint_y=None, height=dp(22), halign='left')
        self.email_lbl.bind(size=lambda *_: setattr(
            self.email_lbl, 'text_size', (self.email_lbl.width, None)))
        self.phone_lbl = Label(text='', font_size=dp(12), color=C_MUTED,
                               size_hint_y=None, height=dp(22), halign='left')
        self.phone_lbl.bind(size=lambda *_: setattr(
            self.phone_lbl, 'text_size', (self.phone_lbl.width, None)))
        root.add_widget(self.email_lbl)
        root.add_widget(self.phone_lbl)

        root.add_widget(Widget(size_hint_y=None, height=dp(6)))
        root.add_widget(FieldLabel(text='BIO'))

        self.bio_in = TextInput(
            background_normal='', background_active='',
            background_color=(0, 0, 0, 0),
            foreground_color=C_TEXT, cursor_color=C_ACCENT,
            hint_text_color=list(C_MUTED),
            font_size=dp(13), padding=[dp(12), dp(10)],
            size_hint_y=None, height=dp(110),
            multiline=True)

        def _draw_bio(*_):
            self.bio_in.canvas.before.clear()
            with self.bio_in.canvas.before:
                Color(*C_SURFACE2)
                RoundedRectangle(pos=self.bio_in.pos,
                                 size=self.bio_in.size,
                                 radius=[dp(10)])

        self.bio_in.bind(pos=_draw_bio, size=_draw_bio)
        root.add_widget(self.bio_in)

        self.status = StatusLabel()
        root.add_widget(self.status)

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(10))
        save_btn = ModernButton(text='Save Bio', accent=C_ACCENT, text_color=C_BG)
        save_btn.bind(on_press=self.save_bio)
        back_btn = ModernButton(text='Back', accent=C_SURFACE2, text_color=C_TEXT)
        back_btn.bind(on_press=self.go_back)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(back_btn)
        root.add_widget(btn_row)

        self.add_widget(root)

    def on_enter(self):
        email = current_email or get_user_email(current_user)
        profile = get_profile(email)
        if profile:
            name, phone, bio, join_date = profile
            self.name_lbl.text  = name
            self.email_lbl.text = f'✉  {email}'
            self.phone_lbl.text = f'📱  {phone if phone else "No phone set"}'
            self.join_lbl.text  = f'Member since {str(join_date)[:10]}'
            self.bio_in.text    = bio if bio else ''

            # Draw avatar
            init = (name[0] + (name.split()[-1][0] if ' ' in name else '')).upper()
            self.avatar.canvas.clear()
            with self.avatar.canvas:
                Color(*C_ACCENT, 0.25)
                Ellipse(pos=self.avatar.pos, size=self.avatar.size)
                Color(*C_ACCENT)
                Line(ellipse=(*self.avatar.pos, *self.avatar.size), width=2)
            # overlay label
            for child in list(self.avatar.children):
                self.avatar.remove_widget(child)
            lbl = Label(text=init, color=C_ACCENT, font_size=dp(24),
                        bold=True, pos=self.avatar.pos, size=self.avatar.size)
            self.avatar.add_widget(lbl)

    def save_bio(self, *_):
        email = current_email or get_user_email(current_user)
        if update_profile(email, self.bio_in.text.strip()):
            self.status.show('Bio saved!', ok=True)
        else:
            self.status.show('Failed to save.')

    def go_back(self, *_): self.manager.current = 'home'


# ─────────────────────────────────────────
#   APP ENTRY
# ─────────────────────────────────────────

class NexusApp(App):
    def build(self):
        setup_db()
        self.title = 'Nexus'
        sm = ScreenManager(transition=FadeTransition(duration=0.18))
        for Cls, name in [
            (HomeScreen,      'home'),
            (RegisterScreen,  'register'),
            (LoginScreen,     'login'),
            (ViewUsersScreen, 'view'),
            (ChatScreen,      'chat'),
            (ProfileScreen,   'profile'),
        ]:
            s = Cls(name=name)
            s.build()
            sm.add_widget(s)
        return sm


if __name__ == '__main__':
    NexusApp().run()