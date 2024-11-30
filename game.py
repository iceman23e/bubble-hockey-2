# game.py

import pygame
import os
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from settings import Settings
from database import Database
from utils import load_image, load_sound
from classic_mode import ClassicMode
from evolved_mode import EvolvedMode
from crazy_play_mode import CrazyPlayMode
from game_states import GameStates
from state_machine import GameStateMachine
from game_analytics import GameAnalytics, GameState, AnalyticsConfig

class Game:
    def __init__(self, screen_manager, settings, gpio_handler):
        self.screen_manager = screen_manager
        self.settings = settings
        self.gpio_handler = gpio_handler
        self.clock = pygame.time.Clock()
        self.db = Database()
        self.current_game_id = None
        
        # Initialize state machine
        self.state_machine = GameStateMachine(initial=GameStates.PREGAME)
        
        # Initialize analytics with configuration
        analytics_config = AnalyticsConfig(
            min_games_basic=30,
            min_games_advanced=300,
            momentum_window=60,
            quick_response_window=30,
            scoring_run_threshold=3,
            cache_size=128,
            critical_moment_threshold=60.0,
            close_game_threshold=2
        )
        self.analytics = GameAnalytics(self.db, config=analytics_config)
        self.current_analysis = None
        
        self.load_assets()
        self.mode = None
        self.gameplay = None
        self.is_over = False
        self.game_started = False
        self.sounds_enabled = True
        
        # Initialize fonts
        self.load_fonts()
        
        self.update_available = False
        self.update_notification_rect = None
        self.check_for_updates()

        # Initialize puck possession state
        self.puck_possession = None
        self.countdown = None
        self.countdown_start_time = None

        # GPIO event processing timing
        self.event_process_interval = 0.01  # 10ms interval
        self.last_event_process = time.monotonic()

        # Set reference to game in gpio_handler
        self.gpio_handler.set_game(self)

        # Register touch zones for both screens
        self.register_touch_zones()

    def register_touch_zones(self):
        """Register touch-interactive zones for both screens."""
        for screen in ['red', 'blue']:
            # Register game-specific touch zones based on state
            if self.state_machine.state == GameStates.PREGAME:
                self.register_pregame_zones(screen)
            elif self.state_machine.state == GameStates.PLAYING:
                self.register_playing_zones(screen)
            elif self.state_machine.state == GameStates.PAUSED:
                self.register_paused_zones(screen)
            elif self.state_machine.state == GameStates.INTERMISSION:
                self.register_intermission_zones(screen)
            elif self.state_machine.state == GameStates.GAME_OVER:
                self.register_game_over_zones(screen)

    def register_pregame_zones(self, screen):
        """Register touch zones for pregame state."""
        self.screen_manager.register_touch_zone(
            screen,
            'pregame_ready',
            pygame.Rect(0, 0, self.settings.screen_width, self.settings.screen_height),
            self.handle_pregame_touch
        )

    def register_playing_zones(self, screen):
        """Register touch zones for playing state."""
        # Add any in-game touch controls here
        pass

    def register_paused_zones(self, screen):
        """Register touch zones for paused state."""
        self.screen_manager.register_touch_zone(
            screen,
            'resume_game',
            pygame.Rect(0, 0, self.settings.screen_width, self.settings.screen_height),
            self.handle_pause_touch
        )

    def register_intermission_zones(self, screen):
        """Register touch zones for intermission state."""
        # Add any intermission-specific touch zones here
        pass

    def register_game_over_zones(self, screen):
        """Register touch zones for game over state."""
        self.screen_manager.register_touch_zone(
            screen,
            'return_to_menu',
            pygame.Rect(0, 0, self.settings.screen_width, self.settings.screen_height),
            self.handle_game_over_touch
        )

    def handle_pregame_touch(self, screen, pos):
        """Handle touch events in pregame state."""
        if self.countdown is None and self.puck_possession == 'in_play':
            self._start_countdown()

    def handle_pause_touch(self, screen, pos):
        """Handle touch events in paused state."""
        if self.state_machine.can('resume_game'):
            self.state_machine.resume_game()

    def handle_game_over_touch(self, screen, pos):
        """Handle touch events in game over state."""
        self.is_over = True

    def load_fonts(self):
        """Load all required fonts"""
        try:
            self.font_small = pygame.font.Font('assets/fonts/Pixellari.ttf', 20)
            self.font_large = pygame.font.Font('assets/fonts/Pixellari.ttf', 40)
            self.font_title = pygame.font.Font('assets/fonts/PressStart2P-Regular.ttf', 36)
            self.font_msdos = pygame.font.Font('assets/fonts/Perfect DOS VGA 437.ttf', 24)
            self.font_matrix = pygame.font.Font('assets/fonts/VCR_OSD_MONO_1.001.ttf', 24)
        except Exception as e:
            logging.error(f"Error loading fonts: {e}")
            sys.exit(1)

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

        # Load sounds - these will be shared between screens
        self.sounds = {
            'taunts': self.load_theme_sounds('taunts', 'assets/sounds/taunts', 5),
            'random_sounds': self.load_theme_sounds('random_sounds', 'assets/sounds/random_sounds', 5),
            'goal': load_sound('assets/sounds/goal_scored.wav'),
            'period_start': load_sound('assets/sounds/period_start.wav'),
            'period_end': load_sound('assets/sounds/period_end.wav'),
            'game_over': load_sound('assets/sounds/game_over.wav')
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
        
        # Initialize state machine for new game
        self.state_machine.reset()
        logging.info(f"Game mode set to {mode}")
        
        # Re-register touch zones for new mode
        self.register_touch_zones()

    def handle_event(self, event):
        """Handle events for the game."""
        if self.game_started:
            # Handle state machine transitions
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and self.state_machine.can('pause_game'):
                    self.state_machine.pause_game()
                elif event.key == pygame.K_p and self.state_machine.can('resume_game'):
                    self.state_machine.resume_game()
                    
            # Pass events to gameplay mode
            if self.gameplay:
                self.gameplay.handle_event(event)

        # Handle update notification
        if self.update_available and event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if self.update_notification_rect and self.update_notification_rect.collidepoint(pos):
                self.initiate_update()

    def _get_current_game_state(self) -> GameState:
        """Create GameState object from current game state"""
        return GameState(
            score=self.gameplay.score if self.gameplay else {'red': 0, 'blue': 0},
            period=self.gameplay.period if self.gameplay else 1,
            clock=self.gameplay.clock if self.gameplay else 0,
            game_id=self.current_game_id,
            mode=self.mode,
            is_running_clock=isinstance(self.gameplay, (EvolvedMode, CrazyPlayMode)),
            max_periods=self.gameplay.max_periods if self.gameplay else 3,
            period_length=self.settings.period_length
        )

    def update(self):
        """Update the game state."""
        # Get the puck possession state from gpio_handler
        self.puck_possession = self.gpio_handler.puck_possession

        # Process GPIO events on regular interval
        current_time = time.monotonic()
        if current_time - self.last_event_process >= self.event_process_interval:
            self.gpio_handler.process_events()
            self.last_event_process = current_time

        # Update game state based on current state machine state
        if self.state_machine.state == GameStates.PREGAME:
            self._handle_pregame()
        elif self.state_machine.state == GameStates.PLAYING:
            self._handle_playing()
        elif self.state_machine.state == GameStates.PAUSED:
            self._handle_paused()
        elif self.state_machine.state == GameStates.INTERMISSION:
            self._handle_intermission()
        elif self.state_machine.state == GameStates.GAME_OVER:
            self._handle_game_over()

        # Check for updates
        self.check_for_updates()
        
        # Update touch zones if state has changed
        if self.state_machine.state != getattr(self, '_last_state', None):
            self.register_touch_zones()
            self._last_state = self.state_machine.state

    def _handle_pregame(self):
        """Handle pregame state"""
        if not self.game_started:
            if self.puck_possession == 'in_play':
                if self.countdown is None:
                    self._start_countdown()
                else:
                    self._update_countdown()
            elif self.puck_possession in ('red', 'blue'):
                self._start_game()

    def _handle_playing(self):
        """Handle playing state"""
        # Update gameplay
        if self.gameplay:
            self.gameplay.update()
            
            # Update analytics
            self.current_analysis = self.analytics.update(self._get_current_game_state())
            
            # Check if game is over
            if self.gameplay.is_over:
                self.is_over = True
                if self.state_machine.can('end_game'):
                    self.state_machine.end_game()
                # Record game end in database
                self.db.end_game(self.current_game_id, self.gameplay.score)
    
    def _handle_paused(self):
        """Handle paused state"""
        # Update analytics with paused state
        if self.gameplay:
            game_state = self._get_current_game_state()
            self.current_analysis = self.analytics.update(game_state)

    def _handle_intermission(self):
        """Handle intermission state"""
        if self.gameplay:
            if self.gameplay.intermission_clock is not None:
                if self.gameplay.intermission_clock <= 0:
                    if self.state_machine.can('resume_game'):
                        self.state_machine.resume_game()
            
            # Update analytics during intermission
            game_state = self._get_current_game_state()
            self.current_analysis = self.analytics.update(game_state)

    def _handle_game_over(self):
        """Handle game over state"""
        # Final analytics update
        if self.gameplay:
            game_state = self._get_current_game_state()
            self.current_analysis = self.analytics.update(game_state)

    def _start_countdown(self):
        """Start the countdown timer"""
        self.countdown = 3
        self.countdown_start_time = pygame.time.get_ticks()
        logging.info("Starting countdown timer")

    def _update_countdown(self):
        """Update the countdown timer"""
        elapsed_time = (pygame.time.get_ticks() - self.countdown_start_time) / 1000
        if elapsed_time >= 1:
            self.countdown -= 1
            self.countdown_start_time = pygame.time.get_ticks()
            if self.countdown <= 0:
                self._start_game()

    def _start_game(self):
        """Start the game"""
        self.game_started = True
        self.countdown = None
        logging.info(f"Game starting. Puck possessed by {self.puck_possession} team.")
        
        # Record game start in database
        self.current_game_id = self.db.start_new_game(self.mode)
        
        # Initialize analytics with starting state
        initial_state = self._get_current_game_state()
        self.current_analysis = self.analytics.update(initial_state)
        
        # Transition state machine to playing
        if self.state_machine.can('start_game'):
            self.state_machine.start_game()
            if self.sounds['period_start']:
                self.sounds['period_start'].play()

    def goal_scored(self, team):
        """Handle a goal scored by a team."""
        if not self.game_started:
            logging.info("Goal detected before game started.")
            return
            
        if self.state_machine.state != GameStates.PLAYING:
            logging.info("Goal scored while game not in playing state.")
            return
            
        if self.gameplay:
            # Update gameplay
            self.gameplay.goal_scored(team)
            
            # Play goal sound
            if self.sounds['goal']:
                self.sounds['goal'].play()
            
            # Update analytics
            game_state = self._get_current_game_state()
            self.current_analysis = self.analytics.record_goal(team, game_state)
            
            # Handle critical moments
            if self.current_analysis['is_critical_moment']:
                self._handle_critical_moment()

    def _handle_critical_moment(self):
        """Handle critical game moments"""
        if self.gameplay and hasattr(self.gameplay, 'handle_critical_moment'):
            self.gameplay.handle_critical_moment(self.current_analysis)

    def check_for_updates(self):
        """Check if an update is available by looking for the flag file."""
        if os.path.exists('update_available.flag'):
            self.update_available = True
            logging.info('Update available.')
        else:
            self.update_available = False

    def get_game_status(self):
        """Return current game status for web display."""
        status = {
            'score': self.gameplay.score if self.gameplay else {'red': 0, 'blue': 0},
            'period': self.gameplay.period if self.gameplay else 0,
            'max_periods': self.gameplay.max_periods if self.gameplay else 0,
            'clock': self.gameplay.clock if self.gameplay else 0,
            'game_state': self.state_machine.state.value,
            'active_event': getattr(self.gameplay, 'active_event', None)
        }
        
        # Add analytics data if available
        if self.current_analysis:
            status['analytics'] = {
                'win_probability': self.current_analysis['win_probability'],
                'momentum': self.current_analysis['momentum']['current_state'],
                'is_critical_moment': self.current_analysis['is_critical_moment']
            }
            
        return status

    def draw(self):
        """Draw the game screen on both displays."""
        for screen in ['red', 'blue']:
            # Clear screen
            self.screen_manager.clear_screen(screen)
            current_screen = self.screen_manager.get_screen(screen)

            if self.state_machine.state == GameStates.PREGAME:
                self._draw_pregame(current_screen, screen)
            elif self.state_machine.state == GameStates.PLAYING:
                self._draw_playing(current_screen, screen)
            elif self.state_machine.state == GameStates.PAUSED:
                self._draw_paused(current_screen, screen)
            elif self.state_machine.state == GameStates.INTERMISSION:
                self._draw_intermission(current_screen, screen)
            elif self.state_machine.state == GameStates.GAME_OVER:
                self._draw_game_over(current_screen, screen)

            # Draw update notification if available
            if self.update_available:
                self.display_update_notification(current_screen)

            # Update the display
            self.screen_manager.update_display(screen)

    def _draw_pregame(self, screen, side):
        """Draw the pre-game screen for specified side."""
        if self.countdown is not None:
            self._draw_countdown(screen)
        else:
            self._draw_waiting_message(screen, side)

    def _draw_playing(self, screen, side):
        """Draw the playing state for specified side."""
        # Draw gameplay specific to this side
        if self.gameplay:
            self.gameplay.draw_for_side(screen, side)
            
            # Draw analytics overlay if enabled
            if self.settings.show_analytics_overlay:
                self._draw_analytics_overlay(screen, side)

    def _draw_paused(self, screen, side):
        """Draw the paused state for specified side."""
        # Draw gameplay in background
        if self.gameplay:
            self.gameplay.draw_for_side(screen, side)
        
        # Draw pause overlay
        pause_text = self.font_large.render("GAME PAUSED", True, (255, 255, 255))
        text_rect = pause_text.get_rect(center=(self.settings.screen_width // 2, 
                                              self.settings.screen_height // 2))
        screen.blit(pause_text, text_rect)

    def _draw_intermission(self, screen, side):
        """Draw the intermission state for specified side."""
        if self.gameplay:
            # Draw gameplay in background
            self.gameplay.draw_for_side(screen, side)
            
            # Draw intermission overlay
            if self.gameplay.intermission_clock is not None:
                time_text = f"Intermission: {int(self.gameplay.intermission_clock)}s"
                time_surface = self.font_large.render(time_text, True, (255, 255, 255))
                time_rect = time_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                        self.settings.screen_height // 2))
                screen.blit(time_surface, time_rect)

    def _draw_game_over(self, screen, side):
        """Draw the game over state for specified side."""
        if self.gameplay:
            # Draw final game state
            self.gameplay.draw_for_side(screen, side)
            
            # Draw game over overlay
            game_over_text = self.font_large.render("GAME OVER", True, (255, 255, 255))
            text_rect = game_over_text.get_rect(center=(self.settings.screen_width // 2, 
                                                      self.settings.screen_height // 2 - 40))
            screen.blit(game_over_text, text_rect)
            
            # Draw winner
            if self.gameplay.score['red'] > self.gameplay.score['blue']:
                winner = "RED TEAM WINS!"
                winner_color = (255, 0, 0) if side == 'red' else (255, 255, 255)
            elif self.gameplay.score['blue'] > self.gameplay.score['red']:
                winner = "BLUE TEAM WINS!"
                winner_color = (0, 0, 255) if side == 'blue' else (255, 255, 255)
            else:
                winner = "IT'S A TIE!"
                winner_color = (255, 255, 255)
                
            winner_text = self.font_large.render(winner, True, winner_color)
            winner_rect = winner_text.get_rect(center=(self.settings.screen_width // 2, 
                                                     self.settings.screen_height // 2 + 40))
            screen.blit(winner_text, winner_rect)

    def _draw_countdown(self, screen):
        """Draw the countdown timer."""
        countdown_text = self.font_large.render(str(self.countdown), True, (255, 255, 255))
        text_rect = countdown_text.get_rect(center=(self.settings.screen_width // 2, 
                                                  self.settings.screen_height // 2))
        screen.blit(countdown_text, text_rect)

    def _draw_waiting_message(self, screen, side):
        """Draw the waiting message for specified side."""
        if self.puck_possession == side:
            text = f"Waiting for {side.title()} Team to eject the puck..."
        else:
            text = "Waiting for puck..."
            
        text_surface = self.font_small.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                self.settings.screen_height // 2))
        screen.blit(text_surface, text_rect)

    def _draw_analytics_overlay(self, screen, side):
        """Draw analytics overlay for specified side."""
        if not self.current_analysis:
            return
            
        # Draw win probability
        win_prob = self.current_analysis['win_probability']
        prob_text = f"Win Probability: Red {win_prob['red']:.1%} - Blue {win_prob['blue']:.1%}"
        prob_surface = self.font_small.render(prob_text, True, (255, 255, 255))
        screen.blit(prob_surface, (10, 10))
        
        # Draw momentum indicator
        momentum = self.current_analysis['momentum']['current_state']
        if momentum['team']:
            momentum_text = f"Momentum: {momentum['team'].upper()} ({momentum['intensity']})"
            momentum_color = (255, 0, 0) if momentum['team'] == side else (255, 255, 255)
            momentum_surface = self.font_small.render(momentum_text, True, momentum_color)
            screen.blit(momentum_surface, (10, 40))
            
        # Draw critical moment indicator
        if self.current_analysis['is_critical_moment']:
            critical_text = "CRITICAL MOMENT!"
            critical_surface = self.font_small.render(critical_text, True, (255, 0, 0))
            screen.blit(critical_surface, (10, 70))

    def display_update_notification(self, screen):
        """Display an update notification on the game screen."""
        notification_text = "Update Available! Tap here to update."
        text_surface = self.font_large.render(notification_text, True, (255, 255, 0))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                self.settings.screen_height // 2))
        screen.blit(text_surface, text_rect)
        self.update_notification_rect = text_rect

    def initiate_update(self):
        """Initiate the update process."""
        logging.info('User initiated update from game screen.')
        
        # Display updating message on both screens
        updating_text = "Updating... Please wait."
        text_surface = self.font_large.render(updating_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                self.settings.screen_height // 2))
        
        for screen in ['red', 'blue']:
            current_screen = self.screen_manager.get_screen(screen)
            current_screen.fill((0, 0, 0))
            current_screen.blit(text_surface, text_rect)
            self.screen_manager.update_display(screen)
        
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
            # Display error message on both screens
            error_text = "Update failed. Check logs."
            error_surface = self.font_large.render(error_text, True, (255, 0, 0))
            error_rect = error_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                      self.settings.screen_height // 2 + 100))
            
            for screen in ['red', 'blue']:
                current_screen = self.screen_manager.get_screen(screen)
                current_screen.blit(error_surface, error_rect)
                self.screen_manager.update_display(screen)
            
            pygame.time.delay(3000)  # Pause for 3 seconds

    def restart_game(self):
        """Restart the game application."""
        logging.info('Restarting game...')
        pygame.quit()
        os.execv(sys.executable, ['python3'] + sys.argv)

    def cleanup(self):
        """Cleanup resources."""
        if self.analytics:
            self.analytics.cleanup()
        if self.db:
            self.db.close()
        # Clear all touch zones
        for screen in ['red', 'blue']:
            self.screen_manager.active_touch_zones[screen].clear()
        logging.info('Game resources cleaned up')
