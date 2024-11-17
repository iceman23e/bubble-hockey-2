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
        
        # Initialize evolved mode specific features
        self.taunt_timer = 0
        self.power_up_timer = 0
        self.combo_multiplier = 1
        self.max_combo_multiplier = 3
        self.streak_count = 0
        
        # Enable all features for evolved mode
        self.power_ups_enabled = True
        self.taunts_enabled = True
        self.combos_enabled = True

    def load_assets(self):
        """Load assets specific to Evolved mode."""
        try:
            # Load background and UI elements
            self.background_image = pygame.image.load('assets/evolved/images/jumbotron.png')
            self.power_up_overlay = pygame.image.load('assets/evolved/images/power_up_overlay.png')
            
            # Load additional evolved mode assets
            self.combo_indicators = [
                pygame.image.load(f'assets/evolved/images/combo_{i}.png')
                for i in range(1, self.max_combo_multiplier + 1)
            ]
            
            logging.debug("Evolved mode assets loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load evolved mode assets: {e}")
            self.background_image = None
            self.power_up_overlay = None
            self.combo_indicators = []

    def update(self):
        """Update the game state."""
        if self.game.state_machine.state != self.game.state_machine.states.PLAYING:
            return

        # Update base game elements
        super().update()
        
        # Clock runs only when puck is in play
        if self.game.puck_possession == 'in_play':
            dt = self.game.clock.tick(60) / 1000.0
            
            # Update timers
            self._update_timers(dt)
            
            # Handle automatic features
            self._check_power_up_spawn()
            self._check_taunt_trigger()
            
        else:
            # Maintain frame rate without updating game time
            self.game.clock.tick(60)

    def _update_timers(self, dt):
        """Update all timers for evolved mode features."""
        if self.taunts_enabled:
            self.taunt_timer += dt
            
        if self.power_ups_enabled:
            self.power_up_timer += dt

    def _check_power_up_spawn(self):
        """Check if it's time to spawn a power-up."""
        if (self.power_ups_enabled and 
            self.power_up_timer >= self.settings.power_up_frequency):
            self.spawn_power_up()
            self.power_up_timer = 0

    def _check_taunt_trigger(self):
        """Check if it's time to trigger a taunt."""
        if (self.taunts_enabled and 
            self.taunt_timer >= self.settings.taunt_frequency):
            self.play_random_taunt()
            self.taunt_timer = 0

    def spawn_power_up(self):
        """Spawn a random power-up."""
        if not self.power_up_active:
            power_up_type = random.choice(['speed_boost', 'goal_multiplier', 'defense_boost'])
            duration = random.uniform(10, 20)  # Power-up duration between 10-20 seconds
            self.activate_power_up(duration)
            self.active_event = f"{power_up_type.upper()} ACTIVATED!"
            logging.info(f"Power-up spawned: {power_up_type}")

    def play_random_taunt(self):
        """Play a random taunt sound."""
        if self.taunts_enabled and self.game.sounds_enabled and self.game.sounds['taunts']:
            taunt_sound = random.choice(self.game.sounds['taunts'])
            taunt_sound.play()
            logging.info("Taunt sound played")

    def handle_goal(self):
        """Handle goal scoring with evolved features."""
        super().handle_goal()
        
        # Handle combo system
        if self.combos_enabled:
            current_time = pygame.time.get_ticks() / 1000.0
            if self.last_goal_time and (current_time - self.last_goal_time < self.settings.combo_time_window):
                self.streak_count += 1
                self.combo_multiplier = min(self.streak_count, self.max_combo_multiplier)
                if self.combo_multiplier > 1:
                    self.active_event = f"COMBO x{self.combo_multiplier}!"
            else:
                self.streak_count = 1
                self.combo_multiplier = 1
            
            self.last_goal_time = current_time
            logging.info(f"Goal scored with combo multiplier: {self.combo_multiplier}")

    def draw(self):
        """Draw the evolved game elements."""
        # Draw background
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            self.screen.fill(self.settings.bg_color)

        # Draw base game elements
        super().draw()

        # Draw evolved mode specific elements
        self._draw_evolved_elements()

    def _draw_evolved_elements(self):
        """Draw elements specific to evolved mode."""
        # Draw combo indicator
        if self.combo_multiplier > 1 and self.combo_indicators:
            indicator = self.combo_indicators[self.combo_multiplier - 1]
            indicator_rect = indicator.get_rect(
                center=(self.settings.screen_width // 4, self.settings.screen_height - 50)
            )
            self.screen.blit(indicator, indicator_rect)

        # Draw power-up overlay when active
        if self.power_up_active and self.power_up_overlay:
            self.screen.blit(self.power_up_overlay, (0, 0))

        # Draw streak counter
        if self.streak_count > 1:
            streak_text = self.font_small.render(
                f"Streak: {self.streak_count}", 
                True, 
                (255, 255, 0)
            )
            streak_rect = streak_text.get_rect(
                center=(self.settings.screen_width * 3 // 4, self.settings.screen_height - 50)
            )
            self.screen.blit(streak_text, streak_rect)

    def handle_period_end(self):
        """Handle the end of a period in evolved mode."""
        super().handle_period_end()
        
        # Reset evolved mode features at period end
        self.streak_count = 0
        self.combo_multiplier = 1
        self.power_up_timer = 0
        self.taunt_timer = 0
        
        logging.info(f"Evolved mode period {self.period} ended")

    def handle_game_end(self):
        """Handle game end in evolved mode."""
        super().handle_game_end()
        
        # Calculate and log evolved mode specific statistics
        max_streak = max(self.streak_count, 0)
        power_ups_used = getattr(self, 'power_ups_used', 0)
        taunts_triggered = getattr(self, 'taunts_triggered', 0)
        
        logging.info(f"Evolved mode stats - Max Streak: {max_streak}, "
                    f"Power-ups Used: {power_ups_used}, "
                    f"Taunts Triggered: {taunts_triggered}")

    def cleanup(self):
        """Clean up evolved mode resources."""
        super().cleanup()
        self.background_image = None
        self.power_up_overlay = None
        self.combo_indicators = []
        logging.info("Evolved mode cleanup completed")
