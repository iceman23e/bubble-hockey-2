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

    def load_assets(self):
        """Load assets specific to Classic mode."""
        self.background_image = pygame.image.load('assets/classic/images/game_board.png')
        # Load other classic mode assets as needed

    def handle_event(self, event):
        """Handle events specific to Classic mode."""
        pass  # No special events in classic mode

    def update(self):
        """Update the game state."""
        # Clock always runs in Classic mode
        dt = self.game.clock.tick(60) / 1000.0
        self.clock -= dt
        if self.clock <= 0:
            self.end_period()

    def draw(self):
        """Draw the game elements."""
        # Draw the classic game board
        self.screen.blit(self.background_image, (0, 0))
        # Draw scores, clock, etc.
        super().draw()
