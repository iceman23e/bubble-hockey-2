# settings.py

import json
import os
import logging

class Settings:
    def __init__(self):
        self.settings_file = 'settings.json'
        # Initialize default settings
        self.initialize_defaults()
        # Load settings from file
        self.load_settings()

    def initialize_defaults(self):
        # Screen settings
        self.screen_width = 1480
        self.screen_height = 320
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
        # New settings
        self.taunts_enabled = True
        self.random_sounds_enabled = True
        self.random_sound_min_interval = 5   # Minimum interval in seconds
        self.random_sound_max_interval = 30  # Maximum interval in seconds
        # Combo goal settings
        self.combo_goals_enabled = True
        self.combo_time_window = 30
        self.combo_reward_type = 'extra_point'  # Options: 'extra_point', 'power_up'
        self.combo_max_stack = 5
        # Theme settings
        self.current_theme = 'default'
        self.classic_mode_theme_selection = False  # New setting to control theme selection in Classic mode
        # GPIO pin configurations
        self.gpio_pins = {
            'goal_sensor_red': 17,       # Replace with actual GPIO pin numbers
            'goal_sensor_blue': 27,
            'puck_sensor_red': 22,
            'puck_sensor_blue': 23
        }
        # Other settings
        self.clock_tick = 0  # To store clock tick time for animations

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    # Load settings from JSON
                    # Screen settings
                    self.screen_width = data.get('screen_width', self.screen_width)
                    self.screen_height = data.get('screen_height', self.screen_height)
                    self.bg_color = tuple(data.get('bg_color', self.bg_color))
                    # Network settings
                    self.mqtt_broker = data.get('mqtt_broker', self.mqtt_broker)
                    self.mqtt_port = data.get('mqtt_port', self.mqtt_port)
                    self.mqtt_topic = data.get('mqtt_topic', self.mqtt_topic)
                    self.web_server_port = data.get('web_server_port', self.web_server_port)
                    # Game settings
                    self.period_length = data.get('period_length', self.period_length)
                    self.overtime_length = data.get('overtime_length', self.overtime_length)
                    self.intermission_length = data.get('intermission_length', self.intermission_length)
                    self.power_up_frequency = data.get('power_up_frequency', self.power_up_frequency)
                    self.taunt_frequency = data.get('taunt_frequency', self.taunt_frequency)
                    # New settings
                    self.taunts_enabled = data.get('taunts_enabled', self.taunts_enabled)
                    self.random_sounds_enabled = data.get('random_sounds_enabled', self.random_sounds_enabled)
                    self.random_sound_min_interval = data.get('random_sound_min_interval', self.random_sound_min_interval)
                    self.random_sound_max_interval = data.get('random_sound_max_interval', self.random_sound_max_interval)
                    # Combo goal settings
                    self.combo_goals_enabled = data.get('combo_goals_enabled', self.combo_goals_enabled)
                    self.combo_time_window = data.get('combo_time_window', self.combo_time_window)
                    self.combo_reward_type = data.get('combo_reward_type', self.combo_reward_type)
                    self.combo_max_stack = data.get('combo_max_stack', self.combo_max_stack)
                    # Theme settings
                    self.current_theme = data.get('current_theme', self.current_theme)
                    self.classic_mode_theme_selection = data.get('classic_mode_theme_selection', self.classic_mode_theme_selection)
                    # GPIO pin configurations
                    self.gpio_pins = data.get('gpio_pins', self.gpio_pins)
                    # Other settings
                    self.clock_tick = 0  # Reset clock tick
            except json.JSONDecodeError as e:
                logging.error(f'Error decoding settings file: {e}')
                logging.info('Using default settings.')
                self.initialize_defaults()
                self.save_settings()
        else:
            # Save default settings if file doesn't exist
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
            # New settings
            'taunts_enabled': self.taunts_enabled,
            'random_sounds_enabled': self.random_sounds_enabled,
            'random_sound_min_interval': self.random_sound_min_interval,
            'random_sound_max_interval': self.random_sound_max_interval,
            # Combo goal settings
            'combo_goals_enabled': self.combo_goals_enabled,
            'combo_time_window': self.combo_time_window,
            'combo_reward_type': self.combo_reward_type,
            'combo_max_stack': self.combo_max_stack,
            # Theme settings
            'current_theme': self.current_theme,
            'classic_mode_theme_selection': self.classic_mode_theme_selection,
            # GPIO pin configurations
            'gpio_pins': self.gpio_pins
        }
        with open(self.settings_file, 'w') as f:
            json.dump(data, f, indent=4)
