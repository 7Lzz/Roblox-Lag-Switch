from dataclasses import dataclass
from typing import Dict, Any
import json
from pathlib import Path

@dataclass
class Settings:
    DEFAULT_SETTINGS = {
        "hotkey": "ctrl+e",
        "block_sound_freq": "500",
        "unblock_sound_freq": "1000",
        "sound_duration": "300",
        "theme": "dark",
        "auto_reconnect": False,
        "throttle_percentage": 50,
        "throttle_interval": 100,
        "selected_processes": []
    }
    
    hotkey: str
    block_sound_freq: str
    unblock_sound_freq: str
    sound_duration: str
    theme: str
    auto_reconnect: bool
    throttle_percentage: int
    throttle_interval: int
    selected_processes: list
    
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
                    return cls(
                        hotkey=data.get('hotkey', cls.DEFAULT_SETTINGS['hotkey']),
                        block_sound_freq=data.get('block_sound_freq', cls.DEFAULT_SETTINGS['block_sound_freq']),
                        unblock_sound_freq=data.get('unblock_sound_freq', cls.DEFAULT_SETTINGS['unblock_sound_freq']),
                        sound_duration=data.get('sound_duration', cls.DEFAULT_SETTINGS['sound_duration']),
                        theme=data.get('theme', cls.DEFAULT_SETTINGS['theme']),
                        auto_reconnect=data.get('auto_reconnect', cls.DEFAULT_SETTINGS['auto_reconnect']),
                        throttle_percentage=data.get('throttle_percentage', cls.DEFAULT_SETTINGS['throttle_percentage']),
                        throttle_interval=data.get('throttle_interval', cls.DEFAULT_SETTINGS['throttle_interval']),
                        selected_processes=data.get('selected_processes', cls.DEFAULT_SETTINGS['selected_processes'])
                    )
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
        """Update the list of selected processes"""
        self.selected_processes = processes
        self.save()