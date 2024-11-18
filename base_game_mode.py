# base_game_mode.py

import pygame
import logging
from datetime import datetime, timedelta
from game_states import GameState

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
        self.active_event = None
        self.font_small = self.game.font_small
        self.font_large = self.game.font_large
        # New clock management variables
        self.in_overtime = False
        self.intermission_clock = None

    def handle_event(self, event):
        """Handle events specific to the game mode."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p and self.game.state_machine.can('pause_game'):
                self.game.state_machine.pause_game()

    def update(self):
        """Update the game mode state."""
        if self.game.state_machine.state != GameState.PLAYING:
            return

        # Update clock
        dt = self.game.clock.get_time() / 1000.0
        if self.intermission_clock is not None:
            self.intermission_clock -= dt
            if self.intermission_clock <= 0:
                self.intermission_clock = None
                logging.info("Intermission ended")
        else:
            self.clock -= dt

        # Handle power-ups
        self._update_power_ups(dt)

        # Check for period end
        if self.clock <= 0:
            if self.game.state_machine.can('end_period'):
                self.game.state_machine.end_period()

        # Update combo timer
        self._update_combo_timer(dt)

    def draw(self):
        """Draw the game mode elements on the screen."""
        self._draw_scores()
        self._draw_period_info()
        self._draw_game_status()
        self._draw_power_up_status()
        if self.active_event:
            self._draw_active_event()

    def _draw_scores(self):
        """Draw the current score."""
        score_text = self.font_large.render(
            f"Red: {self.score['red']}  Blue: {self.score['blue']}", 
            True, 
            (255, 255, 255)
        )
        score_rect = score_text.get_rect(center=(self.settings.screen_width // 2, 50))
        self.screen.blit(score_text, score_rect)

    def _draw_period_info(self):
        """Draw period and time information."""
        if self.in_overtime:
            period_text = self.font_small.render("OVERTIME", True, (255, 255, 255))
        else:
            period_text = self.font_small.render(
                f"Period: {self.period}/{self.max_periods}", 
                True, 
                (255, 255, 255)
            )
        period_rect = period_text.get_rect(center=(self.settings.screen_width // 2, 100))
        self.screen.blit(period_text, period_rect)

        if self.intermission_clock is not None:
            time_text = f"Intermission: {int(self.intermission_clock)}s"
        else:
            time_text = f"Time Remaining: {int(self.clock)}s"
        clock_text = self.font_small.render(time_text, True, (255, 255, 255))
        clock_rect = clock_text.get_rect(center=(self.settings.screen_width // 2, 130))
        self.screen.blit(clock_text, clock_rect)

    def _draw_game_status(self):
        """Draw current game status information."""
        possession_text = (f"Puck Possession: "
                         f"{self.game.puck_possession.capitalize() if self.game.puck_possession else 'Unknown'}")
        possession_surface = self.font_small.render(possession_text, True, (255, 255, 255))
        possession_rect = possession_surface.get_rect(center=(self.settings.screen_width // 2, 160))
        self.screen.blit(possession_surface, possession_rect)

    def _draw_power_up_status(self):
        """Draw power-up status if active."""
        if self.power_up_active and self.power_up_end_time:
            time_remaining = max(0, (self.power_up_end_time - datetime.now()).total_seconds())
            power_up_text = self.font_small.render(
                f"Power Up: {int(time_remaining)}s", 
                True, 
                (255, 255, 0)
            )
            power_up_rect = power_up_text.get_rect(center=(self.settings.screen_width // 2, 190))
            self.screen.blit(power_up_text, power_up_rect)

    def _draw_active_event(self):
        """Draw any active game events."""
        event_text = self.font_small.render(self.active_event, True, (255, 140, 0))
        event_rect = event_text.get_rect(center=(self.settings.screen_width // 2, 220))
        self.screen.blit(event_text, event_rect)

    def _update_power_ups(self, dt):
        """Update power-up status."""
        if self.power_up_active:
            if datetime.now() >= self.power_up_end_time:
                self.power_up_active = False
                self.power_up_end_time = None
                self._on_power_up_end()

    def _update_combo_timer(self, dt):
        """Update combo timer if combo system is enabled."""
        if not self.settings.combo_goals_enabled:
            return

        if self.last_goal_time and self.combo_count > 0:
            time_since_last_goal = (datetime.now() - self.last_goal_time).total_seconds()
            if time_since_last_goal > self.settings.combo_time_window:
                self.combo_count = 0

    def handle_goal(self):
        """Handle goal scoring logic."""
        current_time = datetime.now()
        
        # Check for combo
        if self.settings.combo_goals_enabled and self.last_goal_time:
            time_since_last_goal = (current_time - self.last_goal_time).total_seconds()
            if time_since_last_goal <= self.settings.combo_time_window:
                self.combo_count = min(self.combo_count + 1, self.settings.combo_max_stack)
                if self.combo_count > 1:
                    self.active_event = f"COMBO x{self.combo_count}!"
            else:
                self.combo_count = 1
        else:
            self.combo_count = 1

        self.last_goal_time = current_time

    def handle_period_end(self):
        """Handle the end of a period."""
        if self.period < self.max_periods:
            self.period += 1
            self.clock = self.settings.period_length
            self.intermission_clock = self.settings.intermission_length
            logging.info(f"Starting period {self.period}")
            if self.game.state_machine.can('start_intermission'):
                self.game.state_machine.start_intermission()
        elif not self.in_overtime and self.score['red'] == self.score['blue']:
            # Start overtime
            self.in_overtime = True
            self.clock = self.settings.overtime_length
            self.intermission_clock = self.settings.intermission_length
            logging.info("Game tied - going to overtime")
            if self.game.state_machine.can('start_intermission'):
                self.game.state_machine.start_intermission()
        else:
            self.is_over = True
            if self.game.state_machine.can('end_game'):
                self.game.state_machine.end_game()
            logging.info("Game over")

    def handle_game_end(self):
        """Handle the end of the game."""
        winner = 'red' if self.score['red'] > self.score['blue'] else 'blue'
        logging.info(f"Game ended. Winner: {winner}")
        self.active_event = f"{winner.upper()} TEAM WINS!"

    def activate_power_up(self, duration):
        """Activate a power-up for the specified duration."""
        self.power_up_active = True
        self.power_up_end_time = datetime.now() + timedelta(seconds=duration)

    def _on_power_up_end(self):
        """Handle power-up expiration."""
        logging.info("Power-up expired")
        self.active_event = None

    def cleanup(self):
        """Clean up resources if needed."""
        pass
