import psutil
import ctypes
import os
import winsound
import sys
import keyboard
import threading
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from settings import Settings
import time
import subprocess
from subprocess import CREATE_NO_WINDOW
import re

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
        self.rule_name_prefix = "BlockRobloxInternet"
        self.cached_processes = {}
        self.setup_gui()

        self.block_commands = []
        self.unblock_commands = []
        
    def setup_gui(self):
        ctk.set_appearance_mode(self.settings.theme)
        self.root = ctk.CTk()
        self.root.title("Seven's Advanced Lag Switch")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Set window icon
        if hasattr(sys, '_MEIPASS'):  # Check if running as PyInstaller executable
            icon_path = os.path.join(sys._MEIPASS, "icons", "switch.ico")
        else:
            icon_path = "icons/switch.ico"
        
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.simple_tab = self.tabview.add("Simple")
        self.advanced_tab = self.tabview.add("Advanced")
        
        self.tabview.set("Simple")
        
        self.setup_simple_tab()
        self.setup_advanced_tab()
        
        self.cache_roblox_processes()
        
        self.start_key_listener_thread()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_simple_tab(self):
        frame = ctk.CTkFrame(self.simple_tab)
        frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Hotkey setting
        ctk.CTkLabel(frame, text="Hotkey:").pack(pady=5)
        self.hotkey_button = ctk.CTkButton(
            frame, 
            text=f"Keybind: {self.settings.hotkey}",
            command=self.start_key_listener
        )
        self.hotkey_button.pack(pady=5)
        
        self.status_label = ctk.CTkLabel(frame, text="Status: Running")
        self.status_label.pack(pady=10)
        
        theme_var = tk.StringVar(value=self.settings.theme)
        ctk.CTkOptionMenu(frame, values=["dark", "light"], 
                         command=self.change_theme,
                         variable=theme_var).pack(pady=10)
        
        self.auto_reconnect_var = ctk.BooleanVar(value=self.settings.auto_reconnect)
        self.auto_reconnect_checkbox = ctk.CTkCheckBox(
            frame,
            text="Auto Time Connect",
            variable=self.auto_reconnect_var,
            command=self.toggle_auto_reconnect
        )
        self.auto_reconnect_checkbox.pack(pady=10)
        
        ctk.CTkButton(
            frame,
            text="Toggle Connection",
            command=lambda: self.toggle_roblox_internet(),
            fg_color="#1f538d",
            hover_color="#14375e"
        ).pack(pady=10)
        
        info_text = """Simple Mode: Blocks all Roblox processes
Press the hotkey or use the button to toggle"""
        ctk.CTkLabel(frame, text=info_text, font=("Arial", 10)).pack(pady=10)
    
    def setup_advanced_tab(self):
        frame = ctk.CTkFrame(self.advanced_tab)
        frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        throttle_frame = ctk.CTkFrame(frame)
        throttle_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(throttle_frame, text="Connection Throttle", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.throttle_value_var = ctk.StringVar(value=f"{self.settings.throttle_percentage}%")
        ctk.CTkLabel(throttle_frame, text="Bootleg Packet Throttle Level:").pack(pady=5)
        
        slider_frame = ctk.CTkFrame(throttle_frame)
        slider_frame.pack(fill="x", pady=5)
        
        self.throttle_slider = ctk.CTkSlider(
            slider_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self.update_throttle_value
        )
        self.throttle_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.throttle_slider.set(self.settings.throttle_percentage)
        
        self.throttle_label = ctk.CTkLabel(slider_frame, textvariable=self.throttle_value_var)
        self.throttle_label.pack(side="right", padx=5)
        
        self.throttle_button = ctk.CTkButton(
            throttle_frame,
            text="Start Throttling",
            command=self.toggle_throttling,
            fg_color="#8B3A3A", 
            hover_color="#6B2D2D"
        )
        self.throttle_button.pack(pady=10)
        
        process_frame = ctk.CTkFrame(frame)
        process_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(process_frame, text="Process Management", font=("Arial", 14, "bold")).pack(pady=5)
        
        refresh_btn = ctk.CTkButton(
            process_frame,
            text="Refresh Processes",
            command=self.refresh_roblox_processes,
            width=120
        )
        refresh_btn.pack(pady=5)
        
        self.process_frame = ctk.CTkScrollableFrame(process_frame, height=100)
        self.process_frame.pack(fill="x", pady=5)
        
        self.refresh_roblox_processes()
    
    def cache_roblox_processes(self):
        """Cache all Roblox processes on startup and periodically update the cache"""
        self.cached_processes = self.find_all_roblox_processes()
        self.root.after(30000, self.cache_roblox_processes)
    
    def refresh_roblox_processes(self):
        for widget in self.process_frame.winfo_children():
            widget.destroy()
        
        self.cached_processes = self.find_all_roblox_processes()
        
        if not self.cached_processes:
            ctk.CTkLabel(self.process_frame, text="No Roblox processes found").pack(pady=5)
            return
        
        self.process_vars = {}
        for proc_name, proc_path in self.cached_processes.items():
            var = ctk.BooleanVar(value=True) 
            self.process_vars[proc_path] = var
            
            proc_frame = ctk.CTkFrame(self.process_frame)
            proc_frame.pack(fill="x", pady=2)
            
            checkbox = ctk.CTkCheckBox(
                proc_frame,
                text="",
                variable=var
            )
            checkbox.pack(side="left", padx=5)
            
            ctk.CTkLabel(proc_frame, text=f"{proc_name} ({os.path.basename(proc_path)})").pack(side="left", padx=5)
    
    def find_all_roblox_processes(self):
        roblox_processes = {}
        roblox_pattern = re.compile(r'Roblox.*\.exe', re.IGNORECASE)
        
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['name'] and roblox_pattern.match(proc.info['name']):
                    roblox_processes[proc.info['name']] = proc.info['exe']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return roblox_processes
    
    def update_throttle_value(self, value):
        percentage = int(value)
        self.throttle_value_var.set(f"{percentage}%")
        self.settings.throttle_percentage = percentage
        self.settings.save()
    
    def toggle_throttling(self):
        if self.throttling_active:
            self.stop_throttling()
            self.throttle_button.configure(
                text="Start Throttling",
                fg_color="#8B3A3A",
                hover_color="#6B2D2D"
            )
        else:
            self.start_throttling()
            self.throttle_button.configure(
                text="Stop Throttling",
                fg_color="#3B8A3A",
                hover_color="#2D6B2D"
            )
    
    def start_throttling(self):
        if self.throttling_active:
            return
            
        percentage = self.settings.throttle_percentage
        
        if percentage == 100:
            self.toggle_roblox_internet()
            return
            
        self.throttling_active = True
        
        self.throttling_thread = threading.Thread(target=self.throttle_connection, daemon=True)
        self.throttling_thread.start()
        
        self.status_label.configure(text=f"Status: Throttling ({percentage}%)")
    
    def stop_throttling(self):
        self.throttling_active = False
        
        self.unblock_all_roblox()
        
        if self.throttling_thread:
            self.throttling_thread.join(timeout=1)
            self.throttling_thread = None
        
        self.status_label.configure(text="Status: Running")
    
    def throttle_connection(self):
        """
        Packet throttling by toggling the firewall block on and off
        based on the throttle percentage. (Bootleg)
        """
        percentage = self.settings.throttle_percentage
        
        block_time = 0.05 * (percentage / 100)
        unblock_time = 0.05 * (1 - percentage / 100) 
        
        self.prepare_firewall_rules()
        
        while self.throttling_active:
            self.block_selected_roblox_fast()
            time.sleep(block_time)
            
            if not self.throttling_active:
                break
            
            self.unblock_all_roblox_fast()
            time.sleep(unblock_time)
    
    def prepare_firewall_rules(self):
        """Prepare firewall rules in advance for faster toggling"""
        self.block_commands = []
        self.unblock_commands = []
        
        if not hasattr(self, 'process_vars') or not self.process_vars:
            processes = list(self.cached_processes.values())
        else:
            processes = [path for path, var in self.process_vars.items() if var.get()]
        
        if not processes:
            self.cached_processes = self.find_all_roblox_processes()
            processes = list(self.cached_processes.values())
            
        for proc_path in processes:
            base_name = os.path.basename(proc_path)
            rule_name = f"{self.rule_name_prefix}_{base_name}"
            
            self.block_commands.append(
                f'netsh advfirewall firewall add rule name="{rule_name}" dir=out program="{proc_path}" action=block'
            )
            self.block_commands.append(
                f'netsh advfirewall firewall add rule name="{rule_name}" dir=in program="{proc_path}" action=block'
            )
            
            self.unblock_commands.append(
                f'netsh advfirewall firewall delete rule name="{rule_name}" dir=out'
            )
            self.unblock_commands.append(
                f'netsh advfirewall firewall delete rule name="{rule_name}" dir=in'
            )
    
    def start_key_listener_thread(self):
        if self.key_listener_thread and self.key_listener_thread.is_alive():
            self.running = False
            self.key_listener_thread.join(timeout=1)
        
        self.running = True
        self.key_listener_thread = threading.Thread(target=self.key_listener, daemon=True)
        self.key_listener_thread.start()

    def key_listener(self):
        while self.running:
            try:
                if keyboard.is_pressed(self.settings.hotkey):
                    current_time = time.time()
                    if current_time - self.last_toggle_time > 0.2:
                        self.last_toggle_time = current_time
                        self.toggle_roblox_internet()
                time.sleep(0.01)
            except:
                time.sleep(0.01)
                continue
    
    def block_selected_roblox_fast(self):
        """Block only the selected Roblox processes using precomputed commands"""
        if not hasattr(self, 'block_commands') or not self.block_commands:
            self.prepare_firewall_rules()
            
        if not self.block_commands:
            return
            
        cmd = " && ".join(self.block_commands)
        subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW, shell=True)
        
        with open('C:\\1.txt', 'w') as f:
            f.write('Blocked Roblox internet access')
        
        self.blocked = True
        self.update_status()
        
        if self.settings.auto_reconnect and not self.throttling_active:
            if self.auto_reconnect_timer:
                self.root.after_cancel(self.auto_reconnect_timer)
            self.auto_reconnect_timer = self.root.after(9000, self.auto_reconnect)
    
    def block_selected_roblox(self):
        """Legacy blocking method - use block_selected_roblox_fast instead"""
        self.block_selected_roblox_fast()
    
    def unblock_all_roblox_fast(self):
        """Unblock Roblox processes using precomputed commands"""
        if not hasattr(self, 'unblock_commands') or not self.unblock_commands:
            self.prepare_firewall_rules()
            
        if not self.unblock_commands:
            return
            
        cmd = " && ".join(self.unblock_commands)
        subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW, shell=True)
        
        if os.path.exists('C:\\1.txt'):
            os.remove('C:\\1.txt')
        
        self.blocked = False
        self.update_status()
        
        if self.auto_reconnect_timer:
            self.root.after_cancel(self.auto_reconnect_timer)
            self.auto_reconnect_timer = None
    
    def unblock_all_roblox(self):
        """Legacy unblocking method - use unblock_all_roblox_fast instead"""
        self.unblock_all_roblox_fast()
    
    def auto_reconnect(self):
        if self.blocked:
            self.unblock_all_roblox_fast()
            winsound.Beep(int(self.settings.unblock_sound_freq), int(self.settings.sound_duration))
        self.auto_reconnect_timer = None

    def toggle_roblox_internet(self):
        try:
            if os.path.exists('C:\\1.txt'):
                if not hasattr(self, 'unblock_commands') or not self.unblock_commands:
                    self.prepare_firewall_rules()
                self.unblock_all_roblox_fast()
                winsound.Beep(int(self.settings.unblock_sound_freq), int(self.settings.sound_duration))
            else:
                if not self.cached_processes:
                    processes = self.find_all_roblox_processes()
                    if not processes:
                        ctypes.windll.user32.MessageBoxW(0, 'No Roblox processes found. Please make sure Roblox is running.', 'Error', 0)
                        return
                
                if not hasattr(self, 'block_commands') or not self.block_commands:
                    self.prepare_firewall_rules()
                self.block_selected_roblox_fast()
                winsound.Beep(int(self.settings.block_sound_freq), int(self.settings.sound_duration))
        except Exception as e:
            print(f"Error in toggle_roblox_internet: {e}")
    
    def update_status(self):
        if self.throttling_active:
            self.status_label.configure(text=f"Status: Throttling ({self.settings.throttle_percentage}%)")
        else:
            status = "Blocked" if self.blocked else "Unblocked"
            self.status_label.configure(text=f"Status: {status}")
    
    def change_theme(self, new_theme):
        self.settings.theme = new_theme
        self.settings.save()
        ctk.set_appearance_mode(new_theme)
    
    def on_closing(self):
        self.running = False
        
        if self.throttling_active:
            self.stop_throttling()
        
        self.unblock_all_roblox_fast()
        
        self.root.destroy()
        
    def run(self):
        self.root.mainloop()
    
    def start_key_listener(self):
        if self.listening_for_key:
            return
        
        self.listening_for_key = True
        self.hotkey_button.configure(text="Listening...")

        self.listener_thread = threading.Thread(target=self.listen_for_key, daemon=True)
        self.listener_thread.start()
    
    def listen_for_key(self):
        start_time = time.time()
        recorded_keys = []
        
        while self.listening_for_key and time.time() - start_time < 5:
            event = keyboard.read_event(suppress=True)
            if event.event_type == keyboard.KEY_DOWN:
                key_name = event.name
                if key_name not in recorded_keys:
                    recorded_keys.append(key_name)
                
                new_hotkey = "+".join(recorded_keys)
                
                self.root.after(0, lambda: self.hotkey_button.configure(
                    text=f"Keybind: {new_hotkey}"
                ))
                
                if len(recorded_keys) >= 1:
                    self.settings.hotkey = new_hotkey
                    self.settings.save()
                    self.listening_for_key = False
                    self.start_key_listener_thread()
                    return
        
        if self.listening_for_key:
            self.root.after(0, lambda: self.hotkey_button.configure(
                text=f"Keybind: {self.settings.hotkey}"
            ))
            self.listening_for_key = False
    
    def toggle_auto_reconnect(self):
        self.settings.auto_reconnect = self.auto_reconnect_var.get()
        self.settings.save()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == '__main__':
    if is_admin():
        app = RobloxLagSwitch()
        app.run()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, __file__, None, 1)