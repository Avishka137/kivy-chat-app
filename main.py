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

# ── Blue + Teal Ocean Palette ──────────────────────────────────────────────────
PRIMARY       = (0.10, 0.38, 0.78, 1)
PRIMARY_DARK  = (0.05, 0.20, 0.48, 1)
PRIMARY_LIGHT = (0.58, 0.82, 0.96, 1)
ACCENT        = (0.22, 0.52, 0.90, 1)
ACCENT2       = (0.06, 0.28, 0.62, 1)
BG_LIGHT      = (0.93, 0.95, 0.98, 1)
CARD_BG       = (1,    1,    1,    1)
TEXT_DARK     = (0.07, 0.17, 0.27, 1)
TEXT_MUTED    = (0.45, 0.55, 0.65, 1)
WHITE         = (1,    1,    1,    1)
DANGER        = (0.75, 0.15, 0.15, 1)
SUCCESS       = (0.22, 0.52, 0.90, 1)
SUCCESS_GREEN = (0.10, 0.60, 0.25, 1)
WARNING       = (0.85, 0.55, 0.05, 1)
NAME_COLOR    = (0.98, 0.75, 0.10, 1)
ADMIN_COLOR   = (0.80, 0.10, 0.80, 1)
INBOX_COLOR   = (0.08, 0.50, 0.72, 1)

USER_COLORS = [
    (0.22, 0.52, 0.90, 1),
    (0.06, 0.70, 0.50, 1),
    (0.85, 0.30, 0.35, 1),
    (0.40, 0.60, 0.90, 1),
    (0.10, 0.60, 0.75, 1),
    (0.90, 0.50, 0.20, 1),
    (0.50, 0.20, 0.70, 1),
    (0.20, 0.75, 0.60, 1),
    (0.75, 0.35, 0.60, 1),
    (0.30, 0.50, 0.80, 1),
]

Window.size = (400, 700)
Window.clearcolor = (0.93, 0.95, 0.98, 1)

ADMIN_EMAIL    = "admin@userhub.com"
ADMIN_PASSWORD = "Admin@1234"
ADMIN_NAME     = "Administrator"

current_user        = None
current_user_email  = None
is_admin            = False
is_approved         = False
user_color_map      = {}
dm_target_email     = None
dm_target_name      = None

DB_FILE = os.path.join(os.path.expanduser('~'), 'Documents', 'user_app_database.db')
PROFILE_PICS_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'user_app_profile_pics')

if not os.path.exists(PROFILE_PICS_DIR):
    os.makedirs(PROFILE_PICS_DIR)


def assign_user_color(user_name):
    if user_name not in user_color_map:
        color_idx = sum(ord(c) for c in user_name) % len(USER_COLORS)
        user_color_map[user_name] = USER_COLORS[color_idx]
    return user_color_map[user_name]

def get_user_color(user_name):
    return assign_user_color(user_name)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def setup_db():
    db_valid = False
    if os.path.exists(DB_FILE):
        try:
            test_conn = sqlite3.connect(DB_FILE, timeout=5)
            test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            test_conn.close()
            db_valid = True
        except:
            db_valid = False

    if not db_valid:
        for f in [DB_FILE, f"{DB_FILE}-shm", f"{DB_FILE}-wal", f"{DB_FILE}-journal"]:
            try:
                if os.path.exists(f): os.remove(f)
            except: pass

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")

        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, phone TEXT,
            is_admin INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        # Migrate any missing columns on existing databases.
        # IMPORTANT: SQLite ALTER TABLE cannot accept non-constant defaults
        # like CURRENT_TIMESTAMP, so created_at must default to NULL here;
        # a follow-up UPDATE fills it in for any rows that are still NULL.
        migrations = [
            "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN phone TEXT",
            "ALTER TABLE users ADD COLUMN created_at DATETIME",
        ]
        for sql in migrations:
            try:
                c.execute(sql)
                conn.commit()
            except:
                pass  # Column already exists — safe to ignore

        # Back-fill created_at NULLs left by migration
        try:
            c.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL")
            conn.commit()
        except:
            pass

        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL, message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL, bio TEXT,
            profile_pic TEXT, join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(email) REFERENCES users(email))''')

        # Migrate profiles table — add missing columns on old databases
        profiles_migrations = [
            "ALTER TABLE profiles ADD COLUMN bio TEXT",
            "ALTER TABLE profiles ADD COLUMN profile_pic TEXT",
            "ALTER TABLE profiles ADD COLUMN join_date DATETIME",
        ]
        for sql in profiles_migrations:
            try:
                c.execute(sql)
                conn.commit()
            except:
                pass  # Column already exists — safe to ignore

        c.execute('''CREATE TABLE IF NOT EXISTS timeline_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL, post_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(email) REFERENCES users(email))''')

        c.execute('''CREATE TABLE IF NOT EXISTS user_actions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_email TEXT NOT NULL,
            action TEXT NOT NULL,
            target_user TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS direct_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_email TEXT NOT NULL,
            receiver_email TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()

        c.execute("SELECT id FROM users WHERE email=?", (ADMIN_EMAIL,))
        if not c.fetchone():
            c.execute(
                "INSERT INTO users (name, email, password, phone, is_admin, is_approved, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ADMIN_NAME, ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), "0000000000", 1, 1, datetime.now())
            )
            conn.commit()

        conn.close()
        return True
    except Exception as e:
        print(f"DB setup error: {e}")
        return False


# ── FIX 1: insert_user — safely handle conn before it's guaranteed to exist ──
def insert_user(name, email, password, phone):
    """Returns True on success, 'duplicate' if email already exists, False on other error."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (name, email, password, phone, is_admin, is_approved, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, email, hash_password(password), phone, 0, 0, datetime.now())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Email already exists (UNIQUE constraint on email column)
        return 'duplicate'
    except Exception as e:
        print(f"insert_user error: {e}")
        return False
    finally:
        # Always close conn if it was opened, regardless of success or failure
        if conn:
            try:
                conn.close()
            except:
                pass


def check_user(email, password):
    """Returns (name, is_admin, is_approved) or None"""
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return (ADMIN_NAME, True, True)
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT name, password, is_admin, is_approved FROM users WHERE email=?", (email,))
        result = c.fetchone(); conn.close()
        if result and verify_password(password, result[1]):
            return (result[0], bool(result[2]), bool(result[3]))
        return None
    except: return None

def get_users():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT name, email, is_admin, created_at, is_approved FROM users WHERE email != ? ORDER BY created_at DESC",
            (ADMIN_EMAIL,)
        )
        users = c.fetchall(); conn.close(); return users
    except: return []

def get_pending_users():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT name, email, created_at FROM users WHERE is_approved=0 AND email != ? ORDER BY created_at DESC",
            (ADMIN_EMAIL,)
        )
        users = c.fetchall(); conn.close(); return users
    except: return []

def approve_user(email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("UPDATE users SET is_approved=1 WHERE email=?", (email,))
        conn.commit(); conn.close(); return True
    except: return False

def reject_user(email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("UPDATE users SET is_approved=-1 WHERE email=?", (email,))
        conn.commit(); conn.close(); return True
    except: return False

def delete_user(email):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()

        # Safely try to get profile_pic — column may not exist on old DBs
        try:
            c.execute("SELECT profile_pic FROM profiles WHERE email=?", (email,))
            pic_result = c.fetchone()
            if pic_result and pic_result[0] and os.path.exists(pic_result[0]):
                try: os.remove(pic_result[0])
                except: pass
        except Exception:
            pass  # profiles table or profile_pic column doesn't exist yet

        c.execute("DELETE FROM users WHERE email=?", (email,))
        c.execute("DELETE FROM profiles WHERE email=?", (email,))
        c.execute("DELETE FROM timeline_posts WHERE email=?", (email,))
        c.execute("DELETE FROM direct_messages WHERE sender_email=? OR receiver_email=?", (email, email))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete user error: {e}")
        return False
    finally:
        if conn:
            try: conn.close()
            except: pass

def log_admin_action(admin_email, action, target_user=None):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "INSERT INTO user_actions_log (admin_email, action, target_user, timestamp) VALUES (?, ?, ?, ?)",
            (admin_email, action, target_user, datetime.now())
        )
        conn.commit(); conn.close(); return True
    except: return False

def get_admin_logs():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT admin_email, action, target_user, timestamp FROM user_actions_log ORDER BY timestamp DESC LIMIT 20"
        )
        logs = c.fetchall(); conn.close(); return logs
    except: return []

def delete_message_by_index(idx):
    try:
        msgs = get_messages()
        if 0 <= idx < len(msgs):
            conn = sqlite3.connect(DB_FILE, timeout=10)
            c = conn.cursor()
            c.execute(
                "DELETE FROM messages WHERE user_name=? AND message=? AND timestamp=?",
                (msgs[idx][0], msgs[idx][1], msgs[idx][2])
            )
            conn.commit(); conn.close(); return True
        return False
    except: return False

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

def clear_old_messages(days):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE timestamp < datetime('now', ?)", (f'-{days} days',))
        deleted = c.rowcount
        conn.commit(); conn.close(); return deleted
    except: return 0

def get_profile(email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT u.name, u.phone, p.bio, p.join_date, p.profile_pic
            FROM users u
            LEFT JOIN profiles p ON u.email = p.email
            WHERE u.email = ?
        """, (email,))
        result = c.fetchone(); conn.close()
        return result
    except Exception as e:
        print(f"get_profile error: {e}")
        return None


