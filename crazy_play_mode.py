# crazy_play_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging
import random

class CrazyPlayMode(BaseGameMode):
    """Crazy Play mode with unpredictable elements."""
    def __init__(self, game):
        super().__init__(game)
        logging.info("Crazy Play mode initialized")
        self.load_assets()
        self.random_sound_timer = 0

    def load_assets(self):
        """Load assets specific to Crazy Play mode."""
        self.background_image = pygame.image.load('assets/crazy_play/images/crazy_background.png')
        # Load other crazy play mode assets

    def handle_event(self, event):
        """Handle events specific to Crazy Play mode."""
        pass  # Handle any crazy play mode events

    def update(self):
        """Update the game state."""
        # Clock runs only when puck is in play
        if self.game.puck_possession == 'in_play':
            dt = self.game.clock.tick(60) / 1000.0
            self.clock -= dt
            # Handle random sounds
            self.random_sound_timer += dt
            if self.random_sound_timer >= self.settings.random_sound_frequency:
                self.play_random_sound()
                self.random_sound_timer = 0
        else:
            # Puck not in play; maintain frame rate without decrementing clock
            self.game.clock.tick(60)

        if self.clock <= 0:
            self.end_period()

    def draw(self):
        """Draw the game elements."""
        # Draw the crazy play mode background
        self.screen.blit(self.background_image, (0, 0))
        # Draw scores, clock, etc.
        super().draw()

    def play_random_sound(self):
        """Play a random sound."""
        if self.game.sounds_enabled and self.game.sounds['random_sounds']:
            random_sound = random.choice(self.game.sounds['random_sounds'])
            random_sound.play()
            logging.info("Random sound played")
