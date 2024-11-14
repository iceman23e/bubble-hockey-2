# game.py

import pygame
import os
import json
import logging
import subprocess
import time
from settings import Settings
from database import Database
from utils import load_image, load_sound
from classic_mode import ClassicMode
from evolved_mode import EvolvedMode
from crazy_play_mode import CrazyPlayMode
from game_states import GameStateMachine, GameState

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
        self.update_available = False
        self.update_notification_rect = None
        self.check_for_updates()

        # Initialize state machine
        self.state_machine = GameStateMachine(self)
        
        # Add event processing timing
        self.last_event_process = time.monotonic()
        self.event_process_interval = self.settings.event_process_interval

        # Initialize puck possession state
        self.puck_possession = None
        self.countdown = None
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
            logging.warning(f"Theme configuration not found for theme '{self.settings.current_theme}'. Using default assets.")

        # Load fonts
        self.font_small = self.load_theme_font('font_small', 'assets/fonts/Pixellari.ttf', 20)
        self.font_large = self.load_theme_font('font_large', 'assets/fonts/Pixellari.ttf', 40)

        # Load sounds
        self.sounds = {
            'taunts': self.load_theme_sounds('taunts', 'assets/sounds/taunts', 5),
            'random_sounds': self.load_theme_sounds('random_sounds', 'assets/sounds/random_sounds', 5),
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
        if self.state_machine.state == GameState.PLAYING:
            self.gameplay.handle_event(event)

        # Handle update initiation
        if self.update_available:
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if self.update_notification_rect and self.update_notification_rect.collidepoint(pos):
                    self.initiate_update()

    def update(self):
        """Update the game state."""
        current_time = time.monotonic()
        
        # Process GPIO events on regular interval
        if current_time - self.last_event_process >= self.event_process_interval:
            self.gpio_handler.process_events()
            self.last_event_process = current_time

        # Get the puck possession state from gpio_handler
        self.puck_possession = self.gpio_handler.get_puck_possession()

        # Update based on current state
        if self.state_machine.state == GameState.INITIALIZING:
            if self._check_ready_to_start():
                self.state_machine.start_game()
        
        elif self.state_machine.state == GameState.COUNTDOWN:
            self._update_countdown()
        
        elif self.state_machine.state == GameState.PLAYING:
            if self.gameplay:
                self.gameplay.update()
                if self.gameplay.is_over:
                    self.state_machine.end_game()
        
        elif self.state_machine.state == GameState.ERROR:
            if not self.state_machine.attempt_recovery():
                self.is_over = True
                logging.error("Unable to recover from error state")

        # Check for updates
        self.check_for_updates()

    def _check_ready_to_start(self):
        """Check if the game is ready to start."""
        return (self.puck_possession in ['red', 'blue', 'in_play'] and 
                self.gpio_handler.are_sensors_healthy())

    def _update_countdown(self):
        """Update the countdown timer."""
        if self.countdown is None:
            self.countdown = 3
            self.countdown_start_time = pygame.time.get_ticks()
        else:
            elapsed_time = (pygame.time.get_ticks() - self.countdown_start_time) / 1000
            if elapsed_time >= 1:
                self.countdown -= 1
                self.countdown_start_time = pygame.time.get_ticks()
                if self.countdown <= 0:
                    self.state_machine.transition_to_playing()

    def draw(self):
        """Draw the game screen."""
        if self.state_machine.state == GameState.INITIALIZING:
            self._draw_initialization_screen()
        elif self.state_machine.state == GameState.COUNTDOWN:
            self._draw_countdown_screen()
        elif self.state_machine.state == GameState.PLAYING:
            if self.gameplay:
                self.gameplay.draw()
                if self.update_available:
                    self.display_update_notification()
        elif self.state_machine.state == GameState.ERROR:
            self._draw_error_screen()

    def _draw_initialization_screen(self):
        """Draw the initialization screen."""
        self.screen.fill(self.settings.bg_color)
        if self.puck_possession == 'red':
            text = "Waiting for Red Team to eject the puck..."
        elif self.puck_possession == 'blue':
            text = "Waiting for Blue Team to eject the puck..."
        else:
            text = "Waiting for puck..."
        text_surface = self.font_small.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                 self.settings.screen_height // 2))
        self.screen.blit(text_surface, text_rect)

    def _draw_countdown_screen(self):
        """Draw the countdown screen."""
        self.screen.fill(self.settings.bg_color)
        if self.countdown is not None:
            countdown_text = self.font_large.render(str(self.countdown), True, (255, 255, 255))
            text_rect = countdown_text.get_rect(center=(self.settings.screen_width // 2, 
                                                      self.settings.screen_height // 2))
            self.screen.blit(countdown_text, text_rect)

    def _draw_error_screen(self):
        """Draw the error screen."""
        self.screen.fill((0, 0, 0))
        error_text = self.font_large.render("ERROR - Attempting Recovery", True, (255, 0, 0))
        text_rect = error_text.get_rect(center=(self.settings.screen_width // 2, 
                                              self.settings.screen_height // 2))
        self.screen.blit(error_text, text_rect)

    def goal_scored(self, team):
        """Handle a goal scored by a team."""
        if self.state_machine.state == GameState.PLAYING and self.gameplay:
            self.gameplay.goal_scored(team)
            # Record goal event in database
            if self.current_game_id:
                self.db.record_goal(self.current_game_id, team)
        else:
            logging.info("Goal detected outside of active gameplay")

    def cleanup(self):
        """Cleanup resources."""
        # Save final state
        if self.state_machine.state != GameState.ERROR:
            self.state_machine.save_state()
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
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                 self.settings.screen_height // 2))
        self.screen.blit(text_surface, text_rect)
        self.update_notification_rect = text_rect

    def initiate_update(self):
        """Initiate the update process."""
        logging.info('User initiated update from game screen.')
        self._draw_updating_screen()
        try:
            os.chdir('/home/pi/bubble_hockey')
            subprocess.run(['git', 'pull'], check=True)
            if os.path.exists('update_available.flag'):
                os.remove('update_available.flag')
            logging.info('Game updated successfully.')
            self.restart_game()
        except subprocess.CalledProcessError as e:
            logging.error(f'Update failed: {e}')
            self._draw_update_error()
            pygame.time.delay(3000)

    def _draw_updating_screen(self):
        """Draw the updating screen."""
        updating_text = "Updating... Please wait."
        text_surface = self.font_large.render(updating_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                 self.settings.screen_height // 2))
        self.screen.blit(text_surface, text_rect)
        pygame.display.flip()

    def _draw_update_error(self):
        """Draw the update error screen."""
        error_text = "Update failed. Check logs."
        error_surface = self.font_large.render(error_text, True, (255, 0, 0))
        error_rect = error_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                   self.settings.screen_height // 2 + 100))
        self.screen.blit(error_surface, error_rect)
        pygame.display.flip()

    def restart_game(self):
        """Restart the game application."""
        logging.info('Restarting game...')
        pygame.quit()
        os.execv(sys.executable, ['python3'] + sys.argv)

    def get_game_status(self):
        """Return current game status for web display."""
        status = {
            'state': self.state_machine.state.value,
            'score': self.gameplay.score if self.gameplay else {'red': 0, 'blue': 0},
            'period': self.gameplay.period if self.gameplay else 0,
            'max_periods': self.gameplay.max_periods if self.gameplay else 0,
            'clock': self.gameplay.clock if self.gameplay else 0,
            'active_event': getattr(self.gameplay, 'active_event', None)
        }
        return status
