import psutil
import ctypes
import os
import winsound
import sys
import threading
import time
import subprocess
from subprocess import CREATE_NO_WINDOW
import re
import win32gui
import win32process
from datetime import datetime
import random
from dataclasses import dataclass
from typing import Dict, Any
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
        "block_sound_freq": 800,
        "unblock_sound_freq": 1200,
        "sound_duration": 200,
        "beep_volume": 100,
        "theme": "dark",
        "auto_reconnect": True,
        "throttle_percentage": 50,
        "throttle_interval": 100,
        "selected_processes": [],
        "focus_only": True,
        "beep": True,
        "custom_rule_name": "BlockRobloxInternet",
        "start_minimized": False,
        "enable_logging": True,
        "auto_refresh_interval": 30,
        "block_direction": "both",
        "window": {"width": 750, "height": 650, "x": None, "y": None}
    }
    
    hotkey: str
    block_sound_freq: int
    unblock_sound_freq: int
    sound_duration: int
    beep_volume: int
    theme: str
    auto_reconnect: bool
    throttle_percentage: int
    throttle_interval: int
    selected_processes: list
    focus_only: bool
    beep: bool
    custom_rule_name: str
    start_minimized: bool
    enable_logging: bool
    auto_refresh_interval: int
    block_direction: str
    window: dict
    
    def __post_init__(self):
        self.block_sound_freq = int(self.block_sound_freq)
        self.unblock_sound_freq = int(self.unblock_sound_freq)
        self.sound_duration = int(self.sound_duration)
        self.beep_volume = int(self.beep_volume)
        self.throttle_percentage = int(self.throttle_percentage)
        self.throttle_interval = int(self.throttle_interval)
        self.auto_refresh_interval = int(self.auto_refresh_interval)
        
        self.auto_reconnect = bool(self.auto_reconnect)
        self.focus_only = bool(self.focus_only)
        self.beep = bool(self.beep)
        self.start_minimized = bool(self.start_minimized)
        self.enable_logging = bool(self.enable_logging)
    
    @staticmethod
    def _get_save_directory() -> Path:
        base_dir = Path("C:/Seven's Scripts")
        base_dir.mkdir(exist_ok=True)
        
        app_dir = base_dir / "Seven's Lag Switch"
        app_dir.mkdir(exist_ok=True)
        
        return app_dir
    
    @property
    def _settings_file(self) -> Path:
        return self._get_save_directory() / "settings.json"
    
    @classmethod
    def load(cls) -> 'Settings':
        try:
            settings_file = cls._get_save_directory() / "settings.json"
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                    
                    settings_dict = cls.DEFAULT_SETTINGS.copy()
                    for key, value in data.items():
                        if key in settings_dict:
                            if isinstance(settings_dict[key], int) and not isinstance(value, int):
                                try:
                                    value = int(value)
                                except (ValueError, TypeError):
                                    pass
                            elif isinstance(settings_dict[key], bool) and not isinstance(value, bool):
                                value = bool(value)
                            settings_dict[key] = value
                    
                    return cls(**settings_dict)
            return cls(**cls.DEFAULT_SETTINGS)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return cls(**cls.DEFAULT_SETTINGS)
    
    def save(self) -> None:
        try:
            settings_file = self._settings_file
            with open(settings_file, 'w') as f:
                json.dump(self.__dict__, f)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def update_selected_processes(self, processes: list) -> None:
        self.selected_processes = processes
        self.save()



class KeybindCaptureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Capture Keybind")
        self.setFixedSize(350, 150)
        self.captured_key = None
        self.listener = None
        self.mouse_listener = None
        self.current_modifiers = set()
        self.setup_ui()
        self.setup_style()
        self.start_capture()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.info_label = QLabel("Press any key combination or mouse button...")
        self.info_label.setObjectName("infoLabel")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
        self.current_key_label = QLabel("Waiting for input...")
        self.current_key_label.setObjectName("currentKeyLabel")
        self.current_key_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_key_label)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setObjectName("dialogButton")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dialogButton")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def setup_style(self):
        style = """
        QDialog {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        
        #infoLabel {
            font-size: 12px;
            color: #00d4ff;
            font-weight: 500;
        }
        
        #currentKeyLabel {
            font-size: 11px;
            color: #ffffff;
            font-weight: bold;
            background-color: #2a2a2a;
            border-radius: 6px;
            padding: 8px;
            border: 1px solid #3a3a3a;
            min-height: 15px;
        }
        
        #dialogButton {
            background-color: #4a4a4a;
            color: #ffffff;
            border: 2px solid #5a5a5a;
            border-radius: 6px;
            padding: 8px 15px;
            font-size: 11px;
            font-weight: bold;
            min-height: 25px;
        }
        
        #dialogButton:hover {
            background-color: #5a5a5a;
            border-color: #6a6a6a;
        }
        
        #dialogButton:pressed {
            background-color: #3a3a3a;
            border-color: #4a4a4a;
        }
        
        #dialogButton:disabled {
            background-color: #2a2a2a;
            color: #666666;
            border-color: #3a3a3a;
        }
        """
        self.setStyleSheet(style)
        
    def start_capture(self):
        try:
            self.listener = pynput_keyboard.Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release
            )
            self.mouse_listener = pynput_mouse.Listener(
                on_click=self.on_mouse_click
            )
            self.listener.start()
            self.mouse_listener.start()
        except Exception as e:
            print(f"Error starting capture: {e}")
            
    def on_key_press(self, key):
        try:
            if hasattr(key, 'char') and key.char and key.char.isprintable():
                self.captured_key = key.char.lower()
            elif hasattr(key, 'name'):
                key_name = key.name.lower()
                if key_name.endswith('_l') or key_name.endswith('_r'):
                    key_name = key_name[:-2]
                self.captured_key = key_name
            else:
                key_str = str(key).lower()
                if 'key.' in key_str:
                    self.captured_key = key_str.split('key.')[-1]
                else:
                    return
                    
            self.current_key_label.setText(f"Captured: {self.captured_key}")
            self.ok_btn.setEnabled(True)
            
        except Exception as e:
            print(f"Key capture error: {e}")
            
    def on_key_release(self, key):
        pass
        
    def on_mouse_click(self, x, y, button, pressed):
        if pressed:
            try:
                button_map = {
                    pynput_mouse.Button.right: "mouse_right",
                    pynput_mouse.Button.middle: "mouse_middle"
                }
                
                if button in button_map:
                    self.captured_key = button_map[button]
                    display_name = button_map[button].replace('mouse_', '').title() + ' Button'
                    self.current_key_label.setText(f"Captured: {display_name}")
                    self.ok_btn.setEnabled(True)
            except Exception:
                pass
                
    def get_key_name(self, key):
        try:
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            elif hasattr(key, 'name'):
                return key.name.lower()
            else:
                return str(key).split('.')[-1].lower()
        except:
            return None
            
    def closeEvent(self, event):
        if self.listener:
            self.listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        event.accept()

