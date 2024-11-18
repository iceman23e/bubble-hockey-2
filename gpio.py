# gpio.py

import RPi.GPIO as GPIO
import threading
import time
import logging
import queue
import sys
import traceback
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal, TypedDict
from enum import Enum, auto
from functools import wraps

PuckState = Literal['red', 'blue', 'in_play', 'unknown']

class SensorError(Exception):
    """Base exception for sensor-related errors"""
    pass

class ConfigError(Exception):
    """Exception for configuration validation errors"""
    pass

class PuckReadingDict(TypedDict):
    """Type definition for puck sensor readings"""
    red: bool
    blue: bool
    time: float

@dataclass
class GPIOConfig:
    """Configuration parameters for GPIO handling with validation"""
    debounce_time_ms: int = 300
    goal_sensor_debounce_ms: int = 300
    puck_poll_interval_ms: float = 100.0
    event_timeout_s: float = 1.0
    thread_shutdown_timeout_s: float = 2.0
    sensor_history_window_s: float = 1.0
    
    # Puck possession specific parameters
    stuck_sensor_timeout_s: float = 5.0
    possession_change_min_interval_s: float = 0.1
    possession_history_window_s: float = 1.0
    max_possession_readings: int = 10
    bounce_threshold: int = 3
    
    def __post_init__(self):
        """Validate configuration values"""
        self._validate_positive('debounce_time_ms')
        self._validate_positive('goal_sensor_debounce_ms')
        self._validate_positive('puck_poll_interval_ms')
        self._validate_positive('event_timeout_s')
        self._validate_positive('thread_shutdown_timeout_s')
        self._validate_positive('sensor_history_window_s')
        self._validate_positive('stuck_sensor_timeout_s')
        self._validate_positive('possession_change_min_interval_s')
        self._validate_positive('possession_history_window_s')
        self._validate_positive('max_possession_readings', min_value=5)
        self._validate_positive('bounce_threshold', min_value=2)

    def _validate_positive(self, field: str, min_value: float = 0.0) -> None:
        """Validate that a field is positive and above minimum value"""
        value = getattr(self, field)
        if not isinstance(value, (int, float)) or value <= min_value:
            raise ConfigError(
                f"{field} must be a number greater than {min_value}, got {value}"
            )

def with_logging(level: int = logging.DEBUG):
    """Decorator to add consistent logging to methods"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                logging.log(level, f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logging.exception(f"Error in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator

class GPIOHandler:
    def __init__(self, settings, config: Optional[GPIOConfig] = None):
        """Initialize GPIO handler with validation"""
        self.settings = settings
        self.config = config or GPIOConfig()
        self.game = None
        
        # Thread control
        self._shutdown_event = threading.Event()
        
        # Thread synchronization
        self._possession_state_lock = threading.Lock()  # Renamed for clarity
        self._readings_lock = threading.Lock()
        
        # State tracking
        self.puck_possession: PuckState = 'unknown'
        self._last_possession_change = time.monotonic()
        self._possession_readings: List[PuckReadingDict] = []
        
        # Initialize system
        self._initialize_gpio()
        self._start_monitoring_threads()
        logging.info("GPIO Handler initialized successfully")

    @with_logging(logging.DEBUG)
    def _add_possession_reading(self, red: bool, blue: bool, timestamp: float) -> None:
        """
        Thread-safe addition of new possession reading to history.
        
        Args:
            red: State of red sensor
            blue: State of blue sensor
            timestamp: Monotonic timestamp of reading
        
        Raises:
            SensorError: If timestamp is invalid
        """
        if timestamp < 0 or timestamp < self._last_possession_change:
            raise SensorError(f"Invalid timestamp: {timestamp}")
            
        with self._readings_lock:
            self._possession_readings.append({
                'red': red,
                'blue': blue,
                'time': timestamp
            })
            
            # Clean up old readings
            current_time = time.monotonic()
            self._possession_readings = [
                r for r in self._possession_readings 
                if current_time - r['time'] < self.config.possession_history_window_s
            ]
            
            # Trim to max size
            if len(self._possession_readings) > self.config.max_possession_readings:
                self._possession_readings = self._possession_readings[-self.config.max_possession_readings:]

    @with_logging(logging.DEBUG)
    def _check_stuck_sensors(self) -> bool:
        """
        Check for stuck sensors in reading history.
        
        Returns:
            bool: True if a sensor appears to be stuck
        """
        with self._readings_lock:
            if len(self._possession_readings) < 5:
                return False
                
            red_stuck = all(r['red'] for r in self._possession_readings)
            blue_stuck = all(r['blue'] for r in self._possession_readings)
            
            return red_stuck or blue_stuck

    @with_logging(logging.DEBUG)
    def _check_bounce(self) -> bool:
        """
        Check for puck bouncing by analyzing state changes.
        
        Returns:
            bool: True if bouncing is detected
        """
        with self._readings_lock:
            if len(self._possession_readings) < 3:
                return False
                
            changes = sum(
                1 for i in range(1, len(self._possession_readings))
                if (self._possession_readings[i]['red'] != self._possession_readings[i-1]['red'] or
                    self._possession_readings[i]['blue'] != self._possession_readings[i-1]['blue'])
            )
            
            return changes >= self.config.bounce_threshold

    @with_logging(logging.DEBUG)
    def _validate_puck_state(self, red: bool, blue: bool) -> PuckState:
        """
        Validate and determine puck state with edge case handling.
        
        Args:
            red: State of red sensor
            blue: State of blue sensor
            
        Returns:
            PuckState: Current valid puck state
        """
        current_time = time.monotonic()
        
        try:
            self._add_possession_reading(red, blue, current_time)
        except SensorError as e:
            logging.error(f"Error adding possession reading: {e}")
            return 'unknown'

        # Physically impossible state
        if red and blue:
            logging.warning("Invalid sensor state: Both puck sensors triggered")
            return 'unknown'

        # Check for stuck sensors
        if self._check_stuck_sensors():
            logging.warning("Possible stuck sensor detected")
            return 'unknown'

        # Check for bouncing
        if self._check_bounce():
            logging.debug("Rapid sensor changes detected - possible bounce")
            with self._possession_state_lock:
                return self.puck_possession or 'unknown'

        # Determine new state
        if not red and not blue:
            return 'in_play'
        elif red:
            return 'red'
        elif blue:
            return 'blue'
        
        return 'unknown'  # Fallback state

    @with_logging(logging.DEBUG)
    def _monitor_puck_sensors(self) -> None:
        """Monitor puck sensors with error handling"""
        poll_interval = self.config.puck_poll_interval_ms / 1000.0
        
        while not self._shutdown_event.is_set():
            try:
                red_reading = GPIO.input(self.settings.gpio_pins['puck_sensor_red']) == GPIO.LOW
                blue_reading = GPIO.input(self.settings.gpio_pins['puck_sensor_blue']) == GPIO.LOW

                new_possession = self._validate_puck_state(red_reading, blue_reading)
                
                with self._possession_state_lock:
                    if new_possession != self.puck_possession:
                        current_time = time.monotonic()
                        time_since_change = current_time - self._last_possession_change
                        
                        if (time_since_change > self.config.possession_change_min_interval_s or 
                            'in_play' in (new_possession, self.puck_possession)):
                            self.puck_possession = new_possession
                            self._last_possession_change = current_time
                            logging.debug(f"Puck possession changed to: {new_possession}")

                self._shutdown_event.wait(timeout=poll_interval)
                
            except Exception as e:
                logging.exception("Error in puck monitoring")
                self._shutdown_event.wait(timeout=poll_interval)
