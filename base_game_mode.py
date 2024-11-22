# base_game_mode.py

import pygame
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from game_states import GameState
from utils import load_font

class BaseGameMode:
    """
    Base class for game modes.

    The BaseGameMode class provides common functionalities and structures that
    different game modes can inherit and extend. It manages scores, periods,
    clocks, events, and analytics display, serving as the foundation for the
    game's operation.
    """

    def __init__(self, game: Any) -> None:
        """
        Initialize the base game mode.

        Args:
            game: The main game instance this mode is attached to.

        Raises:
            ValueError: If game settings are invalid.
        """
        try:
            self.game = game
            self.screen = game.screen
            self.settings = game.settings

            # Validate and initialize attributes
            self.score: Dict[str, int] = {'red': 0, 'blue': 0}
            self.period: int = 1
            self.max_periods: int = self._validate_periods(self.settings.max_periods)
            self.clock: float = self._validate_clock(self.settings.period_length)
            self.is_over: bool = False
            self.last_goal_time: Optional[datetime] = None
            self.combo_count: int = 0
            self.power_up_active: bool = False
            self.power_up_end_time: Optional[datetime] = None
            self.active_event: Optional[str] = None

            # Font references from game
            self.font_small = self._load_font('small')
            self.font_large = self._load_font('large')

            # Clock management
            self.in_overtime: bool = False
            self.intermission_clock: Optional[float] = None

            # Analytics display settings
            self.show_analytics: bool = True
            self.analytics_overlay_position: str = 'top-left'

            # Load theme-specific analytics settings
            self._load_theme_analytics_settings()

        except Exception as e:
            logging.error(f"Failed to initialize BaseGameMode: {e}")
            raise

    def _validate_periods(self, periods: int) -> int:
        """Validate the number of periods."""
        if not 1 <= periods <= 7:
            logging.warning(f"Invalid max_periods {periods}, defaulting to 3")
            return 3
        return periods

    def _validate_clock(self, period_length: float) -> float:
        """Validate the period length."""
        if period_length <= 0:
            logging.warning(f"Invalid period_length {period_length}, defaulting to 180.0")
            return 180.0
        return period_length

    def _load_font(self, size: str) -> pygame.font.Font:
        """
        Load the font with the specified size.

        Args:
            size: 'small' or 'large' indicating the font size.

        Returns:
            A pygame Font object.

        Raises:
            FileNotFoundError: If the font file is not found.
            pygame.error: If the font fails to load.
        """
        try:
            if size == 'small':
                return self.game.font_small
            elif size == 'large':
                return self.game.font_large
            else:
                raise ValueError(f"Invalid font size '{size}'")
        except Exception as e:
            logging.error(f"Error loading font '{size}': {e}")
            raise

    def _load_theme_analytics_settings(self) -> None:
        """Load analytics display settings from the current theme."""
        try:
            theme_config = self.game.theme_data
            if 'analytics' in theme_config:
                analytics_config = theme_config['analytics']
                self.analytics_overlay_position = analytics_config.get(
                    'overlay_position', 'top-left'
                )
                self.show_analytics = analytics_config.get(
                    'show_analytics', True
                )
        except Exception as e:
            logging.error(f"Error loading theme analytics settings: {e}")

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events specific to the game mode.

        Args:
            event: The pygame event to handle.
        """
        try:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and self.game.state_machine.can('pause_game'):
                    self.game.state_machine.pause_game()
                elif event.key == pygame.K_a:  # Toggle analytics overlay
                    self.show_analytics = not self.show_analytics
        except Exception as e:
            logging.error(f"Error handling event {event}: {e}")

    def update(self) -> None:
        """Update the game mode state."""
        try:
            if self.game.state_machine.state != GameState.PLAYING:
                return

            # Update clock
            dt = self.game.clock.get_time() / 1000.0
            if self.intermission_clock is not None:
                self.intermission_clock = max(0, self.intermission_clock - dt)
                if self.intermission_clock <= 0:
                    self.intermission_clock = None
                    logging.info("Intermission ended")
            else:
                self.clock = max(0, self.clock - dt)

            # Handle power-ups
            self._update_power_ups()

            # Check for period end
            if self.clock <= 0:
                if self.game.state_machine.can('end_period'):
                    self.game.state_machine.end_period()

            # Update combo timer
            self._update_combo_timer()

        except Exception as e:
            logging.error(f"Error during update in BaseGameMode: {e}")

    def draw(self) -> None:
        """Draw the game mode elements on the screen."""
        try:
            self._draw_scores()
            self._draw_period_info()
            self._draw_game_status()
            self._draw_power_up_status()
            if self.active_event:
                self._draw_active_event()

            # Draw analytics overlay if enabled
            if self.show_analytics and self.game.current_analysis:
                self._draw_analytics_overlay()

        except Exception as e:
            logging.error(f"Error during draw in BaseGameMode: {e}")

    def _draw_scores(self) -> None:
        """Draw the current score."""
        score_text = self.font_large.render(
            f"Red: {self.score['red']}  Blue: {self.score['blue']}",
            True,
            (255, 255, 255)
        )
        score_rect = score_text.get_rect(center=(self.settings.screen_width // 2, 50))
        self.screen.blit(score_text, score_rect)

    def _draw_period_info(self) -> None:
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

    def _draw_game_status(self) -> None:
        """Draw current game status information."""
        possession = self.game.puck_possession
        possession_text = (
            f"Puck Possession: {possession.capitalize()}" if possession else "Puck Possession: Unknown"
        )
        possession_surface = self.font_small.render(possession_text, True, (255, 255, 255))
        possession_rect = possession_surface.get_rect(center=(self.settings.screen_width // 2, 160))
        self.screen.blit(possession_surface, possession_rect)

    def _draw_power_up_status(self) -> None:
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

    def _draw_active_event(self) -> None:
        """Draw any active game events."""
        event_text = self.font_small.render(self.active_event, True, (255, 140, 0))
        event_rect = event_text.get_rect(center=(self.settings.screen_width // 2, 220))
        self.screen.blit(event_text, event_rect)

    def _draw_analytics_overlay(self) -> None:
        """Draw analytics overlay based on theme settings."""
        try:
            analysis = self.game.current_analysis
            y_offset = 10

            # Get position based on theme settings
            positions = {
                'top-left': (10, y_offset),
                'top-right': (self.settings.screen_width - 200, y_offset),
                'bottom-left': (10, self.settings.screen_height - 100),
                'bottom-right': (self.settings.screen_width - 200, self.settings.screen_height - 100)
            }
            x_pos, y_pos = positions.get(self.analytics_overlay_position, (10, y_offset))

            # Draw win probability
            if 'win_probability' in analysis:
                prob_text = (
                    f"Win: R {analysis['win_probability']['red']:.1%} "
                    f"B {analysis['win_probability']['blue']:.1%}"
                )
                prob_surface = self.font_small.render(prob_text, True, (255, 255, 255))
                self.screen.blit(prob_surface, (x_pos, y_pos))
                y_pos += 25

            # Draw momentum
            momentum_data = analysis.get('momentum', {}).get('current_state', {})
            if 'team' in momentum_data and 'intensity' in momentum_data:
                momentum_text = f"Momentum: {momentum_data['team'].upper()} ({momentum_data['intensity']})"
                momentum_surface = self.font_small.render(momentum_text, True, (255, 140, 0))
                self.screen.blit(momentum_surface, (x_pos, y_pos))
                y_pos += 25

            # Draw scoring patterns
            patterns = analysis.get('patterns', {})
            if 'current_run' in patterns and patterns['current_run'].get('length', 0) > 1:
                run = patterns['current_run']
                run_text = f"Scoring Run: {run['team'].upper()} x{run['length']}"
                run_surface = self.font_small.render(run_text, True, (255, 255, 0))
                self.screen.blit(run_surface, (x_pos, y_pos))

        except Exception as e:
            logging.error(f"Error drawing analytics overlay: {e}")

    def _update_power_ups(self) -> None:
        """Update power-up status."""
        if self.power_up_active and self.power_up_end_time:
            if datetime.now() >= self.power_up_end_time:
                self.power_up_active = False
                self.power_up_end_time = None
                self._on_power_up_end()

    def _on_power_up_end(self) -> None:
        """Handle power-up expiration."""
        logging.info("Power-up expired")
        self.active_event = None

    def _update_combo_timer(self) -> None:
        """Update combo timer if combo system is enabled."""
        if not self.settings.combo_goals_enabled:
            return

        if self.last_goal_time and self.combo_count > 0:
            time_since_last = (datetime.now() - self.last_goal_time).total_seconds()
            if time_since_last > self.settings.combo_time_window:
                self.combo_count = 0

    def handle_goal(self, team: str) -> None:
        """
        Handle goal scoring logic.

        Args:
            team: The team that scored ('red' or 'blue').

        Raises:
            ValueError: If the team name is invalid.
        """
        try:
            if team not in ['red', 'blue']:
                raise ValueError(f"Invalid team name '{team}'")

            current_time = datetime.now()

            # Basic goal handling
            if self.settings.combo_goals_enabled and self.last_goal_time:
                time_since_last = (current_time - self.last_goal_time).total_seconds()
                if time_since_last <= self.settings.combo_time_window:
                    self.combo_count = min(self.combo_count + 1, self.settings.combo_max_stack)
                    if self.combo_count > 1:
                        self.active_event = f"COMBO x{self.combo_count}!"
                else:
                    self.combo_count = 1
            else:
                self.combo_count = 1

            self.last_goal_time = current_time

            # Update score
            self.score[team] += 1

            logging.info(f"Goal scored by {team} team. Current score: Red {self.score['red']}, Blue {self.score['blue']}")

        except Exception as e:
            logging.error(f"Error handling goal for team '{team}': {e}")

    def handle_period_end(self) -> None:
        """Handle the end of a period."""
        try:
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
        except Exception as e:
            logging.error(f"Error handling period end: {e}")

    def handle_game_end(self) -> None:
        """Handle the end of the game."""
        try:
            if self.score['red'] > self.score['blue']:
                winner = 'red'
            elif self.score['blue'] > self.score['red']:
                winner = 'blue'
            else:
                winner = 'tie'

            if winner != 'tie':
                logging.info(f"Game ended. Winner: {winner}")
                self.active_event = f"{winner.upper()} TEAM WINS!"
            else:
                logging.info("Game ended in a tie.")
                self.active_event = "GAME ENDED IN A TIE!"
        except Exception as e:
            logging.error(f"Error handling game end: {e}")

    def handle_critical_moment(self, analysis: Dict[str, Any]) -> None:
        """
        Handle critical game moments identified by analytics.

        Args:
            analysis: The current analysis data from the analytics engine.
        """
        try:
            if analysis.get('is_critical_moment'):
                momentum_data = analysis.get('momentum', {}).get('current_state', {})
                if momentum_data.get('intensity') == 'overwhelming':
                    self.active_event = "CRITICAL MOMENT - MOMENTUM SHIFT!"
                elif self.clock <= 60 and abs(self.score['red'] - self.score['blue']) <= 1:
                    self.active_event = "CRITICAL MOMENT - CLOSE GAME!"
        except Exception as e:
            logging.error(f"Error handling critical moment: {e}")

    def activate_power_up(self, duration: float) -> None:
        """
        Activate a power-up for the specified duration.

        Args:
            duration: Duration of the power-up in seconds.

        Raises:
            ValueError: If the duration is invalid.
        """
        try:
            if duration <= 0:
                raise ValueError("Power-up duration must be positive")
            self.power_up_active = True
            self.power_up_end_time = datetime.now() + timedelta(seconds=duration)
            logging.info(f"Power-up activated for {duration} seconds")
        except Exception as e:
            logging.error(f"Error activating power-up: {e}")

    def cleanup(self) -> None:
        """Clean up resources if needed."""
        try:
            # Perform any necessary cleanup
            logging.info("BaseGameMode cleanup completed")
        except Exception as e:
            logging.error(f"Error during cleanup in BaseGameMode: {e}")
