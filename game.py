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

        # Load images
        self.taunt_button_image = self.load_theme_image('taunt_button', 'assets/images/taunt_button.png')
        self.power_up_icon_image = self.load_theme_image('power_up_icon', 'assets/images/power_up_icon.png')
        # Load other images as needed

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

    def load_theme_image(self, key, default_path):
        """Load an image from the theme, or use the default if not specified."""
        if key in self.theme_data.get('assets', {}):
            image_path = os.path.join('assets/themes', self.settings.current_theme, self.theme_data['assets'][key])
        else:
            image_path = default_path
        return load_image(image_path)

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
            self.gameplay.draw(self.screen)
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

# Game Mode Classes

class BaseGameMode:
    """Base class for game modes."""
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.settings = game.settings
        self.score = {'red': 0, 'blue': 0}
        self.period = 1
        self.max_periods = 3
        self.clock = self.settings.period_length
        self.is_over = False
        self.last_goal_time = None
        self.combo_count = 0
        self.power_up_active = False
        self.power_up_end_time = None

    def handle_event(self, event):
        """Handle events specific to the game mode."""
        pass  # To be implemented in subclasses

    def update(self):
        """Update the game mode state."""
        # In Evolved and Crazy Play modes, the clock runs only when the puck is in play
        if isinstance(self, ClassicMode):
            # In Classic mode, clock always runs
            dt = self.game.clock.tick(60) / 1000.0
            self.clock -= dt
        else:
            # In other modes, clock runs only when puck is in play
            if self.game.puck_possession == 'in_play':
                dt = self.game.clock.tick(60) / 1000.0
                self.clock -= dt
            else:
                # Puck not in play, clock does not decrement
                self.game.clock.tick(60)  # Maintain frame rate

        if self.clock <= 0:
            self.end_period()

    def draw(self, screen):
        """Draw the game mode elements on the screen."""
        # Clear the screen
        screen.fill(self.settings.bg_color)
        # Draw the scores
        score_text = self.game.font_large.render(f"Red: {self.score['red']}  Blue: {self.score['blue']}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.settings.screen_width // 2, 50))
        screen.blit(score_text, score_rect)
        # Draw the period and time remaining
        period_text = self.game.font_small.render(f"Period: {self.period}/{self.max_periods}", True, (255, 255, 255))
        period_rect = period_text.get_rect(center=(self.settings.screen_width // 2, 100))
        screen.blit(period_text, period_rect)
        clock_text = self.game.font_small.render(f"Time Remaining: {int(self.clock)}s", True, (255, 255, 255))
        clock_rect = clock_text.get_rect(center=(self.settings.screen_width // 2, 130))
        screen.blit(clock_text, clock_rect)
        # Display puck possession
        possession_text = f"Puck Possession: {self.game.puck_possession.capitalize() if self.game.puck_possession else 'Unknown'}"
        possession_surface = self.game.font_small.render(possession_text, True, (255, 255, 255))
        possession_rect = possession_surface.get_rect(center=(self.settings.screen_width // 2, 160))
        screen.blit(possession_surface, possession_rect)
        # Draw other game elements as needed

    def end_period(self):
        """Handle the end of a period."""
        if self.period < self.max_periods:
            self.period += 1
            self.clock = self.settings.period_length
            logging.info(f"Starting period {self.period}")
        else:
            self.is_over = True
            logging.info("Game over")

    def goal_scored(self, team):
        """Handle a goal scored by a team."""
        self.score[team] += 1
        logging.info(f"Goal scored by {team} team")
        # Handle combo goals
        current_time = datetime.now()
        if self.last_goal_time and (current_time - self.last_goal_time).total_seconds() <= self.settings.combo_time_window:
            self.combo_count += 1
            if self.combo_count <= self.settings.combo_max_stack:
                logging.info(f"Combo count increased to {self.combo_count}")
                # Apply combo reward
                if self.settings.combo_reward_type == 'extra_point':
                    self.score[team] += 1
                    logging.info(f"Extra point awarded to {team} team")
                elif self.settings.combo_reward_type == 'power_up':
                    self.activate_power_up()
        else:
            self.combo_count = 1
        self.last_goal_time = current_time

    def activate_power_up(self):
        """Activate a power-up."""
        self.power_up_active = True
        self.power_up_end_time = datetime.now() + timedelta(seconds=10)  # Power-up lasts 10 seconds
        logging.info("Power-up activated")

    def deactivate_power_up(self):
        """Deactivate the power-up."""
        self.power_up_active = False
        self.power_up_end_time = None
        logging.info("Power-up deactivated")

    def cleanup(self):
        """Clean up resources if needed."""
        pass

class ClassicMode(BaseGameMode):
    """Classic game mode with standard rules."""
    def __init__(self, game):
        super().__init__(game)
        logging.info("Classic mode initialized")

    def handle_event(self, event):
        """Handle events specific to Classic mode."""
        pass  # No special events in classic mode

    def update(self):
        """Update the game state."""
        super().update()
        # Handle power-up expiration
        if self.power_up_active and datetime.now() >= self.power_up_end_time:
            self.deactivate_power_up()

    def draw(self, screen):
        """Draw the game elements."""
        super().draw(screen)
        # Draw power-up status
        if self.power_up_active:
            power_up_text = self.game.font_small.render("Power-Up Active!", True, (255, 255, 0))
            power_up_rect = power_up_text.get_rect(center=(self.settings.screen_width // 2, 190))
            screen.blit(power_up_text, power_up_rect)

class EvolvedMode(BaseGameMode):
    """Evolved game mode with additional features."""
    def __init__(self, game):
        super().__init__(game)
        logging.info("Evolved mode initialized")
        # Initialize evolved mode features
        self.taunt_timer = 0

    def handle_event(self, event):
        """Handle events specific to Evolved mode."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_t and self.settings.taunts_enabled:
                self.play_random_taunt()

    def update(self):
        """Update the game state."""
        super().update()
        # Handle taunt timing
        if self.settings.taunts_enabled and self.game.puck_possession == 'in_play':
            self.taunt_timer += self.game.clock.get_time() / 1000.0
            if self.taunt_timer >= self.settings.taunt_frequency:
                self.play_random_taunt()
                self.taunt_timer = 0
        # Handle power-up expiration
        if self.power_up_active and datetime.now() >= self.power_up_end_time:
            self.deactivate_power_up()

    def draw(self, screen):
        """Draw the game elements."""
        super().draw(screen)
        # Additional drawing for evolved mode if needed

    def play_random_taunt(self):
        """Play a random taunt sound."""
        if self.game.sounds_enabled and self.game.sounds['taunts']:
            taunt_sound = random.choice(self.game.sounds['taunts'])
            taunt_sound.play()
            logging.info("Taunt sound played")

class CrazyPlayMode(BaseGameMode):
    """Crazy Play mode with unpredictable elements."""
    def __init__(self, game):
        super().__init__(game)
        logging.info("Crazy Play mode initialized")
        # Initialize crazy play features
        self.random_sound_timer = 0

    def handle_event(self, event):
        """Handle events specific to Crazy Play mode."""
        pass  # No special events in crazy play mode

    def update(self):
        """Update the game state."""
        super().update()
        # Handle random sounds
        if self.settings.random_sounds_enabled and self.game.puck_possession == 'in_play':
            self.random_sound_timer += self.game.clock.get_time() / 1000.0
            if self.random_sound_timer >= self.settings.random_sound_frequency:
                self.play_random_sound()
                self.random_sound_timer = 0
        # Handle power-up expiration
        if self.power_up_active and datetime.now() >= self.power_up_end_time:
            self.deactivate_power_up()

    def draw(self, screen):
        """Draw the game elements."""
        super().draw(screen)
        # Additional drawing for crazy play mode if needed

    def play_random_sound(self):
        """Play a random sound."""
        if self.game.sounds_enabled and self.game.sounds['random_sounds']:
            random_sound = random.choice(self.game.sounds['random_sounds'])
            random_sound.play()
            logging.info("Random sound played")

    def activate_power_up(self):
        """Activate a power-up with crazy effects."""
        super().activate_power_up()
        # Implement crazy power-up effects
        logging.info("Crazy power-up activated")

    def deactivate_power_up(self):
        """Deactivate the power-up."""
        super().deactivate_power_up()
        # Revert any crazy effects
        logging.info("Crazy power-up deactivated")
