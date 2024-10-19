# settings.py

import json
import os
import logging

class Settings:
    def __init__(self):
        self.settings_file = 'settings.json'
        self.initialize_defaults()
        self.load_settings()

    def initialize_defaults(self):
        # Screen settings
        self.dual_screen = True
        self.screen_width_total = 2960  # 1480 * 2
        self.screen_height = 320
        self.screen_width_single = 1480
        self.bg_color = (0, 0, 0)
        # Network settings
        self.mqtt_broker = 'localhost'
        self.mqtt_port = 1883
        self.mqtt_topic = 'bubble_hockey/game_status'
        self.web_server_port = 5000
        # Game settings
        self.period_length = 180
        self.overtime_length = 180
        self.intermission_length = 60
        self.power_up_frequency = 30
        self.taunt_frequency = 60
        self.taunts_enabled = True
        self.random_sounds_enabled = True
        self.random_sound_frequency = 60
        # Combo goal settings
        self.combo_goals_enabled = True
        self.combo_time_window = 30
        self.combo_reward_type = 'extra_point'
        self.combo_max_stack = 5
        # Theme settings
        self.current_theme = 'default'
        self.classic_mode_theme_selection = False
        # GPIO pin configurations
        self.gpio_pins = {
            'goal_sensor_red': 17,
            'goal_sensor_blue': 27,
            'puck_sensor_red': 22,
            'puck_sensor_blue': 23
        }
        # Other settings
        self.clock_tick = 0

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except json.JSONDecodeError as e:
                logging.error(f'Error decoding settings file: {e}')
                logging.info('Using default settings.')
                self.save_settings()
        else:
            self.save_settings()

    def save_settings(self):
        data = {key: value for key, value in self.__dict__.items() if not key.startswith('_')}
        with open(self.settings_file, 'w') as f:
            json.dump(data, f, indent=4)
