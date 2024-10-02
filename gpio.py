# gpio.py

import RPi.GPIO as GPIO
import threading
import time
import logging

class GPIOHandler:
    """Class to handle GPIO interactions for the bubble hockey game."""
    
    def __init__(self, game):
        self.game = game
        self.settings = game.settings
        
        # Initialize GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Define GPIO pins
        self.goal_sensor_red = self.settings.gpio_pins['goal_sensor_red']
        self.goal_sensor_blue = self.settings.gpio_pins['goal_sensor_blue']
        self.puck_sensor_red = self.settings.gpio_pins['puck_sensor_red']
        self.puck_sensor_blue = self.settings.gpio_pins['puck_sensor_blue']
        
        # Set up GPIO pins
        GPIO.setup(self.goal_sensor_red, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.goal_sensor_blue, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.puck_sensor_red, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.puck_sensor_blue, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Set up event detection
        GPIO.add_event_detect(self.goal_sensor_red, GPIO.FALLING, callback=self.goal_scored_red, bouncetime=300)
        GPIO.add_event_detect(self.goal_sensor_blue, GPIO.FALLING, callback=self.goal_scored_blue, bouncetime=300)
        
        # Puck in play flag
        self.puck_in_play = False
        self.puck_check_thread = threading.Thread(target=self.monitor_puck_sensors)
        self.puck_check_thread.daemon = True
        self.puck_check_thread.start()
    
    def goal_scored_red(self, channel):
        """Handle goal scored by red team."""
        logging.info("Goal detected for red team")
        self.game.gameplay.goal_scored('red')
    
    def goal_scored_blue(self, channel):
        """Handle goal scored by blue team."""
        logging.info("Goal detected for blue team")
        self.game.gameplay.goal_scored('blue')
    
    def monitor_puck_sensors(self):
        """Continuously monitor puck sensors to determine if puck is in play."""
        while True:
            puck_waiting_red = GPIO.input(self.puck_sensor_red)
            puck_waiting_blue = GPIO.input(self.puck_sensor_blue)
            
            if puck_waiting_red == GPIO.HIGH and puck_waiting_blue == GPIO.HIGH:
                # Puck is in play
                if not self.puck_in_play:
                    self.puck_in_play = True
                    logging.info("Puck is now in play")
                    self.game.gameplay.puck_in_play = True
            else:
                # Puck is not in play
                if self.puck_in_play:
                    self.puck_in_play = False
                    logging.info("Puck is no longer in play")
                    self.game.gameplay.puck_in_play = False
            
            time.sleep(0.1)  # Adjust as needed
    
    def cleanup(self):
        """Clean up GPIO pins."""
        GPIO.cleanup()
