# game.py

import pygame
import os
import json
import logging
import subprocess
from settings import Settings
from database import Database
from utils import load_image, load_sound
from classic_mode import ClassicMode
from evolved_mode import EvolvedMode
from crazy_play_mode import CrazyPlayMode

class Game:
    def __init__(self, screen, settings, gpio_handler):
        self.screen = screen
        self.settings = settings
        self.gpio_handler = gpio_handler
        self.clock = pygame.time.Clock()
        self.db = Database()
        self.current_game_id = None
        self.load_assets()
        self.mode = None
        self.gameplay = None
        self.is_over = False
        self.game_started = False
        self.sounds_enabled = True
        self.font_small = pygame.font.Font('assets/fonts/Pixellari.ttf', 20)
        self.font_large = pygame.font.Font('assets/fonts/Pixellari.ttf', 40)
        self.update_available = False  # Flag to indicate if an update is available
        self.update_notification_rect = None  # Rect for the update notification
        self.check_for_updates()  # Check for updates on game start

        # Initialize puck possession state
        self.puck_possession = None  # 'red', 'blue', 'in_play', or None
        self.countdown = None  # Countdown timer
        self.countdown_start_time = None

        # Set reference to game in gpio_handler
        self.gpio_handler.set_game(self)

    def load_assets(self):
        """Load all necessary assets for the game."""
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

        # Load sounds
        self.sounds = {
            'taunts': self.load_theme_sounds('taunts', 'assets/sounds/taunts', 5),
            'random_sounds': self.load_theme_sounds('random_sounds', 'assets/sounds/random_sounds', 5),
            # Load other sounds as needed
        }

    def load_theme_font(self, key, default_path, size):
        """Load a font from the theme, or use the default if not specified."""
        if key in self.theme_data.get('assets', {}):
            font_path = os.path.join('assets/themes', self.settings.current_theme, self.theme_data['assets'][key])
        else:
            font_path = default_path
        try:
            font = pygame.font.Font(font_path, size)
            return font
        except Exception as e:
            logging.error(f'Failed to load font {font_path}: {e}')
            return pygame.font.SysFont(None, size)

    def load_theme_sounds(self, key, default_path, count):
        """Load sounds from the theme, or use the default if not specified."""
        sounds = []
        theme_assets = self.theme_data.get('assets', {})
        if key in theme_assets:
            sound_dir = os.path.join('assets/themes', self.settings.current_theme, theme_assets[key])
        else:
            sound_dir = default_path
        for i in range(1, count + 1):
            sound_path = os.path.join(sound_dir, f'{key}_{i}.wav')
            sound = load_sound(sound_path)
            if sound:
                sounds.append(sound)
        return sounds

    def set_mode(self, mode):
        """Set the game mode and initialize the corresponding gameplay class."""
        self.mode = mode
        self.is_over = False
        if mode == 'classic':
            self.gameplay = ClassicMode(self)
        elif mode == 'evolved':
            self.gameplay = EvolvedMode(self)
        elif mode == 'crazy_play':
            self.gameplay = CrazyPlayMode(self)
        else:
            logging.error(f'Unknown game mode: {mode}')
            return
        logging.info(f"Game mode set to {mode}")

    def handle_event(self, event):
        """Handle events for the game."""
        if self.game_started:
            # Pass events to gameplay
            self.gameplay.handle_event(event)

        # Handle update initiation
        if self.update_available:
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if self.update_notification_rect and self.update_notification_rect.collidepoint(pos):
                    self.initiate_update()

    def update(self):
        """Update the game state."""
        # Get the puck possession state from gpio_handler
        self.puck_possession = self.gpio_handler.puck_possession

        # Game start logic
        if not self.game_started:
            if self.puck_possession == 'in_play':
                # Start countdown if not already started
                if self.countdown is None:
                    self.countdown = 3
                    self.countdown_start_time = pygame.time.get_ticks()
                    logging.info("Starting countdown timer")
                else:
                    # Update countdown
                    elapsed_time = (pygame.time.get_ticks() - self.countdown_start_time) / 1000
                    if elapsed_time >= 1:
                        self.countdown -= 1
                        self.countdown_start_time = pygame.time.get_ticks()
                        if self.countdown <= 0:
                            # Start the game
                            self.game_started = True
                            self.countdown = None
                            logging.info("Countdown complete. Game starting.")
                            # Record game start in the database
                            self.current_game_id = self.db.start_new_game(self.mode)
            elif self.puck_possession in ('red', 'blue'):
                # Start the game immediately
                self.game_started = True
                logging.info(f"Game starting. Puck possessed by {self.puck_possession} team.")
                # Record game start in the database
                self.current_game_id = self.db.start_new_game(self.mode)
            else:
                # Waiting for puck
                pass
        else:
            # Game has started, update gameplay
            self.gameplay.update()
            if self.gameplay.is_over:
                self.is_over = True
                # Record game end in database
                self.db.end_game(self.current_game_id, self.gameplay.score)

        # Check for updates
        self.check_for_updates()

    def draw(self):
        """Draw the game screen."""
        if not self.game_started:
            # Clear the screen
            self.screen.fill(self.settings.bg_color)
            # Draw countdown or waiting message
            if self.countdown is not None:
                # Display countdown
                countdown_text = self.font_large.render(str(self.countdown), True, (255, 255, 255))
                text_rect = countdown_text.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2))
                self.screen.blit(countdown_text, text_rect)
            else:
                # Display waiting message
                if self.puck_possession == 'red':
                    text = "Waiting for Red Team to eject the puck..."
                elif self.puck_possession == 'blue':
                    text = "Waiting for Blue Team to eject the puck..."
                else:
                    text = "Waiting for puck..."
                text_surface = self.font_small.render(text, True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2))
                self.screen.blit(text_surface, text_rect)
        else:
            # Game has started, draw gameplay
            self.gameplay.draw()
            # If an update is available, display the notification
            if self.update_available:
                self.display_update_notification()

    def goal_scored(self, team):
        """Handle a goal scored by a team."""
        if self.game_started and self.gameplay:
            self.gameplay.goal_scored(team)
        else:
            logging.info("Goal detected before game started.")

    def cleanup(self):
        """Cleanup resources."""
        self.db.close()

    def check_for_updates(self):
        """Check if an update is available by looking for the flag file."""
        if os.path.exists('update_available.flag'):
            self.update_available = True
            logging.info('Update available.')
        else:
            self.update_available = False

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
            os.chdir('/home/pi/bubble_hockey')  # Update path if necessary
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

    def get_game_status(self):
        """Return current game status for web display."""
        status = {
            'score': self.gameplay.score if self.gameplay else {'red': 0, 'blue': 0},
            'period': self.gameplay.period if self.gameplay else 0,
            'max_periods': self.gameplay.max_periods if self.gameplay else 0,
            'clock': self.gameplay.clock if self.gameplay else 0,
            'active_event': getattr(self.gameplay, 'active_event', None)
        }
        return status
