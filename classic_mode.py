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

        # Initialize last goal time for analytics tracking
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

        # Draw base game elements
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

        # Draw analytics if enabled
        if self.show_analytics and self.game.current_analysis:
            self._draw_classic_analytics()

    def handle_goal(self, team):
        """Handle goal scoring in classic mode.

        Args:
            team (str): The team that scored ('red' or 'blue').
        """
        # Record current time for analytics
        current_time = datetime.now()
        
        # Basic goal handling
        logging.info(f"Goal scored in classic mode by team {team}")

        # Record goal time for analytics tracking
        self.last_goal_time = current_time

        # Call parent class goal handling
        super().handle_goal(team)

        # Show simple goal notification
        self.active_event = "GOAL!"

        # Play goal sound
        if self.game.sounds_enabled and self.game.sounds.get('goal'):
            self.game.sounds['goal'].play()

        # Check for critical moments in analytics
        if self.game.current_analysis:
            self._check_critical_moments()

    def _check_critical_moments(self):
        """Check and handle critical game moments based on analytics."""
        if not self.game.current_analysis.get('is_critical_moment'):
            return

        score_diff = abs(self.score['red'] - self.score['blue'])
        
        # Only show notifications for significant moments
        if self.clock <= 60 and score_diff <= 1:
            self.active_event = "FINAL MINUTE!"
        elif (score_diff == 1 and 
              self.period == self.max_periods and 
              self.clock <= 120):
            self.active_event = "TIE BROKEN!"

    def _draw_classic_analytics(self):
        """Draw minimal analytics overlay for classic mode."""
        if not self.game.current_analysis:
            return

        analysis = self.game.current_analysis
        
        # Only show win probability in top-right corner
        if 'win_probability' in analysis:
            x_pos = self.settings.screen_width - 180
            y_pos = 10

            prob = analysis['win_probability']
            win_prob_text = f"Win Prob: R {prob['red']:.0%} B {prob['blue']:.0%}"
            win_prob_surface = self.font_small.render(win_prob_text, True, (255, 255, 255))
            win_prob_surface.set_alpha(180)  # Slightly transparent
            self.screen.blit(win_prob_surface, (x_pos, y_pos))

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
