# game.py

import pygame
import sys
import os
import json
from utils import load_image, load_sound
from settings import Settings
from database import Database
import logging
import random
from datetime import datetime, timedelta
import subprocess

class Game:
    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.clock = pygame.time.Clock()
        self.db = Database()
        self.current_game_id = None
        self.load_assets()
        self.mode = None
        self.gameplay = None
        self.is_over = False
        self.sounds_enabled = True
        self.font_small = pygame.font.Font('assets/fonts/Pixellari.ttf', 20)
        self.font_large = pygame.font.Font('assets/fonts/Pixellari.ttf', 40)
        self.update_available = False  # Flag to indicate if an update is available
        self.update_notification_rect = None  # Rect for the update notification
        self.check_for_updates()  # Check for updates on game start

    def load_assets(self):
        # Load theme configuration
        theme_path = f'assets/themes/{self.settings.current_theme}'
        theme_config_path = os.path.join(theme_path, 'theme.json')
        if os.path.exists(theme_config_path):
            with open(theme_config_path, 'r') as f:
                self.theme_data = json.load(f)
        else:
            self.theme_data = {}

        # Load fonts
        self.font_small = self.load_theme_font('font_small', 'assets/fonts/Pixellari.ttf', 20)
        self.font_large = self.load_theme_font('font_large', 'assets/fonts/Pixellari.ttf', 40)

        # Load images
        self.taunt_button_image = self.load_theme_image('taunt_button', 'assets/images/taunt_button.png')
        self.power_up_icon_image = self.load_theme_image('power_up_icon', 'assets/images/power_up_icon.png')
        # Other images...

        # Load sounds
        self.sounds = {
            'taunts': self.load_theme_sounds('taunts', 'assets/sounds/taunts', 5),
            'random_sounds': self.load_theme_sounds('random_sounds', 'assets/sounds/random_sounds', 5),
            # Other sounds...
        }

    # ... (Other methods remain unchanged) ...

    def check_for_updates(self):
        """Check if an update is available by looking for the flag file."""
        if os.path.exists('update_available.flag'):
            self.update_available = True
            logging.info('Update available.')
        else:
            self.update_available = False

    def handle_event(self, event):
        """Handle events for the game."""
        # Pass events to gameplay
        self.gameplay.handle_event(event)

        # Handle update initiation
        if self.update_available:
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if self.update_notification_rect and self.update_notification_rect.collidepoint(pos):
                    self.initiate_update()

    def draw(self):
        """Draw the game screen."""
        self.gameplay.draw(self.screen)
        # If an update is available, display the notification
        if self.update_available:
            self.display_update_notification()

    def display_update_notification(self):
        """Display an update notification on the game screen."""
        notification_text = "Update Available! Tap here to update."
        text_surface = self.font_large.render(notification_text, True, (255, 255, 0))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2))
        self.screen.blit(text_surface, text_rect)
        self.update_notification_rect = text_rect  # Save rect for event handling

    def initiate_update(self):
        """Initiate the update process."""
        logging.info('User initiated update from game screen.')
        # Display updating message
        updating_text = "Updating... Please wait."
        text_surface = self.font_large.render(updating_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2 + 50))
        self.screen.blit(text_surface, text_rect)
        pygame.display.flip()
        # Perform the update
        try:
            # Navigate to the project directory
            os.chdir('/home/pi/bubble_hockey')
            # Pull the latest changes from the repository
            subprocess.run(['git', 'pull'], check=True)
            # Remove the update flag
            if os.path.exists('update_available.flag'):
                os.remove('update_available.flag')
            logging.info('Game updated successfully.')
            # Restart the game
            self.restart_game()
        except subprocess.CalledProcessError as e:
            logging.error(f'Update failed: {e}')
            # Display error message
            error_text = "Update failed. Check logs."
            error_surface = self.font_large.render(error_text, True, (255, 0, 0))
            error_rect = error_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2 + 100))
            self.screen.blit(error_surface, error_rect)
            pygame.display.flip()
            pygame.time.delay(3000)  # Pause for 3 seconds

    def restart_game(self):
        """Restart the game application."""
        logging.info('Restarting game...')
        pygame.quit()
        os.execv(sys.executable, ['python3'] + sys.argv)

    # ... (Other methods remain unchanged) ...
