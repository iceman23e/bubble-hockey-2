# gpio.py

import RPi.GPIO as GPIO
import threading
import time
import logging

class GPIOHandler:
    """Class to handle GPIO interactions for the bubble hockey game."""

    def __init__(self, settings):
        # Initialize GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.settings = settings

        # Define GPIO pins from settings
        self.goal_sensor_red = self.settings.gpio_pins['goal_sensor_red']
        self.goal_sensor_blue = self.settings.gpio_pins['goal_sensor_blue']
        self.puck_sensor_red = self.settings.gpio_pins['puck_sensor_red']
        self.puck_sensor_blue = self.settings.gpio_pins['puck_sensor_blue']

        # Set up GPIO pins
        GPIO.setup(self.goal_sensor_red, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.goal_sensor_blue, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.puck_sensor_red, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.puck_sensor_blue, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Set up event detection for goal sensors
        GPIO.add_event_detect(self.goal_sensor_red, GPIO.FALLING, callback=self.goal_scored_red, bouncetime=300)
        GPIO.add_event_detect(self.goal_sensor_blue, GPIO.FALLING, callback=self.goal_scored_blue, bouncetime=300)

        # Initialize puck possession state
        self.puck_possession = None  # 'red', 'blue', 'in_play', or None

        # Reference to the game instance
        self.game = None

        # Start thread to monitor puck sensors
        self.puck_check_thread = threading.Thread(target=self.monitor_puck_sensors)
        self.puck_check_thread.daemon = True
        self.puck_check_thread.start()

    def set_game(self, game):
        """Set the game instance for callback use."""
        self.game = game

    def goal_scored_red(self, channel):
        """Handle goal scored by red team's goal sensor (opponent scores)."""
        logging.info("Goal detected for blue team (red team's goal sensor triggered)")
        if self.game:
            self.game.goal_scored('blue')  # Blue team scores

    def goal_scored_blue(self, channel):
        """Handle goal scored by blue team's goal sensor (opponent scores)."""
        logging.info("Goal detected for red team (blue team's goal sensor triggered)")
        if self.game:
            self.game.goal_scored('red')  # Red team scores

    def monitor_puck_sensors(self):
        """Continuously monitor puck sensors to determine puck possession."""
        while True:
            puck_waiting_red = GPIO.input(self.puck_sensor_red) == GPIO.LOW
            puck_waiting_blue = GPIO.input(self.puck_sensor_blue) == GPIO.LOW

            if not puck_waiting_red and not puck_waiting_blue:
                # Puck is in play
                if self.puck_possession != 'in_play':
                    self.puck_possession = 'in_play'
                    logging.info("Puck is now in play")
            elif puck_waiting_red and not puck_waiting_blue:
                # Puck is possessed by red team
                if self.puck_possession != 'red':
                    self.puck_possession = 'red'
                    logging.info("Puck is possessed by red team")
            elif puck_waiting_blue and not puck_waiting_red:
                # Puck is possessed by blue team
                if self.puck_possession != 'blue':
                    self.puck_possession = 'blue'
                    logging.info("Puck is possessed by blue team")
            else:
                # Undefined state or both sensors detect puck (should not happen)
                if self.puck_possession != 'unknown':
                    self.puck_possession = 'unknown'
                    logging.warning("Puck in unknown state")
            time.sleep(0.1)

    def cleanup(self):
        """Clean up GPIO pins."""
        GPIO.cleanup()
