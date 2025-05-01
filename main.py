import psutil
import ctypes
import os
import winsound
import sys
import keyboard
import mouse
import threading
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
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

@dataclass
class Settings:
    DEFAULT_SETTINGS = {
        "hotkey": "alt",
        "block_sound_freq": 800,
        "unblock_sound_freq": 1200,
        "sound_duration": 200,
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
        "auto_refresh_interval": 30
    }
    
    hotkey: str
    block_sound_freq: int
    unblock_sound_freq: int
    sound_duration: int
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
    
    def __post_init__(self):
        self.block_sound_freq = int(self.block_sound_freq)
        self.unblock_sound_freq = int(self.unblock_sound_freq)
        self.sound_duration = int(self.sound_duration)
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

class RobloxLagSwitch:
    def __init__(self):
        self.settings = Settings.load()
        self.running = True
        self.blocked = False
        self.listening_for_key = False
        self.key_listener_thread = None
        self.last_toggle_time = 0
        self.auto_reconnect_timer = None
        self.throttling_active = False
        self.throttling_thread = None
        self.current_tab = "simple"
        self.rule_name_prefix = self.settings.custom_rule_name
        self.cached_processes = {}
        self.block_commands = []
        self.unblock_commands = []
        self.setup_gui()
        self.cache_roblox_processes()
        self.start_key_listener_thread()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.special_key_map = {
            "ctrl": "control",
            "alt": "alt",
            "shift": "shift",
            "win": "windows"
        }

    def setup_gui(self):
        ctk.set_appearance_mode(self.settings.theme)
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Seven's Advanced Lag Switch")
        self.root.geometry("900x810")
        self.root.minsize(900, 810)
        
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "icons", "switch.ico")
        else:
            icon_path = "icons/icon.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            
        self.root.configure(fg_color="#1a1a1a")
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        
        header_frame = ctk.CTkFrame(self.root, fg_color="#212121", corner_radius=0, height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_propagate(False)
        
        ctk.CTkLabel(header_frame, text="Advanced Lag Switch", font=("Segoe UI", 22, "bold"), 
                   text_color="#ffffff").pack(side="left", padx=20, pady=10)
        
        main_content = ctk.CTkFrame(self.root, fg_color="transparent")
        main_content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        main_content.grid_columnconfigure(0, weight=1)
        main_content.grid_rowconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(main_content, corner_radius=15, segmented_button_fg_color="#2d2d2d",
                                   segmented_button_selected_color="#3d5af1", 
                                   segmented_button_selected_hover_color="#2d3ab1",
                                   segmented_button_unselected_color="#2d2d2d",
                                   segmented_button_unselected_hover_color="#3d3d3d")
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.simple_tab = self.tabview.add("Simple")
        self.advanced_tab = self.tabview.add("Advanced")
        self.settings_tab = self.tabview.add("Settings")
        self.tabview.set("Simple")
        
        for tab in [self.simple_tab, self.advanced_tab, self.settings_tab]:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
        
        self.setup_simple_tab()
        self.setup_advanced_tab()
        self.setup_settings_tab()
        
        console_frame = ctk.CTkFrame(self.root, fg_color="#212121", corner_radius=10, height=150)
        console_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 15))
        console_frame.grid_propagate(False)
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)
        
        console_header = ctk.CTkFrame(console_frame, fg_color="#141414", corner_radius=5, height=30)
        console_header.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))
        console_header.grid_propagate(False)
        
        ctk.CTkLabel(console_header, text="Console Output", font=("Segoe UI", 12, "bold"), 
                   text_color="#aaaaaa").pack(side="left", padx=10)
        
        clear_btn = ctk.CTkButton(console_header, text="Clear", width=60, height=20,
                               fg_color="#3d5af1", hover_color="#2d3ab1",
                               font=("Segoe UI", 10),
                               command=self.clear_console)
        clear_btn.pack(side="right", padx=10)
        
        self.log_box = ctk.CTkTextbox(console_frame, state="disabled", 
                                    text_color="#cccccc", fg_color="#141414", 
                                    scrollbar_button_color="#3d5af1",
                                    scrollbar_button_hover_color="#2d3ab1")
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 2))
        
        if self.settings.start_minimized:
            self.root.withdraw()
            self.root.iconify()

    def clear_console(self):
        self.log_box.configure(state="normal")
        self.log_box.delete(1.0, "end")
        self.log_box.configure(state="disabled")
        self.log("Console cleared")

    def log(self, msg):
        if not self.settings.enable_logging:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def setup_simple_tab(self):
        container = ctk.CTkFrame(self.simple_tab, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        container.grid_columnconfigure(0, weight=1)
        
        frame = ctk.CTkFrame(container, fg_color="#212121", corner_radius=15)
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        header = ctk.CTkFrame(frame, fg_color="#141414", corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="Quick Controls", font=("Segoe UI", 18, "bold"), 
                   text_color="#ffffff").pack(pady=10)
        
        controls_frame = ctk.CTkFrame(frame, fg_color="#141414", corner_radius=10)
        controls_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        keybind_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        keybind_frame.pack(fill="x", pady=(20, 10))
        
        ctk.CTkLabel(keybind_frame, text="Hotkey:", font=("Segoe UI", 14), 
                   text_color="#ffffff").pack(side="left", padx=15)
        
        self.hotkey_button = ctk.CTkButton(keybind_frame, text=f"Keybind: {self.settings.hotkey}", 
                                        command=self.start_key_listener,
                                        font=("Segoe UI", 14),
                                        fg_color="#3d5af1", hover_color="#2d3ab1",
                                        corner_radius=8, height=36)
        self.hotkey_button.pack(side="right", padx=15, fill="x", expand=True)
        
        keybind_help = ctk.CTkLabel(controls_frame, 
                                text="Supports combos like 'ctrl+z', 'shift+alt+p', or mouse buttons",
                                font=("Segoe UI", 12), text_color="#aaaaaa")
        keybind_help.pack(fill="x", padx=15, pady=(0, 10))
        
        self.status_frame = ctk.CTkFrame(controls_frame, fg_color="#1a1a1a", corner_radius=8, height=60)
        self.status_frame.pack(fill="x", pady=15, padx=15)
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Status: Running", 
                                      font=("Segoe UI", 18, "bold"),
                                      text_color="#4dff4d")
        self.status_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        options_frame = ctk.CTkFrame(controls_frame, fg_color="#1a1a1a", corner_radius=8)
        options_frame.pack(fill="x", pady=15, padx=15)
        
        left_options = ctk.CTkFrame(options_frame, fg_color="transparent")
        left_options.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        right_options = ctk.CTkFrame(options_frame, fg_color="transparent")
        right_options.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.auto_reconnect_var = ctk.BooleanVar(value=self.settings.auto_reconnect)
        ctk.CTkCheckBox(left_options, text="Auto Time Connect", variable=self.auto_reconnect_var,
                       command=self.toggle_auto_reconnect,
                       font=("Segoe UI", 13),
                       checkbox_height=22, checkbox_width=22,
                       corner_radius=3,
                       fg_color="#3d5af1", hover_color="#2d3ab1",
                       border_color="#555555").pack(pady=5, anchor="w")
        
        self.focus_only_var = ctk.BooleanVar(value=self.settings.focus_only)
        ctk.CTkCheckBox(right_options, text="Lag Only When Roblox Focused", variable=self.focus_only_var,
                       command=self.update_focus_only,
                       font=("Segoe UI", 13),
                       checkbox_height=22, checkbox_width=22,
                       corner_radius=3,
                       fg_color="#3d5af1", hover_color="#2d3ab1",
                       border_color="#555555").pack(pady=5, anchor="w")
        
        self.beep_var = ctk.BooleanVar(value=self.settings.beep)
        ctk.CTkCheckBox(left_options, text="Enable Beep", variable=self.beep_var,
                       command=self.update_beep,
                       font=("Segoe UI", 13),
                       checkbox_height=22, checkbox_width=22,
                       corner_radius=3,
                       fg_color="#3d5af1", hover_color="#2d3ab1",
                       border_color="#555555").pack(pady=5, anchor="w")
        
        button_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 20), padx=15)
        
        toggle_btn = ctk.CTkButton(button_frame, text="Toggle Connection", 
                                 command=lambda: self.toggle_roblox_internet(),
                                 fg_color="#3d5af1", hover_color="#2d3ab1",
                                 corner_radius=8, height=50,
                                 font=("Segoe UI", 16, "bold"))
        toggle_btn.pack(fill="x", pady=5)


    def setup_advanced_tab(self):
        container = ctk.CTkFrame(self.advanced_tab, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        
        main_frame = ctk.CTkScrollableFrame(container, fg_color="transparent",
                                        scrollbar_button_color="#3d5af1",
                                        scrollbar_button_hover_color="#2d3ab1")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        main_frame.grid_columnconfigure(0, weight=1)
        
        throttle_frame = ctk.CTkFrame(main_frame, fg_color="#212121", corner_radius=15)
        throttle_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        throttle_content = ctk.CTkFrame(throttle_frame, fg_color="#141414", corner_radius=10)
        throttle_content.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(throttle_content, text="Connection Throttle", font=("Segoe UI", 18, "bold"), 
                text_color="#ffffff").pack(pady=10)
        
        self.throttle_value_var = ctk.StringVar(value=f"{self.settings.throttle_percentage}%")
        
        ctk.CTkLabel(throttle_content, text="Bootleg Packet Throttle Level:", 
                font=("Segoe UI", 14),
                text_color="#ffffff").pack(pady=(10, 5), padx=15, anchor="w")
        
        slider_frame = ctk.CTkFrame(throttle_content, fg_color="#1a1a1a", corner_radius=8)
        slider_frame.pack(fill="x", pady=10, padx=15)
        
        self.throttle_slider = ctk.CTkSlider(slider_frame, from_=0, to=100, 
                                        number_of_steps=100, 
                                        command=self.update_throttle_value,
                                        button_color="#3d5af1",
                                        button_hover_color="#2d3ab1",
                                        progress_color="#3d5af1",
                                        height=20)
        self.throttle_slider.pack(side="left", fill="x", expand=True, padx=(15, 10), pady=15)
        try:
            self.throttle_slider.set(int(self.settings.throttle_percentage))
        except (TypeError, ValueError):
            self.throttle_slider.set(50)
        
        self.throttle_label = ctk.CTkLabel(slider_frame, textvariable=self.throttle_value_var,
                                        font=("Segoe UI", 16, "bold"),
                                        text_color="#ffffff",
                                        width=60)
        self.throttle_label.pack(side="right", padx=(0, 15), pady=15)
        
        interval_frame = ctk.CTkFrame(throttle_content, fg_color="#1a1a1a", corner_radius=8)
        interval_frame.pack(fill="x", pady=10, padx=15)
        
        ctk.CTkLabel(interval_frame, text="Throttle Interval (ms):", 
                font=("Segoe UI", 14),
                text_color="#ffffff").pack(side="left", padx=10, pady=10)
        
        self.interval_var = ctk.StringVar(value=str(self.settings.throttle_interval))
        interval_entry = ctk.CTkEntry(interval_frame, width=60, textvariable=self.interval_var)
        interval_entry.pack(side="right", padx=10, pady=10)
        interval_entry.bind("<FocusOut>", lambda e: self.update_throttle_interval())
        
        self.throttle_button = ctk.CTkButton(throttle_content, text="Start Throttling", 
                                        command=self.toggle_throttling, 
                                        fg_color="#8B3A3A", hover_color="#6B2D2D",
                                        corner_radius=8, height=40,
                                        font=("Segoe UI", 14, "bold"))
        self.throttle_button.pack(pady=15, padx=15, fill="x")
        
        process_container = ctk.CTkFrame(main_frame, fg_color="#212121", corner_radius=15)
        process_container.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        process_header = ctk.CTkFrame(process_container, fg_color="#141414", corner_radius=10)
        process_header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(process_header, text="Process Management", 
                font=("Segoe UI", 18, "bold"),
                text_color="#ffffff").pack(side="left", pady=10, padx=15)
        
        ctk.CTkButton(process_header, text="Refresh Processes", 
                    command=self.refresh_roblox_processes, 
                    width=150, height=30,
                    fg_color="#3d5af1", hover_color="#2d3ab1",
                    font=("Segoe UI", 13),
                    corner_radius=6).pack(side="right", pady=10, padx=15)
        
        process_content = ctk.CTkFrame(process_container, fg_color="#141414", corner_radius=10)
        process_content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.process_frame = ctk.CTkScrollableFrame(process_content, 
                                                fg_color="#1a1a1a",
                                                scrollbar_button_color="#3d5af1",
                                                scrollbar_button_hover_color="#2d3ab1",
                                                corner_radius=8,
                                                height=300)
        self.process_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.refresh_roblox_processes()

    def setup_settings_tab(self):
        container = ctk.CTkFrame(self.settings_tab, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        
        frame = ctk.CTkFrame(container, fg_color="#212121", corner_radius=15)
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(frame, fg_color="#141414", corner_radius=10)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="Application Settings", 
                font=("Segoe UI", 18, "bold"),
                text_color="#ffffff").pack(pady=10)
        
        settings_frame = ctk.CTkScrollableFrame(frame, fg_color="#141414", corner_radius=10,
                                            scrollbar_button_color="#3d5af1",
                                            scrollbar_button_hover_color="#2d3ab1")
        settings_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        sound_frame = ctk.CTkFrame(settings_frame, fg_color="#1a1a1a", corner_radius=8)
        sound_frame.pack(fill="x", pady=15, padx=15)
        
        ctk.CTkLabel(sound_frame, text="Sound Settings", 
                font=("Segoe UI", 16, "bold"),
                text_color="#ffffff").pack(pady=(10, 5), padx=15, anchor="w")
        
        block_freq_frame = ctk.CTkFrame(sound_frame, fg_color="#141414", corner_radius=5)
        block_freq_frame.pack(fill="x", pady=5, padx=15)
        
        ctk.CTkLabel(block_freq_frame, text="Block Sound Frequency:", 
                font=("Segoe UI", 14),
                text_color="#ffffff").pack(side="left", padx=10, pady=10)
        
        block_freq_slider = ctk.CTkSlider(block_freq_frame, from_=200, to=2000, 
                                        number_of_steps=18, 
                                        command=lambda v: self.update_sound_setting('block_sound_freq', v),
                                        button_color="#3d5af1",
                                        button_hover_color="#2d3ab1",
                                        progress_color="#3d5af1")
        block_freq_slider.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        try:
            block_freq_slider.set(int(self.settings.block_sound_freq))
        except (TypeError, ValueError):
            block_freq_slider.set(800)
        
        unblock_freq_frame = ctk.CTkFrame(sound_frame, fg_color="#141414", corner_radius=5)
        unblock_freq_frame.pack(fill="x", pady=5, padx=15)
        
        ctk.CTkLabel(unblock_freq_frame, text="Unblock Sound Frequency:", 
                font=("Segoe UI", 14),
                text_color="#ffffff").pack(side="left", padx=10, pady=10)
        
        unblock_freq_slider = ctk.CTkSlider(unblock_freq_frame, from_=200, to=2000, 
                                        number_of_steps=18, 
                                        command=lambda v: self.update_sound_setting('unblock_sound_freq', v),
                                        button_color="#3d5af1",
                                        button_hover_color="#2d3ab1",
                                        progress_color="#3d5af1")
        unblock_freq_slider.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        try:
            unblock_freq_slider.set(int(self.settings.unblock_sound_freq))
        except (TypeError, ValueError):
            unblock_freq_slider.set(1200)
        
        sound_duration_frame = ctk.CTkFrame(sound_frame, fg_color="#141414", corner_radius=5)
        sound_duration_frame.pack(fill="x", pady=5, padx=15)
        
        ctk.CTkLabel(sound_duration_frame, text="Sound Duration (ms):", 
                font=("Segoe UI", 14),
                text_color="#ffffff").pack(side="left", padx=10, pady=10)
        
        sound_duration_slider = ctk.CTkSlider(sound_duration_frame, from_=50, to=500, 
                                            number_of_steps=9, 
                                            command=lambda v: self.update_sound_setting('sound_duration', v),
                                            button_color="#3d5af1",
                                            button_hover_color="#2d3ab1",
                                            progress_color="#3d5af1")
        sound_duration_slider.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        try:
            sound_duration_slider.set(int(self.settings.sound_duration))
        except (TypeError, ValueError):
            sound_duration_slider.set(200)
        
        ui_settings_frame = ctk.CTkFrame(settings_frame, fg_color="#1a1a1a", corner_radius=8)
        ui_settings_frame.pack(fill="x", pady=15, padx=15)
        
        ctk.CTkLabel(ui_settings_frame, text="UI Settings", 
                font=("Segoe UI", 16, "bold"),
                text_color="#ffffff").pack(pady=(10, 5), padx=15, anchor="w")
        
        self.start_minimized_var = ctk.BooleanVar(value=self.settings.start_minimized)
        ctk.CTkCheckBox(ui_settings_frame, text="Start Minimized", variable=self.start_minimized_var,
                    command=self.update_start_minimized,
                    font=("Segoe UI", 13),
                    checkbox_height=22, checkbox_width=22,
                    corner_radius=3,
                    fg_color="#3d5af1", hover_color="#2d3ab1",
                    border_color="#555555").pack(pady=5, padx=15, anchor="w")
        
        self.enable_logging_var = ctk.BooleanVar(value=self.settings.enable_logging)
        ctk.CTkCheckBox(ui_settings_frame, text="Enable Console Logging", variable=self.enable_logging_var,
                    command=self.update_enable_logging,
                    font=("Segoe UI", 13),
                    checkbox_height=22, checkbox_width=22,
                    corner_radius=3,
                    fg_color="#3d5af1", hover_color="#2d3ab1",
                    border_color="#555555").pack(pady=5, padx=15, anchor="w")
                    
        refresh_interval_frame = ctk.CTkFrame(ui_settings_frame, fg_color="#141414", corner_radius=5)
        refresh_interval_frame.pack(fill="x", pady=5, padx=15)
        
        ctk.CTkLabel(refresh_interval_frame, text="Auto Refresh Interval (seconds):", 
                font=("Segoe UI", 14),
                text_color="#ffffff").pack(side="left", padx=10, pady=10)
        
        self.refresh_interval_var = ctk.StringVar(value=str(self.settings.auto_refresh_interval))
        refresh_entry = ctk.CTkEntry(refresh_interval_frame, width=60, textvariable=self.refresh_interval_var)
        refresh_entry.pack(side="right", padx=10, pady=10)
        refresh_entry.bind("<FocusOut>", lambda e: self.update_refresh_interval())
        
        firewall_frame = ctk.CTkFrame(settings_frame, fg_color="#1a1a1a", corner_radius=8)
        firewall_frame.pack(fill="x", pady=15, padx=15)
        
        ctk.CTkLabel(firewall_frame, text="Firewall Settings", 
                font=("Segoe UI", 16, "bold"),
                text_color="#ffffff").pack(pady=(10, 5), padx=15, anchor="w")
                
        rule_name_frame = ctk.CTkFrame(firewall_frame, fg_color="#141414", corner_radius=5)
        rule_name_frame.pack(fill="x", pady=5, padx=15)
        
        ctk.CTkLabel(rule_name_frame, text="Firewall Rule Prefix:", 
                font=("Segoe UI", 14),
                text_color="#ffffff").pack(side="left", padx=10, pady=10)
        
        self.rule_name_var = ctk.StringVar(value=self.settings.custom_rule_name)
        rule_name_entry = ctk.CTkEntry(rule_name_frame, width=200, textvariable=self.rule_name_var)
        rule_name_entry.pack(side="right", padx=10, pady=10)
        rule_name_entry.bind("<FocusOut>", lambda e: self.update_rule_name())
        
        about_frame = ctk.CTkFrame(settings_frame, fg_color="#1a1a1a", corner_radius=8)
        about_frame.pack(fill="x", pady=15, padx=15)
        
        ctk.CTkLabel(about_frame, text="About", 
                font=("Segoe UI", 16, "bold"),
                text_color="#ffffff").pack(pady=(10, 5), padx=15, anchor="w")
        
        ctk.CTkLabel(about_frame, text="Seven's Advanced Lag Switch v3", 
                font=("Segoe UI", 14),
                text_color="#cccccc").pack(pady=5, padx=15)
        
        ctk.CTkLabel(about_frame, text="Enhanced GUI Edition with Advanced Keybinds", 
                font=("Segoe UI", 12),
                text_color="#aaaaaa").pack(pady=(0, 10), padx=15)

    def update_throttle_value(self, value):
        perc = int(value)
        self.throttle_value_var.set(f"{perc}%")
        self.settings.throttle_percentage = perc
        self.settings.save()
        
    def update_throttle_interval(self):
        try:
            value = max(10, int(self.interval_var.get()))
            self.interval_var.set(str(value))
            self.settings.throttle_interval = value
            self.settings.save()
        except ValueError:
            self.interval_var.set(str(self.settings.throttle_interval))
            
    def update_refresh_interval(self):
        try:
            value = max(5, int(self.refresh_interval_var.get()))
            self.refresh_interval_var.set(str(value))
            self.settings.auto_refresh_interval = value
            self.settings.save()
            self.cache_roblox_processes()
        except ValueError:
            self.refresh_interval_var.set(str(self.settings.auto_refresh_interval))
            
    def update_rule_name(self):
        new_name = self.rule_name_var.get().strip()
        if new_name:
            self.settings.custom_rule_name = new_name
            self.rule_name_prefix = new_name
            self.settings.save()
            self.log(f"Firewall rule prefix updated to: {new_name}")
        else:
            self.rule_name_var.set(self.settings.custom_rule_name)
            
    def update_focus_only(self):
        self.settings.focus_only = self.focus_only_var.get()
        self.settings.save()
        
    def update_beep(self):
        self.settings.beep = self.beep_var.get()
        self.settings.save()
        
    def update_start_minimized(self):
        self.settings.start_minimized = self.start_minimized_var.get()
        self.settings.save()
        
    def update_enable_logging(self):
        self.settings.enable_logging = self.enable_logging_var.get()
        self.settings.save()

    def update_sound_setting(self, setting_name, value):
        setattr(self.settings, setting_name, int(value))
        self.settings.save()

    def cache_roblox_processes(self):
        self.cached_processes = self.find_all_roblox_processes()
        self.root.after(self.settings.auto_refresh_interval * 1000, self.cache_roblox_processes)

    def refresh_roblox_processes(self):
        for w in self.process_frame.winfo_children():
            w.destroy()
        self.cached_processes = self.find_all_roblox_processes()
        if not self.cached_processes:
            ctk.CTkLabel(self.process_frame, text="No Roblox processes found", 
                       font=("Segoe UI", 14),
                       text_color="#ff6666").pack(pady=15)
            return
        self.process_vars = {}
        for proc_name, proc_path in self.cached_processes.items():
            var = ctk.BooleanVar(value=True)
            self.process_vars[proc_path] = var
            row = ctk.CTkFrame(self.process_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkCheckBox(row, text="", variable=var,
                           checkbox_height=22, checkbox_width=22,
                           corner_radius=3,
                           fg_color="#3d5af1", hover_color="#2d3ab1",
                           border_color="#555555").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=f"{proc_name} ({os.path.basename(proc_path)})", 
                       font=("Segoe UI", 12),
                       text_color="#ffffff").pack(side="left", padx=5)

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
            self.throttle_button.configure(text="Start Throttling", fg_color="#8B3A3A", hover_color="#6B2D2D")
        else:
            self.start_throttling()
            self.throttle_button.configure(text="Stop Throttling", fg_color="#3B8A3A", hover_color="#2D6B2D")

    def start_throttling(self):
        if self.throttling_active:
            return
        if self.settings.throttle_percentage == 100:
            self.toggle_roblox_internet()
            return
        self.throttling_active = True
        self.throttling_thread = threading.Thread(target=self.throttle_connection, daemon=True)
        self.throttling_thread.start()
        self.status_label.configure(text=f"Status: Throttling ({self.settings.throttle_percentage}%)")
        self.log("Started throttling")

    def stop_throttling(self):
        self.throttling_active = False
        self.unblock_all_roblox()
        if self.throttling_thread:
            self.throttling_thread.join(timeout=1)
            self.throttling_thread = None
        self.status_label.configure(text="Status: Running")
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
        if not hasattr(self, 'process_vars') or not self.process_vars:
            processes = list(self.cached_processes.values())
        else:
            processes = [p for p,v in self.process_vars.items() if v.get()]
        if not processes:
            self.cached_processes = self.find_all_roblox_processes()
            processes = list(self.cached_processes.values())
        for p in processes:
            name = os.path.basename(p)
            rname = f"{self.rule_name_prefix}_{name}"
            self.block_commands.extend([
                f'netsh advfirewall firewall add rule name="{rname}" dir=out program="{p}" action=block',
                f'netsh advfirewall firewall add rule name="{rname}" dir=in program="{p}" action=block'])
            self.unblock_commands.extend([
                f'netsh advfirewall firewall delete rule name="{rname}" dir=out',
                f'netsh advfirewall firewall delete rule name="{rname}" dir=in'])
            
    def start_key_listener_thread(self):
        if self.key_listener_thread and self.key_listener_thread.is_alive():
            self.running = False
            self.key_listener_thread.join(timeout=1)
        self.running = True
        self.key_listener_thread = threading.Thread(target=self.key_listener, daemon=True)
        self.key_listener_thread.start()

    def active_window_is_roblox(self):
        try:
            h = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(h)
            name = psutil.Process(pid).name()
            return 'roblox' in name.lower()
        except Exception:
            return False

    def key_listener(self):
        while self.running:
            try:
                if self.focus_only_var.get() and not self.active_window_is_roblox():
                    time.sleep(0.05)
                    continue
                if self.hotkey_pressed():
                    ct = time.time()
                    if ct - self.last_toggle_time > 0.2:
                        self.last_toggle_time = ct
                        self.toggle_roblox_internet()
                time.sleep(0.01)
            except Exception:
                time.sleep(0.01)

    def hotkey_pressed(self):
        parts = self.settings.hotkey.lower().split('+')
        checks = []
        for part in parts:
            if part.startswith('mouse_'):
                button = part.split('_', 1)[1]                  
                checks.append(mouse.is_pressed(button))
            else:
                checks.append(
                    keyboard.is_pressed(self.special_key_map.get(part, part))
                )
        return all(checks)


    def start_key_listener(self):
        if self.listening_for_key:
            return

        self.listening_for_key = True
        self.hotkey_button.configure(text="Press keys now...")
        threading.Thread(target=self.listen_for_key, daemon=True).start()

    def listen_for_key(self):
        recorded = []        
        current = set()      
        finalize_id = None   
        cancel_id = None     

        modifiers = {
            "ctrl", "control", "alt", "shift", "windows", "win",
            "right ctrl", "right control", "right alt", "right shift",
            "left ctrl", "left control", "left alt", "left shift"
        }

        def update_button_text():
            if not recorded:
                text = "Press keys now..."
            elif current & modifiers:
                text = "+".join(recorded) + "+"
            else:
                text = "+".join(recorded)
            self.root.after(0, lambda: self.hotkey_button.configure(text=f"Current: {text}"))

        def do_finalize():
            nonlocal finalize_id, cancel_id
            finalize_id = None
            if cancel_id:
                self.root.after_cancel(cancel_id)
            if not recorded:
                self.listening_for_key = False
                return
            hotkey = "+".join(recorded)
            self.settings.hotkey = hotkey
            self.settings.save()
            self.root.after(0, lambda: self.hotkey_button.configure(text=f"Keybind: {hotkey}"))
            self.log(f"New keybind set: {hotkey}")
            self.listening_for_key = False

        def do_cancel():
            nonlocal cancel_id, finalize_id
            cancel_id = None
            if self.listening_for_key:
                self.listening_for_key = False
                self.log("Keybind recording timed out")
                self.root.after(0, lambda: self.hotkey_button.configure(
                    text=f"Keybind: {self.settings.hotkey}"
                ))
            if finalize_id:
                self.root.after_cancel(finalize_id)

        def schedule_finalize():
            nonlocal finalize_id
            if finalize_id:
                self.root.after_cancel(finalize_id)
            finalize_id = self.root.after(300, do_finalize)

        def on_press(evt):
            if not self.listening_for_key:
                return
            name = evt.name.lower()
            if name in ("mouse left", "left mouse"):
                self.root.after(0, lambda: self.hotkey_button.configure(text="Left click not allowed"))
                self.root.after(1500, update_button_text)
                return
            if name not in current:
                current.add(name)
                if name not in recorded:
                    recorded.append(name)
                update_button_text()
            schedule_finalize()

        def on_release(evt):
            if not self.listening_for_key:
                return
            name = evt.name.lower()
            if name in current:
                current.remove(name)
            update_button_text()
            if not current:
                schedule_finalize()

        keyboard.unhook_all()
        keyboard.on_press(on_press)
        keyboard.on_release(on_release)

        cancel_id = self.root.after(5000, do_cancel)

        MOUSE_BUTTONS = (
            "right", "middle",
            "x", "x2", 
            "button4", "button5", "back", "forward"
        )

        while self.listening_for_key:
            for btn in MOUSE_BUTTONS:
                if mouse.is_pressed(btn):
                    name = f"mouse_{btn}"
                    if name not in current:
                        current.add(name)
                        recorded.append(name)
                        update_button_text()
                        schedule_finalize()
                    time.sleep(0.3)
            time.sleep(0.05)

        keyboard.unhook_all()

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
                self.root.after_cancel(self.auto_reconnect_timer)
            self.auto_reconnect_timer = self.root.after(9000, self.auto_reconnect)

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
            self.root.after_cancel(self.auto_reconnect_timer)
            self.auto_reconnect_timer = None

    def unblock_all_roblox(self):
        self.unblock_all_roblox_fast()

    def auto_reconnect(self):
        if self.blocked:
            self.unblock_all_roblox_fast()
            if self.beep_var.get():
                winsound.Beep(int(self.settings.unblock_sound_freq), int(self.settings.sound_duration))
        self.auto_reconnect_timer = None

    def toggle_roblox_internet(self):
        try:
            if self.blocked:
                self.unblock_all_roblox_fast()
                if self.beep_var.get():
                    winsound.Beep(int(self.settings.unblock_sound_freq), int(self.settings.sound_duration))
            else:
                if not self.cached_processes and not self.find_all_roblox_processes():
                    ctypes.windll.user32.MessageBoxW(0, 'No Roblox processes found. Please make sure Roblox is running.', 'Error', 0)
                    return
                if not self.block_commands:
                    self.prepare_firewall_rules()
                self.block_selected_roblox_fast()
                if self.beep_var.get():
                    winsound.Beep(int(self.settings.block_sound_freq), int(self.settings.sound_duration))
        except Exception as e:
            self.log(f"Error: {e}")

    def update_status(self):
        if self.throttling_active:
            self.status_label.configure(text=f"Status: Throttling ({self.settings.throttle_percentage}%)")
            self.status_label.configure(text_color="#ffcc00")
        elif self.blocked:
            self.status_label.configure(text="Status: Blocked") 
            self.status_label.configure(text_color="#ff6666")
        else:
            self.status_label.configure(text="Status: Unblocked")
            self.status_label.configure(text_color="#4dff4d")

    def change_theme(self, t):
        self.settings.theme = t
        self.settings.save()
        ctk.set_appearance_mode(t)

    def on_closing(self):
        self.running = False
        if self.throttling_active:
            self.stop_throttling()
        self.unblock_all_roblox_fast()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

    def toggle_auto_reconnect(self):
        self.settings.auto_reconnect = self.auto_reconnect_var.get()
        self.settings.save()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


if __name__ == '__main__':
    if is_admin():
        RobloxLagSwitch().run()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, __file__, None, 1)