# gpio.py

import RPi.GPIO as GPIO
from queue import Queue
from threading import Lock, Event
import time
import logging
from collections import deque
from dataclasses import dataclass
from typing import Dict, Deque

@dataclass
class SensorState:
    """Class to track sensor state and history"""
    value: bool
    last_change: float
    debounce_count: int
    history: Deque[bool]
    lock: Lock

class GPIOHandler:
    """Class to handle GPIO interactions for the bubble hockey game."""

    def __init__(self, settings):
        # Initialize GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.settings = settings
        self.event_queue = Queue()
        self.shutdown_event = Event()

        # Define GPIO pins from settings
        self.goal_sensor_red = self.settings.gpio_pins['goal_sensor_red']
        self.goal_sensor_blue = self.settings.gpio_pins['goal_sensor_blue']
        self.puck_sensor_red = self.settings.gpio_pins['puck_sensor_red']
        self.puck_sensor_blue = self.settings.gpio_pins['puck_sensor_blue']

        # Initialize sensor states with thread-safe tracking
        self.sensors: Dict[str, SensorState] = {}
        self._initialize_sensors()

        # Reference to the game instance
        self.game = None

    def _initialize_sensors(self):
        """Initialize all sensors with default states"""
        sensor_pins = {
            'goal_red': self.goal_sensor_red,
            'goal_blue': self.goal_sensor_blue,
            'puck_red': self.puck_sensor_red,
            'puck_blue': self.puck_sensor_blue
        }

        for name, pin in sensor_pins.items():
            # Set up GPIO pin
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Initialize sensor state
            self.sensors[name] = SensorState(
                value=False,
                last_change=time.monotonic(),
                debounce_count=0,
                history=deque(maxlen=10),
                lock=Lock()
            )

            # Add event detection with hardware debouncing
            GPIO.add_event_detect(
                pin,
                GPIO.FALLING,
                callback=lambda x, n=name: self._handle_sensor_event(n),
                bouncetime=50
            )

    def set_game(self, game):
        """Set the game instance for callback use."""
        self.game = game

    def _handle_sensor_event(self, sensor_name: str):
        """Handle sensor event with software debouncing"""
        sensor = self.sensors[sensor_name]
        
        with sensor.lock:
            current_time = time.monotonic()
            
            # Check software debounce time
            if (current_time - sensor.last_change) < self.settings.software_debounce_time:
                return
                
            # Get current value and add to history
            pin = self._get_pin_for_sensor(sensor_name)
            value = GPIO.input(pin)
            sensor.history.append(value)
            
            # Check if we have consistent readings
            if len(sensor.history) >= 3 and all(v == value for v in sensor.history):
                sensor.value = value
                sensor.last_change = current_time
                sensor.debounce_count = 0
                
                # Add event to queue for main thread processing
                self.event_queue.put((sensor_name, value))
            else:
                sensor.debounce_count += 1
                if sensor.debounce_count > 10:
                    logging.warning(f"Excessive bouncing on sensor {sensor_name}")
                    self._trigger_diagnostics(sensor_name)

    def _get_pin_for_sensor(self, sensor_name: str) -> int:
        """Get GPIO pin number for a given sensor name"""
        pin_map = {
            'goal_red': self.goal_sensor_red,
            'goal_blue': self.goal_sensor_blue,
            'puck_red': self.puck_sensor_red,
            'puck_blue': self.puck_sensor_blue
        }
        return pin_map.get(sensor_name)

    def process_events(self):
        """Process queued events in main thread"""
        while not self.event_queue.empty():
            event_type, event_data = self.event_queue.get()
            
            if event_type.startswith('goal_'):
                team = 'red' if event_type == 'goal_red' else 'blue'
                self._handle_goal_event(team)
            elif event_type.startswith('puck_'):
                self._update_puck_possession()
            elif event_type == 'diagnostic_needed':
                self.run_sensor_diagnostics(event_data)

    def _handle_goal_event(self, team: str):
        """Handle goal scored event"""
        if self.game and self._validate_goal(team):
            opposite_team = 'blue' if team == 'red' else 'red'
            self.game.goal_scored(opposite_team)
            logging.info(f"Goal detected for {opposite_team} team")

    def _validate_goal(self, team: str) -> bool:
        """Validate that a goal event is legitimate"""
        sensor = self.sensors[f'goal_{team}']
        with sensor.lock:
            # Check recent history for consistent readings
            if len(sensor.history) < 3:
                return False
            return all(sensor.history)

    def _update_puck_possession(self):
        """Update puck possession state based on sensor readings"""
        puck_red = self._get_sensor_value('puck_red')
        puck_blue = self._get_sensor_value('puck_blue')

        if not puck_red and not puck_blue:
            self.puck_possession = 'in_play'
        elif puck_red and not puck_blue:
            self.puck_possession = 'red'
        elif puck_blue and not puck_red:
            self.puck_possession = 'blue'
        else:
            self.puck_possession = None
            logging.warning("Invalid puck sensor state detected")

    def _get_sensor_value(self, sensor_name: str) -> bool:
        """Get the current value of a sensor with thread safety"""
        sensor = self.sensors[sensor_name]
        with sensor.lock:
            return sensor.value

    def get_puck_possession(self) -> str:
        """Get the current puck possession state"""
        self._update_puck_possession()
        return self.puck_possession

    def are_sensors_healthy(self) -> bool:
        """Check if all sensors are functioning properly"""
        return all(
            sensor.debounce_count < self.settings.max_debounce_count
            for sensor in self.sensors.values()
        )

    def run_sensor_diagnostics(self, sensor_name: str):
        """Run diagnostics on a specific sensor"""
        sensor = self.sensors[sensor_name]
        with sensor.lock:
            # Collect diagnostic data
            diagnostic_data = {
                'bounce_count': sensor.debounce_count,
                'history': list(sensor.history),
                'last_change': sensor.last_change
            }
            
        # Log diagnostic data
        logging.info(f"Sensor {sensor_name} diagnostics: {diagnostic_data}")
        
        # Reset sensor if needed
        if sensor.debounce_count > self.settings.sensor_reset_threshold:
            self.reset_sensor(sensor_name)

    def reset_sensor(self, sensor_name: str):
        """Reset a sensor's state"""
        sensor = self.sensors[sensor_name]
        with sensor.lock:
            sensor.history.clear()
            sensor.debounce_count = 0
            sensor.last_change = time.monotonic()
        logging.info(f"Reset sensor {sensor_name}")

    def reset_sensors(self):
        """Reset all sensors"""
        for sensor_name in self.sensors:
            self.reset_sensor(sensor_name)
        logging.info("All sensors reset")

    def cleanup(self):
        """Clean up GPIO pins and resources."""
        self.shutdown_event.set()
        GPIO.cleanup()
        logging.info("GPIO cleanup completed")
