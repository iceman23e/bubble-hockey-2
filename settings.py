# settings.py

import json
import os

class Settings:
    def __init__(self):
        self.settings_file = 'settings.json'
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
                # Load settings from JSON
                # Screen settings
                self.screen_width = data.get('screen_width', 1480)
                self.screen_height = data.get('screen_height', 320)
                self.bg_color = tuple(data.get('bg_color', [0, 0, 0]))
                # Network settings
                self.mqtt_broker = data.get('mqtt_broker', 'localhost')
                self.mqtt_port = data.get('mqtt_port', 1883)
                self.mqtt_topic = data.get('mqtt_topic', 'bubble_hockey/game_status')
                self.web_server_port = data.get('web_server_port', 5000)
                # Game settings
                self.period_length = data.get('period_length', 180)
                self.overtime_length = data.get('overtime_length', 180)
                self.intermission_length = data.get('intermission_length', 60)
                self.power_up_frequency = data.get('power_up_frequency', 30)
                self.taunt_frequency = data.get('taunt_frequency', 60)
                # Theme settings
                self.current_theme = data.get('current_theme', 'default')
        else:
            # Set default settings
            self.screen_width = 1480
            self.screen_height = 320
            self.bg_color = (0, 0, 0)
            self.mqtt_broker = 'localhost'
            self.mqtt_port = 1883
            self.mqtt_topic = 'bubble_hockey/game_status'
            self.web_server_port = 5000
            self.period_length = 180
            self.overtime_length = 180
            self.intermission_length = 60
            self.power_up_frequency = 30
            self.taunt_frequency = 60
            self.current_theme = 'default'
            # Save default settings
            self.save_settings()

    def save_settings(self):
        data = {
            # Screen settings
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'bg_color': list(self.bg_color),
            # Network settings
            'mqtt_broker': self.mqtt_broker,
            'mqtt_port': self.mqtt_port,
            'mqtt_topic': self.mqtt_topic,
            'web_server_port': self.web_server_port,
            # Game settings
            'period_length': self.period_length,
            'overtime_length': self.overtime_length,
            'intermission_length': self.intermission_length,
            'power_up_frequency': self.power_up_frequency,
            'taunt_frequency': self.taunt_frequency,
            # Theme settings
            'current_theme': self.current_theme,
        }
        with open(self.settings_file, 'w') as f:
            json.dump(data, f, indent=4)
