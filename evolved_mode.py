# evolved_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging
import random

class EvolvedMode(BaseGameMode):
    """Evolved game mode with additional features."""
    def __init__(self, game):
        super().__init__(game)
        logging.info("Evolved mode initialized")
        self.load_assets()
        self.taunt_timer = 0

    def load_assets(self):
        """Load assets specific to Evolved mode."""
        self.background_image = pygame.image.load('assets/evolved/images/jumbotron.png')
        # Load other evolved mode assets

    def handle_event(self, event):
        """Handle events specific to Evolved mode."""
        pass  # Handle any evolved mode events

    def update(self):
        """Update the game state."""
        # Clock runs only when puck is in play
        if self.game.puck_possession == 'in_play':
            dt = self.game.clock.tick(60) / 1000.0
            self.clock -= dt
            # Handle taunts
            self.taunt_timer += dt
            if self.taunt_timer >= self.settings.taunt_frequency:
                self.play_random_taunt()
                self.taunt_timer = 0
        else:
            # Puck not in play; maintain frame rate without decrementing clock
            self.game.clock.tick(60)

        if self.clock <= 0:
            self.end_period()

    def draw(self):
        """Draw the game elements."""
        # Draw the evolved mode background
        self.screen.blit(self.background_image, (0, 0))
        # Draw scores, clock, etc.
        super().draw()

    def play_random_taunt(self):
        """Play a random taunt sound."""
        if self.game.sounds_enabled and self.game.sounds['taunts']:
            taunt_sound = random.choice(self.game.sounds['taunts'])
            taunt_sound.play()
            logging.info("Taunt sound played")
