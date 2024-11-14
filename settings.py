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
        
        # GPIO and sensor settings
        self.software_debounce_time = 0.05  # 50ms software debounce
        self.max_debounce_count = 10  # Maximum allowed debounces before reset
        self.sensor_reset_threshold = 20  # Threshold for sensor reset
        self.gpio_pins = {
            'goal_sensor_red': 17,
            'goal_sensor_blue': 27,
            'puck_sensor_red': 22,
            'puck_sensor_blue': 23
        }
        
        # State management settings
        self.state_save_interval = 5.0  # Save state every 5 seconds
        self.max_error_count = 3  # Maximum errors before forcing recovery
        self.event_process_interval = 0.016  # ~60fps for event processing
        
        # Sound settings
        self.taunts_enabled = True
        self.random_sounds_enabled = True
        self.random_sound_min_interval = 5
        self.random_sound_max_interval = 30
        
        # Combo goal settings
        self.combo_goals_enabled = True
        self.combo_time_window = 30
        self.combo_reward_type = 'extra_point'
        self.combo_max_stack = 5
        
        # Theme settings
        self.current_theme = 'default'
        self.classic_mode_theme_selection = False
        
        # Other settings
        self.clock_tick = 0

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    
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
                    
                    # GPIO and sensor settings
                    self.software_debounce_time = data.get('software_debounce_time', self.software_debounce_time)
                    self.max_debounce_count = data.get('max_debounce_count', self.max_debounce_count)
                    self.sensor_reset_threshold = data.get('sensor_reset_threshold', self.sensor_reset_threshold)
                    self.gpio_pins = data.get('gpio_pins', self.gpio_pins)
                    
                    # State management settings
                    self.state_save_interval = data.get('state_save_interval', self.state_save_interval)
                    self.max_error_count = data.get('max_error_count', self.max_error_count)
                    self.event_process_interval = data.get('event_process_interval', self.event_process_interval)
                    
                    # Sound settings
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
                    
                    # Validate sound interval settings
                    if self.random_sound_min_interval > self.random_sound_max_interval:
                        logging.warning("random_sound_min_interval is greater than random_sound_max_interval. Adjusting values.")
                        self.random_sound_min_interval, self.random_sound_max_interval = (
                            self.random_sound_max_interval, self.random_sound_min_interval)
                            
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
            
            # GPIO and sensor settings
            'software_debounce_time': self.software_debounce_time,
            'max_debounce_count': self.max_debounce_count,
            'sensor_reset_threshold': self.sensor_reset_threshold,
            'gpio_pins': self.gpio_pins,
            
            # State management settings
            'state_save_interval': self.state_save_interval,
            'max_error_count': self.max_error_count,
            'event_process_interval': self.event_process_interval,
            
            # Sound settings
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
            'classic_mode_theme_selection': self.classic_mode_theme_selection
        }
        
        with open(self.settings_file, 'w') as f:
            json.dump(data, f, indent=4)
