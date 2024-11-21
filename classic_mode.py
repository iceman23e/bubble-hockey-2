# classic_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging
from datetime import datetime

class ClassicMode(BaseGameMode):
    """Classic game mode with standard rules."""

    def __init__(self, game):
        """Initialize the classic game mode."""
        super().__init__(game)
        logging.info("Classic mode initialized")
        self.load_assets()

        # Disable power-ups and combos in classic mode
        self.power_up_active = False
        self.combo_count = 0

        # Set classic mode timing
        self.clock = self.settings.period_length
        self.max_periods = 3  # Standard hockey game length

        # Add clock management variables
        self.intermission_clock = None

        # Classic mode analytics configuration
        self.show_analytics = self.settings.classic_mode_analytics
        self.analytics_overlay_position = 'top-right'  # Classic mode default position

        # Initialize last goal time
        self.last_goal_time = None

    def load_assets(self):
        """Load assets specific to Classic mode."""
        try:
            self.background_image = pygame.image.load('assets/classic/images/game_board.png')
            self.board_overlay = pygame.image.load('assets/classic/images/board_overlay.png')
            logging.debug("Classic mode assets loaded successfully")
        except pygame.error as e:
            logging.error(f"Failed to load classic mode assets: {e}")
            self.background_image = None
            self.board_overlay = None
            self._init_fallback_assets()

    def _init_fallback_assets(self):
        """Initialize basic shapes as fallback assets."""
        self.background_image = pygame.Surface(
            (self.settings.screen_width, self.settings.screen_height)
        )
        self.background_image.fill(self.settings.bg_color)

    def handle_event(self, event):
        """Handle events specific to Classic mode.

        Args:
            event (pygame.event.Event): The event to handle.
        """
        super().handle_event(event)
        # Add any classic mode specific event handling if needed

    def update(self):
        """Update the game state. In classic mode, clock always runs."""
        if self.game.state_machine.state == self.game.state_machine.states.PLAYING:
            # Update clock
            dt = self.game.clock.get_time() / 1000.0

            if self.intermission_clock is not None:
                self.intermission_clock -= dt
                if self.intermission_clock <= 0:
                    self.intermission_clock = None
                    logging.info("Intermission ended")
            else:
                self.clock -= dt

            # Check for period end
            if self.clock <= 0:
                if self.game.state_machine.can('end_period'):
                    self.game.state_machine.end_period()
        else:
            # Handle other states if necessary
            pass

        # Call base class update for any additional updates
        super().update()

    def draw(self):
        """Draw the classic game elements."""
        # Draw background
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill(self.settings.bg_color)

        # Draw base game elements (score, clock, etc.)
        super().draw()

        # Draw classic mode specific elements
        self._draw_classic_elements()

        # Draw board overlay
        if self.board_overlay:
            self.screen.blit(self.board_overlay, (0, 0))

    def _draw_classic_elements(self):
        """Draw elements specific to classic mode."""
        # Draw period indicator
        period_text = self.font_small.render(
            f"Period {self.period} of {self.max_periods}",
            True,
            (255, 255, 255)
        )
        period_rect = period_text.get_rect(
            center=(self.settings.screen_width // 2, self.settings.screen_height - 30)
        )
        self.screen.blit(period_text, period_rect)

    def handle_goal(self, team):
        """Handle goal scoring in classic mode.

        Args:
            team (str): The team that scored ('red' or 'blue').
        """
        # Call parent class goal handling first
        super().handle_goal(team)

        # Basic goal handling without combos or power-ups
        logging.info(f"Goal scored in classic mode by team {team}")

        # Record goal time for analytics
        self.last_goal_time = datetime.now()

        # Show simple goal notification
        self.active_event = "GOAL!"

        # Play goal sound if available
        if self.game.sounds_enabled and self.game.sounds.get('goal'):
            self.game.sounds['goal'].play()

        # Update analytics after goal
        if self.game.current_analysis:
            analysis = self.game.current_analysis
            if analysis and analysis.get('is_critical_moment'):
                self.handle_critical_moment(analysis)

    def handle_critical_moment(self, analysis):
        """Handle critical moments in classic mode.

        Args:
            analysis (dict): The current analysis data from the analytics engine.
        """
        # In classic mode, only show critical moment alerts for:
        # 1. Final minute in close game
        # 2. Tie-breaking goals
        score_diff = abs(self.score['red'] - self.score['blue'])
        if self.clock <= 60 and score_diff <= 1:
            self.active_event = "FINAL MINUTE - CLOSE GAME!"
        elif score_diff == 1:
            self.active_event = "TIE BROKEN!"

    def handle_period_end(self):
        """Handle the end of a period in classic mode."""
        super().handle_period_end()
        logging.info(f"Classic mode period {self.period} ended")

        if not self.is_over:
            # Show period end message
            self.active_event = f"END OF PERIOD {self.period}"

            # Play period end sound
            if self.game.sounds_enabled and self.game.sounds.get('period_end'):
                self.game.sounds['period_end'].play()

    def handle_game_end(self):
        """Handle game end in classic mode."""
        super().handle_game_end()
        logging.info("Classic mode game ended")

        # Calculate final statistics
        total_goals = self.score['red'] + self.score['blue']
        avg_goals_per_period = total_goals / self.max_periods

        logging.info(f"Game statistics - Total goals: {total_goals}, "
                     f"Average goals per period: {avg_goals_per_period:.1f}")

        # Play game over sound
        if self.game.sounds_enabled and self.game.sounds.get('game_over'):
            self.game.sounds['game_over'].play()

    def cleanup(self):
        """Clean up classic mode resources."""
        super().cleanup()
        # Clear any classic mode specific resources
        self.background_image = None
        self.board_overlay = None
        logging.info("Classic mode cleanup completed")

    def _draw_analytics_overlay(self):
        """Override analytics overlay for classic mode - simplified version."""
        if not self.show_analytics or not self.game.current_analysis:
            return

        analysis = self.game.current_analysis
        x_pos = self.settings.screen_width - 180  # Classic mode fixed position
        y_pos = 10

        # Only show win probability in classic mode
        if 'win_probability' in analysis:
            prob = analysis['win_probability']
            prob_text = "Win Probability:"
            red_text = f"Red: {prob['red']:.1%}"
            blue_text = f"Blue: {prob['blue']:.1%}"

            text_surface = self.font_small.render(prob_text, True, (255, 255, 255))
            self.screen.blit(text_surface, (x_pos, y_pos))

            red_surface = self.font_small.render(red_text, True, (255, 0, 0))
            self.screen.blit(red_surface, (x_pos, y_pos + 25))

            blue_surface = self.font_small.render(blue_text, True, (0, 0, 255))
            self.screen.blit(blue_surface, (x_pos, y_pos + 50))
