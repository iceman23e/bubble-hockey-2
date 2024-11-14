# crazy_play_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging
import random
from datetime import datetime, timedelta

class CrazyPlayMode(BaseGameMode):
    """Crazy Play mode with unpredictable elements."""
    def __init__(self, game):
        super().__init__(game)
        logging.info("Crazy Play mode initialized")
        self.load_assets()
        
        # Initialize crazy play specific features
        self.random_timer = 0
        self.next_random_event = self._get_next_random_time()
        self.active_effects = []
        self.current_modifier = 1.0
        self.gravity_reversed = False
        self.chaos_level = 0
        
        # Override base settings for crazy mode
        self.max_periods = 5  # Longer games in crazy mode
        self.clock = self.settings.period_length * 1.5  # 50% longer periods
        
        # Enable all features
        self.random_events_enabled = True
        self.power_ups_enabled = True
        self.combos_enabled = True

    def load_assets(self):
        """Load assets specific to Crazy Play mode."""
        try:
            # Load backgrounds for different chaos levels
            self.backgrounds = {
                'normal': pygame.image.load('assets/crazy_play/images/background_normal.png'),
                'chaos': pygame.image.load('assets/crazy_play/images/background_chaos.png'),
                'extreme': pygame.image.load('assets/crazy_play/images/background_extreme.png')
            }
            
            # Load effect overlays
            self.effect_overlays = {
                'gravity': pygame.image.load('assets/crazy_play/images/gravity_overlay.png'),
                'speed': pygame.image.load('assets/crazy_play/images/speed_overlay.png'),
                'multiplier': pygame.image.load('assets/crazy_play/images/multiplier_overlay.png')
            }
            
            logging.debug("Crazy Play mode assets loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Crazy Play mode assets: {e}")
            self.backgrounds = {}
            self.effect_overlays = {}

    def update(self):
        """Update the game state with crazy elements."""
        if self.game.state_machine.state != self.game.state_machine.states.PLAYING:
            return

        # Update base game elements
        super().update()
        
        # Update only when puck is in play
        if self.game.puck_possession == 'in_play':
            dt = self.game.clock.tick(60) / 1000.0
            
            # Update random event timer
            self.random_timer += dt
            if self.random_timer >= self.next_random_event:
                self._trigger_random_event()
                self.random_timer = 0
                self.next_random_event = self._get_next_random_time()
            
            # Update active effects
            self._update_active_effects(dt)
            
            # Update chaos level
            self._update_chaos_level()
        else:
            self.game.clock.tick(60)

    def _get_next_random_time(self):
        """Get time until next random event based on chaos level."""
        base_time = max(5, 30 - (self.chaos_level * 3))
        return random.uniform(base_time * 0.5, base_time)

    def _trigger_random_event(self):
        """Trigger a random crazy event."""
        events = [
            self._reverse_gravity,
            self._multiply_scores,
            self._speed_burst,
            self._bonus_powerup,
            self._chaos_mode
        ]
        event = random.choice(events)
        event()
        logging.info(f"Triggered random event: {event.__name__}")

    def _update_active_effects(self, dt):
        """Update all active effects."""
        current_time = datetime.now()
        remaining_effects = []
        
        for effect in self.active_effects:
            if current_time < effect['end_time']:
                remaining_effects.append(effect)
            else:
                self._end_effect(effect)
        
        self.active_effects = remaining_effects

    def _end_effect(self, effect):
        """End an active effect."""
        effect_type = effect['type']
        if effect_type == 'gravity':
            self.gravity_reversed = False
        elif effect_type == 'multiplier':
            self.current_modifier = 1.0
        
        logging.info(f"Effect ended: {effect_type}")

    def _update_chaos_level(self):
        """Update the chaos level based on game progress."""
        total_score = self.score['red'] + self.score['blue']
        self.chaos_level = min(10, total_score // 5)

    def _add_effect(self, effect_type, duration):
        """Add a new effect."""
        end_time = datetime.now() + timedelta(seconds=duration)
        self.active_effects.append({
            'type': effect_type,
            'end_time': end_time
        })
        logging.info(f"Added effect: {effect_type}, duration: {duration}s")

    # Random event implementations
    def _reverse_gravity(self):
        """Reverse gravity effect."""
        self.gravity_reversed = not self.gravity_reversed
        self._add_effect('gravity', 10)
        self.active_event = "GRAVITY REVERSED!"

    def _multiply_scores(self):
        """Multiply all scores for a period."""
        self.current_modifier = 2.0
        self._add_effect('multiplier', 15)
        self.active_event = "DOUBLE POINTS!"

    def _speed_burst(self):
        """Increase game speed temporarily."""
        self._add_effect('speed', 8)
        self.active_event = "SPEED BURST!"

    def _bonus_powerup(self):
        """Spawn multiple power-ups."""
        for _ in range(3):
            self.spawn_power_up()
        self.active_event = "POWER-UP FRENZY!"

    def _chaos_mode(self):
        """Enter temporary chaos mode."""
        self.chaos_level = 10
        self._add_effect('chaos', 20)
        self.active_event = "CHAOS MODE ACTIVATED!"

    def handle_goal(self):
        """Handle goal scoring with crazy modifiers."""
        # Apply current score modifier
        super().handle_goal()
        
        if self.current_modifier != 1.0:
            for team in ['red', 'blue']:
                self.score[team] = int(self.score[team] * self.current_modifier)
        
        # Increase chaos with each goal
        self.chaos_level = min(10, self.chaos_level + 1)
        logging.info(f"Goal scored with modifier: {self.current_modifier}, Chaos level: {self.chaos_level}")

    def draw(self):
        """Draw the crazy play elements."""
        # Draw appropriate background based on chaos level
        background_key = 'normal'
        if self.chaos_level >= 7:
            background_key = 'extreme'
        elif self.chaos_level >= 4:
            background_key = 'chaos'
            
        if background_key in self.backgrounds:
            self.screen.blit(self.backgrounds[background_key], (0, 0))
        else:
            self.screen.fill(self.settings.bg_color)

        # Draw base game elements
        super().draw()

        # Draw crazy play specific elements
        self._draw_crazy_elements()

    def _draw_crazy_elements(self):
        """Draw elements specific to crazy play mode."""
        # Draw active effects
        for effect in self.active_effects:
            if effect['type'] in self.effect_overlays:
                self.screen.blit(self.effect_overlays[effect['type']], (0, 0))

        # Draw chaos meter
        chaos_text = self.font_small.render(
            f"Chaos Level: {self.chaos_level}", 
            True, 
            (255, 0, 0)
        )
        chaos_rect = chaos_text.get_rect(
            center=(self.settings.screen_width // 4, 30)
        )
        self.screen.blit(chaos_text, chaos_rect)

        # Draw score modifier if active
        if self.current_modifier != 1.0:
            modifier_text = self.font_small.render(
                f"Score Multiplier: x{self.current_modifier}", 
                True, 
                (255, 255, 0)
            )
            modifier_rect = modifier_text.get_rect(
                center=(self.settings.screen_width * 3 // 4, 30)
            )
            self.screen.blit(modifier_text, modifier_rect)

    def handle_period_end(self):
        """Handle the end of a period in crazy play mode."""
        super().handle_period_end()
        
        # Reset some effects between periods
        self.gravity_reversed = False
        self.current_modifier = 1.0
        self.active_effects = []
        
        # But maintain chaos level
        logging.info(f"Crazy play period {self.period} ended at chaos level {self.chaos_level}")

    def handle_game_end(self):
        """Handle game end in crazy play mode."""
        super().handle_game_end()
        
        # Calculate crazy play specific statistics
        max_chaos = getattr(self, 'max_chaos_level', self.chaos_level)
        total_effects = getattr(self, 'total_effects_triggered', len(self.active_effects))
        
        logging.info(f"Crazy play stats - Max Chaos: {max_chaos}, "
                    f"Total Effects: {total_effects}")

    def cleanup(self):
        """Clean up crazy play mode resources."""
        super().cleanup()
        self.backgrounds = {}
        self.effect_overlays = {}
        self.active_effects = []
        logging.info("Crazy play mode cleanup completed")