class ProcessWidget(QWidget):
    def __init__(self, proc_name, proc_path, parent=None):
        super().__init__(parent)
        self.proc_name = proc_name
        self.proc_path = proc_path
        self.setup_ui()
        
    def setup_ui(self):
        self.setObjectName("processWidget")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("processCheckbox")
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox)
        
        name_label = QLabel(f"{self.proc_name} ({os.path.basename(self.proc_path)})")
        name_label.setObjectName("processLabel")
        layout.addWidget(name_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def is_selected(self):
        return self.checkbox.isChecked()

class RobloxLagSwitch(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.running = True
        self.blocked = False
        self.listening_for_key = False
        self.key_listener = None
        self.mouse_listener = None
        self.last_toggle_time = 0
        self.auto_reconnect_timer = None
        self.throttling_active = False
        self.throttling_thread = None
        self.current_tab = "simple"
        self.rule_name_prefix = self.settings.custom_rule_name
        self.cached_processes = {}
        self.block_commands = []
        self.unblock_commands = []
        self.process_widgets = []
        
        self.setup_ui()
        self.setup_style()
        self.apply_settings()
        self.cache_roblox_processes()
        self.start_key_listener()
        
    def setup_ui(self):
        self.setWindowTitle("Seven's Advanced Lag Switch")
        self.setMinimumSize(1050, 750)
        
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "icons", "switch.ico")
        else:
            icon_path = "icons/icon.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 12, 15, 12)
        
        title_label = QLabel("Seven's Lag Switch")
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        main_layout.addWidget(header_frame)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("tabWidget")
        
        self.setup_simple_tab()
        self.setup_advanced_tab()
        self.setup_settings_tab()
        
        main_layout.addWidget(self.tab_widget, 1)
        
        console_frame = QFrame()
        console_frame.setObjectName("consoleFrame")
        console_frame.setMinimumHeight(100)
        console_frame.setMaximumHeight(120)
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(12, 10, 12, 12)
        console_layout.setSpacing(5)
        
        console_header_layout = QHBoxLayout()
        console_header_label = QLabel("Console Output")
        console_header_label.setObjectName("consoleHeaderLabel")
        console_header_layout.addWidget(console_header_label)
        
        console_header_layout.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("clearButton")
        clear_btn.clicked.connect(self.clear_console)
        console_header_layout.addWidget(clear_btn)
        
        console_layout.addLayout(console_header_layout)
        
        self.log_box = QTextEdit()
        self.log_box.setObjectName("logBox")
        self.log_box.setReadOnly(True)
        console_layout.addWidget(self.log_box)
        
        main_layout.addWidget(console_frame)
        
    def setup_simple_tab(self):
        simple_widget = QWidget()
        simple_widget.setObjectName("tabContent")
        simple_layout = QVBoxLayout(simple_widget)
        simple_layout.setSpacing(15)
        simple_layout.setContentsMargins(15, 15, 15, 15)
        
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(20, 20, 20, 20)
        controls_layout.setSpacing(15)
        
        header_label = QLabel("Quick Controls")
        header_label.setObjectName("sectionHeaderLabel")
        controls_layout.addWidget(header_label)
        
        keybind_frame = QFrame()
        keybind_frame.setObjectName("settingFrame")
        keybind_layout = QHBoxLayout(keybind_frame)
        keybind_layout.setContentsMargins(12, 10, 12, 10)
        keybind_layout.setSpacing(15)
        
        keybind_label = QLabel("Hotkey:")
        keybind_label.setObjectName("settingLabel")
        keybind_layout.addWidget(keybind_label)
        
        self.hotkey_button = QPushButton(f"Keybind: {self.settings.hotkey}")
        self.hotkey_button.setObjectName("keybindButton")
        self.hotkey_button.clicked.connect(self.start_key_listener_dialog)
        keybind_layout.addWidget(self.hotkey_button)
        
        controls_layout.addWidget(keybind_frame)
        
        help_label = QLabel("Supports combos like 'ctrl+z', 'shift+alt+p', or mouse buttons")
        help_label.setObjectName("helpLabel")
        help_label.setAlignment(Qt.AlignCenter)
        controls_layout.addWidget(help_label)
        
        self.status_frame = QFrame()
        self.status_frame.setObjectName("statusDisplayFrame")
        status_layout = QVBoxLayout(self.status_frame)
        status_layout.setContentsMargins(15, 12, 15, 12)
        
        self.status_label = QLabel("Status: Running")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        controls_layout.addWidget(self.status_frame)
        
        options_frame = QFrame()
        options_frame.setObjectName("optionsFrame")
        options_layout = QVBoxLayout(options_frame)
        options_layout.setContentsMargins(15, 12, 15, 12)
        options_layout.setSpacing(8)
        
        self.auto_reconnect_cb = QCheckBox("Auto Time Connect")
        self.auto_reconnect_cb.setObjectName("optionCheckbox")
        self.auto_reconnect_cb.toggled.connect(self.toggle_auto_reconnect)
        options_layout.addWidget(self.auto_reconnect_cb)
        
        self.focus_only_cb = QCheckBox("Lag Only When Roblox Focused")
        self.focus_only_cb.setObjectName("optionCheckbox")
        self.focus_only_cb.toggled.connect(self.update_focus_only)
        options_layout.addWidget(self.focus_only_cb)
        
        self.beep_cb = QCheckBox("Enable Beep")
        self.beep_cb.setObjectName("optionCheckbox")
        self.beep_cb.toggled.connect(self.update_beep)
        options_layout.addWidget(self.beep_cb)
        
        controls_layout.addWidget(options_frame)
        
        toggle_btn = QPushButton("Toggle Connection")
        toggle_btn.setObjectName("toggleButton")
        toggle_btn.clicked.connect(self.toggle_roblox_internet)
        controls_layout.addWidget(toggle_btn)
        
        simple_layout.addWidget(controls_frame)
        simple_layout.addStretch()
        
        self.tab_widget.addTab(simple_widget, "Simple")
        
    def setup_advanced_tab(self):
        advanced_widget = QWidget()
        advanced_widget.setObjectName("tabContent")
        advanced_layout = QVBoxLayout(advanced_widget)
        advanced_layout.setSpacing(0)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(15, 15, 15, 15)
        
        throttle_frame = QFrame()
        throttle_frame.setObjectName("advancedFrame")
        throttle_layout = QVBoxLayout(throttle_frame)
        throttle_layout.setContentsMargins(15, 15, 15, 15)
        throttle_layout.setSpacing(12)
        
        throttle_header = QLabel("Connection Throttle")
        throttle_header.setObjectName("sectionHeaderLabel")
        throttle_layout.addWidget(throttle_header)
        
        throttle_setting_frame = QFrame()
        throttle_setting_frame.setObjectName("settingFrame")
        throttle_setting_layout = QVBoxLayout(throttle_setting_frame)
        throttle_setting_layout.setContentsMargins(12, 12, 12, 12)
        throttle_setting_layout.setSpacing(8)
        
        throttle_label = QLabel("Bootleg Packet Throttle Level:")
        throttle_label.setObjectName("settingLabel")
        throttle_setting_layout.addWidget(throttle_label)
        
        slider_container = QHBoxLayout()
        slider_container.setSpacing(10)
        self.throttle_slider = QSlider(Qt.Horizontal)
        self.throttle_slider.setObjectName("throttleSlider")
        self.throttle_slider.setRange(0, 100)
        self.throttle_slider.setValue(self.settings.throttle_percentage)
        self.throttle_slider.valueChanged.connect(self.update_throttle_value)
        slider_container.addWidget(self.throttle_slider)
        
        self.throttle_value_label = QLabel(f"{self.settings.throttle_percentage}%")
        self.throttle_value_label.setObjectName("sliderValueLabel")
        slider_container.addWidget(self.throttle_value_label)
        
        throttle_setting_layout.addLayout(slider_container)
        throttle_layout.addWidget(throttle_setting_frame)
        
        interval_frame = QFrame()
        interval_frame.setObjectName("settingFrame")
        interval_layout = QHBoxLayout(interval_frame)
        interval_layout.setContentsMargins(12, 10, 12, 10)
        interval_layout.setSpacing(15)
        
        interval_label = QLabel("Throttle Interval (ms):")
        interval_label.setObjectName("settingLabel")
        interval_layout.addWidget(interval_label)
        
        interval_layout.addStretch()
        
        self.interval_input = QLineEdit(str(self.settings.throttle_interval))
        self.interval_input.setObjectName("settingInput")
        self.interval_input.editingFinished.connect(self.update_throttle_interval)
        interval_layout.addWidget(self.interval_input)
        
        throttle_layout.addWidget(interval_frame)
        
        self.throttle_button = QPushButton("Start Throttling")
        self.throttle_button.setObjectName("throttleButton")
        self.throttle_button.clicked.connect(self.toggle_throttling)
        throttle_layout.addWidget(self.throttle_button)
        
        scroll_layout.addWidget(throttle_frame)
        
        process_frame = QFrame()
        process_frame.setObjectName("advancedFrame")
        process_layout = QVBoxLayout(process_frame)
        process_layout.setContentsMargins(15, 15, 15, 15)
        process_layout.setSpacing(12)
        
        process_header_layout = QHBoxLayout()
        process_header = QLabel("Process Management")
        process_header.setObjectName("sectionHeaderLabel")
        process_header_layout.addWidget(process_header)
        
        process_header_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh Processes")
        refresh_btn.setObjectName("refreshButton")
        refresh_btn.clicked.connect(self.refresh_roblox_processes)
        process_header_layout.addWidget(refresh_btn)
        
        process_layout.addLayout(process_header_layout)
        
        self.process_scroll = QScrollArea()
        self.process_scroll.setObjectName("processScrollArea")
        self.process_scroll.setWidgetResizable(True)
        self.process_scroll.setMinimumHeight(200)
        self.process_scroll.setMaximumHeight(250)
        
        self.process_content = QWidget()
        self.process_content.setObjectName("processScrollContent")
        self.process_content_layout = QVBoxLayout(self.process_content)
        self.process_content_layout.setSpacing(5)
        self.process_content_layout.setContentsMargins(10, 10, 10, 10)
        
        self.process_scroll.setWidget(self.process_content)
        process_layout.addWidget(self.process_scroll)
        
        scroll_layout.addWidget(process_frame)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        advanced_layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(advanced_widget, "Advanced")
        
    def setup_settings_tab(self):
        settings_widget = QWidget()
        settings_widget.setObjectName("tabContent")
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(0)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(15, 15, 15, 15)
        
        settings_header = QLabel("Application Settings")
        settings_header.setObjectName("pageHeaderLabel")
        scroll_layout.addWidget(settings_header)
        
        sound_frame = QFrame()
        sound_frame.setObjectName("settingsGroupFrame")
        sound_layout = QVBoxLayout(sound_frame)
        sound_layout.setContentsMargins(15, 15, 15, 15)
        sound_layout.setSpacing(10)
        
        sound_header = QLabel("Sound Settings")
        sound_header.setObjectName("groupHeaderLabel")
        sound_layout.addWidget(sound_header)
        
        block_freq_frame = QFrame()
        block_freq_frame.setObjectName("settingFrame")
        block_freq_layout = QHBoxLayout(block_freq_frame)
        block_freq_layout.setContentsMargins(12, 8, 12, 8)
        block_freq_layout.setSpacing(10)
        
        block_freq_label = QLabel("Block Sound Frequency:")
        block_freq_label.setObjectName("settingLabel")
        block_freq_layout.addWidget(block_freq_label)
        
        self.block_freq_slider = QSlider(Qt.Horizontal)
        self.block_freq_slider.setObjectName("settingSlider")
        self.block_freq_slider.setRange(200, 2000)
        self.block_freq_slider.setValue(self.settings.block_sound_freq)
        self.block_freq_slider.valueChanged.connect(lambda v: self.update_sound_setting('block_sound_freq', v))
        block_freq_layout.addWidget(self.block_freq_slider)
        
        self.block_freq_value = QLabel(str(self.settings.block_sound_freq))
        self.block_freq_value.setObjectName("sliderValueLabel")
        block_freq_layout.addWidget(self.block_freq_value)
        
        sound_layout.addWidget(block_freq_frame)
        
        unblock_freq_frame = QFrame()
        unblock_freq_frame.setObjectName("settingFrame")
        unblock_freq_layout = QHBoxLayout(unblock_freq_frame)
        unblock_freq_layout.setContentsMargins(12, 8, 12, 8)
        unblock_freq_layout.setSpacing(10)
        
        unblock_freq_label = QLabel("Unblock Sound Frequency:")
        unblock_freq_label.setObjectName("settingLabel")
        unblock_freq_layout.addWidget(unblock_freq_label)
        
        self.unblock_freq_slider = QSlider(Qt.Horizontal)
        self.unblock_freq_slider.setObjectName("settingSlider")
        self.unblock_freq_slider.setRange(200, 2000)
        self.unblock_freq_slider.setValue(self.settings.unblock_sound_freq)
        self.unblock_freq_slider.valueChanged.connect(lambda v: self.update_sound_setting('unblock_sound_freq', v))
        unblock_freq_layout.addWidget(self.unblock_freq_slider)
        
        self.unblock_freq_value = QLabel(str(self.settings.unblock_sound_freq))
        self.unblock_freq_value.setObjectName("sliderValueLabel")
        unblock_freq_layout.addWidget(self.unblock_freq_value)
        
        sound_layout.addWidget(unblock_freq_frame)
        
        sound_duration_frame = QFrame()
        sound_duration_frame.setObjectName("settingFrame")
        sound_duration_layout = QHBoxLayout(sound_duration_frame)
        sound_duration_layout.setContentsMargins(12, 8, 12, 8)
        sound_duration_layout.setSpacing(10)
        
        sound_duration_label = QLabel("Sound Duration (ms):")
        sound_duration_label.setObjectName("settingLabel")
        sound_duration_layout.addWidget(sound_duration_label)
        
        self.sound_duration_slider = QSlider(Qt.Horizontal)
        self.sound_duration_slider.setObjectName("settingSlider")
        self.sound_duration_slider.setRange(50, 500)
        self.sound_duration_slider.setValue(self.settings.sound_duration)
        self.sound_duration_slider.valueChanged.connect(lambda v: self.update_sound_setting('sound_duration', v))
        sound_duration_layout.addWidget(self.sound_duration_slider)
        
        self.sound_duration_value = QLabel(str(self.settings.sound_duration))
        self.sound_duration_value.setObjectName("sliderValueLabel")
        sound_duration_layout.addWidget(self.sound_duration_value)
        
        sound_layout.addWidget(sound_duration_frame)
        
        beep_volume_frame = QFrame()
        beep_volume_frame.setObjectName("settingFrame")
        beep_volume_layout = QHBoxLayout(beep_volume_frame)
        beep_volume_layout.setContentsMargins(12, 8, 12, 8)
        beep_volume_layout.setSpacing(10)
        
        beep_volume_label = QLabel("Beep Volume:")
        beep_volume_label.setObjectName("settingLabel")
        beep_volume_layout.addWidget(beep_volume_label)
        
        self.beep_volume_slider = QSlider(Qt.Horizontal)
        self.beep_volume_slider.setObjectName("settingSlider")
        self.beep_volume_slider.setRange(10, 100)
        self.beep_volume_slider.setValue(self.settings.beep_volume)
        self.beep_volume_slider.valueChanged.connect(lambda v: self.update_sound_setting('beep_volume', v))
        beep_volume_layout.addWidget(self.beep_volume_slider)
        
        self.beep_volume_value = QLabel(f"{self.settings.beep_volume}%")
        self.beep_volume_value.setObjectName("sliderValueLabel")
        beep_volume_layout.addWidget(self.beep_volume_value)
        
        sound_layout.addWidget(beep_volume_frame)
        
        scroll_layout.addWidget(sound_frame)
        
        ui_frame = QFrame()
        ui_frame.setObjectName("settingsGroupFrame")
        ui_layout = QVBoxLayout(ui_frame)
        ui_layout.setContentsMargins(15, 15, 15, 15)
        ui_layout.setSpacing(10)
        
        ui_header = QLabel("UI Settings")
        ui_header.setObjectName("groupHeaderLabel")
        ui_layout.addWidget(ui_header)
        
        self.start_minimized_cb = QCheckBox("Start Minimized")
        self.start_minimized_cb.setObjectName("settingCheckbox")
        self.start_minimized_cb.toggled.connect(self.update_start_minimized)
        ui_layout.addWidget(self.start_minimized_cb)
        
        self.enable_logging_cb = QCheckBox("Enable Console Logging")
        self.enable_logging_cb.setObjectName("settingCheckbox")
        self.enable_logging_cb.toggled.connect(self.update_enable_logging)
        ui_layout.addWidget(self.enable_logging_cb)
        
        refresh_interval_frame = QFrame()
        refresh_interval_frame.setObjectName("settingFrame")
        refresh_interval_layout = QHBoxLayout(refresh_interval_frame)
        refresh_interval_layout.setContentsMargins(12, 8, 12, 8)
        refresh_interval_layout.setSpacing(10)
        
        refresh_interval_label = QLabel("Auto Refresh Interval (seconds):")
        refresh_interval_label.setObjectName("settingLabel")
        refresh_interval_layout.addWidget(refresh_interval_label)
        
        refresh_interval_layout.addStretch()
        
        self.refresh_interval_input = QLineEdit(str(self.settings.auto_refresh_interval))
        self.refresh_interval_input.setObjectName("settingInput")
        self.refresh_interval_input.editingFinished.connect(self.update_refresh_interval)
        refresh_interval_layout.addWidget(self.refresh_interval_input)
        
        ui_layout.addWidget(refresh_interval_frame)
        
        scroll_layout.addWidget(ui_frame)
        
        firewall_frame = QFrame()
        firewall_frame.setObjectName("settingsGroupFrame")
        firewall_layout = QVBoxLayout(firewall_frame)
        firewall_layout.setContentsMargins(15, 15, 15, 15)
        firewall_layout.setSpacing(10)
        
        firewall_header = QLabel("Firewall Settings")
        firewall_header.setObjectName("groupHeaderLabel")
        firewall_layout.addWidget(firewall_header)
        
        rule_name_frame = QFrame()
        rule_name_frame.setObjectName("settingFrame")
        rule_name_layout = QHBoxLayout(rule_name_frame)
        rule_name_layout.setContentsMargins(12, 8, 12, 8)
        rule_name_layout.setSpacing(10)
        
        rule_name_label = QLabel("Firewall Rule Prefix:")
        rule_name_label.setObjectName("settingLabel")
        rule_name_layout.addWidget(rule_name_label)
        
        rule_name_layout.addStretch()
        
        self.rule_name_input = QLineEdit(self.settings.custom_rule_name)
        self.rule_name_input.setObjectName("settingInput")
        self.rule_name_input.editingFinished.connect(self.update_rule_name)
        rule_name_layout.addWidget(self.rule_name_input)
        
        firewall_layout.addWidget(rule_name_frame)
        
        block_direction_frame = QFrame()
        block_direction_frame.setObjectName("settingFrame")
        block_direction_layout = QVBoxLayout(block_direction_frame)
        block_direction_layout.setContentsMargins(12, 10, 12, 10)
        block_direction_layout.setSpacing(8)
        
        block_direction_label = QLabel("Block Direction:")
        block_direction_label.setObjectName("settingLabel")
        block_direction_layout.addWidget(block_direction_label)
        
        direction_radio_layout = QHBoxLayout()
        direction_radio_layout.setSpacing(15)
        
        self.both_radio = QRadioButton("Both")
        self.both_radio.setObjectName("settingRadio")
        self.both_radio.toggled.connect(lambda: self.update_block_direction("both"))
        direction_radio_layout.addWidget(self.both_radio)
        
        self.outbound_radio = QRadioButton("Outbound Only")
        self.outbound_radio.setObjectName("settingRadio")
        self.outbound_radio.toggled.connect(lambda: self.update_block_direction("outbound"))
        direction_radio_layout.addWidget(self.outbound_radio)
        
        self.inbound_radio = QRadioButton("Inbound Only")
        self.inbound_radio.setObjectName("settingRadio")
        self.inbound_radio.toggled.connect(lambda: self.update_block_direction("inbound"))
        direction_radio_layout.addWidget(self.inbound_radio)
        
        direction_radio_layout.addStretch()
        block_direction_layout.addLayout(direction_radio_layout)
        
        firewall_layout.addWidget(block_direction_frame)
        
        scroll_layout.addWidget(firewall_frame)
        
        about_frame = QFrame()
        about_frame.setObjectName("settingsGroupFrame")
        about_layout = QVBoxLayout(about_frame)
        about_layout.setContentsMargins(15, 15, 15, 15)
        about_layout.setSpacing(8)
        
        about_header = QLabel("About")
        about_header.setObjectName("groupHeaderLabel")
        about_layout.addWidget(about_header)
        
        about_title = QLabel("Seven's Advanced Lag Switch v3.2")
        about_title.setObjectName("aboutTitleLabel")
        about_layout.addWidget(about_title)
        
        about_subtitle = QLabel("Enhanced GUI Edition with Advanced Keybinds")
        about_subtitle.setObjectName("aboutSubtitleLabel")
        about_layout.addWidget(about_subtitle)
        
        scroll_layout.addWidget(about_frame)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        settings_layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(settings_widget, "Settings")
        
    def setup_style(self):
        style = """
        QMainWindow {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        
        #headerFrame {
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #3a3a3a;
        }
        
        #titleLabel {
            font-size: 18px;
            font-weight: bold;
            color: #00d4ff;
        }
        
        #tabWidget {
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #3a3a3a;
        }
        
        #tabWidget::pane {
            background-color: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
        }
        
        QTabBar::tab {
            background-color: #3a3a3a;
            color: #cccccc;
            padding: 8px 20px;
            margin: 2px;
            border-radius: 4px;
            font-weight: bold;
            min-width: 60px;
        }
        
        QTabBar::tab:selected {
            background-color: #00d4ff;
            color: #000000;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #4a4a4a;
            color: #ffffff;
        }
        
        #tabContent {
            background-color: #2a2a2a;
        }
        
        #mainScrollArea {
            background-color: #2a2a2a;
            border: none;
        }
        
        #scrollContent {
            background-color: #2a2a2a;
        }
        
        #processScrollContent {
            background-color: #333333;
        }
        
        #controlsFrame, #advancedFrame, #settingsGroupFrame {
            background-color: #212121;
            border-radius: 10px;
            border: 1px solid #3a3a3a;
        }
        
        #sectionHeaderLabel, #pageHeaderLabel {
            font-size: 16px;
            font-weight: bold;
            color: #00d4ff;
        }
        
        #groupHeaderLabel {
            font-size: 14px;
            font-weight: bold;
            color: #00d4ff;
        }
        
        #settingFrame {
            background-color: #333333;
            border-radius: 6px;
            border: 1px solid #4a4a4a;
        }
        
        #settingFrame:hover {
            background-color: #3a3a3a;
            border-color: #5a5a5a;
        }
        
        #settingLabel {
            font-size: 12px;
            color: #ffffff;
            font-weight: 500;
            min-width: 150px;
        }
        
        #helpLabel {
            font-size: 10px;
            color: #aaaaaa;
            font-style: italic;
        }
        
        #statusDisplayFrame {
            background-color: #333333;
            border-radius: 8px;
            border: 2px solid #4a4a4a;
            min-height: 40px;
        }
        
        #statusLabel {
            font-size: 16px;
            font-weight: bold;
            color: #4dff4d;
        }
        
        #optionsFrame {
            background-color: #333333;
            border-radius: 6px;
            border: 1px solid #4a4a4a;
        }
        
        #keybindButton {
            background-color: #4a4a4a;
            color: #ffffff;
            border: 2px solid #5a5a5a;
            border-radius: 6px;
            padding: 8px 15px;
            font-size: 12px;
            font-weight: bold;
            min-height: 30px;
        }
        
        #keybindButton:hover {
            background-color: #5a5a5a;
            border-color: #6a6a6a;
        }
        
        #keybindButton:pressed {
            background-color: #3a3a3a;
            border-color: #4a4a4a;
        }
        
        #toggleButton {
            background-color: #3d5af1;
            color: #ffffff;
            border: 2px solid #4d6af1;
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
            font-weight: bold;
            min-height: 35px;
        }
        
        #toggleButton:hover {
            background-color: #2d3ab1;
            border-color: #3d4ab1;
        }
        
        #toggleButton:pressed {
            background-color: #1d2a91;
            border-color: #2d3a91;
        }
        
        #throttleButton {
            background-color: #ff4444;
            color: #ffffff;
            border: 2px solid #ff5555;
            border-radius: 6px;
            padding: 10px;
            font-size: 12px;
            font-weight: bold;
            min-height: 30px;
        }
        
        #throttleButton:hover {
            background-color: #ff5555;
            border-color: #ff6666;
        }
        
        #refreshButton, #clearButton {
            background-color: #3d5af1;
            color: #ffffff;
            border: 2px solid #4d6af1;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 10px;
            font-weight: bold;
            min-height: 25px;
        }
        
        #refreshButton:hover, #clearButton:hover {
            background-color: #2d3ab1;
            border-color: #3d4ab1;
        }
        
        #throttleSlider, #settingSlider {
            height: 20px;
        }
        
        #throttleSlider::groove:horizontal, #settingSlider::groove:horizontal {
            border: 1px solid #4a4a4a;
            height: 6px;
            background: #2a2a2a;
            border-radius: 3px;
        }
        
        #throttleSlider::handle:horizontal, #settingSlider::handle:horizontal {
            background: #00d4ff;
            border: 1px solid #00b4df;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        
        #throttleSlider::handle:horizontal:hover, #settingSlider::handle:horizontal:hover {
            background: #00b4df;
        }
        
        #sliderValueLabel {
            font-size: 12px;
            font-weight: bold;
            color: #00d4ff;
            min-width: 50px;
        }
        
        #settingInput {
            background-color: #4a4a4a;
            color: #ffffff;
            border: 2px solid #5a5a5a;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 11px;
            min-width: 80px;
            max-width: 120px;
        }
        
        #settingInput:focus {
            border-color: #00d4ff;
        }
        
        #optionCheckbox, #settingCheckbox {
            color: #ffffff;
            font-size: 12px;
            font-weight: 500;
            spacing: 6px;
        }
        
        #optionCheckbox::indicator, #settingCheckbox::indicator {
            width: 16px;
            height: 16px;
        }
        
        #optionCheckbox::indicator:unchecked, #settingCheckbox::indicator:unchecked {
            background-color: #4a4a4a;
            border: 2px solid #5a5a5a;
            border-radius: 3px;
        }
        
        #optionCheckbox::indicator:checked, #settingCheckbox::indicator:checked {
            background-color: #00d4ff;
            border: 2px solid #00d4ff;
            border-radius: 3px;
        }
        
        #settingRadio {
            color: #ffffff;
            font-size: 12px;
            font-weight: 500;
            spacing: 6px;
        }
        
        #settingRadio::indicator {
            width: 16px;
            height: 16px;
        }
        
        #settingRadio::indicator:unchecked {
            background-color: #4a4a4a;
            border: 2px solid #5a5a5a;
            border-radius: 8px;
        }
        
        #settingRadio::indicator:checked {
            background-color: #00d4ff;
            border: 2px solid #00d4ff;
            border-radius: 8px;
        }
        
        #consoleFrame {
            background-color: #212121;
            border-radius: 8px;
            border: 1px solid #3a3a3a;
        }
        
        #consoleHeaderLabel {
            font-size: 11px;
            font-weight: bold;
            color: #aaaaaa;
        }
        
        #logBox {
            background-color: #141414;
            color: #cccccc;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            font-size: 9px;
            padding: 6px;
        }
        
        #processScrollArea {
            background-color: #333333;
            border: 1px solid #4a4a4a;
            border-radius: 6px;
        }
        
        #processWidget {
            background-color: #3a3a3a;
            border-radius: 4px;
            border: 1px solid #4a4a4a;
            margin: 1px;
        }
        
        #processWidget:hover {
            background-color: #4a4a4a;
            border-color: #5a5a5a;
        }
        
        #processCheckbox::indicator {
            width: 14px;
            height: 14px;
        }
        
        #processCheckbox::indicator:unchecked {
            background-color: #4a4a4a;
            border: 2px solid #5a5a5a;
            border-radius: 2px;
        }
        
        #processCheckbox::indicator:checked {
            background-color: #00d4ff;
            border: 2px solid #00d4ff;
            border-radius: 2px;
        }
        
        #processLabel {
            font-size: 11px;
            color: #ffffff;
        }
        
        #aboutTitleLabel {
            font-size: 12px;
            color: #cccccc;
            font-weight: 500;
        }
        
        #aboutSubtitleLabel {
            font-size: 10px;
            color: #aaaaaa;
        }
        
        QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 10px;
            border-radius: 5px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #4a4a4a;
            border-radius: 5px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #5a5a5a;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """
        self.setStyleSheet(style)
        
    def apply_settings(self):
        if self.settings.window["width"] and self.settings.window["height"]:
            self.resize(self.settings.window["width"], self.settings.window["height"])
        
        if self.settings.window["x"] is not None and self.settings.window["y"] is not None:
            self.move(self.settings.window["x"], self.settings.window["y"])
        
        self.auto_reconnect_cb.setChecked(self.settings.auto_reconnect)
        self.focus_only_cb.setChecked(self.settings.focus_only)
        self.beep_cb.setChecked(self.settings.beep)
        self.start_minimized_cb.setChecked(self.settings.start_minimized)
        self.enable_logging_cb.setChecked(self.settings.enable_logging)
        
        if self.settings.block_direction == "both":
            self.both_radio.setChecked(True)
        elif self.settings.block_direction == "outbound":
            self.outbound_radio.setChecked(True)
        elif self.settings.block_direction == "inbound":
            self.inbound_radio.setChecked(True)
        
        if self.settings.start_minimized:
            QTimer.singleShot(200, self.showMinimized)
        
    def clear_console(self):
        self.log_box.clear()
        self.log("Console cleared")
        
    def log(self, msg):
        if not self.settings.enable_logging:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {msg}")
        
    def update_throttle_value(self, value):
        self.throttle_value_label.setText(f"{value}%")
        self.settings.throttle_percentage = value
        self.settings.save()
        
    def update_throttle_interval(self):
        try:
            value = max(10, int(self.interval_input.text()))
            self.interval_input.setText(str(value))
            self.settings.throttle_interval = value
            self.settings.save()
        except ValueError:
            self.interval_input.setText(str(self.settings.throttle_interval))
            
    def update_refresh_interval(self):
        try:
            value = max(5, int(self.refresh_interval_input.text()))
            self.refresh_interval_input.setText(str(value))
            self.settings.auto_refresh_interval = value
            self.settings.save()
            self.cache_roblox_processes()
        except ValueError:
            self.refresh_interval_input.setText(str(self.settings.auto_refresh_interval))
            
    def update_rule_name(self):
        new_name = self.rule_name_input.text().strip()
        if new_name:
            self.settings.custom_rule_name = new_name
            self.rule_name_prefix = new_name
            self.settings.save()
            self.log(f"Firewall rule prefix updated to: {new_name}")
        else:
            self.rule_name_input.setText(self.settings.custom_rule_name)
            
    def update_block_direction(self, direction):
        self.settings.block_direction = direction
        self.settings.save()
        self.log(f"Block direction updated to: {direction}")
        
    def update_focus_only(self):
        self.settings.focus_only = self.focus_only_cb.isChecked()
        self.settings.save()
        
    def update_beep(self):
        self.settings.beep = self.beep_cb.isChecked()
        self.settings.save()
        
    def update_start_minimized(self):
        self.settings.start_minimized = self.start_minimized_cb.isChecked()
        self.settings.save()
        
    def update_enable_logging(self):
        self.settings.enable_logging = self.enable_logging_cb.isChecked()
        self.settings.save()
        
    def update_sound_setting(self, setting_name, value):
        setattr(self.settings, setting_name, int(value))
        self.settings.save()
        
        if setting_name == 'block_sound_freq':
            self.block_freq_value.setText(str(value))
        elif setting_name == 'unblock_sound_freq':
            self.unblock_freq_value.setText(str(value))
        elif setting_name == 'sound_duration':
            self.sound_duration_value.setText(str(value))
        elif setting_name == 'beep_volume':
            self.beep_volume_value.setText(f"{value}%")
            
    def cache_roblox_processes(self):
        self.cached_processes = self.find_all_roblox_processes()
        QTimer.singleShot(self.settings.auto_refresh_interval * 1000, self.cache_roblox_processes)
        
    def refresh_roblox_processes(self):
        for widget in self.process_widgets:
            widget.deleteLater()
        self.process_widgets.clear()
        
        self.cached_processes = self.find_all_roblox_processes()
        
        if not self.cached_processes:
            no_process_label = QLabel("No Roblox processes found")
            no_process_label.setObjectName("processLabel")
            no_process_label.setStyleSheet("color: #ff6666; padding: 15px; font-size: 12px; text-align: center;")
            no_process_label.setAlignment(Qt.AlignCenter)
            self.process_content_layout.addWidget(no_process_label)
            self.process_widgets.append(no_process_label)
            return
            
        for proc_name, proc_path in self.cached_processes.items():
            widget = ProcessWidget(proc_name, proc_path)
            self.process_content_layout.addWidget(widget)
            self.process_widgets.append(widget)
            
    def find_all_roblox_processes(self):
        roblox_processes = {}
        pattern = re.compile(r'Roblox.*\.exe', re.IGNORECASE)
        for p in psutil.process_iter(['name', 'exe']):
            try:
                if p.info['name'] and pattern.match(p.info['name']):
                    roblox_processes[p.info['name']] = p.info['exe']
            except Exception:
                pass
        return roblox_processes
        
    def toggle_throttling(self):
        if self.throttling_active:
            self.stop_throttling()
            self.throttle_button.setText("Start Throttling")
            self.throttle_button.setStyleSheet("""
                background-color: #ff4444;
                color: #ffffff;
                border: 2px solid #ff5555;
            """)
        else:
            self.start_throttling()
            self.throttle_button.setText("Stop Throttling")
            self.throttle_button.setStyleSheet("""
                background-color: #3B8A3A;
                color: #ffffff;
                border: 2px solid #4B9A4A;
            """)
            
    def start_throttling(self):
        if self.throttling_active:
            return
        if self.settings.throttle_percentage == 100:
            self.toggle_roblox_internet()
            return
        self.throttling_active = True
        self.throttling_thread = threading.Thread(target=self.throttle_connection, daemon=True)
        self.throttling_thread.start()
        self.status_label.setText(f"Status: Throttling ({self.settings.throttle_percentage}%)")
        self.status_label.setStyleSheet("color: #ffcc00;")
        self.log("Started throttling")
        
    def stop_throttling(self):
        self.throttling_active = False
        self.unblock_all_roblox()
        if self.throttling_thread:
            self.throttling_thread.join(timeout=1)
            self.throttling_thread = None
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("color: #4dff4d;")
        self.log("Stopped throttling")
        
    def throttle_connection(self):
        perc = self.settings.throttle_percentage
        interval = self.settings.throttle_interval / 1000.0
        block_time = interval * (perc / 100)
        unblock_time = interval * (1 - perc / 100)
        self.prepare_firewall_rules()
        while self.throttling_active:
            self.block_selected_roblox_fast()
            time.sleep(block_time)
            if not self.throttling_active:
                break
            self.unblock_all_roblox_fast()
            time.sleep(unblock_time)
            
    def prepare_firewall_rules(self):
        self.block_commands.clear()
        self.unblock_commands.clear()
        
        selected_processes = []
        for widget in self.process_widgets:
            if isinstance(widget, ProcessWidget) and widget.is_selected():
                selected_processes.append(widget.proc_path)
                
        if not selected_processes:
            self.cached_processes = self.find_all_roblox_processes()
            selected_processes = list(self.cached_processes.values())
            
        if not selected_processes:
            return
            
        for p in selected_processes:
            name = os.path.basename(p)
            rname = f"{self.rule_name_prefix}_{name}"
            
            if self.settings.block_direction == "both":
                self.block_commands.extend([
                    f'netsh advfirewall firewall add rule name="{rname}" dir=out program="{p}" action=block',
                    f'netsh advfirewall firewall add rule name="{rname}" dir=in program="{p}" action=block'])
                self.unblock_commands.extend([
                    f'netsh advfirewall firewall delete rule name="{rname}" dir=out',
                    f'netsh advfirewall firewall delete rule name="{rname}" dir=in'])
            elif self.settings.block_direction == "outbound":
                self.block_commands.append(
                    f'netsh advfirewall firewall add rule name="{rname}" dir=out program="{p}" action=block')
                self.unblock_commands.append(
                    f'netsh advfirewall firewall delete rule name="{rname}" dir=out')
            elif self.settings.block_direction == "inbound":
                self.block_commands.append(
                    f'netsh advfirewall firewall add rule name="{rname}" dir=in program="{p}" action=block')
                self.unblock_commands.append(
                    f'netsh advfirewall firewall delete rule name="{rname}" dir=in')
                
    def start_key_listener(self):
        try:
            if self.key_listener:
                self.key_listener.stop()
            if self.mouse_listener:
                self.mouse_listener.stop()
                
            self.key_listener = pynput_keyboard.Listener(
                on_press=self.on_key_press
            )
            self.mouse_listener = pynput_mouse.Listener(
                on_click=self.on_mouse_click
            )
            
            self.key_listener.start()
            self.mouse_listener.start()
        except Exception as e:
            self.log(f"Error starting key listener: {e}")
            
    def on_key_press(self, key):
        try:
            if self.settings.focus_only and not self.active_window_is_roblox():
                return
                
            current_time = time.time()
            if current_time - self.last_toggle_time < 0.3:
                return
                
            key_name = self.get_key_name(key)
            if key_name and key_name == self.settings.hotkey.lower():
                self.last_toggle_time = current_time
                QTimer.singleShot(0, self.toggle_roblox_internet)
        except Exception:
            pass
            
    def on_mouse_click(self, x, y, button, pressed):
        if not pressed:
            return
            
        try:
            if self.settings.focus_only and not self.active_window_is_roblox():
                return
                
            current_time = time.time()
            if current_time - self.last_toggle_time < 0.3:
                return
                
            button_map = {
                pynput_mouse.Button.right: "mouse_right",
                pynput_mouse.Button.middle: "mouse_middle"
            }
            
            if button in button_map and self.settings.hotkey == button_map[button]:
                self.last_toggle_time = current_time
                QTimer.singleShot(0, self.toggle_roblox_internet)
        except Exception:
            pass
            
    def check_hotkey_match(self, key, hotkey_parts):
        try:
            key_name = self.get_key_name(key)
            if not key_name:
                return False
            return key_name == self.settings.hotkey.lower()
        except:
            return False
            
    def get_key_name(self, key):
        try:
            if hasattr(key, 'char') and key.char and key.char.isprintable():
                return key.char.lower()
            elif hasattr(key, 'name'):
                key_name = key.name.lower()
                if key_name.endswith('_l') or key_name.endswith('_r'):
                    key_name = key_name[:-2]
                return key_name
            else:
                key_str = str(key).lower()
                if 'key.' in key_str:
                    return key_str.split('key.')[-1]
                return key_str.split('.')[-1]
        except:
            return None
        
    def active_window_is_roblox(self):
        try:
            h = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(h)
            name = psutil.Process(pid).name()
            return 'roblox' in name.lower()
        except Exception:
            return False
        
    def start_key_listener_dialog(self):
        if self.listening_for_key:
            return
        
        dialog = KeybindCaptureDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.captured_key:
            old_hotkey = self.settings.hotkey
            self.settings.hotkey = dialog.captured_key
            self.settings.save()
            self.hotkey_button.setText(f"Keybind: {dialog.captured_key}")
            self.log(f"Keybind changed from '{old_hotkey}' to '{dialog.captured_key}'")
            self.start_key_listener()
            
    def block_selected_roblox_fast(self):
        if not self.block_commands:
            self.prepare_firewall_rules()
        if not self.block_commands:
            return
        subprocess.Popen(" && ".join(self.block_commands), creationflags=CREATE_NO_WINDOW, shell=True)
        self.blocked = True
        self.update_status()
        self.log("Blocked Roblox internet access")
        if self.settings.auto_reconnect and not self.throttling_active:
            if self.auto_reconnect_timer:
                self.auto_reconnect_timer.stop()
            self.auto_reconnect_timer = QTimer()
            self.auto_reconnect_timer.timeout.connect(self.auto_reconnect)
            self.auto_reconnect_timer.start(9000)
            
    def unblock_all_roblox_fast(self):
        if not self.unblock_commands:
            self.prepare_firewall_rules()
        if not self.unblock_commands:
            return
        subprocess.Popen(" && ".join(self.unblock_commands), creationflags=CREATE_NO_WINDOW, shell=True)
        self.blocked = False
        self.update_status()
        self.log("Unblocked Roblox internet access")
        if self.auto_reconnect_timer:
            self.auto_reconnect_timer.stop()
            self.auto_reconnect_timer = None
            
    def unblock_all_roblox(self):
        self.unblock_all_roblox_fast()
        
    def auto_reconnect(self):
        if self.blocked:
            self.unblock_all_roblox_fast()
            if self.beep_cb.isChecked():
                self.play_beep(self.settings.unblock_sound_freq)
        if self.auto_reconnect_timer:
            self.auto_reconnect_timer.stop()
            self.auto_reconnect_timer = None
            
    def play_beep(self, frequency):
        try:
            volume_factor = self.settings.beep_volume / 100.0
            adjusted_freq = int(frequency * volume_factor)
            if adjusted_freq < 37:
                adjusted_freq = 37
            winsound.Beep(adjusted_freq, self.settings.sound_duration)
        except Exception:
            pass
            
    def toggle_roblox_internet(self):
        try:
            if self.blocked:
                self.unblock_all_roblox_fast()
                if self.beep_cb.isChecked():
                    self.play_beep(self.settings.unblock_sound_freq)
            else:
                if not self.cached_processes and not self.find_all_roblox_processes():
                    QMessageBox.warning(self, 'Error', 'No Roblox processes found. Please make sure Roblox is running.')
                    return
                if not self.block_commands:
                    self.prepare_firewall_rules()
                self.block_selected_roblox_fast()
                if self.beep_cb.isChecked():
                    self.play_beep(self.settings.block_sound_freq)
        except Exception as e:
            self.log(f"Error: {e}")
            
    def update_status(self):
        if self.throttling_active:
            self.status_label.setText(f"Status: Throttling ({self.settings.throttle_percentage}%)")
            self.status_label.setStyleSheet("color: #ffcc00;")
        elif self.blocked:
            self.status_label.setText("Status: Blocked") 
            self.status_label.setStyleSheet("color: #ff6666;")
        else:
            self.status_label.setText("Status: Unblocked")
            self.status_label.setStyleSheet("color: #4dff4d;")
            
    def toggle_auto_reconnect(self):
        self.settings.auto_reconnect = self.auto_reconnect_cb.isChecked()
        self.settings.save()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.settings.window["width"] = self.width()
        self.settings.window["height"] = self.height()
        QTimer.singleShot(500, self.settings.save)
        
    def moveEvent(self, event):
        super().moveEvent(event)
        self.settings.window["x"] = self.x()
        self.settings.window["y"] = self.y()
        QTimer.singleShot(500, self.settings.save)
        
    def closeEvent(self, event):
        self.running = False
        if self.throttling_active:
            self.stop_throttling()
        self.unblock_all_roblox_fast()
        
        if self.key_listener:
            self.key_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
            
        event.accept()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
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