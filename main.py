import sys
import os
from datetime import datetime
import sqlite3
import shutil

from PyQt5.QtMultimedia import QSound
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTextEdit, QFileDialog, QListWidget, QStackedWidget,
                             QDialog, QInputDialog, QMessageBox, QScrollArea,
                             QFrame, QListWidgetItem)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QImage
import base64, bcrypt


class Database:
    def __init__(self):
        self.conn = sqlite3.connect('chat_app.db')
        self.cur = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cur.executescript('''
            CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password BLOB NOT NULL,
            telephone TEXT,
            profile_pic TEXT
        );


            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                sender_id INTEGER,
                receiver_id INTEGER,
                group_id INTEGER,
                content TEXT,
                media_path TEXT,
                media_type TEXT,
                timestamp DATETIME,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id),
                FOREIGN KEY (group_id) REFERENCES groups (id)
            );

            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                user_id INTEGER,
                FOREIGN KEY (group_id) REFERENCES groups (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS status_posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT,
                media_path TEXT,
                media_type TEXT,
                timestamp DATETIME,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')
        self.conn.commit()


class PostsWidget(QWidget):
    def __init__(self, db, user_id):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        post_input = QTextEdit()
        post_input.setPlaceholderText("What's on your mind?")
        post_input.setMaximumHeight(100)
        layout.addWidget(post_input)

        attach_btn = QPushButton("Attach Media")
        attach_btn.setStyleSheet("padding: 20px;\n"
                                  "border: 1px solid;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")
        self.media_path = None

        def attach_media():
            file_path, _ = QFileDialog.getOpenFileName(self, "Attach Media",
                                                       filter="Media Files (*.png *.jpg *.jpeg *.mp4 *.avi)")
            if file_path:
                self.media_path = file_path
                attach_btn.setText("Media Selected ✓")

        attach_btn.clicked.connect(attach_media)
        layout.addWidget(attach_btn)

        post_btn = QPushButton("Post")
        post_btn.setStyleSheet("padding: 20px;\n"
                                  "border: 1px solid;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")

        def make_post():
            content = post_input.toPlainText()
            if content or self.media_path:
                media_type = None
                new_media_path = None
                if self.media_path:
                    ext = os.path.splitext(self.media_path)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png']:
                        media_type = 'image'
                    elif ext in ['.mp4', '.avi']:
                        media_type = 'video'

                    storage_dir = f"posts/{media_type}s"
                    os.makedirs(storage_dir, exist_ok=True)
                    new_media_path = os.path.join(storage_dir, f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                    shutil.copy2(self.media_path, new_media_path)

                self.db.cur.execute("""
                    INSERT INTO status_posts (user_id, content, media_path, media_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.user_id, content, new_media_path, media_type, datetime.now()))
                self.db.conn.commit()

                post_input.clear()
                self.media_path = None
                attach_btn.setText("Attach Media")
                self.load_posts()

        post_btn.clicked.connect(make_post)
        layout.addWidget(post_btn)

        self.posts_area = QScrollArea()
        self.posts_widget = QWidget()
        self.posts_layout = QVBoxLayout()
        self.posts_widget.setLayout(self.posts_layout)
        self.posts_area.setWidget(self.posts_widget)
        self.posts_area.setWidgetResizable(True)
        layout.addWidget(self.posts_area)

        self.setLayout(layout)
        self.load_posts()

    def load_posts(self):

        for i in reversed(range(self.posts_layout.count())):
            self.posts_layout.itemAt(i).widget().setParent(None)


        self.db.cur.execute("""
            SELECT sp.content, sp.media_path, sp.media_type, sp.timestamp, u.username, u.profile_pic
            FROM status_posts sp
            JOIN users u ON sp.user_id = u.id
            ORDER BY sp.timestamp DESC
        """)

        for content, media_path, media_type, timestamp, username, profile_pic in self.db.cur.fetchall():
            post_frame = QFrame()
            post_frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
            post_layout = QVBoxLayout()


            user_info = QHBoxLayout()
            if profile_pic and os.path.exists(profile_pic):
                pic_label = QLabel()
                pixmap = QPixmap(profile_pic)
                pic_label.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio))
                user_info.addWidget(pic_label)

            user_info.addWidget(QLabel(f"{username} - {timestamp}"))
            post_layout.addLayout(user_info)

            if content:
                post_layout.addWidget(QLabel(content))

            if media_path and os.path.exists(media_path):
                media_label = QLabel()
                if media_type == 'image':
                    pixmap = QPixmap(media_path)
                    media_label.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio))
                    post_layout.addWidget(media_label)
                elif media_type == 'video':
                    post_layout.addWidget(QLabel(f"[Video: {os.path.basename(media_path)}]"))

            post_frame.setLayout(post_layout)
            self.posts_layout.addWidget(post_frame)

class LoginWindow(QWidget):
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
    

        logo_label = QLabel()
        logo_label.setPixmap(QPixmap("ictu-logo.png").scaled(200, 200, Qt.KeepAspectRatio))
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        author_label = QLabel()
        author_label.setText("Developed by: Bayiha Hesed Charis")
        author_label.setStyleSheet("font-size: 18px;")

        layout.addWidget(author_label, alignment=Qt.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setStyleSheet("border-radius: 5px;\n"
"background-color: rgba(0,0,0,0);\n"
"border: none;\n"
"border-bottom: 2px solid rgba(145, 163, 177, 255);\n"
"padding: 5px;\n"
"padding-bottom: 7px;\n"
"font-size: 14px;")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("border-radius: 5px;\n"
"background-color: rgba(0,0,0,0);\n"
"border: none;\n"
"border-bottom: 2px solid rgba(145, 163, 177, 255);\n"
"padding: 5px;\n"
"padding-bottom: 7px;\n"
"font-size: 14px;")
        layout.addWidget(self.password_input)

        loginButton = QPushButton("Login/Register")
        loginButton.setStyleSheet("padding: 20px;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")
        loginButton.clicked.connect(self.handle_login)
        layout.addWidget(loginButton)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password.")
            return

        self.db.cur.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = self.db.cur.fetchone()

        if user:
            user_id, stored_hashed_password = user


            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
                QMessageBox.information(self, "Success", "Login successful!")
                self.main_window.set_current_user(user_id, username)
                self.main_window.show_main_screen()
            else:
                QMessageBox.critical(self, "Error", "Incorrect password. Please try again.")
        else:
            telephone, ok = QInputDialog.getText(self, "Register", "Enter your telephone number:")
            if not ok or not telephone.strip():
                QMessageBox.warning(self, "Error", "Registration cancelled. Telephone number is required.")
                return

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            try:
                self.db.cur.execute("INSERT INTO users (username, password, telephone) VALUES (?, ?, ?)",
                                    (username, hashed_password, telephone))
                self.db.conn.commit()
                user_id = self.db.cur.lastrowid

                QMessageBox.information(self, "Success", "Registration successful! You can now log in.")
                self.main_window.set_current_user(user_id, username)
                self.main_window.show_main_screen()

            except sqlite3.Error as e:
                QMessageBox.critical(self, "Error", f"Failed to register: {str(e)}")
                self.db.conn.rollback()


class MemberSelectionDialog(QDialog):
    def __init__(self, db, current_user_id):
        super().__init__()
        self.db = db
        self.current_user_id = current_user_id
        self.selected_members = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Select Group Members")
        self.setGeometry(200, 200, 300, 400)

        layout = QVBoxLayout()

        self.members_list = QListWidget()
        self.members_list.setSelectionMode(QListWidget.MultiSelection)

        self.db.cur.execute("SELECT id, username FROM users WHERE id != ?", (self.current_user_id,))
        for user_id, username in self.db.cur.fetchall():
            item = QListWidgetItem(username)
            item.setData(Qt.UserRole, user_id)
            self.members_list.addItem(item)

        layout.addWidget(QLabel("Select members for the group:"))
        layout.addWidget(self.members_list)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_selected_members(self):
        selected_items = self.members_list.selectedItems()
        return [item.data(Qt.UserRole) for item in selected_items]

class ChatWidget(QWidget):
    def __init__(self, db, user_id, chat_id, is_group=False):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.chat_id = chat_id
        self.is_group = is_group
        self.last_message_id = 0
        self.init_ui()
        self.load_messages()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_new_messages)
        self.update_timer.start(1000)

    def init_ui(self):
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        self.profile_pic_label = QLabel()
        self.profile_pic_label.setFixedSize(50, 50)
        header_layout.addWidget(self.profile_pic_label)

        self.name_label = QLabel()
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.update_header_info()

        self.messages_area = QTextEdit()
        self.messages_area.setReadOnly(True)
        layout.addWidget(self.messages_area)

        input_layout = QHBoxLayout()

        self.message_input = QLineEdit()
        self.message_input.setStyleSheet("padding: 10;\n"
                                         "border: 1px solid #333333;\n"
                                         "font-size: 14px;\n")
        input_layout.addWidget(self.message_input)

        attach_btn = QPushButton("Attach")
        attach_btn.setStyleSheet("padding: 20px;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")
        attach_btn.clicked.connect(self.attach_file)
        input_layout.addWidget(attach_btn)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("padding: 20px;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)
        self.setLayout(layout)

    def update_header_info(self):
        if self.is_group:
            self.db.cur.execute("SELECT name FROM groups WHERE id = ?", (self.chat_id,))
            name = self.db.cur.fetchone()[0]
            self.name_label.setText(name)
        else:
            self.db.cur.execute("SELECT username, profile_pic FROM users WHERE id = ?", (self.chat_id,))
            username, profile_pic = self.db.cur.fetchone()
            self.name_label.setText(username)

            if profile_pic and os.path.exists(profile_pic):
                pixmap = QPixmap(profile_pic)
                self.profile_pic_label.setPixmap(pixmap.scaled(75, 75, Qt.AspectRatioMode.KeepAspectRatio))
            else:
                pixmap = QPixmap("logo.png")
                self.profile_pic_label.setPixmap(pixmap.scaled(75,75, Qt.AspectRatioMode.KeepAspectRatio))

    def check_new_messages(self):
        if self.is_group:
            self.db.cur.execute("""
                SELECT MAX(id) FROM messages WHERE group_id = ?
            """, (self.chat_id,))
        else:
            self.db.cur.execute("""
                SELECT MAX(id) FROM messages 
                WHERE (sender_id = ? AND receiver_id = ?)
                OR (sender_id = ? AND receiver_id = ?)
            """, (self.user_id, self.chat_id, self.chat_id, self.user_id))

        latest_id = self.db.cur.fetchone()[0] or 0
        if latest_id > self.last_message_id:
            self.load_messages()
            
    def load_messages(self):
        scroll_bar = self.messages_area.verticalScrollBar()
        scroll_position = scroll_bar.value()

        self.messages_area.clear()
        chat_html = ""

        if self.is_group:
            self.db.cur.execute("""
                SELECT m.content, m.media_path, m.media_type, m.timestamp, u.username
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.group_id = ?
                ORDER BY m.timestamp
            """, (self.chat_id,))
        else:
            self.db.cur.execute("""
                SELECT m.content, m.media_path, m.media_type, m.timestamp, u.username
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE (sender_id = ? AND receiver_id = ?)
                OR (sender_id = ? AND receiver_id = ?)
                ORDER BY m.timestamp
            """, (self.user_id, self.chat_id, self.chat_id, self.user_id))

        for content, media_path, media_type, timestamp, username in self.db.cur.fetchall():
            message_html = f"<b>{username}</b> <i>({timestamp})</i>:<br>"

            if content:
                message_html += f"{content}<br>"

            if media_path:
                if media_type == 'image' and os.path.exists(media_path):
                    message_html += f"<img src='{media_path}' width='200'><br>"
                elif media_type == 'video':
                    message_html += f"<a href='{media_path}'>[Click to Play Video]</a><br>"
                else:
                    message_html += f"<a href='{media_path}'>[Download File]</a><br>"

            chat_html += message_html + "<br>"

        self.messages_area.setHtml(chat_html)

        scroll_bar.setValue(scroll_position)
    def attach_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Attach File")
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                media_type = 'image'
            elif ext in ['.mp4', '.avi', '.mov']:
                media_type = 'video'
            else:
                media_type = 'file'

            storage_dir = f"media/{media_type}s"
            os.makedirs(storage_dir, exist_ok=True)
            new_path = os.path.join(storage_dir, os.path.basename(file_path))
            shutil.copy2(file_path, new_path)

            self.save_message(None, new_path, media_type)

    def send_message(self):
        content = self.message_input.text()
        if content:
            self.save_message(content)
            self.message_input.clear()

    def save_message(self, content, media_path=None, media_type=None):
        timestamp = datetime.now()

        if self.is_group:
            self.db.cur.execute("""
                INSERT INTO messages (sender_id, group_id, content, media_path, media_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.user_id, self.chat_id, content, media_path, media_type, timestamp))
        else:
            self.db.cur.execute("""
                INSERT INTO messages (sender_id, receiver_id, content, media_path, media_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.user_id, self.chat_id, content, media_path, media_type, timestamp))

        self.db.conn.commit()
        self.load_messages()

    def closeEvent(self, event):
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        super().closeEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
        self.current_chat_widget = None
        self.current_user_id = None
        self.current_username = None
        self.last_user_count = 0
        self.notification_sound = QSound("notification.wav")

    def show_notification(self, title, message):
        try:
            self.notification_sound.play()
        except Exception as e:
            print(f"Error playing sound: {str(e)}")

        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.show()
    def check_new_users(self):
        try:
            self.db.cur.execute("SELECT COUNT(*) FROM users")
            current_user_count = self.db.cur.fetchone()[0]

            if current_user_count > self.last_user_count:
                self.load_users()
                if self.last_user_count > 0:
                    self.show_notification("New User", "A new user has joined the chat!")
                self.last_user_count = current_user_count
        except Exception as e:
            print(f"Error checking new users: {str(e)}")
    def init_ui(self):
        self.setWindowTitle("Chat Application")
        self.setGeometry(100, 100, 800, 600)

        self.users_list = QListWidget()

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_screen = LoginWindow(self.db, self)
        self.stacked_widget.addWidget(self.login_screen)

        self.main_screen = None

        self.user_check_timer = QTimer(self)
        self.user_check_timer.timeout.connect(self.check_new_users)
        self.user_check_timer.start(1000)

        self.group_check_timer = QTimer(self)
        self.group_check_timer.timeout.connect(self.check_new_groups)
        self.group_check_timer.start(1000)

    def cleanup_current_chat(self):
        if self.current_chat_widget:
            if hasattr(self.current_chat_widget, 'update_timer'):
                self.current_chat_widget.update_timer.stop()
            self.chat_stack.removeWidget(self.current_chat_widget)
            self.current_chat_widget.deleteLater()
            self.current_chat_widget = None

    def check_new_groups(self):
        try:
            self.db.cur.execute("""
                SELECT COUNT(*) FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.user_id = ?
            """, (self.current_user_id,))
            current_groups_count = self.db.cur.fetchone()[0]

            if not hasattr(self, 'last_groups_count'):
                self.last_groups_count = current_groups_count
            elif current_groups_count > self.last_groups_count:
                self.load_groups()
                self.show_notification("New Group", "You've been added to a new group!")
                self.last_groups_count = current_groups_count
        except Exception as e:
            print(f"Error checking new groups: {str(e)}")
            
    def set_current_user(self, user_id, username):
        self.current_user_id = user_id
        self.current_username = username

    def show_main_screen(self):
        if not self.main_screen:
            self.create_main_screen()
        self.stacked_widget.setCurrentWidget(self.main_screen)

    def create_main_screen(self):
        self.main_screen = QWidget()
        layout = QHBoxLayout()

        users_layout = QVBoxLayout()
        users_header = QHBoxLayout()
        users_header.addWidget(QLabel("Users"))

        view_profile_btn = QPushButton("View Profile")
        view_profile_btn.setStyleSheet("""
            padding: 5px;
            background-color: #0077b9;
            color: rgba(255,255,255,210);
            font-size: 14px;
            border-radius: 5px;
        """)
        view_profile_btn.clicked.connect(self.show_profile_info)
        users_header.addWidget(view_profile_btn)

        
        
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout()

        profile_btn = QPushButton("Set Profile Picture")
        profile_btn.setStyleSheet("padding: 5px;\n"
                                  "border: 1px solid;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")
        profile_btn.clicked.connect(self.set_profile_picture)
        sidebar_layout.addWidget(profile_btn)

        posts_btn = QPushButton("Posts")
        posts_btn.setStyleSheet("padding: 20px;\n"
                                  "border: 1px solid;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")
        posts_btn.clicked.connect(self.show_posts)
        sidebar_layout.addWidget(posts_btn)
        users_layout.addLayout(users_header)
        sidebar_layout.addLayout(users_layout)
        users_label = QLabel("Users")
        sidebar_layout.addWidget(users_label)
        self.users_list = QListWidget()
        self.load_users()
        self.users_list.itemClicked.connect(self.open_chat)
        sidebar_layout.addWidget(self.users_list)

        groups_label = QLabel("Groups")
        sidebar_layout.addWidget(groups_label)
        self.groups_list = QListWidget()
        create_group_btn = QPushButton("Create Group")
        create_group_btn.setStyleSheet("padding: 20px;\n"
                                  "border: 1px solid;\n"
                                  "background-color: #0077b9;\n"
                                  "color: rgba(255,255,255,210);\n"
                                  "font-size: 18px;\n"
                                  "border-radius: 5px;\n")
        create_group_btn.clicked.connect(self.create_group)
        sidebar_layout.addWidget(create_group_btn)
        self.load_groups()
        self.groups_list.itemClicked.connect(self.open_group_chat)
        sidebar_layout.addWidget(self.groups_list)

        sidebar.setLayout(sidebar_layout)
        layout.addWidget(sidebar)

        self.chat_stack = QStackedWidget()
        layout.addWidget(self.chat_stack)

        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout()
        welcome_label = QLabel("Welcome! Select a chat to begin.")
        welcome_layout.addWidget(welcome_label, alignment=Qt.AlignmentFlag.AlignCenter)
        welcome_widget.setLayout(welcome_layout)
        self.chat_stack.addWidget(welcome_widget)

        self.main_screen.setLayout(layout)
        self.stacked_widget.addWidget(self.main_screen)
        
        self.message_check_timer = QTimer(self)
        self.message_check_timer.timeout.connect(self.check_unread_messages)
        self.message_check_timer.start(1000)

    def load_users(self):
        current_selection = self.users_list.currentItem()
        selected_user_id = current_selection.data(Qt.ItemDataRole.UserRole) if current_selection else None

        self.users_list.clear()
        self.db.cur.execute("SELECT id, username FROM users WHERE id != ?", (self.current_user_id,))
        for user_id, username in self.db.cur.fetchall():
            item = QListWidgetItem(f"{username}")
            item.setData(Qt.ItemDataRole.UserRole, user_id)
            self.users_list.addItem(item)

            if user_id == selected_user_id:
                self.users_list.setCurrentItem(item)
    def load_groups(self):
        self.groups_list.clear()
        self.db.cur.execute("""
            SELECT g.id, g.name FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
        """, (self.current_user_id,))
        for group_id, name in self.db.cur.fetchall():
            self.groups_list.addItem(f"{name}")
            self.groups_list.item(self.groups_list.count() - 1).setData(Qt.ItemDataRole.UserRole, group_id)

    def open_chat(self, item):
        try:
            user_id = item.data(Qt.ItemDataRole.UserRole)

            self.cleanup_current_chat()

            chat_widget = ChatWidget(self.db, self.current_user_id, user_id)
            self.current_chat_widget = chat_widget
            self.chat_stack.addWidget(chat_widget)
            self.chat_stack.setCurrentWidget(chat_widget)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening chat: {str(e)}")

    def open_group_chat(self, item):
        try:
            group_id = item.data(Qt.ItemDataRole.UserRole)

            self.cleanup_current_chat()

            chat_widget = ChatWidget(self.db, self.current_user_id, group_id, is_group=True)
            self.current_chat_widget = chat_widget
            self.chat_stack.addWidget(chat_widget)
            self.chat_stack.setCurrentWidget(chat_widget)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening group chat: {str(e)}")

    def show_posts(self):
        try:
            self.cleanup_current_chat()

            posts_widget = PostsWidget(self.db, self.current_user_id)
            self.current_chat_widget = posts_widget
            self.chat_stack.addWidget(posts_widget)
            self.chat_stack.setCurrentWidget(posts_widget)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error showing posts: {str(e)}")

    def closeEvent(self, event):
        self.cleanup_current_chat()
        if hasattr(self, 'user_check_timer'):
            self.user_check_timer.stop()
        if hasattr(self, 'group_check_timer'):
            self.group_check_timer.stop()
        if hasattr(self, 'message_check_timer'):
            self.message_check_timer.stop()
        super().closeEvent(event)

    def check_unread_messages(self):
        try:
            for i in range(self.users_list.count()):
                item = self.users_list.item(i)
                user_id = item.data(Qt.ItemDataRole.UserRole)
                username = item.text().split(" [")[0] 
                self.db.cur.execute("""
                    SELECT COUNT(*) FROM messages 
                    WHERE sender_id = ? AND receiver_id = ? 
                    AND id > COALESCE((
                        SELECT MAX(id) FROM messages 
                        WHERE (sender_id = ? AND receiver_id = ?) 
                        OR (sender_id = ? AND receiver_id = ?)
                    ), 0)
                """, (user_id, self.current_user_id, self.current_user_id, user_id, user_id, self.current_user_id))
            
                unread_count = self.db.cur.fetchone()[0]
                if unread_count > 0:
                    item.setText(f"{username} [{unread_count}]")
                else:
                    item.setText(username)

            for i in range(self.groups_list.count()):
                item = self.groups_list.item(i)
                group_id = item.data(Qt.ItemDataRole.UserRole)
                group_name = item.text().split(" [")[0]

                self.db.cur.execute("""
                    SELECT COUNT(*) FROM messages 
                    WHERE group_id = ? AND sender_id != ? 
                    AND id > COALESCE((
                        SELECT MAX(id) FROM messages 
                        WHERE group_id = ? AND sender_id = ?
                    ), 0)
                """, (group_id, self.current_user_id, group_id, self.current_user_id))
            
                unread_count = self.db.cur.fetchone()[0]
                if unread_count > 0:
                    item.setText(f"{group_name} [{unread_count}]")
                else:
                    item.setText(group_name)

        except Exception as e:
            print(f"Error checking unread messages: {str(e)}")
        
    def show_profile_info(self):
        try:
            selected_item = self.users_list.currentItem()
            if not selected_item:
                QMessageBox.warning(self, "Warning", "Please select a user first.")
                return

            user_id = selected_item.data(Qt.ItemDataRole.UserRole)
            self.db.cur.execute("""
                SELECT username, telephone, profile_pic 
                FROM users 
                WHERE id = ?
            """, (user_id,))
        
            user_info = self.db.cur.fetchone()
            if user_info:
                username, telephone, profile_pic = user_info
            
                dialog = QDialog(self)
                dialog.setWindowTitle("User Profile")
                dialog.setMinimumWidth(300)
            
                layout = QVBoxLayout()
            
                if profile_pic and os.path.exists(profile_pic):
                    pic_label = QLabel()
                    pixmap = QPixmap(profile_pic)
                    pic_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
                    layout.addWidget(pic_label, alignment=Qt.AlignmentFlag.AlignCenter)
            
                info_layout = QVBoxLayout()
                info_layout.addWidget(QLabel(f"Username: {username}"))
                info_layout.addWidget(QLabel(f"Telephone: {telephone}"))
            
                layout.addLayout(info_layout)
                dialog.setLayout(layout)
                dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error showing profile info: {str(e)}")
     
    def create_group(self):
        name, ok = QInputDialog.getText(self, "Create Group", "Enter group name:")
        if ok and name:
            member_dialog = MemberSelectionDialog(self.db, self.current_user_id)
            if member_dialog.exec_() == QDialog.Accepted:
                selected_members = member_dialog.get_selected_members()

                if not selected_members:
                    QMessageBox.warning(self, "Warning", "Please select at least one member for the group.")
                    return

                try:
                    self.db.cur.execute("INSERT INTO groups (name, created_by) VALUES (?, ?)",
                                        (name, self.current_user_id))
                    group_id = self.db.cur.lastrowid

                    self.db.cur.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
                                        (group_id, self.current_user_id))

                    for member_id in selected_members:
                        self.db.cur.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
                                            (group_id, member_id))

                    self.db.conn.commit()
                    self.load_groups()
                    QMessageBox.information(self, "Success", "Group created successfully!")

                except sqlite3.Error as e:
                    self.db.conn.rollback()
                    QMessageBox.critical(self, "Error", f"Failed to create group: {str(e)}")

    def set_profile_picture(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Profile Picture",
                                                   filter="Images (*.png *.jpg *.jpeg)")
        if file_path:
            storage_dir = "profile_pictures"
            os.makedirs(storage_dir, exist_ok=True)
            new_path = os.path.join(storage_dir, f"profile_{self.current_user_id}{os.path.splitext(file_path)[1]}")
            shutil.copy2(file_path, new_path)

            self.db.cur.execute("UPDATE users SET profile_pic = ? WHERE id = ?",
                                (new_path, self.current_user_id))
            self.db.conn.commit()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
