# classic_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging

class ClassicMode(BaseGameMode):
    """Classic game mode with standard rules."""
    def __init__(self, game):
        super().__init__(game)
        logging.info("Classic mode initialized")
        self.load_assets()
        
        # Disable power-ups and combos in classic mode
        self.power_up_active = False
        self.combo_count = 0
        
        # Set classic mode timing
        self.clock = self.settings.period_length
        self.max_periods = 3  # Standard hockey game length
        # Add new clock management variables
        self.intermission_clock = None

    def load_assets(self):
        """Load assets specific to Classic mode."""
        try:
            self.background_image = pygame.image.load('assets/classic/images/game_board.png')
            logging.debug("Classic mode assets loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load classic mode assets: {e}")
            # Use fallback color if image fails to load
            self.background_image = None

    def update(self):
        """Update the game state. In classic mode, clock always runs."""
        if self.game.state_machine.state == self.game.state_machine.states.PLAYING:
            # Always update clock in classic mode
            dt = self.game.clock.tick(60) / 1000.0
            
            if self.intermission_clock is not None:
                self.intermission_clock -= dt
                if self.intermission_clock <= 0:
                    self.intermission_clock = None
                    logging.info("Intermission ended")
            else:
                self.clock -= dt
            
            if self.clock <= 0:
                if self.game.state_machine.can('end_period'):
                    self.game.state_machine.end_period()

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

    def handle_goal(self):
        """Handle goal scoring in classic mode (no combos)."""
        # Basic goal handling without combos or power-ups
        logging.info(f"Goal scored in classic mode")
        self.last_goal_time = pygame.time.get_ticks() / 1000.0
        
        # Show simple goal notification
        self.active_event = "GOAL!"

    def handle_period_end(self):
        """Handle the end of a period in classic mode."""
        super().handle_period_end()
        logging.info(f"Classic mode period {self.period} ended")
        
        if not self.is_over:
            # Show period end message
            self.active_event = f"END OF PERIOD {self.period}"

    def handle_game_end(self):
        """Handle game end in classic mode."""
        super().handle_game_end()
        logging.info("Classic mode game ended")
        
        # Calculate final statistics
        total_goals = self.score['red'] + self.score['blue']
        avg_goals_per_period = total_goals / self.max_periods
        
        logging.info(f"Game statistics - Total goals: {total_goals}, "
                    f"Average goals per period: {avg_goals_per_period:.1f}")

    def cleanup(self):
        """Clean up classic mode resources."""
        super().cleanup()
        # Clear any classic mode specific resources
        self.background_image = None
        logging.info("Classic mode cleanup completed")