# ── FIX 2: update_profile — use proper upsert so profile_pic is never wiped ──
def update_profile(email, bio, profile_pic=None):
    """
    Upsert the profiles row for this email.
    - If no row exists yet, insert one (preserving join_date as NOW).
    - If a row already exists, update only the columns that were passed in.
      Crucially, when profile_pic is None we do NOT overwrite the stored path —
      we keep whatever was already saved. This prevents a bio-save from blanking
      a previously uploaded photo.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()

        # Check whether a profile row already exists
        c.execute("SELECT profile_pic FROM profiles WHERE email=?", (email,))
        existing = c.fetchone()

        if existing is None:
            # No row yet — insert fresh. Use the supplied pic (may be None).
            c.execute(
                "INSERT INTO profiles (email, bio, profile_pic, join_date) VALUES (?, ?, ?, ?)",
                (email, bio, profile_pic, datetime.now())
            )
        else:
            # Row exists — decide which pic path to keep.
            # If a new pic was supplied use it; otherwise keep the stored path.
            final_pic = profile_pic if profile_pic is not None else existing[0]
            c.execute(
                "UPDATE profiles SET bio=?, profile_pic=? WHERE email=?",
                (bio, final_pic, email)
            )

        conn.commit()
        return True
    except Exception as e:
        print(f"update_profile error: {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_user_email(name):
    if name == ADMIN_NAME:
        return ADMIN_EMAIL
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
        c.execute(
            "SELECT post_text, timestamp FROM timeline_posts WHERE email = ? ORDER BY timestamp DESC",
            (email,)
        )
        posts = c.fetchall(); conn.close(); return posts
    except: return []

def get_all_messages_count():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM messages")
        result = c.fetchone(); conn.close()
        return result[0] if result else 0
    except: return 0

def get_total_users_count():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE email != ?", (ADMIN_EMAIL,))
        result = c.fetchone(); conn.close()
        return result[0] if result else 0
    except: return 0

def get_pending_count():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE is_approved=0 AND email != ?", (ADMIN_EMAIL,))
        result = c.fetchone(); conn.close()
        return result[0] if result else 0
    except: return 0

def send_dm(sender_email, receiver_email, message):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "INSERT INTO direct_messages (sender_email, receiver_email, message, timestamp) VALUES (?, ?, ?, ?)",
            (sender_email, receiver_email, message, datetime.now())
        )
        conn.commit(); conn.close(); return True
    except: return False

def get_dm_messages(user1_email, user2_email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("""SELECT sender_email, message, timestamp FROM direct_messages
                     WHERE (sender_email=? AND receiver_email=?) OR (sender_email=? AND receiver_email=?)
                     ORDER BY timestamp ASC LIMIT 100""",
                  (user1_email, user2_email, user2_email, user1_email))
        msgs = c.fetchall(); conn.close(); return msgs
    except: return []

def get_dm_conversations(email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("""SELECT other_email, MAX(timestamp) as last_time
                     FROM (
                         SELECT receiver_email as other_email, timestamp FROM direct_messages WHERE sender_email=?
                         UNION ALL
                         SELECT sender_email as other_email, timestamp FROM direct_messages WHERE receiver_email=?
                     ) GROUP BY other_email ORDER BY last_time DESC""",
                  (email, email))
        partners = c.fetchall()
        result = []
        for other_email, last_time in partners:
            c.execute("""SELECT message FROM direct_messages
                         WHERE (sender_email=? AND receiver_email=?) OR (sender_email=? AND receiver_email=?)
                         ORDER BY timestamp DESC LIMIT 1""",
                      (email, other_email, other_email, email))
            last_msg_row = c.fetchone()
            c.execute("SELECT name FROM users WHERE email=?", (other_email,))
            name_row = c.fetchone()
            other_name = name_row[0] if name_row else other_email
            result.append((other_email, other_name, last_msg_row[0] if last_msg_row else '', last_time))
        conn.close(); return result
    except: return []

def get_unread_count(my_email, other_email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM direct_messages WHERE sender_email=? AND receiver_email=? AND is_read=0",
            (other_email, my_email)
        )
        result = c.fetchone(); conn.close()
        return result[0] if result else 0
    except: return 0

def get_total_unread(my_email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM direct_messages WHERE receiver_email=? AND is_read=0", (my_email,))
        result = c.fetchone(); conn.close()
        return result[0] if result else 0
    except: return 0

def mark_dm_read(my_email, other_email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "UPDATE direct_messages SET is_read=1 WHERE sender_email=? AND receiver_email=?",
            (other_email, my_email)
        )
        conn.commit(); conn.close()
    except: pass

def get_all_approved_users(exclude_email):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        c = conn.cursor()
        c.execute(
            "SELECT name, email FROM users WHERE email != ? AND email != ? AND is_approved=1 ORDER BY name",
            (exclude_email, ADMIN_EMAIL)
        )
        users = c.fetchall(); conn.close(); return users
    except: return []


# ── UI Helpers ────────────────────────────────────────────────────────────────
def make_rounded_button(text, bg_color, text_color=WHITE, height=50, radius=12):
    btn = Button(
        text=text, size_hint_y=None, height=dp(height),
        background_normal='', background_color=(0, 0, 0, 0),
        color=text_color, font_size='15sp', bold=True
    )
    with btn.canvas.before:
        Color(*bg_color)
        btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(radius)])
    btn.bind(
        pos=lambda w, v: setattr(w._bg_rect, 'pos', v),
        size=lambda w, v: setattr(w._bg_rect, 'size', v)
    )
    return btn

def make_card(padding=16, spacing=10):
    card = BoxLayout(orientation='vertical', padding=dp(padding), spacing=dp(spacing), size_hint_y=None)
    with card.canvas.before:
        Color(0.10, 0.40, 0.80, 0.04)
        card._shadow = RoundedRectangle(pos=(card.x + dp(2), card.y - dp(2)), size=card.size, radius=[dp(14)])
        Color(*CARD_BG)
        card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(14)])
    card.bind(
        pos=lambda w, v: (setattr(w._shadow, 'pos', (v[0]+dp(2), v[1]-dp(2))), setattr(w._bg, 'pos', v)),
        size=lambda w, v: (setattr(w._shadow, 'size', v), setattr(w._bg, 'size', v))
    )
    return card

def styled_input(hint, is_password=False):
    inp = TextInput(
        hint_text=hint, password=is_password, multiline=False,
        size_hint_y=None, height=dp(50),
        background_color=(1, 1, 1, 1), foreground_color=TEXT_DARK,
        hint_text_color=(*TEXT_MUTED[:3], 0.6), cursor_color=PRIMARY,
        padding=[dp(16), dp(14)], font_size='14sp',
        background_normal='', background_active='',
    )
    with inp.canvas.after:
        Color(*PRIMARY_LIGHT)
        inp._border = Rectangle(pos=(inp.x, inp.y), size=(inp.width, dp(2)))
    inp.bind(
        pos=lambda w, v: setattr(w._border, 'pos', (v[0], v[1])),
        size=lambda w, v: setattr(w._border, 'size', (v[0], dp(2)))
    )
    return inp

def icon_label(icon, text, color=TEXT_MUTED):
    lbl = Label(text=f'{icon}  {text}', font_size='13sp', color=color,
                size_hint_y=None, height=dp(28), halign='left', valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    return lbl

def section_label(text, color=ACCENT):
    lbl = Label(text=text.upper(), font_size='10sp', color=color,
                size_hint_y=None, height=dp(28), halign='left', valign='middle', bold=True)
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


# ── Decorative Header Widget ──────────────────────────────────────────────────
class HeroHeader(Widget):
    def __init__(self, icon='👤', title='', subtitle='', bg1=PRIMARY, bg2=PRIMARY_DARK,
                 height=220, **kwargs):
        super().__init__(size_hint_y=None, height=dp(height), **kwargs)
        self.icon = icon; self.title_text = title; self.subtitle_text = subtitle
        self.bg1 = bg1; self.bg2 = bg2
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*self.bg2); Rectangle(pos=self.pos, size=self.size)
            Color(*self.bg1, 0.55)
            Ellipse(pos=(self.x - dp(50), self.y + self.height * 0.30), size=(dp(220), dp(220)))
            Color(*self.bg1, 0.40)
            Ellipse(pos=(self.x + self.width - dp(120), self.y + self.height * 0.45), size=(dp(180), dp(180)))
            Color(1, 1, 1, 0.07)
            Ellipse(pos=(self.x + self.width * 0.25, self.y - dp(30)), size=(dp(140), dp(140)))
            Color(1, 1, 1, 0.05)
            Ellipse(pos=(self.x + self.width * 0.55, self.y + self.height * 0.60), size=(dp(90), dp(90)))
            Color(1, 1, 1, 0.14)
            cx = self.x + self.width / 2 - dp(44); cy = self.y + self.height * 0.40
            Ellipse(pos=(cx, cy), size=(dp(88), dp(88)))
            Color(*self.bg2)
            RoundedRectangle(pos=(self.x, self.y), size=(self.width, dp(36)), radius=[0, 0, dp(30), dp(30)])
            Color(*self.bg1, 0.3)
            RoundedRectangle(pos=(self.x, self.y), size=(self.width, dp(24)), radius=[0, 0, dp(28), dp(28)])

        if not hasattr(self, '_icon_lbl'):
            self._icon_lbl = Label(font_size='36sp', color=WHITE, bold=True)
            self.add_widget(self._icon_lbl)
        self._icon_lbl.text = self.icon
        self._icon_lbl.pos = (self.x, self.y + self.height * 0.38)
        self._icon_lbl.size = (self.width, dp(80))
        self._icon_lbl.halign = 'center'; self._icon_lbl.valign = 'middle'
        self._icon_lbl.text_size = self._icon_lbl.size

        if not hasattr(self, '_title_lbl'):
            self._title_lbl = Label(font_size='22sp', bold=True, color=WHITE)
            self.add_widget(self._title_lbl)
        self._title_lbl.text = self.title_text
        self._title_lbl.pos = (self.x, self.y + dp(52)); self._title_lbl.size = (self.width, dp(34))
        self._title_lbl.halign = 'center'; self._title_lbl.text_size = self._title_lbl.size

        if not hasattr(self, '_sub_lbl'):
            self._sub_lbl = Label(font_size='13sp', color=(1, 1, 1, 0.80))
            self.add_widget(self._sub_lbl)
        self._sub_lbl.text = self.subtitle_text
        self._sub_lbl.pos = (self.x, self.y + dp(26)); self._sub_lbl.size = (self.width, dp(28))
        self._sub_lbl.halign = 'center'; self._sub_lbl.text_size = self._sub_lbl.size


# ══════════════════════════════════════════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════════════════════════════════════════

class HomeScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')
        hero = HeroHeader(icon='🌐', title='User Hub', subtitle='Connect · Chat · Share',
                          bg1=PRIMARY, bg2=PRIMARY_DARK, height=230)
        root.add_widget(hero)

        self.status_bar = BoxLayout(size_hint_y=None, height=dp(36), padding=[dp(20), dp(4)])
        with self.status_bar.canvas.before:
            Color(*PRIMARY, 0.06)
            self.status_bar._bg = Rectangle(pos=self.status_bar.pos, size=self.status_bar.size)
        self.status_bar.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v)
        )
        self.status_lbl = Label(text='  Not logged in', font_size='12sp',
                                color=TEXT_MUTED, halign='left', valign='middle', markup=True)
        self.status_lbl.bind(size=self.status_lbl.setter('text_size'))
        self.status_bar.add_widget(self.status_lbl)
        root.add_widget(self.status_bar)

        scroll = ScrollView(size_hint_y=1)
        inner = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12), size_hint_y=None)
        inner.bind(minimum_height=inner.setter('height'))

        inner.add_widget(section_label('Account'))
        row1 = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(52))
        b_reg = make_rounded_button('  Register', PRIMARY, height=52)
        b_log = make_rounded_button('  Login', ACCENT, height=52)
        b_reg.bind(on_press=lambda *_: setattr(self.manager, 'current', 'register'))
        b_log.bind(on_press=lambda *_: setattr(self.manager, 'current', 'login'))
        row1.add_widget(b_reg); row1.add_widget(b_log)
        inner.add_widget(row1)

        inner.add_widget(section_label('Explore'))
        b_view = make_rounded_button('  Community Members', (1,1,1,1), text_color=PRIMARY_DARK, height=52)
        b_view.bind(on_press=lambda *_: setattr(self.manager, 'current', 'view'))
        inner.add_widget(b_view)

        b_chat = make_rounded_button('  💬  Chat Room', ACCENT, height=52)
        b_chat.bind(on_press=self.go_chat)
        inner.add_widget(b_chat)

        inner.add_widget(section_label('You'))
        b_prof = make_rounded_button('  My Profile', (1,1,1,1), text_color=PRIMARY_DARK, height=52)
        b_prof.bind(on_press=self.go_profile)
        inner.add_widget(b_prof)

        self.inbox_btn = make_rounded_button('  📬  Inbox', INBOX_COLOR, height=52)
        self.inbox_btn.bind(on_press=self.go_inbox)
        self.inbox_btn.opacity = 0; self.inbox_btn.disabled = True
        inner.add_widget(self.inbox_btn)

        self.pending_lbl = Label(text='', font_size='12sp', color=WARNING,
                                 size_hint_y=None, height=dp(0), halign='center', markup=True)
        self.pending_lbl.bind(size=self.pending_lbl.setter('text_size'))
        inner.add_widget(self.pending_lbl)

        self.admin_btn = make_rounded_button('  🛡️  Admin Panel', (0.50, 0.10, 0.70, 1), height=52)
        self.admin_btn.bind(on_press=lambda *_: setattr(self.manager, 'current', 'admin'))
        self.admin_btn.opacity = 0; self.admin_btn.disabled = True
        inner.add_widget(self.admin_btn)

        self.logout_btn = make_rounded_button('  Logout', DANGER, height=44)
        self.logout_btn.bind(on_press=self.do_logout)
        self.logout_btn.opacity = 0; self.logout_btn.disabled = True
        inner.add_widget(self.logout_btn)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self):
        if current_user:
            badge = '  [color=cc00cc][b]👑 ADMIN[/b][/color]' if is_admin else ''
            pending_badge = '  [color=ffaa00]⏳ Pending[/color]' if (not is_admin and not is_approved) else ''
            self.status_lbl.text = f'✅  [color=ffc018][b]{current_user}[/b][/color]{badge}{pending_badge}'
            self.logout_btn.opacity = 1; self.logout_btn.disabled = False

            if is_approved or is_admin:
                self.inbox_btn.opacity = 1; self.inbox_btn.disabled = False
            else:
                self.inbox_btn.opacity = 0; self.inbox_btn.disabled = True

            if not is_admin and not is_approved:
                self.pending_lbl.text = '⏳  Your account is awaiting admin approval'
                self.pending_lbl.height = dp(30)
            else:
                self.pending_lbl.text = ''
                self.pending_lbl.height = dp(0)

            if is_admin:
                self.admin_btn.opacity = 1; self.admin_btn.disabled = False
                pending = get_pending_count()
                badge_txt = f'  🛡️  Admin Panel ({pending} pending)' if pending else '  🛡️  Admin Panel'
                self.admin_btn.text = badge_txt
            else:
                self.admin_btn.opacity = 0; self.admin_btn.disabled = True
        else:
            self.status_lbl.text = 'Not logged in'
            self.logout_btn.opacity = 0; self.logout_btn.disabled = True
            self.admin_btn.opacity = 0; self.admin_btn.disabled = True
            self.inbox_btn.opacity = 0; self.inbox_btn.disabled = True
            self.pending_lbl.text = ''; self.pending_lbl.height = dp(0)

    def go_chat(self, *_):
        if not current_user:
            self.status_lbl.text = '⚠️  Please login first'; return
        if not is_admin and not is_approved:
            self.status_lbl.text = '⏳  Waiting for admin approval'; return
        self.manager.current = 'chat'

    def go_profile(self, *_):
        if current_user: self.manager.current = 'profile'
        else: self.status_lbl.text = '⚠️  Please login first'

    def go_inbox(self, *_):
        if current_user and (is_approved or is_admin): self.manager.current = 'inbox'
        else: self.status_lbl.text = '⚠️  Please login first'

    def do_logout(self, *_):
        global current_user, current_user_email, is_admin, is_approved
        current_user = None; current_user_email = None; is_admin = False; is_approved = False
        self.on_enter()


# ── Register ──────────────────────────────────────────────────────────────────
class RegisterScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')
        hero = HeroHeader(icon='✏️', title='Create Account', subtitle='Join the community today',
                          bg1=ACCENT, bg2=PRIMARY_DARK, height=200)
        root.add_widget(hero)

        scroll = ScrollView(size_hint_y=1)
        form = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12), size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        self.name_input  = styled_input('👤  Full Name')
        self.email_input = styled_input('📧  Email Address')
        self.pass_input  = styled_input('🔒  Password (min 6 chars)', is_password=True)
        self.phone_input = styled_input('📱  Phone Number')

        for w in [self.name_input, self.email_input, self.pass_input, self.phone_input]:
            form.add_widget(w)

        notice = Label(
            text='ℹ️  After registration, an admin must approve\nyour account before you can join the chat.',
            font_size='11sp', color=TEXT_MUTED, size_hint_y=None, height=dp(44),
            halign='center', valign='middle'
        )
        notice.bind(size=notice.setter('text_size'))
        form.add_widget(notice)

        self.msg = Label(text='', color=DANGER, size_hint_y=None, height=dp(28),
                         font_size='12sp', halign='center')
        self.msg.bind(size=self.msg.setter('text_size'))
        form.add_widget(self.msg)

        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(52))
        b_reg  = make_rounded_button('  Register', PRIMARY, height=52)
        b_back = make_rounded_button('  Back', (1,1,1,1), text_color=PRIMARY_DARK, height=52)
        b_reg.bind(on_press=self.register)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        btn_row.add_widget(b_reg); btn_row.add_widget(b_back)
        form.add_widget(btn_row)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def register(self, *_):
        name     = self.name_input.text.strip()
        email    = self.email_input.text.strip().lower()
        password = self.pass_input.text.strip()
        phone    = self.phone_input.text.strip()

        if not name or not email or not password:
            self.msg.color = DANGER
            self.msg.text = '⚠️  Please fill in all required fields'; return
        if '@' not in email or '.' not in email:
            self.msg.color = DANGER
            self.msg.text = '⚠️  Please enter a valid email address'; return
        if len(password) < 6:
            self.msg.color = DANGER
            self.msg.text = '⚠️  Password must be at least 6 characters'; return
        if email == ADMIN_EMAIL.lower():
            self.msg.color = DANGER
            self.msg.text = '⚠️  This email is reserved'; return

        result = insert_user(name, email, password, phone)
        if result is True:
            self.msg.color = SUCCESS_GREEN
            self.msg.text = '🎉  Registered! Waiting for admin approval.'
            for inp in [self.name_input, self.email_input, self.pass_input, self.phone_input]:
                inp.text = ''
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'login'), 2.0)
        elif result == 'duplicate':
            self.msg.color = DANGER
            self.msg.text = '⚠️  This email is already registered'
        else:
            self.msg.color = DANGER
            self.msg.text = '⚠️  Registration failed. Please try again.'


# ── Login ─────────────────────────────────────────────────────────────────────
class LoginScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')
        hero = HeroHeader(icon='🔑', title='Welcome Back', subtitle='Sign in to your account',
                          bg1=PRIMARY, bg2=PRIMARY_DARK, height=210)
        root.add_widget(hero)

        scroll = ScrollView(size_hint_y=1)
        form = BoxLayout(orientation='vertical', padding=dp(24), spacing=dp(14), size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        self.email_input = styled_input('📧  Email Address')
        self.pass_input  = styled_input('🔒  Password', is_password=True)
        form.add_widget(self.email_input); form.add_widget(self.pass_input)

        self.msg = Label(text='', color=DANGER, size_hint_y=None, height=dp(36),
                         font_size='12sp', halign='center')
        self.msg.bind(size=self.msg.setter('text_size'))
        form.add_widget(self.msg)

        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(52))
        b_login = make_rounded_button('  Login', PRIMARY, height=52)
        b_back  = make_rounded_button('  Back', PRIMARY_LIGHT, text_color=PRIMARY_DARK, height=52)
        b_login.bind(on_press=self.login)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        btn_row.add_widget(b_login); btn_row.add_widget(b_back)
        form.add_widget(btn_row)

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def login(self, *_):
        global current_user, current_user_email, is_admin, is_approved
        email    = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        result   = check_user(email, password)
        if result:
            name, admin, approved = result
            current_user       = name
            current_user_email = email
            is_admin           = admin
            is_approved        = approved
            assign_user_color(name)
            self.msg.color = SUCCESS_GREEN
            if admin:
                self.msg.text = f'✅  Welcome back, {name}! 👑'
            elif approved:
                self.msg.text = f'✅  Welcome back, {name}!'
            else:
                self.msg.color = WARNING
                self.msg.text  = f'⏳  Logged in. Awaiting admin approval to join chat.'
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'home'), 1.2)
        else:
            self.msg.color = DANGER
            self.msg.text  = '⚠️  Invalid email or password'


# ── View Users ────────────────────────────────────────────────────────────────
class ViewUsersScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')
        hero = HeroHeader(icon='👥', title='Community', subtitle='All registered members',
                          bg1=ACCENT, bg2=PRIMARY_DARK, height=190)
        root.add_widget(hero)

        inner = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))
        self.stats_lbl = Label(text='', font_size='12sp', color=TEXT_MUTED,
                               size_hint_y=None, height=dp(28), halign='left')
        self.stats_lbl.bind(size=self.stats_lbl.setter('text_size'))
        inner.add_widget(self.stats_lbl)

        self.scroll = ScrollView(size_hint_y=1)
        self.user_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.user_layout.bind(minimum_height=self.user_layout.setter('height'))
        self.scroll.add_widget(self.user_layout)
        inner.add_widget(self.scroll)

        b_back = make_rounded_button('  Back to Home', (1,1,1,1), text_color=PRIMARY_DARK, height=48)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        inner.add_widget(b_back)
        root.add_widget(inner)
        self.add_widget(root)

    def on_enter(self):
        self.user_layout.clear_widgets()
        users = get_users()
        approved_users = [u for u in users if u[4] == 1]
        self.stats_lbl.text = f'👥  {len(approved_users)} approved member{"s" if len(approved_users) != 1 else ""}'
        avatars = ['🧑', '👩', '🧔', '👱', '🧕', '👲', '🧑‍💻', '👩‍💼', '🧑‍🎨', '👩‍🔬']

        if approved_users:
            for i, (name, email, admin_flag, created_at, approved) in enumerate(approved_users):
                card = make_card(padding=12, spacing=6)
                card.size_hint_y = None; card.height = dp(68)
                row = BoxLayout(spacing=dp(12))
                av = Label(text=avatars[i % len(avatars)], font_size='22sp',
                           size_hint=(None, None), size=(dp(44), dp(44)))
                with av.canvas.before:
                    Color(*PRIMARY, 0.15); Ellipse(pos=av.pos, size=av.size)
                av.bind(pos=lambda w, v: setattr(w.canvas.before.children[-1], 'pos', v))
                info = BoxLayout(orientation='vertical')
                n_lbl = Label(text=name, font_size='14sp', bold=True, color=TEXT_DARK,
                              halign='left', valign='middle')
                n_lbl.bind(size=n_lbl.setter('text_size'))
                e_lbl = Label(text=email, font_size='11sp', color=TEXT_MUTED, halign='left', valign='middle')
                e_lbl.bind(size=e_lbl.setter('text_size'))
                info.add_widget(n_lbl); info.add_widget(e_lbl)
                row.add_widget(av); row.add_widget(info)
                card.add_widget(row)
                self.user_layout.add_widget(card)
        else:
            self.user_layout.add_widget(
                Label(text='No approved members yet.', color=TEXT_MUTED,
                      size_hint_y=None, height=dp(60)))


# ── Chat Room ─────────────────────────────────────────────────────────────────
class ChatScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        # ── Header ────────────────────────────────────────────────────────────
        hero = HeroHeader(icon='💬', title='Chat Room', subtitle='Live community messages',
                          bg1=ACCENT, bg2=PRIMARY_DARK, height=160)
        root.add_widget(hero)

        # ── Live indicator ────────────────────────────────────────────────────
        top_row = BoxLayout(size_hint_y=None, height=dp(24), padding=[dp(4), 0])
        top_row.add_widget(Label(text='*  Live', font_size='11sp', color=ACCENT,
                                 halign='left', valign='middle'))
        root.add_widget(top_row)

        # ── Message list ──────────────────────────────────────────────────────
        self.scroll = ScrollView(size_hint_y=1)
        self.chat_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        self.scroll.add_widget(self.chat_layout)
        root.add_widget(self.scroll)

        # ── Input row ─────────────────────────────────────────────────────────
        input_row = BoxLayout(size_hint_y=None, height=dp(56),
                              padding=[dp(8), dp(6)], spacing=dp(8))
        with input_row.canvas.before:
            Color(*CARD_BG)
            input_row._bg = Rectangle(pos=input_row.pos, size=input_row.size)
        input_row.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v)
        )
        self.msg_input = TextInput(
            hint_text='Type a message...', multiline=False,
            background_color=(1, 1, 1, 1), background_normal='', background_active='',
            foreground_color=(0.05, 0.10, 0.25, 1),
            hint_text_color=(0.55, 0.60, 0.70, 1),
            cursor_color=PRIMARY, padding=[dp(12), dp(12)], font_size='14sp'
        )
        send_btn = make_rounded_button('Send', PRIMARY, height=42, radius=20)
        send_btn.size_hint_x = 0.26
        send_btn.bind(on_press=self.send_message)

        # Admin-only delete-all button (added/removed in on_enter)
        self.clear_btn = make_rounded_button('🗑', DANGER, height=42, radius=20)
        self.clear_btn.size_hint_x = 0.16
        self.clear_btn.bind(on_press=self.clear_chat_admin)

        input_row.add_widget(self.msg_input)
        input_row.add_widget(send_btn)
        self._input_row = input_row
        root.add_widget(input_row)

        # ── Back button ───────────────────────────────────────────────────────
        b_back = make_rounded_button('  Back', (1, 1, 1, 1), text_color=PRIMARY_DARK, height=44)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        root.add_widget(b_back)

        self.add_widget(root)

    def on_enter(self):
        Clock.unschedule(self._auto_refresh_chat)
        self._last_msg_hash = None

        _allowed = bool(current_user) and (bool(is_admin) or bool(is_approved))
        _is_adm  = bool(is_admin)

        # 🗑 clear button — admin only
        if _is_adm:
            if self.clear_btn not in self._input_row.children:
                self._input_row.add_widget(self.clear_btn)
        else:
            if self.clear_btn in self._input_row.children:
                self._input_row.remove_widget(self.clear_btn)

        # Show appropriate hint in the text input
        if not current_user:
            self.msg_input.hint_text = 'Please login first...'
            self.msg_input.disabled = True
        elif not _allowed:
            self.msg_input.hint_text = '⏳  Awaiting admin approval...'
            self.msg_input.disabled = True
        else:
            self.msg_input.hint_text = 'Type a message...'
            self.msg_input.disabled = False

        if not _allowed:
            self.chat_layout.clear_widgets()
            return

        self.load_messages()
        Clock.schedule_interval(self._auto_refresh_chat, 3)

    def on_leave(self):
        Clock.unschedule(self._auto_refresh_chat)

    def _auto_refresh_chat(self, dt):
        if not self.msg_input.focus:
            self.load_messages()

    def load_messages(self, *_):
        messages = get_messages()
        msg_hash = hash(tuple((m[0], m[1], str(m[2])) for m in messages))
        if msg_hash == getattr(self, '_last_msg_hash', None):
            return
        self._last_msg_hash = msg_hash
        self.chat_layout.clear_widgets()

        if not messages:
            empty = Label(text='No messages yet — say hello! 👋',
                          font_size='13sp', color=TEXT_MUTED,
                          size_hint_y=None, height=dp(60), halign='center')
            empty.bind(size=empty.setter('text_size'))
            self.chat_layout.add_widget(empty)
            return

        for msg_idx, (user_name, message, timestamp) in enumerate(messages):
            is_me = (user_name == current_user)
            time_str = str(timestamp)[11:16]
            user_color = get_user_color(user_name)

            outer = BoxLayout(size_hint_y=None, height=dp(72), padding=[dp(6), dp(4)])
            bubble = BoxLayout(orientation='vertical',
                               size_hint_y=None, padding=[dp(12), dp(8)], spacing=dp(2))
            bubble.height = dp(62)

            if is_me:
                with bubble.canvas.before:
                    Color(*PRIMARY)
                    bubble._bg = RoundedRectangle(pos=bubble.pos, size=bubble.size,
                                                  radius=[dp(16), dp(16), dp(4), dp(16)])
                name_color = (0.8, 0.9, 1.0, 1); msg_color = WHITE
            else:
                with bubble.canvas.before:
                    Color(*user_color, 0.20)
                    bubble._bg = RoundedRectangle(pos=bubble.pos, size=bubble.size,
                                                  radius=[dp(16), dp(16), dp(16), dp(4)])
                name_color = user_color; msg_color = TEXT_DARK

            bubble.bind(
                pos=lambda w, v: setattr(w._bg, 'pos', v),
                size=lambda w, v: setattr(w._bg, 'size', v)
            )
            admin_badge = ' 👑' if user_name == ADMIN_NAME else ''
            dot = '🔵' if is_me else '●'
            name_lbl = Label(text=f"{dot} {user_name}{admin_badge}",
                             font_size='11sp', bold=True, color=name_color,
                             size_hint_y=None, height=dp(20), halign='left', valign='middle')
            name_lbl.bind(size=name_lbl.setter('text_size'))

            msg_row = BoxLayout(size_hint_y=None, height=dp(26))
            msg_lbl = Label(text=f"{message}  [{time_str}]", font_size='13sp',
                            color=msg_color, halign='left', valign='middle')
            msg_lbl.bind(size=msg_lbl.setter('text_size'))
            msg_row.add_widget(msg_lbl)

            if is_admin:
                idx_copy = msg_idx
                del_btn = Button(text='✕', font_size='11sp',
                                 size_hint=(None, None), size=(dp(24), dp(24)),
                                 background_color=(0.8, 0.1, 0.1, 0.7),
                                 background_normal='', color=WHITE)
                del_btn.bind(on_press=lambda btn, i=idx_copy: self.delete_msg(i))
                msg_row.add_widget(del_btn)

            bubble.add_widget(name_lbl); bubble.add_widget(msg_row)
            outer.add_widget(bubble)
            self.chat_layout.add_widget(outer)

        self.scroll.scroll_y = 0

    def delete_msg(self, idx):
        delete_message_by_index(idx)
        self._last_msg_hash = None
        self.load_messages()

    def send_message(self, *_):
        msg = self.msg_input.text.strip()
        if msg and save_message(current_user, msg):
            self.msg_input.text = ''
            self._last_msg_hash = None
            self.load_messages()

    def clear_chat_admin(self, *_):
        if not is_admin: return
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        content.add_widget(Label(text='Delete ALL messages?\nThis cannot be undone!',
                                 color=DANGER, halign='center', font_size='14sp'))
        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        yes_btn = make_rounded_button('Yes, Delete All', DANGER, height=44)
        no_btn  = make_rounded_button('Cancel', (1, 1, 1, 1), text_color=PRIMARY_DARK, height=44)
        btn_row.add_widget(yes_btn); btn_row.add_widget(no_btn)
        content.add_widget(btn_row)
        popup = Popup(title='Confirm', content=content, size_hint=(0.85, 0.35))

        def do_clear(*_):
            try:
                conn = sqlite3.connect(DB_FILE, timeout=10)
                c = conn.cursor(); c.execute("DELETE FROM messages")
                conn.commit(); conn.close()
                log_admin_action(current_user_email, "CLEAR_ALL_MESSAGES")
            except: pass
            self._last_msg_hash = None
            popup.dismiss()
            self.load_messages()

        yes_btn.bind(on_press=do_clear); no_btn.bind(on_press=popup.dismiss); popup.open()


# ── Admin Panel ───────────────────────────────────────────────────────────────
class AdminScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')

        top_bar = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(12), dp(6)], spacing=dp(10))
        with top_bar.canvas.before:
            Color(0.25, 0.05, 0.40, 1)
            top_bar._bg = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v)
        )
        back_top_btn = make_rounded_button('← Home', (0.40, 0.10, 0.60, 1),
                                           text_color=WHITE, height=36, radius=8)
        back_top_btn.size_hint = (None, 1); back_top_btn.width = dp(110)
        back_top_btn.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        top_lbl = Label(text='🛡️  Admin Panel', font_size='15sp', bold=True,
                        color=WHITE, halign='center', valign='middle')
        top_lbl.bind(size=top_lbl.setter('text_size'))
        top_bar.add_widget(back_top_btn)
        top_bar.add_widget(top_lbl)
        root.add_widget(top_bar)

        hero = HeroHeader(icon='🛡️', title='Admin Dashboard',
                          subtitle='Full control · Approve · Manage',
                          bg1=(0.50, 0.10, 0.70, 1), bg2=(0.25, 0.05, 0.40, 1), height=150)
        root.add_widget(hero)

        scroll = ScrollView(size_hint_y=1)
        inner = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12), size_hint_y=None)
        inner.bind(minimum_height=inner.setter('height'))

        stats_card = make_card(padding=14, spacing=8)
        stats_card.size_hint_y = None; stats_card.height = dp(80)
        stats_row = BoxLayout(spacing=dp(10))
        self.users_stat = Label(text='👥\n—', font_size='13sp', bold=True, color=PRIMARY,
                                halign='center', valign='middle')
        self.users_stat.bind(size=self.users_stat.setter('text_size'))
        self.msgs_stat = Label(text='💬\n—', font_size='13sp', bold=True, color=ACCENT,
                               halign='center', valign='middle')
        self.msgs_stat.bind(size=self.msgs_stat.setter('text_size'))
        self.pending_stat = Label(text='⏳\n—', font_size='13sp', bold=True, color=WARNING,
                                  halign='center', valign='middle')
        self.pending_stat.bind(size=self.pending_stat.setter('text_size'))
        stats_row.add_widget(self.users_stat)
        stats_row.add_widget(self.msgs_stat)
        stats_row.add_widget(self.pending_stat)
        stats_card.add_widget(stats_row)
        inner.add_widget(stats_card)

        inner.add_widget(section_label('⏳  Pending Approvals', WARNING))
        self.pending_scroll = ScrollView(size_hint_y=None, height=dp(220))
        self.pending_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self.pending_layout.bind(minimum_height=self.pending_layout.setter('height'))
        self.pending_scroll.add_widget(self.pending_layout)
        inner.add_widget(self.pending_scroll)

        inner.add_widget(section_label('👥  User Management (Delete / Threat Removal)'))
        self.users_scroll = ScrollView(size_hint_y=None, height=dp(240))
        self.users_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self.users_layout.bind(minimum_height=self.users_layout.setter('height'))
        self.users_scroll.add_widget(self.users_layout)
        inner.add_widget(self.users_scroll)

        inner.add_widget(section_label('🗑️  Clear Old Chats'))
        old_chat_card = make_card(padding=12, spacing=8)
        old_chat_card.size_hint_y = None; old_chat_card.height = dp(160)
        old_chat_card.add_widget(Label(
            text='Delete messages older than:', font_size='13sp', color=TEXT_DARK,
            halign='left', valign='middle', size_hint_y=None, height=dp(26)
        ))
        clr_row1 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        for days, label in [(1, '1 Day'), (7, '7 Days'), (30, '30 Days')]:
            btn = make_rounded_button(label, (0.60, 0.20, 0.20, 1), height=40, radius=8)
            d = days
            btn.bind(on_press=lambda b, d=d: self.clear_old(d))
            clr_row1.add_widget(btn)
        old_chat_card.add_widget(clr_row1)
        b_clear_all = make_rounded_button('🗑️  Delete ALL Messages (No Filter)', DANGER, height=44)
        b_clear_all.bind(on_press=self.clear_all_messages)
        old_chat_card.add_widget(b_clear_all)
        self.clear_status_lbl = Label(text='', font_size='11sp', color=SUCCESS_GREEN,
                                      size_hint_y=None, height=dp(24), halign='center')
        self.clear_status_lbl.bind(size=self.clear_status_lbl.setter('text_size'))
        old_chat_card.add_widget(self.clear_status_lbl)
        inner.add_widget(old_chat_card)

        inner.add_widget(section_label('📋  Recent Admin Actions'))
        self.logs_scroll = ScrollView(size_hint_y=None, height=dp(150))
        self.logs_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
        self.logs_layout.bind(minimum_height=self.logs_layout.setter('height'))
        self.logs_scroll.add_widget(self.logs_layout)
        inner.add_widget(self.logs_scroll)

        b_back = make_rounded_button('  ← Back to Home', (1,1,1,1), text_color=PRIMARY_DARK, height=50)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        inner.add_widget(b_back)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self):
        self.users_stat.text   = f'👥\n{get_total_users_count()} Users'
        self.msgs_stat.text    = f'💬\n{get_all_messages_count()} Msgs'
        self.pending_stat.text = f'⏳\n{get_pending_count()} Pending'
        self.load_pending_users()
        self.load_all_users()
        self.load_admin_logs()

    def load_pending_users(self):
        self.pending_layout.clear_widgets()
        pending = get_pending_users()
        if not pending:
            self.pending_layout.add_widget(
                Label(text='✅  No pending approvals.', color=SUCCESS_GREEN,
                      font_size='13sp', size_hint_y=None, height=dp(44)))
            return

        for name, email, created_at in pending:
            card = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(8), padding=[dp(10), dp(6)])
            with card.canvas.before:
                Color(0.95, 0.75, 0.10, 0.12)
                card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(8)])
            card.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                      size=lambda w, v: setattr(w._bg, 'size', v))

            info = BoxLayout(orientation='vertical', spacing=dp(2))
            n_lbl = Label(text=f'⏳  {name}', font_size='13sp', bold=True, color=TEXT_DARK,
                         halign='left', valign='middle', size_hint_y=None, height=dp(24))
            n_lbl.bind(size=n_lbl.setter('text_size'))
            e_lbl = Label(text=email, font_size='10sp', color=TEXT_MUTED,
                         halign='left', valign='middle', size_hint_y=None, height=dp(18))
            e_lbl.bind(size=e_lbl.setter('text_size'))
            info.add_widget(n_lbl); info.add_widget(e_lbl)
            card.add_widget(info)

            btn_col = BoxLayout(orientation='vertical', spacing=dp(4),
                                size_hint=(None, 1), width=dp(130))
            ap_btn = make_rounded_button('✅ Approve', SUCCESS_GREEN, height=24, radius=6)
            ap_btn.font_size = '12sp'
            rj_btn = make_rounded_button('❌ Reject', DANGER, height=24, radius=6)
            rj_btn.font_size = '12sp'
            em_copy = email
            ap_btn.bind(on_press=lambda b, em=em_copy: self.do_approve(em))
            rj_btn.bind(on_press=lambda b, em=em_copy: self.do_reject(em))
            btn_col.add_widget(ap_btn); btn_col.add_widget(rj_btn)
            card.add_widget(btn_col)
            self.pending_layout.add_widget(card)

    def do_approve(self, email):
        approve_user(email)
        log_admin_action(current_user_email, "APPROVE_USER", email)
        self.on_enter()

    def do_reject(self, email):
        reject_user(email)
        log_admin_action(current_user_email, "REJECT_USER", email)
        self.on_enter()

    def load_all_users(self):
        self.users_layout.clear_widgets()
        users = get_users()
        if not users:
            self.users_layout.add_widget(
                Label(text='No users registered yet.', color=TEXT_MUTED,
                      size_hint_y=None, height=dp(40)))
            return

        for name, email, admin_flag, created_at, approved in users:
            card = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
            with card.canvas.before:
                Color(*ACCENT, 0.06)
                card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(8)])
            card.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                      size=lambda w, v: setattr(w._bg, 'size', v))

            info_row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10), padding=[dp(8), dp(4)])
            info_col = BoxLayout(orientation='vertical', spacing=dp(2))

            status_icon = '✅' if approved == 1 else ('❌' if approved == -1 else '⏳')
            n_lbl = Label(text=f'{status_icon} {name}', font_size='13sp', bold=True, color=TEXT_DARK,
                         halign='left', valign='middle', size_hint_y=None, height=dp(24))
            n_lbl.bind(size=n_lbl.setter('text_size'))
            e_lbl = Label(text=email, font_size='10sp', color=TEXT_MUTED,
                         halign='left', valign='middle', size_hint_y=None, height=dp(18))
            e_lbl.bind(size=e_lbl.setter('text_size'))
            info_col.add_widget(n_lbl); info_col.add_widget(e_lbl)
            info_row.add_widget(info_col)

            del_btn = make_rounded_button('🗑 Remove', DANGER, height=40, radius=8)
            del_btn.size_hint_x = 0.30
            em_copy = email
            del_btn.bind(on_press=lambda b, em=em_copy: self.confirm_delete_user(em))
            info_row.add_widget(del_btn)
            card.add_widget(info_row)

            if created_at:
                meta_lbl = Label(text=f'  Joined: {str(created_at)[:10]}', font_size='9sp',
                                color=TEXT_MUTED, halign='left', valign='middle',
                                size_hint_y=None, height=dp(16))
                meta_lbl.bind(size=meta_lbl.setter('text_size'))
                card.add_widget(meta_lbl)

            self.users_layout.add_widget(card)

    def clear_old(self, days):
        deleted = clear_old_messages(days)
        log_admin_action(current_user_email, f"CLEAR_MSGS_OLDER_{days}D", f"{deleted} deleted")
        self.clear_status_lbl.text = f'✅  {deleted} message{"s" if deleted != 1 else ""} removed (>{days}d old)'
        self.on_enter()
        Clock.schedule_once(lambda dt: setattr(self.clear_status_lbl, 'text', ''), 3)

    def clear_all_messages(self, *_):
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        content.add_widget(Label(text='Delete ALL messages?\nThis cannot be undone!',
                                 color=DANGER, halign='center', font_size='14sp'))
        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        yes_btn = make_rounded_button('Yes, Delete All', DANGER, height=44)
        no_btn  = make_rounded_button('Cancel', (1,1,1,1), text_color=PRIMARY_DARK, height=44)
        btn_row.add_widget(yes_btn); btn_row.add_widget(no_btn)
        content.add_widget(btn_row)
        popup = Popup(title='Confirm', content=content, size_hint=(0.85, 0.35))

        def do_clear(*_):
            try:
                conn = sqlite3.connect(DB_FILE, timeout=10)
                c = conn.cursor(); c.execute("DELETE FROM messages")
                conn.commit(); conn.close()
                log_admin_action(current_user_email, "CLEAR_ALL_MESSAGES", "ALL")
            except: pass
            popup.dismiss(); self.on_enter()

        yes_btn.bind(on_press=do_clear); no_btn.bind(on_press=popup.dismiss); popup.open()

    def confirm_delete_user(self, email):
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        content.add_widget(Label(
            text=f'Remove this user?\n{email}\n\n⚠️ All their data will be deleted.',
            color=TEXT_DARK, halign='center', font_size='13sp'
        ))
        btn_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        yes_btn = make_rounded_button('Yes, Remove', DANGER, height=44)
        no_btn  = make_rounded_button('Cancel', (1,1,1,1), text_color=PRIMARY_DARK, height=44)
        btn_row.add_widget(yes_btn); btn_row.add_widget(no_btn)
        content.add_widget(btn_row)
        popup = Popup(title='Confirm Removal', content=content, size_hint=(0.88, 0.40))

        def do_delete(*_):
            if delete_user(email):
                log_admin_action(current_user_email, "DELETE_USER", email)
                popup.dismiss(); self.on_enter()

        yes_btn.bind(on_press=do_delete); no_btn.bind(on_press=popup.dismiss); popup.open()

    def load_admin_logs(self):
        self.logs_layout.clear_widgets()
        logs = get_admin_logs()
        if not logs:
            self.logs_layout.add_widget(
                Label(text='No admin actions yet.', color=TEXT_MUTED,
                      size_hint_y=None, height=dp(40)))
            return
        for admin_email, action, target_user, timestamp in logs:
            log_lbl = Label(
                text=f'{action} → {target_user or "N/A"} [{str(timestamp)[11:16]}]',
                font_size='9sp', color=ACCENT, halign='left', valign='middle',
                size_hint_y=None, height=dp(28)
            )
            log_lbl.bind(size=log_lbl.setter('text_size'))
            self.logs_layout.add_widget(log_lbl)


# ── Inbox Screen ──────────────────────────────────────────────────────────────
class InboxScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')
        hero = HeroHeader(icon='📬', title='Inbox', subtitle='Private messages',
                          bg1=INBOX_COLOR, bg2=PRIMARY_DARK, height=170)
        root.add_widget(hero)

        inner = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))

        new_btn = make_rounded_button('✉️  Start New Conversation', PRIMARY, height=48)
        new_btn.bind(on_press=self.show_new_message_picker)
        inner.add_widget(new_btn)

        inner.add_widget(section_label('Conversations', INBOX_COLOR))

        self.scroll = ScrollView(size_hint_y=1)
        self.conv_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.conv_layout.bind(minimum_height=self.conv_layout.setter('height'))
        self.scroll.add_widget(self.conv_layout)
        inner.add_widget(self.scroll)

        b_back = make_rounded_button('  Back to Home', (1,1,1,1), text_color=PRIMARY_DARK, height=46)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        inner.add_widget(b_back)

        root.add_widget(inner)
        self.add_widget(root)

    def on_enter(self):
        self.load_conversations()

    def load_conversations(self):
        self.conv_layout.clear_widgets()
        if not current_user_email: return
        convs = get_dm_conversations(current_user_email)
        if not convs:
            empty_lbl = Label(
                text='No conversations yet.\nTap "Start New Conversation" to message someone!',
                font_size='13sp', color=TEXT_MUTED, halign='center',
                size_hint_y=None, height=dp(80)
            )
            empty_lbl.bind(size=empty_lbl.setter('text_size'))
            self.conv_layout.add_widget(empty_lbl); return

        for other_email, other_name, last_msg, last_time in convs:
            unread = get_unread_count(current_user_email, other_email)
            self._make_conv_row(other_email, other_name, last_msg, unread)

    def _make_conv_row(self, other_email, other_name, last_msg, unread):
        float_layer = FloatLayout(size_hint_y=None, height=dp(74))

        card_bg = Widget(size_hint=(1, 1))
        with card_bg.canvas:
            Color(*CARD_BG)
            card_bg._bg = RoundedRectangle(pos=card_bg.pos, size=card_bg.size, radius=[dp(14)])
        card_bg.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v)
        )
        float_layer.add_widget(card_bg)

        content_row = BoxLayout(spacing=dp(12), padding=[dp(12), dp(10)],
                                size_hint=(1, 1))
        u_col = get_user_color(other_name)
        av = Label(text=other_name[0].upper() if other_name else '?',
                   font_size='18sp', bold=True, color=WHITE,
                   size_hint=(None, None), size=(dp(46), dp(46)))
        with av.canvas.before:
            Color(*u_col, 0.85)
            av._circ = Ellipse(pos=av.pos, size=av.size)
        av.bind(pos=lambda w, v: setattr(w._circ, 'pos', v),
                size=lambda w, v: setattr(w._circ, 'size', v))

        text_col = BoxLayout(orientation='vertical', spacing=dp(2))
        name_text = other_name + (f'  [{unread} new]' if unread else '')
        name_lbl = Label(
            text=name_text, font_size='14sp', bold=True,
            color=INBOX_COLOR if unread else TEXT_DARK,
            halign='left', valign='middle', size_hint_y=None, height=dp(28)
        )
        name_lbl.bind(size=name_lbl.setter('text_size'))
        preview = last_msg[:38] + '…' if len(last_msg) > 38 else last_msg
        prev_lbl = Label(
            text=preview, font_size='11sp', color=TEXT_MUTED,
            halign='left', valign='middle', size_hint_y=None, height=dp(22)
        )
        prev_lbl.bind(size=prev_lbl.setter('text_size'))
        text_col.add_widget(name_lbl); text_col.add_widget(prev_lbl)
        content_row.add_widget(av); content_row.add_widget(text_col)
        float_layer.add_widget(content_row)

        tap_btn = Button(size_hint=(1, 1), background_normal='', background_color=(0, 0, 0, 0))
        em_c = other_email; nm_c = other_name
        tap_btn.bind(on_press=lambda b, em=em_c, nm=nm_c: self.open_dm(em, nm))
        float_layer.add_widget(tap_btn)
        self.conv_layout.add_widget(float_layer)

    def open_dm(self, other_email, other_name):
        global dm_target_email, dm_target_name
        dm_target_email = other_email; dm_target_name = other_name
        self.manager.current = 'dm'

    def show_new_message_picker(self, *_):
        users = get_all_approved_users(current_user_email)
        if not users:
            self.conv_layout.clear_widgets()
            self.conv_layout.add_widget(
                Label(text='No other approved users to message yet.',
                      color=TEXT_MUTED, font_size='13sp', size_hint_y=None, height=dp(60)))
            return

        content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        content.add_widget(Label(text='Select a user to message:',
                                 color=TEXT_DARK, font_size='14sp',
                                 size_hint_y=None, height=dp(36), halign='center'))
        scroll = ScrollView(size_hint_y=1)
        ulist = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        ulist.bind(minimum_height=ulist.setter('height'))
        popup = Popup(title='New Message', content=content, size_hint=(0.88, 0.75))

        for name, email in users:
            btn = make_rounded_button(f'  {name[0].upper()}  {name}', PRIMARY_DARK, height=50)
            em_c = email; nm_c = name
            def go(b, em=em_c, nm=nm_c):
                popup.dismiss()
                self.open_dm(em, nm)
            btn.bind(on_press=go)
            ulist.add_widget(btn)

        scroll.add_widget(ulist); content.add_widget(scroll)
        can_btn = make_rounded_button('Cancel', (1,1,1,1), text_color=PRIMARY_DARK, height=44)
        can_btn.bind(on_press=popup.dismiss)
        content.add_widget(can_btn)
        popup.open()


# ── Direct Message Screen ─────────────────────────────────────────────────────
class DMScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')
        self.hero = HeroHeader(icon='💌', title='Direct Message',
                               subtitle='Private conversation',
                               bg1=ACCENT2, bg2=PRIMARY_DARK, height=155)
        root.add_widget(self.hero)

        inner = BoxLayout(orientation='vertical',
                          padding=[dp(10), dp(6), dp(10), dp(6)], spacing=dp(6))

        self.scroll = ScrollView(size_hint_y=1)
        self.msg_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self.msg_layout.bind(minimum_height=self.msg_layout.setter('height'))
        self.scroll.add_widget(self.msg_layout)
        inner.add_widget(self.scroll)

        input_card = make_card(padding=8, spacing=6)
        input_card.size_hint_y = None; input_card.height = dp(56)
        input_row = BoxLayout(spacing=dp(8))
        self.msg_input = TextInput(
            hint_text='Write a private message...', multiline=False,
            background_color=(1, 1, 1, 1), background_normal='', background_active='',
            foreground_color=(0.05, 0.10, 0.25, 1), hint_text_color=(0.55, 0.60, 0.70, 1),
            cursor_color=INBOX_COLOR, padding=[dp(14), dp(13)], font_size='14sp'
        )
        send_btn = make_rounded_button('Send', INBOX_COLOR, height=44, radius=22)
        send_btn.size_hint_x = 0.28
        send_btn.bind(on_press=self.send_message)
        input_row.add_widget(self.msg_input); input_row.add_widget(send_btn)
        input_card.add_widget(input_row)
        inner.add_widget(input_card)

        b_back = make_rounded_button('  ← Back to Inbox', (1,1,1,1), text_color=PRIMARY_DARK, height=44)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'inbox'))
        inner.add_widget(b_back)

        root.add_widget(inner)
        self.add_widget(root)

    def on_enter(self):
        if dm_target_name:
            self.hero.title_text = f'💌  {dm_target_name}'
            self.hero.subtitle_text = 'Private conversation'
            self.hero._draw()
        if dm_target_email and current_user_email:
            mark_dm_read(current_user_email, dm_target_email)
        self.load_messages()
        Clock.schedule_interval(self._auto_refresh, 3)

    def on_leave(self):
        try: Clock.unschedule(self._auto_refresh)
        except: pass

    def _auto_refresh(self, dt):
        if dm_target_email and current_user_email:
            mark_dm_read(current_user_email, dm_target_email)
        self.load_messages()

    def load_messages(self):
        if not current_user_email or not dm_target_email: return
        self.msg_layout.clear_widgets()
        messages = get_dm_messages(current_user_email, dm_target_email)

        if not messages:
            empty = Label(
                text=f'Start your conversation with {dm_target_name} 👋',
                font_size='13sp', color=TEXT_MUTED, halign='center',
                size_hint_y=None, height=dp(60)
            )
            empty.bind(size=empty.setter('text_size'))
            self.msg_layout.add_widget(empty); return

        for sender_email, message, timestamp in messages:
            is_me = (sender_email == current_user_email)
            time_str = str(timestamp)[11:16]

            outer = BoxLayout(size_hint_y=None, height=dp(70), padding=[dp(6), dp(4)])
            bubble = BoxLayout(orientation='vertical',
                               size_hint_y=None, padding=[dp(12), dp(8)], spacing=dp(2))
            bubble.height = dp(60)

            if is_me:
                with bubble.canvas.before:
                    Color(*INBOX_COLOR)
                    bubble._bg = RoundedRectangle(pos=bubble.pos, size=bubble.size,
                                                  radius=[dp(16), dp(16), dp(4), dp(16)])
                name_color = (0.75, 0.92, 1.0, 1); msg_color = WHITE
                sender_name = current_user or 'Me'
            else:
                other_col = get_user_color(dm_target_name or '')
                with bubble.canvas.before:
                    Color(*other_col, 0.18)
                    bubble._bg = RoundedRectangle(pos=bubble.pos, size=bubble.size,
                                                  radius=[dp(16), dp(16), dp(16), dp(4)])
                name_color = other_col; msg_color = TEXT_DARK
                sender_name = dm_target_name or 'User'

            bubble.bind(
                pos=lambda w, v: setattr(w._bg, 'pos', v),
                size=lambda w, v: setattr(w._bg, 'size', v)
            )
            name_lbl = Label(text=sender_name, font_size='11sp', bold=True, color=name_color,
                             size_hint_y=None, height=dp(18), halign='left', valign='middle')
            name_lbl.bind(size=name_lbl.setter('text_size'))
            msg_lbl = Label(text=f'{message}  [{time_str}]', font_size='13sp',
                            color=msg_color, halign='left', valign='middle',
                            size_hint_y=None, height=dp(26))
            msg_lbl.bind(size=msg_lbl.setter('text_size'))

            bubble.add_widget(name_lbl); bubble.add_widget(msg_lbl)
            outer.add_widget(bubble)
            self.msg_layout.add_widget(outer)

        self.scroll.scroll_y = 0

    def send_message(self, *_):
        msg = self.msg_input.text.strip()
        if msg and send_dm(current_user_email, dm_target_email, msg):
            self.msg_input.text = ''
            self.load_messages()


# ── Profile Screen ────────────────────────────────────────────────────────────
class ProfileScreen(Screen):
    def build(self):
        root = BoxLayout(orientation='vertical')
        self.hero = HeroHeader(icon='🪪', title='My Profile', subtitle='Your personal space',
                               bg1=PRIMARY, bg2=PRIMARY_DARK, height=200)
        root.add_widget(self.hero)

        scroll = ScrollView(size_hint_y=1)
        form = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10), size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        info_card = make_card(); info_card.size_hint_y = None; info_card.height = dp(140)
        top_row = BoxLayout(spacing=dp(14), size_hint_y=None, height=dp(80))

        self.pic_container = FloatLayout(size_hint=(None, None), size=(dp(70), dp(70)))
        self.avatar_placeholder = Label(text='👤', font_size='36sp',
                                        size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with self.avatar_placeholder.canvas.before:
            Color(*PRIMARY, 0.15)
            self.av_bg = Ellipse(pos=self.avatar_placeholder.pos, size=self.avatar_placeholder.size)
        self.avatar_placeholder.bind(
            pos=lambda w, v: setattr(self.av_bg, 'pos', v),
            size=lambda w, v: setattr(self.av_bg, 'size', v)
        )
        self.profile_image = Image(
            source='', size_hint=(1, 1), pos_hint={'x': 0, 'y': 0},
            allow_stretch=True, keep_ratio=True
        )
        self.pic_container.add_widget(self.avatar_placeholder)
        self.pic_container.add_widget(self.profile_image)

        top_row.add_widget(self.pic_container)
        details = BoxLayout(orientation='vertical', spacing=dp(4))
        self.name_label  = Label(text='—', font_size='16sp', bold=True, color=TEXT_DARK,
                                 halign='left', valign='top')
        self.email_label = Label(text='—', font_size='11sp', color=TEXT_MUTED,
                                 halign='left', valign='top')
        self.phone_label = Label(text='—', font_size='11sp', color=TEXT_MUTED,
                                 halign='left', valign='top')
        for l in [self.name_label, self.email_label, self.phone_label]:
            l.bind(size=l.setter('text_size')); details.add_widget(l)
        top_row.add_widget(details)
        upload_btn = make_rounded_button('📷', ACCENT, height=40, radius=10)
        upload_btn.size_hint = (None, None); upload_btn.size = (dp(50), dp(40))
        upload_btn.bind(on_press=self.choose_profile_pic)
        top_row.add_widget(upload_btn)
        info_card.add_widget(top_row)
        meta_row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(30))
        self.join_label = Label(text='📅 Member since —', font_size='10sp', color=TEXT_MUTED,
                                halign='left', valign='middle')
        self.join_label.bind(size=self.join_label.setter('text_size'))
        meta_row.add_widget(self.join_label)
        info_card.add_widget(meta_row)
        form.add_widget(info_card)

        bio_card = make_card(); bio_card.size_hint_y = None; bio_card.height = dp(160)
        bio_lbl = Label(text='Bio', font_size='13sp', bold=True, color=PRIMARY,
                        size_hint_y=None, height=dp(28), halign='left', valign='middle')
        bio_lbl.bind(size=bio_lbl.setter('text_size'))
        bio_card.add_widget(bio_lbl)
        self.bio_input = TextInput(
            hint_text='Tell the community about yourself...',
            background_color=(0.92, 0.95, 1.00, 1), foreground_color=TEXT_DARK,
            size_hint_y=None, height=dp(80), padding=[dp(10), dp(8)], font_size='13sp'
        )
        bio_card.add_widget(self.bio_input)
        save_bio_btn = make_rounded_button('  Save Bio', ACCENT, height=38, radius=8)
        save_bio_btn.bind(on_press=self.save_bio)
        bio_card.add_widget(save_bio_btn)
        form.add_widget(bio_card)

        tl_card = make_card(); tl_card.size_hint_y = None; tl_card.height = dp(320)
        tl_header = Label(text='My Timeline', font_size='14sp', bold=True, color=PRIMARY,
                          size_hint_y=None, height=dp(30), halign='left', valign='middle')
        tl_header.bind(size=tl_header.setter('text_size'))
        tl_card.add_widget(tl_header)
        post_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.timeline_input = TextInput(
            hint_text='Share something...', multiline=False,
            background_color=(0.92, 0.95, 1.00, 1), foreground_color=TEXT_DARK,
            hint_text_color=(*TEXT_MUTED[:3], 0.6), padding=[dp(10), dp(10)], font_size='13sp'
        )
        post_btn = make_rounded_button('Post', ACCENT, height=44, radius=8)
        post_btn.size_hint_x = 0.28; post_btn.bind(on_press=self.post_timeline)
        post_row.add_widget(self.timeline_input); post_row.add_widget(post_btn)
        tl_card.add_widget(post_row)
        self.tl_scroll = ScrollView(size_hint_y=1)
        self.tl_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self.tl_layout.bind(minimum_height=self.tl_layout.setter('height'))
        self.tl_scroll.add_widget(self.tl_layout)
        tl_card.add_widget(self.tl_scroll)
        form.add_widget(tl_card)

        b_back = make_rounded_button('  Back to Home', (1,1,1,1), text_color=PRIMARY_DARK, height=50)
        b_back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'home'))
        form.add_widget(b_back)
        scroll.add_widget(form); root.add_widget(scroll); self.add_widget(root)

    def on_enter(self):
        if not current_user: return
        email = get_user_email(current_user)
        if not email: return

        profile = get_profile(email)
        if profile:
            name, phone, bio, join_date, profile_pic = profile
            self.hero.title_text = name or current_user
            self.hero._draw()
            self.name_label.text  = name or '—'
            self.email_label.text = email
            self.phone_label.text = phone if phone else 'Not set'
            self.join_label.text  = f'📅  Since {str(join_date)[:10] if join_date else "—"}'
            self.bio_input.text   = bio if bio else ''

            if profile_pic and os.path.exists(profile_pic):
                self.profile_image.source = profile_pic
                self.profile_image.reload()
                self.avatar_placeholder.opacity = 0
            else:
                self.profile_image.source = ''
                self.avatar_placeholder.opacity = 1
                self.avatar_placeholder.text = '👤'
        else:
            self.name_label.text  = current_user
            self.email_label.text = email
            self.phone_label.text = 'Not set'
            self.join_label.text  = '📅  Since —'
            self.bio_input.text   = ''
            self.profile_image.source = ''
            self.avatar_placeholder.opacity = 1
            self.avatar_placeholder.text = '👤'

        self.load_timeline()

    def choose_profile_pic(self, *_):
        # Outer layout: file chooser + preview + action buttons
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(6))

        fc = FileChooserIconView(filters=['*.png', '*.jpg', '*.jpeg'], size_hint_y=1)
        content.add_widget(fc)

        # Preview row: thumbnail + status label
        preview_row = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(10))
        self._pic_preview = Image(source='', size_hint=(None, None), size=(dp(60), dp(60)),
                                  allow_stretch=True, keep_ratio=True)
        self._pic_status  = Label(text='No file selected', font_size='12sp',
                                  color=TEXT_MUTED, halign='left', valign='middle')
        self._pic_status.bind(size=self._pic_status.setter('text_size'))
        preview_row.add_widget(self._pic_preview)
        preview_row.add_widget(self._pic_status)
        content.add_widget(preview_row)

        # Update preview when user taps a file in the chooser
        def on_selection(fc_widget, selection):
            if selection:
                self._pic_preview.source = selection[0]
                self._pic_preview.reload()
                self._pic_status.text = os.path.basename(selection[0])
                self._pic_status.color = SUCCESS_GREEN
            else:
                self._pic_preview.source = ''
                self._pic_status.text = 'No file selected'
                self._pic_status.color = TEXT_MUTED
        fc.bind(selection=on_selection)

        # Buttons
        btn_box = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = make_rounded_button('💾  Save Picture', PRIMARY, height=48)
        can_btn  = make_rounded_button('Cancel', PRIMARY_LIGHT, text_color=PRIMARY_DARK, height=48)
        btn_box.add_widget(save_btn); btn_box.add_widget(can_btn)
        content.add_widget(btn_box)

        popup = Popup(title='Choose Profile Picture', content=content, size_hint=(0.92, 0.92))

        def do_save(*_):
            if not fc.selection:
                self._pic_status.text = '⚠️  Please select a file first'
                self._pic_status.color = DANGER
                return
            src_path = fc.selection[0]
            email = get_user_email(current_user)
            dst = os.path.join(PROFILE_PICS_DIR, f"{email}_{os.path.basename(src_path)}")
            try:
                shutil.copy(src_path, dst)
                update_profile(email, self.bio_input.text, dst)
                # Update the profile screen image live
                self.profile_image.source = dst
                self.profile_image.reload()
                self.avatar_placeholder.opacity = 0
                popup.dismiss()
            except Exception as e:
                self._pic_status.text = f'Error: {e}'
                self._pic_status.color = DANGER
                print(f"Copy error: {e}")

        save_btn.bind(on_press=do_save)
        can_btn.bind(on_press=popup.dismiss)
        popup.open()

    def save_bio(self, *_):
        email = get_user_email(current_user)
        # Pass profile_pic=None so update_profile keeps the stored pic path intact
        if update_profile(email, self.bio_input.text.strip(), profile_pic=None):
            self.bio_input.hint_text = '✅  Bio saved!'
            Clock.schedule_once(
                lambda dt: setattr(self.bio_input, 'hint_text', 'Tell the community about yourself...'), 2
            )

    def post_timeline(self, *_):
        email = get_user_email(current_user)
        text  = self.timeline_input.text.strip()
        if text and save_timeline_post(email, text):
            self.timeline_input.text = ''; self.load_timeline()

    def load_timeline(self):
        self.tl_layout.clear_widgets()
        email = get_user_email(current_user)
        if not email: return
        posts = get_timeline_posts(email)
        if posts:
            for text, timestamp in posts:
                time_str = str(timestamp)[:16]
                row = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8), padding=[dp(4), dp(4)])
                with row.canvas.before:
                    Color(*ACCENT, 0.08)
                    row._bg = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(8)])
                row.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                         size=lambda w, v: setattr(w._bg, 'size', v))
                col = BoxLayout(orientation='vertical')
                t_lbl = Label(text=text, font_size='13sp', color=TEXT_DARK,
                              halign='left', valign='middle')
                t_lbl.bind(size=t_lbl.setter('text_size'))
                d_lbl = Label(text=time_str, font_size='10sp', color=TEXT_MUTED,
                              halign='left', valign='middle', size_hint_y=None, height=dp(18))
                d_lbl.bind(size=d_lbl.setter('text_size'))
                col.add_widget(t_lbl); col.add_widget(d_lbl)
                row.add_widget(col)
                self.tl_layout.add_widget(row)
        else:
            self.tl_layout.add_widget(
                Label(text='No posts yet — share your first thought! 💙',
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
            (AdminScreen,     'admin'),
            (InboxScreen,     'inbox'),
            (DMScreen,        'dm'),
        ]:
            s = cls(name=name)
            s.build()
            sm.add_widget(s)
        return sm

if __name__ == '__main__':
    MyApp().run()
