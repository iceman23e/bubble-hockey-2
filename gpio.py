# gpio.py

import RPi.GPIO as GPIO
import threading
import time
import logging
import queue
import traceback
import sys
from typing import Optional, Dict, List
from dataclasses import dataclass
from functools import partial
from threading import Lock

@dataclass
class GPIOConfig:
    """Configuration parameters for GPIO handling"""
    debounce_time_ms: int = 300
    goal_sensor_debounce_ms: int = 300
    puck_poll_interval_ms: float = 100.0
    event_timeout_s: float = 1.0
    thread_shutdown_timeout_s: float = 2.0
    sensor_history_window_s: float = 1.0

@dataclass
class SensorEvent:
    """Data class for sensor events"""
    pin: int
    state: bool
    timestamp: float  # Using monotonic time
    sensor_name: str

class GPIOHandler:
    """Enhanced GPIO handler with improved error handling and debouncing"""
    
    def __init__(self, settings, config: Optional[GPIOConfig] = None):
        self.settings = settings
        self.config = config or GPIOConfig()
        self.game = None
        
        # Thread control
        self._shutdown_event = threading.Event()
        
        # Sensor state tracking with thread safety
        self.puck_possession = None
        self._last_sensor_states = {
            'goal_sensor_red': False,
            'goal_sensor_blue': False,
            'puck_sensor_red': False,
            'puck_sensor_blue': False
        }
        self._sensor_states_lock = Lock()
        
        # Event handling with thread safety
        self._event_queue = queue.Queue()
        self._sensor_history: Dict[int, List[SensorEvent]] = {
            pin: [] for pin in self.settings.gpio_pins.values()
        }
        self._history_lock = Lock()
        
        # Initialize GPIO system
        self._initialize_gpio()
        
        # Start monitoring threads
        self._start_monitoring_threads()
        logging.info("GPIO Handler initialized successfully")

    def _initialize_gpio(self):
        """Initialize GPIO with error handling"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Set up pins with error checking
            for sensor_name, pin in self.settings.gpio_pins.items():
                try:
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    if sensor_name.startswith('goal_sensor'):
                        callback = partial(self._sensor_callback, sensor_name=sensor_name)
                        GPIO.add_event_detect(
                            pin,
                            GPIO.FALLING,
                            callback=callback,
                            bouncetime=self.config.goal_sensor_debounce_ms
                        )
                except (RuntimeError, ValueError) as e:
                    logging.exception(f"Failed to initialize {sensor_name} on pin {pin}")
                    raise RuntimeError(f"Critical sensor initialization failed: {sensor_name}") from e
                    
        except Exception as e:
            logging.exception("Fatal GPIO initialization error")
            raise RuntimeError("GPIO system failed to initialize") from e

    def _start_monitoring_threads(self):
        """Start the monitoring threads with error handling"""
        try:
            # Thread for processing sensor events
            self.event_thread = threading.Thread(
                target=self._process_events,
                name="EventProcessor",
                daemon=True
            )
            self.event_thread.start()

            # Thread for monitoring puck sensors
            self.puck_thread = threading.Thread(
                target=self._monitor_puck_sensors,
                name="PuckMonitor",
                daemon=True
            )
            self.puck_thread.start()
            
        except Exception as e:
            logging.exception("Failed to start monitoring threads")
            self._shutdown_event.set()
            raise RuntimeError("Failed to start GPIO monitoring system") from e

    def _sensor_callback(self, channel: int, *, sensor_name: str):
        """Handle sensor callbacks with improved context"""
        try:
            event = SensorEvent(
                pin=channel,
                state=GPIO.input(channel),
                timestamp=time.monotonic(),
                sensor_name=sensor_name
            )
            self._event_queue.put(event, timeout=self.config.event_timeout_s)
        except queue.Full:
            logging.error(f"Event queue full, dropped event for {sensor_name}")
        except Exception as e:
            logging.exception(f"Sensor callback error on pin {channel}")

    def _is_valid_event(self, event: SensorEvent) -> bool:
        """Validate sensor events with improved physical validation"""
        with self._history_lock:
            history = self._sensor_history[event.pin]
            current_time = time.monotonic()
            
            # Clean up old history
            history = [e for e in history 
                      if (current_time - e.timestamp) < self.config.sensor_history_window_s]
            
            # Validate event timing
            if history:
                time_since_last = event.timestamp - history[-1].timestamp
                if time_since_last < (self.config.debounce_time_ms / 1000):
                    return False
                
                # Check for physically impossible rapid goal sequences
                if event.sensor_name.startswith('goal_sensor'):
                    goals_in_window = len(history)
                    if goals_in_window >= 3:  # More than 2 goals in history window
                        logging.warning(f"Suspicious rapid goal sequence detected on {event.sensor_name}")
                        return False
            
            # Update history
            history.append(event)
            self._sensor_history[event.pin] = history
            
            return True

    def _process_events(self):
        """Process sensor events from the queue with improved shutdown handling"""
        while not self._shutdown_event.is_set():
            try:
                event = self._event_queue.get(timeout=self.config.event_timeout_s)
                if self._is_valid_event(event):
                    self._handle_event(event)
                self._event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.exception("Error processing sensor event")
                self._shutdown_event.wait(timeout=1.0)  # Longer timeout to reduce CPU usage during errors

    def _handle_event(self, event: SensorEvent):
        """Handle validated sensor events"""
        try:
            if event.sensor_name == 'goal_sensor_red':
                logging.info("Goal detected for blue team")
                if self.game:
                    self.game.goal_scored('blue')
            elif event.sensor_name == 'goal_sensor_blue':
                logging.info("Goal detected for red team")
                if self.game:
                    self.game.goal_scored('red')
        except Exception as e:
            logging.exception("Error handling sensor event")

    def _monitor_puck_sensors(self):
        """Monitor puck sensors with improved resource management"""
        poll_interval = self.config.puck_poll_interval_ms / 1000.0
        
        while not self._shutdown_event.is_set():
            try:
                puck_waiting_red = GPIO.input(self.settings.gpio_pins['puck_sensor_red']) == GPIO.LOW
                puck_waiting_blue = GPIO.input(self.settings.gpio_pins['puck_sensor_blue']) == GPIO.LOW

                new_possession = self._validate_puck_state(puck_waiting_red, puck_waiting_blue)
                
                with self._sensor_states_lock:
                    if new_possession != self.puck_possession:
                        self.puck_possession = new_possession
                        logging.info(f"Puck possession changed to: {new_possession}")

                self._shutdown_event.wait(timeout=poll_interval)
                
            except Exception as e:
                logging.exception("Error in puck monitoring")
                self._shutdown_event.wait(timeout=poll_interval)

    def _validate_puck_state(self, red: bool, blue: bool) -> str:
        """Validate and determine puck state with physical possibility checking"""
        if red and blue:
            logging.warning("Invalid sensor state: Both puck sensors triggered")
            return 'unknown'
        elif not red and not blue:
            return 'in_play'
        elif red:
            return 'red'
        elif blue:
            return 'blue'
        return 'unknown'

    def set_game(self, game):
        """Set the game instance reference"""
        self.game = game

    def cleanup(self):
        """Clean up GPIO resources with improved thread shutdown"""
        try:
            # Signal threads to stop
            self._shutdown_event.set()
            
            # Wait for threads to finish with timeout
            for thread in [self.event_thread, self.puck_thread]:
                thread.join(timeout=self.config.thread_shutdown_timeout_s)
                if thread.is_alive():
                    thread_id = thread.ident
                    logging.error(f"Thread {thread.name} (id: {thread_id}) failed to shut down cleanly")
                    frames = sys._current_frames()
                    if thread_id in frames:
                        stack = traceback.format_stack(frames[thread_id])
                        logging.error(f"Thread {thread.name} stack trace:\n{''.join(stack)}")
            
            # Clean up GPIO
            GPIO.cleanup()
            logging.info("GPIO cleanup completed successfully")
        except Exception as e:
            logging.exception("Error during GPIO cleanup")
