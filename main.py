import psutil
import ctypes
import os
import sys
import math
import threading
import time
import subprocess
from subprocess import CREATE_NO_WINDOW
import struct
import wave
import tempfile
import win32gui
import win32process
import winsound
from datetime import datetime
from dataclasses import dataclass
import json
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse


@dataclass
class Settings:
    DEFAULT_SETTINGS = {
        "hotkey": "alt",
        "beep_volume": 10,
        "beep": True,
        "auto_reconnect": True,
        "selected_processes": [],
        "focus_only": True,
        "custom_rule_name": "BlockRobloxInternet",
        "start_minimized": False,
        "window": {"width": 480, "height": 575, "x": None, "y": None}
    }

    hotkey: str
    beep_volume: int
    beep: bool
    auto_reconnect: bool
    selected_processes: list
    focus_only: bool
    custom_rule_name: str
    start_minimized: bool
    window: dict

    def __post_init__(self):
        self.beep_volume = int(self.beep_volume)
        self.auto_reconnect = bool(self.auto_reconnect)
        self.focus_only = bool(self.focus_only)
        self.beep = bool(self.beep)
        self.start_minimized = bool(self.start_minimized)

    @staticmethod
    def _get_save_directory() -> Path:
        base_dir = Path("C:/Seven's Scripts")
        base_dir.mkdir(exist_ok=True)
        app_dir = base_dir / "Seven's Lag Switch"
        app_dir.mkdir(exist_ok=True)
        return app_dir

    @classmethod
    def load(cls) -> 'Settings':
        try:
            settings_file = cls._get_save_directory() / "settings.json"
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                    merged = {**cls.DEFAULT_SETTINGS, **data}
                    return cls(**{k: merged[k] for k in cls.DEFAULT_SETTINGS})
        except Exception as e:
            print(f"Settings load error: {e}")
        return cls(**cls.DEFAULT_SETTINGS)

    def save(self):
        try:
            settings_file = self._get_save_directory() / "settings.json"
            data = {}
            for key in self.DEFAULT_SETTINGS:
                data[key] = getattr(self, key)
            with open(settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Settings save error: {e}")


class TonePlayer:
    SAMPLE_RATE = 44100
    _temp_dir = None

    @classmethod
    def _get_temp_dir(cls):
        if cls._temp_dir is None:
            cls._temp_dir = tempfile.mkdtemp(prefix="lagswitch_")
        return cls._temp_dir

    @staticmethod
    def play(freq, duration_ms, volume_pct):
        if volume_pct <= 0:
            return
        try:
            n_samples = int(TonePlayer.SAMPLE_RATE * duration_ms / 1000)
            amplitude = max(0.0, min(1.0, volume_pct / 100.0))
            samples = bytearray()
            fade = min(500, n_samples // 4)
            for i in range(n_samples):
                t = i / TonePlayer.SAMPLE_RATE
                sample = math.sin(2.0 * math.pi * freq * t)
                if i < fade:
                    sample *= i / fade
                elif i > n_samples - fade:
                    sample *= (n_samples - i) / fade
                val = int(sample * amplitude * 32767)
                val = max(-32768, min(32767, val))
                samples += struct.pack('<h', val)

            temp_path = os.path.join(TonePlayer._get_temp_dir(), f"tone_{freq}_{volume_pct}.wav")
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(TonePlayer.SAMPLE_RATE)
                wf.writeframes(bytes(samples))

            winsound.PlaySound(temp_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception as e:
            print(f"TonePlayer error: {e}")


class KeyCaptureButton(QPushButton):
    key_captured = pyqtSignal(str)

    def __init__(self, initial_key="", parent=None):
        super().__init__(parent)
        self.current_key = initial_key
        self.is_capturing = False
        self.setFixedHeight(32)
        self.setFixedWidth(145)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 9))
        self.setFocusPolicy(Qt.StrongFocus)
        self.update_display()

    def update_display(self):
        if self.is_capturing:
            self.setText("Press any key...")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: 1px solid #005a9e;
                    border-radius: 4px;
                    padding: 6px 12px;
                    text-align: center;
                }
            """)
        else:
            display = self.current_key.upper() if self.current_key else "Click to set"
            self.setText(display)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 6px 12px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #333333;
                    border: 1px solid #0078d4;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_capturing = True
            self.update_display()
            self.setFocus()

    def keyPressEvent(self, event):
        if self.is_capturing:
            key = event.key()
            key_map = {
                Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3",
                Qt.Key_F4: "f4", Qt.Key_F5: "f5", Qt.Key_F6: "f6",
                Qt.Key_F7: "f7", Qt.Key_F8: "f8", Qt.Key_F9: "f9",
                Qt.Key_F10: "f10", Qt.Key_F11: "f11", Qt.Key_F12: "f12",
                Qt.Key_Space: "space", Qt.Key_Tab: "tab",
                Qt.Key_CapsLock: "caps_lock", Qt.Key_Shift: "shift",
                Qt.Key_Control: "ctrl", Qt.Key_Alt: "alt",
            }
            if key in key_map:
                key_str = key_map[key]
            else:
                key_str = event.text().lower()
            if key_str:
                self.current_key = key_str
                self.key_captured.emit(key_str)
            self.is_capturing = False
            self.update_display()
            self.clearFocus()


def resolve_icon_path():
    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "icons", "icon.ico")
        if os.path.isfile(path):
            return path
    except:
        pass
    return None


class RobloxLagSwitch(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.running = True
        self.blocked = False
        self.rule_name_prefix = self.settings.custom_rule_name
        self.cached_processes = {}
        self.block_commands = []
        self.unblock_commands = []
        self.offset = None
        self.key_listener = None
        self.mouse_listener = None
        self.block_timestamp = 0
        self.icon_path = resolve_icon_path()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 575)

        if sys.platform == 'win32':
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Sevens.LagSwitch")
            except:
                pass

        if self.icon_path:
            self.setWindowIcon(QIcon(self.icon_path))

        self.init_ui()
        self.cache_roblox_processes()
        self.start_listeners()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.cache_roblox_processes)
        self.refresh_timer.start(30000)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.check_auto_unblock)
        self.countdown_timer.start(250)

        if self.settings.start_minimized:
            QTimer.singleShot(100, self.showMinimized)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 10, 10)
        painter.fillPath(path, QColor(24, 24, 24))
        painter.setPen(QPen(QColor(70, 70, 70), 0.75))
        painter.drawPath(path)
        painter.end()

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(44)
        title_bar.setStyleSheet("background-color: #202020; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 8, 0)

        if self.icon_path:
            icon_label = QLabel()
            icon_pixmap = QPixmap(self.icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(icon_pixmap)
            icon_label.setFixedSize(20, 20)
            icon_label.setStyleSheet("background: transparent;")
            title_layout.addWidget(icon_label)
            title_layout.addSpacing(8)
        else:
            icon_label = QLabel()
            fallback = QPixmap(20, 20)
            fallback.fill(Qt.transparent)
            p = QPainter(fallback)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor(0, 120, 212))
            p.setPen(Qt.NoPen)
            p.drawEllipse(2, 2, 16, 16)
            p.end()
            icon_label.setPixmap(fallback)
            icon_label.setFixedSize(20, 20)
            icon_label.setStyleSheet("background: transparent;")
            title_layout.addWidget(icon_label)
            title_layout.addSpacing(8)

        title_text = QLabel("Seven's Lag Switch")
        title_text.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        title_text.setStyleSheet("color: white; background: transparent;")
        title_layout.addWidget(title_text)
        title_layout.addStretch()

        minimize_btn = QPushButton("─")
        minimize_btn.setFixedSize(40, 32)
        minimize_btn.setCursor(Qt.PointingHandCursor)
        minimize_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #cccccc; border: none; font-size: 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #2d2d2d; }
        """)
        minimize_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_btn)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(40, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #cccccc; border: none; font-size: 18px; border-radius: 4px; }
            QPushButton:hover { background-color: #e81123; color: white; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        outer.addWidget(title_bar)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #2d2d2d;")
        outer.addWidget(sep)

        body = QWidget()
        body.setStyleSheet("background-color: transparent;")
        self.cl = QVBoxLayout(body)
        self.cl.setContentsMargins(24, 20, 24, 24)
        self.cl.setSpacing(14)

        self.build_status()
        self.build_hotkey()
        self.build_sound()
        self.build_behavior()

        self.cl.addStretch()

        apply_btn = QPushButton("Apply Settings")
        apply_btn.setFixedHeight(40)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setFont(QFont("Segoe UI", 10))
        apply_btn.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        apply_btn.clicked.connect(self.save_settings)
        self.cl.addWidget(apply_btn)

        outer.addWidget(body)

        title_bar.mousePressEvent = self.title_press
        title_bar.mouseMoveEvent = self.title_move
        title_bar.mouseReleaseEvent = self.title_release
        title_text.mousePressEvent = self.title_press
        title_text.mouseMoveEvent = self.title_move

    def section(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        lbl.setStyleSheet("color: #ffffff; background: transparent;")
        lbl.setFixedHeight(24)
        return lbl

    def labeled_row(self, label_text, widget, height=40):
        r = QWidget()
        r.setFixedHeight(height)
        r.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(r)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        lbl = QLabel(label_text)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color: #cccccc; background: transparent;")
        lay.addWidget(lbl)
        lay.addStretch()
        lay.addWidget(widget)
        return r

    def make_checkbox(self, text, checked):
        cb = QCheckBox(text)
        cb.setFont(QFont("Segoe UI", 9))
        cb.setChecked(checked)
        cb.setCursor(Qt.PointingHandCursor)
        cb.setStyleSheet("""
            QCheckBox { color: #cccccc; background: transparent; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 3px; border: 1px solid #3d3d3d; background-color: #2d2d2d; }
            QCheckBox::indicator:hover { border: 1px solid #0078d4; }
            QCheckBox::indicator:checked { background-color: #0078d4; border: 1px solid #0078d4; }
        """)
        cb.stateChanged.connect(self.auto_apply)
        return cb

    def build_status(self):
        frame = QWidget()
        frame.setFixedHeight(64)
        frame.setStyleSheet("background-color: #202020; border-radius: 6px;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)

        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Segoe UI", 14))
        self.status_dot.setStyleSheet("color: #4dff4d; background: transparent;")
        self.status_dot.setFixedWidth(24)
        lay.addWidget(self.status_dot)

        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        self.status_label = QLabel("Unblocked")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.status_label.setStyleSheet("color: #4dff4d; background: transparent;")
        self.status_sub = QLabel("Press hotkey to toggle")
        self.status_sub.setFont(QFont("Segoe UI", 8))
        self.status_sub.setStyleSheet("color: #888888; background: transparent;")
        text_lay.addWidget(self.status_label)
        text_lay.addWidget(self.status_sub)
        lay.addLayout(text_lay)
        lay.addStretch()

        self.timer_label = QLabel("")
        self.timer_label.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.timer_label.setStyleSheet("color: #888888; background: transparent;")
        lay.addWidget(self.timer_label)

        self.cl.addWidget(frame)

    def build_hotkey(self):
        self.cl.addWidget(self.section("Hotkey"))
        self.hotkey_btn = KeyCaptureButton(self.settings.hotkey)
        self.hotkey_btn.key_captured.connect(self.on_hotkey_changed)
        self.cl.addWidget(self.labeled_row("Toggle Key", self.hotkey_btn))

    def build_sound(self):
        self.cl.addWidget(self.section("Sound"))
        self.beep_cb = self.make_checkbox("Enable beep sound", self.settings.beep)
        self.cl.addWidget(self.beep_cb)

        slider_container = QWidget()
        slider_container.setFixedWidth(175)
        slider_container.setFixedHeight(32)
        slider_container.setStyleSheet("background: transparent;")
        s_lay = QHBoxLayout(slider_container)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lay.setSpacing(8)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.settings.beep_volume)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setCursor(Qt.PointingHandCursor)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #2d2d2d; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #0078d4; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #0078d4; border-radius: 2px; }
        """)

        self.vol_label = QLabel(f"{self.settings.beep_volume}%")
        self.vol_label.setFont(QFont("Segoe UI", 9))
        self.vol_label.setStyleSheet("color: #cccccc; background: transparent;")
        self.vol_label.setFixedWidth(40)
        self.vol_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.volume_slider.valueChanged.connect(self.on_volume_changed)

        s_lay.addWidget(self.volume_slider)
        s_lay.addWidget(self.vol_label)

        self.cl.addWidget(self.labeled_row("Volume", slider_container))

    def build_behavior(self):
        self.cl.addWidget(self.section("Behavior"))
        self.auto_reconnect_cb = self.make_checkbox(
            "Auto timed reconnect (avoid getting disconnected)",
            self.settings.auto_reconnect
        )
        self.cl.addWidget(self.auto_reconnect_cb)
        self.focus_only_cb = self.make_checkbox(
            "Only block focused Roblox window",
            self.settings.focus_only
        )
        self.cl.addWidget(self.focus_only_cb)
        self.start_min_cb = self.make_checkbox("Start minimized", self.settings.start_minimized)
        self.cl.addWidget(self.start_min_cb)

    def on_volume_changed(self, value):
        self.vol_label.setText(f"{value}%")
        self.auto_apply()

    def auto_apply(self, _=None):
        self.settings.hotkey = self.hotkey_btn.current_key
        self.settings.beep = self.beep_cb.isChecked()
        self.settings.beep_volume = self.volume_slider.value()
        self.settings.auto_reconnect = self.auto_reconnect_cb.isChecked()
        self.settings.focus_only = self.focus_only_cb.isChecked()
        self.settings.start_minimized = self.start_min_cb.isChecked()
        self.block_commands = []
        self.unblock_commands = []
        self.settings.save()

    def save_settings(self):
        self.auto_apply()

    def on_hotkey_changed(self, key):
        self.auto_apply()

    def update_status(self):
        if self.blocked:
            self.status_label.setText("Blocked")
            self.status_label.setStyleSheet("color: #ff6666; background: transparent;")
            self.status_dot.setStyleSheet("color: #ff6666; background: transparent;")
            self.status_sub.setText("Traffic is blocked")
        else:
            self.status_label.setText("Unblocked")
            self.status_label.setStyleSheet("color: #4dff4d; background: transparent;")
            self.status_dot.setStyleSheet("color: #4dff4d; background: transparent;")
            self.status_sub.setText("Press hotkey to toggle")
            self.timer_label.setText("")
            self.timer_label.setStyleSheet("color: #888888; background: transparent;")

    def check_auto_unblock(self):
        if not self.blocked or not self.settings.auto_reconnect:
            return
        elapsed = time.time() - self.block_timestamp
        remaining = max(0, 9.0 - elapsed)
        if remaining > 0:
            self.timer_label.setText(f"{remaining:.1f}s")
            self.timer_label.setStyleSheet("color: #ffcc00; background: transparent;")
        else:
            self.unblock_all_roblox_fast()
            self.play_beep(600)

    def cache_roblox_processes(self):
        self.cached_processes.clear()
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    name = proc.info['name'].lower()
                    if 'roblox' in name:
                        pid = proc.info['pid']
                        exe = proc.info.get('exe', 'Unknown')
                        self.cached_processes[pid] = {
                            'name': proc.info['name'],
                            'exe': exe,
                            'pid': pid
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except:
            pass
        self.block_commands = []
        self.unblock_commands = []

    def get_focused_roblox_pid(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in self.cached_processes:
                return pid
        except:
            pass
        return None

    def prepare_firewall_rules(self):
        self.block_commands = []
        self.unblock_commands = []

        if self.settings.focus_only:
            pid = self.get_focused_roblox_pid()
            targets = {pid: self.cached_processes[pid]} if pid and pid in self.cached_processes else {}
        else:
            targets = self.cached_processes

        if not targets:
            return

        for pid, info in targets.items():
            exe = info.get('exe', '')
            if not exe or exe == 'Unknown':
                continue
            rule_base = f"{self.rule_name_prefix}_{pid}"
            self.block_commands.append(
                f'netsh advfirewall firewall add rule name="{rule_base}_in" dir=in action=block program="{exe}" enable=yes'
            )
            self.block_commands.append(
                f'netsh advfirewall firewall add rule name="{rule_base}_out" dir=out action=block program="{exe}" enable=yes'
            )
            self.unblock_commands.append(
                f'netsh advfirewall firewall delete rule name="{rule_base}_in"'
            )
            self.unblock_commands.append(
                f'netsh advfirewall firewall delete rule name="{rule_base}_out"'
            )

    def block_selected_roblox_fast(self):
        if not self.block_commands:
            self.prepare_firewall_rules()
        if not self.block_commands:
            return
        combined = " & ".join(self.block_commands)
        try:
            subprocess.run(combined, shell=True, creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.blocked = True
            self.block_timestamp = time.time()
            self.update_status()
        except:
            pass

    def unblock_all_roblox_fast(self):
        if not self.unblock_commands:
            try:
                subprocess.run(
                    f'netsh advfirewall firewall delete rule name="{self.rule_name_prefix}" >nul 2>&1',
                    shell=True, creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except:
                pass
            cleanup = []
            for pid in list(self.cached_processes.keys()):
                rule_base = f"{self.rule_name_prefix}_{pid}"
                cleanup.append(f'netsh advfirewall firewall delete rule name="{rule_base}_in"')
                cleanup.append(f'netsh advfirewall firewall delete rule name="{rule_base}_out"')
            if cleanup:
                try:
                    subprocess.run(" & ".join(cleanup), shell=True, creationflags=CREATE_NO_WINDOW,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass
        else:
            try:
                subprocess.run(" & ".join(self.unblock_commands), shell=True, creationflags=CREATE_NO_WINDOW,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
        self.blocked = False
        self.block_timestamp = 0
        self.update_status()

    def play_beep(self, freq):
        if not self.settings.beep or self.settings.beep_volume <= 0:
            return
        vol = self.settings.beep_volume
        def _play():
            TonePlayer.play(freq, 50, vol)
        threading.Thread(target=_play, daemon=True).start()

    def toggle_block(self):
        try:
            if self.blocked:
                self.unblock_all_roblox_fast()
                self.play_beep(600)
            else:
                if not self.cached_processes:
                    self.cache_roblox_processes()
                if not self.cached_processes:
                    return
                self.block_commands = []
                self.unblock_commands = []
                self.prepare_firewall_rules()
                if not self.block_commands:
                    return
                self.block_selected_roblox_fast()
                if self.blocked:
                    self.play_beep(400)
        except:
            pass

    def normalize_key(self, key):
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        key_map = {
            pynput_keyboard.Key.f1: "f1", pynput_keyboard.Key.f2: "f2",
            pynput_keyboard.Key.f3: "f3", pynput_keyboard.Key.f4: "f4",
            pynput_keyboard.Key.f5: "f5", pynput_keyboard.Key.f6: "f6",
            pynput_keyboard.Key.f7: "f7", pynput_keyboard.Key.f8: "f8",
            pynput_keyboard.Key.f9: "f9", pynput_keyboard.Key.f10: "f10",
            pynput_keyboard.Key.f11: "f11", pynput_keyboard.Key.f12: "f12",
            pynput_keyboard.Key.space: "space", pynput_keyboard.Key.tab: "tab",
            pynput_keyboard.Key.caps_lock: "caps_lock",
            pynput_keyboard.Key.shift: "shift", pynput_keyboard.Key.shift_l: "shift",
            pynput_keyboard.Key.shift_r: "shift",
            pynput_keyboard.Key.ctrl: "ctrl", pynput_keyboard.Key.ctrl_l: "ctrl",
            pynput_keyboard.Key.ctrl_r: "ctrl",
            pynput_keyboard.Key.alt: "alt", pynput_keyboard.Key.alt_l: "alt",
            pynput_keyboard.Key.alt_r: "alt",
        }
        return key_map.get(key, None)

    def on_key_press(self, key):
        try:
            normalized = self.normalize_key(key)
            if normalized and normalized == self.settings.hotkey:
                QTimer.singleShot(0, self.toggle_block)
        except:
            pass

    def start_listeners(self):
        self.key_listener = pynput_keyboard.Listener(on_press=self.on_key_press)
        self.key_listener.start()
        self.mouse_listener = pynput_mouse.Listener()
        self.mouse_listener.start()

    def title_press(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.pos()

    def title_move(self, event):
        if self.offset and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def title_release(self, event):
        self.offset = None

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_first_shown'):
            self._first_shown = True
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = geo.x() + (geo.width() - self.width()) // 2
                y = geo.y() + (geo.height() - self.height()) // 2
                self.move(x, y)

    def closeEvent(self, event):
        self.running = False
        if self.blocked:
            self.unblock_all_roblox_fast()
        if self.key_listener:
            self.key_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        try:
            import shutil
            if TonePlayer._temp_dir and os.path.isdir(TonePlayer._temp_dir):
                shutil.rmtree(TonePlayer._temp_dir, ignore_errors=True)
        except:
            pass
        event.accept()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    if is_admin():
        window = RobloxLagSwitch()
        window.show()
        return app.exec_()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, __file__, None, 1)
        return 0


if __name__ == '__main__':
    sys.exit(main())
