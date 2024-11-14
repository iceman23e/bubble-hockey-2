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
        # Initialize random sound timing variables
        self.last_random_sound_time = pygame.time.get_ticks() / 1000.0  # Time in seconds
        self.next_random_sound_interval = self.get_next_random_sound_interval()

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
            current_time = pygame.time.get_ticks() / 1000.0
            if current_time - self.last_random_sound_time >= self.next_random_sound_interval:
                self.play_random_sound()
                self.last_random_sound_time = current_time
                self.next_random_sound_interval = self.get_next_random_sound_interval()
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

    def get_next_random_sound_interval(self):
        """Get the next random sound interval."""
        min_interval = self.game.settings.random_sound_min_interval
        max_interval = self.game.settings.random_sound_max_interval
        return random.uniform(min_interval, max_interval)
