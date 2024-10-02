# base_game_mode.py

import pygame
import logging
from datetime import datetime, timedelta

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
        self.font_small = self.game.font_small
        self.font_large = self.game.font_large

    def handle_event(self, event):
        """Handle events specific to the game mode."""
        pass  # To be implemented in subclasses

    def update(self):
        """Update the game mode state."""
        pass  # To be implemented in subclasses

    def draw(self):
        """Draw the game mode elements on the screen."""
        # Draw scores
        score_text = self.font_large.render(f"Red: {self.score['red']}  Blue: {self.score['blue']}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.settings.screen_width // 2, 50))
        self.screen.blit(score_text, score_rect)
        # Draw period and time
        period_text = self.font_small.render(f"Period: {self.period}/{self.max_periods}", True, (255, 255, 255))
        period_rect = period_text.get_rect(center=(self.settings.screen_width // 2, 100))
        self.screen.blit(period_text, period_rect)
        clock_text = self.font_small.render(f"Time Remaining: {int(self.clock)}s", True, (255, 255, 255))
        clock_rect = clock_text.get_rect(center=(self.settings.screen_width // 2, 130))
        self.screen.blit(clock_text, clock_rect)
        # Display puck possession
        possession_text = f"Puck Possession: {self.game.puck_possession.capitalize() if self.game.puck_possession else 'Unknown'}"
        possession_surface = self.font_small.render(possession_text, True, (255, 255, 255))
        possession_rect = possession_surface.get_rect(center=(self.settings.screen_width // 2, 160))
        self.screen.blit(possession_surface, possession_rect)

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

    def cleanup(self):
        """Clean up resources if needed."""
        pass
