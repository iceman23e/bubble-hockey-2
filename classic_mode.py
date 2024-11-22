# classic_mode.py

import pygame
import logging
from datetime import datetime
from typing import Optional
from base_game_mode import BaseGameMode
from utils import load_image

class ClassicMode(BaseGameMode):
    """
    Classic game mode with standard rules and gameplay.

    The ClassicMode class extends the BaseGameMode to provide a traditional
    bubble hockey experience without power-ups or special features. It focuses
    on fundamental gameplay mechanics, making it suitable for players seeking
    a standard game.

    Features:
    - Standard scoring without multipliers or bonuses
    - Fixed game periods and timing
    - Minimal analytics display
    - Simple visual elements with fallback options
    """

    def __init__(self, game):
        """
        Initialize the classic game mode.

        Args:
            game: The main game instance this mode is attached to.

        Raises:
            ValueError: If game settings are invalid.
            pygame.error: If critical assets fail to load.
            OSError: If required asset directories are not accessible.
        """
        try:
            super().__init__(game)
            logging.info("ClassicMode initialized")

            # Disable power-ups and combos in classic mode
            self.power_up_active: bool = False
            self.combo_count: int = 0

            # Set classic mode timing
            self.clock: float = self._validate_clock(self.settings.period_length)
            self.max_periods: int = self._validate_periods(3)  # Standard hockey game length

            # Clock management variables
            self.intermission_clock: Optional[float] = None

            # Classic mode analytics configuration
            self.show_analytics: bool = self.settings.classic_mode_analytics
            self.analytics_overlay_position: str = 'top-right'  # Classic mode default position

            # Initialize last goal time for analytics tracking
            self.last_goal_time: Optional[datetime] = None

            # Load assets
            self.load_assets()

        except Exception as e:
            logging.error(f"Failed to initialize ClassicMode: {e}")
            raise

    # Validation methods
    def _validate_clock(self, time: float) -> float:
        """Validate clock time is within acceptable range."""
        if not 60 <= time <= 600:
            logging.warning(f"Invalid clock time {time}, using default of 180")
            return 180.0
        return float(time)

    def _validate_periods(self, periods: int) -> int:
        """Validate number of periods is reasonable."""
        if not 1 <= periods <= 7:
            logging.warning(f"Invalid periods {periods}, using default of 3")
            return 3
        return periods

    def load_assets(self) -> None:
        """
        Load assets specific to Classic mode.

        Raises:
            pygame.error: If assets fail to load.
            FileNotFoundError: If asset files are missing.
            OSError: If asset directories are not accessible.
        """
        try:
            self.background_image = load_image('assets/classic/images/game_board.png')
            self.board_overlay = load_image('assets/classic/images/board_overlay.png')

            if self.background_image is None or self.board_overlay is None:
                raise pygame.error("Failed to load one or more classic mode assets.")

            logging.debug("Classic mode assets loaded successfully")

        except (pygame.error, FileNotFoundError, OSError) as e:
            logging.error(f"Failed to load classic mode assets: {e}")
            self._init_fallback_assets()

    def _init_fallback_assets(self) -> None:
        """Initialize basic shapes as fallback assets."""
        self.background_image = pygame.Surface(
            (self.settings.screen_width, self.settings.screen_height)
        )
        self.background_image.fill(self.settings.bg_color)
        self.board_overlay = None
        logging.warning("Using fallback assets for ClassicMode.")

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events specific to Classic mode.

        Args:
            event: The pygame event to handle.
        """
        super().handle_event(event)
        # Add any classic mode specific event handling if needed

    def update(self) -> None:
        """
        Update the game state.

        In classic mode, the clock always runs during the PLAYING state.
        """
        try:
            if self.game.state_machine.state == self.game.state_machine.states.PLAYING:
                # Update clock
                dt = self.game.clock.get_time() / 1000.0

                if self.intermission_clock is not None:
                    self.intermission_clock -= dt
                    if self.intermission_clock <= 0:
                        self.intermission_clock = None
                        logging.info("Intermission ended")
                else:
                    self.clock = max(0, self.clock - dt)

                # Check for period end
                if self.clock <= 0:
                    if self.game.state_machine.can('end_period'):
                        self.game.state_machine.end_period()

            # Call base class update for any additional updates
            super().update()

        except Exception as e:
            logging.error(f"Error during update in ClassicMode: {e}")

    def draw(self) -> None:
        """
        Draw the classic game elements.

        Renders the background, base game elements, classic mode specific elements,
        and the board overlay.
        """
        try:
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

        except Exception as e:
            logging.error(f"Error during draw in ClassicMode: {e}")

    def _draw_classic_elements(self) -> None:
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

    def handle_goal(self, team: str) -> None:
        """
        Handle goal scoring in classic mode.

        Args:
            team: The team that scored ('red' or 'blue').
        """
        try:
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

        except Exception as e:
            logging.error(f"Error handling goal in ClassicMode: {e}")

    def _check_critical_moments(self) -> None:
        """Check and handle critical game moments based on analytics."""
        try:
            analysis = self.game.current_analysis
            if not analysis.get('is_critical_moment'):
                return

            score_diff = abs(self.score['red'] - self.score['blue'])

            # Only show notifications for significant moments
            if self.clock <= 60 and score_diff <= 1:
                self.active_event = "FINAL MINUTE!"
            elif (
                score_diff == 1 and
                self.period == self.max_periods and
                self.clock <= 120
            ):
                self.active_event = "TIE BROKEN!"

        except Exception as e:
            logging.error(f"Error in _check_critical_moments: {e}")

    def _draw_classic_analytics(self) -> None:
        """Draw minimal analytics overlay for classic mode."""
        try:
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

        except Exception as e:
            logging.error(f"Error in _draw_classic_analytics: {e}")

    def handle_period_end(self) -> None:
        """Handle the end of a period in classic mode."""
        try:
            super().handle_period_end()
            logging.info(f"Classic mode period {self.period} ended")

            if not self.is_over:
                # Show period end message
                self.active_event = f"END OF PERIOD {self.period}"

                # Play period end sound
                if self.game.sounds_enabled and self.game.sounds.get('period_end'):
                    self.game.sounds['period_end'].play()

        except Exception as e:
            logging.error(f"Error handling period end in ClassicMode: {e}")

    def handle_game_end(self) -> None:
        """Handle game end in classic mode."""
        try:
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

        except Exception as e:
            logging.error(f"Error handling game end in ClassicMode: {e}")

    def cleanup(self) -> None:
        """Clean up classic mode resources."""
        try:
            super().cleanup()
            # Clear any classic mode specific resources
            if self.background_image:
                self.background_image = None
            if self.board_overlay:
                self.board_overlay = None
            logging.info("ClassicMode cleanup completed")
        except Exception as e:
            logging.error(f"Error during cleanup in ClassicMode: {e}")
