# evolved_mode.py

import pygame
import logging
import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from base_game_mode import BaseGameMode
from utils import load_image

class EvolvedMode(BaseGameMode):
    """
    Evolved game mode with additional features and full analytics integration.

    The EvolvedMode class extends the BaseGameMode to provide advanced gameplay features,
    including power-ups, taunts, combos, momentum effects, and comprehensive analytics
    integration. It aims to enhance the gaming experience while maintaining balance and
    performance.

    Features:
    - Power-ups with varying effects
    - Taunts to add excitement
    - Combo scoring system
    - Momentum-based visual effects
    - Analytics-driven events and alerts
    - Enhanced visual and particle effects
    """

    def __init__(self, game):
        """
        Initialize the evolved game mode.

        Args:
            game: The main game instance this mode is attached to.

        Raises:
            ValueError: If game settings are invalid.
            pygame.error: If critical assets fail to load.
            OSError: If required asset directories are not accessible.
        """
        try:
            super().__init__(game)
            logging.info("EvolvedMode initialized")

            # Initialize evolved mode specific features
            self.taunt_timer: float = 0.0
            self.taunt_frequency: float = 30.0  # Seconds between taunts
            self.power_up_timer: float = 0.0
            self.combo_multiplier: int = 1
            self.max_combo_multiplier: int = 3
            self.streak_count: int = 0

            # Feature toggles
            self.power_ups_enabled: bool = True
            self.taunts_enabled: bool = True
            self.combos_enabled: bool = True

            # Power-up related variables
            self.power_up_active: bool = False
            self.power_up_end_time: Optional[datetime] = None
            self.current_power_up: Optional[str] = None  # Type of active power-up

            # Analytics-specific features
            self.momentum_effects_enabled: bool = True
            self.show_analytics: bool = True
            self.analytics_overlay_position: str = 'dynamic'  # Changes based on gameplay

            # Visual effect trackers
            self.visual_effects: List[Dict[str, Any]] = []
            self.momentum_particles: List[Dict[str, Any]] = []
            self.analytics_alerts: List[Dict[str, Any]] = []

            # Enhanced statistics tracking
            self.stats: Dict[str, int] = {
                'power_ups_used': 0,
                'taunts_triggered': 0,
                'max_streak': 0,
                'comeback_attempts': 0,
                'successful_comebacks': 0,
                'critical_moments': 0
            }

            # Load evolved mode configuration
            self._load_evolved_config()

            # Initialize last probabilities for analytics
            self.last_probabilities: Dict[str, float] = {'red': 0.5, 'blue': 0.5}

            # Initialize last goal time
            self.last_goal_time: Optional[datetime] = None

            # Load assets
            self.load_assets()

        except Exception as e:
            logging.error(f"Failed to initialize EvolvedMode: {e}")
            raise

    def _load_evolved_config(self) -> None:
        """Load evolved mode specific configuration."""
        try:
            config_path = 'assets/evolved/config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.effect_intensity = config.get('effect_intensity', 1.0)
                    self.momentum_threshold = config.get('momentum_threshold', 0.5)
                    self.analytics_update_rate = config.get('analytics_update_rate', 1.0)
                    self.settings.power_up_frequency = config.get('power_up_frequency', 30.0)
                    logging.info("Evolved mode configuration loaded")
            else:
                logging.warning("Evolved mode config not found, using defaults")
                self.effect_intensity = 1.0
                self.momentum_threshold = 0.5
                self.analytics_update_rate = 1.0
                self.settings.power_up_frequency = 30.0
        except Exception as e:
            logging.error(f"Error loading evolved mode config: {e}")
            self.effect_intensity = 1.0
            self.momentum_threshold = 0.5
            self.analytics_update_rate = 1.0
            self.settings.power_up_frequency = 30.0

    def load_assets(self) -> None:
        """
        Load assets specific to Evolved mode.

        Raises:
            pygame.error: If assets fail to load.
            FileNotFoundError: If asset files are missing.
            OSError: If asset directories are not accessible.
        """
        try:
            # Load background and UI elements
            self.background_image = load_image('assets/evolved/images/jumbotron.png')
            self.power_up_overlay = load_image('assets/evolved/images/power_up_overlay.png')

            # Load combo indicators
            self.combo_indicators = [
                load_image(f'assets/evolved/images/combo_{i}.png')
                for i in range(1, self.max_combo_multiplier + 1)
            ]

            # Validate combo indicators
            if not all(self.combo_indicators):
                raise pygame.error("Failed to load all combo indicators.")

            # Load analytics-specific assets
            self.momentum_indicator = load_image('assets/evolved/images/momentum_indicator.png')
            self.critical_moment_overlay = load_image('assets/evolved/images/critical_moment.png')
            self.analytics_alert_bg = load_image('assets/evolved/images/alert_background.png')

            # Load particle effects
            self.particle_images = {
                'momentum': load_image('assets/evolved/images/momentum_particle.png'),
                'power_up': load_image('assets/evolved/images/power_up_particle.png'),
                'critical': load_image('assets/evolved/images/critical_particle.png')
            }

            # Validate particle images
            if not all(self.particle_images.values()):
                raise pygame.error("Failed to load all particle images.")

            logging.debug("Evolved mode assets loaded successfully")

        except (pygame.error, FileNotFoundError, OSError) as e:
            logging.error(f"Failed to load evolved mode assets: {e}")
            self.background_image = None
            self.power_up_overlay = None
            self.combo_indicators = []
            self._init_fallback_assets()

    def _init_fallback_assets(self) -> None:
        """Initialize basic shapes as fallback assets."""
        self.momentum_indicator = self._create_fallback_surface((100, 20), (255, 140, 0))
        self.critical_moment_overlay = self._create_fallback_surface((200, 50), (255, 0, 0))
        self.analytics_alert_bg = self._create_fallback_surface((150, 40), (0, 0, 0))
        logging.warning("Using fallback assets for EvolvedMode.")

    def _create_fallback_surface(
        self,
        size: tuple,
        color: tuple
    ) -> pygame.Surface:
        """
        Create a basic surface as a fallback asset.

        Args:
            size: The size of the surface (width, height).
            color: The fill color of the surface.

        Returns:
            A pygame.Surface object with the specified size and color.
        """
        surface = pygame.Surface(size)
        surface.fill(color)
        return surface

    def update(self) -> None:
        """Update the game state with enhanced analytics integration."""
        try:
            super().update()
            dt = self.game.clock.get_time() / 1000.0

            if self.game.state_machine.state == self.game.state_machine.states.PLAYING:
                # Update timers
                self._update_timers(dt)

                # Check for power-up spawning
                self._check_power_up_spawn()

                # Handle power-up expiration
                if self.power_up_active and datetime.now() >= self.power_up_end_time:
                    self._on_power_up_end()

                # Update visual effects
                self._update_visual_effects(dt)

                # Handle analytics-driven events
                if self.game.current_analysis:
                    self._handle_analytics_update(self.game.current_analysis)

                # Update particle effects
                self._update_particles(dt)

                # Update analytics alerts
                self._update_analytics_alerts(dt)

                # Handle taunts
                if self.taunts_enabled and self.taunt_timer >= self.taunt_frequency:
                    self.play_random_taunt()
                    self.taunt_timer = 0.0

        except Exception as e:
            logging.error(f"Error during update in EvolvedMode: {e}")

    def _update_timers(self, dt: float) -> None:
        """
        Update all timers for evolved mode features.

        Args:
            dt: Delta time since last update in seconds.
        """
        if self.taunts_enabled:
            self.taunt_timer += dt

        if self.power_ups_enabled:
            self.power_up_timer += dt

    def _check_power_up_spawn(self) -> None:
        """Check if it's time to spawn a power-up."""
        if self.power_ups_enabled and self.power_up_timer >= self.settings.power_up_frequency:
            self.spawn_power_up()
            self.power_up_timer = 0.0

    def spawn_power_up(self) -> None:
        """Spawn and activate a random power-up."""
        if not self.power_up_active:
            power_up_type = random.choice(['speed_boost', 'goal_multiplier', 'defense_boost'])
            duration = random.uniform(10, 20)  # Power-up duration between 10-20 seconds
            self.activate_power_up(power_up_type, duration)
            self.active_event = f"{power_up_type.replace('_', ' ').upper()} ACTIVATED!"
            logging.info(f"Power-up spawned: {power_up_type}")

    def activate_power_up(self, power_up_type: str, duration: float) -> None:
        """
        Activate a power-up for the specified duration.

        Args:
            power_up_type: The type of power-up to activate.
            duration: Duration of the power-up in seconds.
        """
        self.power_up_active = True
        self.current_power_up = power_up_type
        self.power_up_end_time = datetime.now() + timedelta(seconds=duration)
        self.stats['power_ups_used'] += 1
        logging.info(f"Power-up {power_up_type} activated for {duration} seconds")

    def _on_power_up_end(self) -> None:
        """Handle power-up expiration."""
        logging.info("Power-up expired")
        self.power_up_active = False
        self.current_power_up = None
        self.power_up_end_time = None
        self.active_event = None

    def play_random_taunt(self) -> None:
        """Play a random taunt sound."""
        if self.game.sounds_enabled and self.game.sounds.get('taunts'):
            try:
                taunt_sound = random.choice(self.game.sounds['taunts'])
                if taunt_sound:
                    taunt_sound.play()
                    self.stats['taunts_triggered'] += 1
                    logging.info("Taunt sound played")
            except pygame.error as e:
                logging.warning(f"Failed to play taunt sound: {e}")

    def _update_visual_effects(self, dt: float) -> None:
        """
        Update visual effects based on game state.

        Args:
            dt: Delta time since last update in seconds.
        """
        # Update existing effects
        self.visual_effects = [effect for effect in self.visual_effects if effect['duration'] > 0]
        for effect in self.visual_effects:
            effect['duration'] -= dt

        # Update momentum particles if momentum is high
        if (self.game.current_analysis and
                self.game.current_analysis['momentum']['current_state']['intensity'] in ['strong', 'overwhelming']):
            self._spawn_momentum_particles()

    def _update_particles(self, dt: float) -> None:
        """
        Update particle effects.

        Args:
            dt: Delta time since last update in seconds.
        """
        for particle in self.momentum_particles[:]:
            particle['life'] -= dt
            if particle['life'] <= 0:
                self.momentum_particles.remove(particle)
            else:
                particle['x'] += particle['dx'] * dt
                particle['y'] += particle['dy'] * dt
                particle['alpha'] = min(255, int(255 * (particle['life'] / particle['max_life'])))

    def _update_analytics_alerts(self, dt: float) -> None:
        """
        Update analytics-driven alerts.

        Args:
            dt: Delta time since last update in seconds.
        """
        for alert in self.analytics_alerts[:]:
            alert['duration'] -= dt
            if alert['duration'] <= 0:
                self.analytics_alerts.remove(alert)
            else:
                # Fade out effect
                if alert['duration'] < 1.0:
                    alert['alpha'] = int(255 * alert['duration'])

    def _handle_analytics_update(self, analysis: Dict[str, Any]) -> None:
        """
        Handle updates from the analytics system.

        Args:
            analysis: Analytics data from the current game state.
        """
        try:
            # Check for momentum shifts
            if analysis['momentum']['current_state']['team']:
                self._handle_momentum_effects(analysis['momentum'])

            # Check for critical moments
            if analysis.get('is_critical_moment'):
                self.handle_critical_moment(analysis)

            # Check for significant pattern detection
            if 'patterns' in analysis:
                self._handle_pattern_detection(analysis['patterns'])
        except Exception as e:
            logging.error(f"Error handling analytics update: {e}")

    def _handle_momentum_effects(self, momentum: Dict[str, Any]) -> None:
        """
        Handle momentum-based visual effects.

        Args:
            momentum: Momentum data from the analytics system.
        """
        if not self.momentum_effects_enabled:
            return

        team = momentum['current_state']['team']
        intensity = momentum['current_state']['intensity']

        if intensity in ['strong', 'overwhelming']:
            color = (255, 0, 0) if team == 'red' else (0, 0, 255)
            self._add_visual_effect('momentum_glow', color, 2.0)

            if momentum['current_state']['score'] > self.momentum_threshold:
                self._spawn_momentum_particles()

    def _spawn_momentum_particles(self) -> None:
        """Create momentum particle effects."""
        for _ in range(3):  # Spawn 3 particles per update
            particle = {
                'x': random.randint(0, self.settings.screen_width),
                'y': random.randint(0, self.settings.screen_height),
                'dx': random.uniform(-50, 50),
                'dy': random.uniform(-50, 50),
                'life': random.uniform(0.5, 1.5),
                'max_life': 1.5,
                'alpha': 255
            }
            self.momentum_particles.append(particle)

    def _handle_pattern_detection(self, patterns: Dict[str, Any]) -> None:
        """
        Handle detected gameplay patterns.

        Args:
            patterns: Pattern data from the analytics system.
        """
        try:
            if patterns.get('scoring_runs', {}).get('current_run', {}).get('length', 0) >= 3:
                run = patterns['scoring_runs']['current_run']
                self._add_analytics_alert(
                    f"Hot Streak: {run['team'].upper()} x{run['length']}!",
                    3.0,
                    'streak'
                )
        except Exception as e:
            logging.error(f"Error handling pattern detection: {e}")

    def _add_visual_effect(
        self,
        effect_type: str,
        color: tuple,
        duration: float
    ) -> None:
        """
        Add a new visual effect.

        Args:
            effect_type: Type of the visual effect.
            color: Color associated with the effect.
            duration: Duration of the effect in seconds.
        """
        self.visual_effects.append({
            'type': effect_type,
            'color': color,
            'duration': duration,
            'intensity': self.effect_intensity
        })
        logging.debug(f"Added visual effect: {effect_type}")

    def _add_analytics_alert(
        self,
        message: str,
        duration: float,
        alert_type: str
    ) -> None:
        """
        Add a new analytics alert.

        Args:
            message: Alert message to display.
            duration: Duration to display the alert in seconds.
            alert_type: Type of alert for styling.
        """
        self.analytics_alerts.append({
            'message': message,
            'duration': duration,
            'type': alert_type,
            'alpha': 255
        })
        logging.debug(f"Added analytics alert: {message}")

    def handle_goal(self, team: str) -> None:
        """
        Handle goal scoring with enhanced features.

        Args:
            team: The team that scored ('red' or 'blue').
        """
        try:
            super().handle_goal(team)
            current_time = datetime.now()
            points = 1  # Base points for a goal

            # Apply combo multiplier if enabled
            if self.combos_enabled:
                if self.last_goal_time:
                    time_since_last = (current_time - self.last_goal_time).total_seconds()
                    if time_since_last < self.settings.combo_time_window:
                        self.streak_count += 1
                        self.combo_multiplier = min(self.streak_count, self.max_combo_multiplier)
                        if self.combo_multiplier > 1:
                            points *= self.combo_multiplier
                            self.active_event = f"COMBO x{self.combo_multiplier}!"
                            self._add_visual_effect('combo', (255, 255, 0), 1.5)
                    else:
                        self.streak_count = 1
                        self.combo_multiplier = 1
                else:
                    self.streak_count = 1
                    self.combo_multiplier = 1
            else:
                self.combo_multiplier = 1

            # Apply power-up effects
            if self.power_up_active and self.current_power_up == 'goal_multiplier':
                multiplier = 2  # Example multiplier
                points *= multiplier
                self.active_event = f"POWER-UP! GOAL WORTH {points} POINTS!"

            # Update score
            self.score[team] += points

            # Update last goal time
            self.last_goal_time = current_time
            self.stats['max_streak'] = max(self.stats['max_streak'], self.streak_count)

            # Check for comeback
            score_diff = self.score['red'] - self.score['blue']
            if abs(score_diff) >= 3:
                trailing_team = 'blue' if score_diff > 0 else 'red'
                if team == trailing_team:
                    self.stats['comeback_attempts'] += 1
                    if abs(score_diff) == 3:
                        self.stats['successful_comebacks'] += 1
                        self._add_analytics_alert("Comeback Complete!", 3.0, 'comeback')

            logging.info(f"Goal scored by {team} with {points} points (Combo x{self.combo_multiplier})")

        except Exception as e:
            logging.error(f"Error handling goal in EvolvedMode: {e}")

    def handle_critical_moment(self, analysis: Dict[str, Any]) -> None:
        """
        Handle critical game moments with enhanced effects.

        Args:
            analysis: Analytics data indicating a critical moment.
        """
        try:
            if not analysis.get('is_critical_moment'):
                return

            self.stats['critical_moments'] += 1

            # Add visual effects based on the type of critical moment
            if analysis['momentum']['current_state']['intensity'] == 'overwhelming':
                self._add_visual_effect('critical_momentum', (255, 140, 0), 3.0)
                self._add_analytics_alert("Momentum Shift!", 2.0, 'momentum')

            if self.clock <= 60 and abs(self.score['red'] - self.score['blue']) <= 1:
                self._add_visual_effect('critical_time', (255, 0, 0), 3.0)
                self._add_analytics_alert("Final Minute - Close Game!", 2.0, 'time')

        except Exception as e:
            logging.error(f"Error handling critical moment: {e}")

    def draw(self) -> None:
        """Draw the evolved game screen with enhanced visuals."""
        try:
            # Draw background
            if self.background_image:
                self.screen.blit(self.background_image, (0, 0))
            else:
                self.screen.fill(self.settings.bg_color)

            # Draw base game elements
            super().draw()

            # Draw evolved mode specific elements
            self._draw_evolved_elements()

            # Draw visual effects
            self._draw_visual_effects()

            # Draw analytics overlays and alerts
            if self.show_analytics:
                self._draw_analytics_overlay()
                self._draw_analytics_alerts()

            # Draw particle effects
            self._draw_particles()

        except Exception as e:
            logging.error(f"Error during draw in EvolvedMode: {e}")

    def _draw_evolved_elements(self) -> None:
        """Draw elements specific to evolved mode."""
        # Draw combo indicator
        if self.combo_multiplier > 1 and self.combo_indicators:
            index = min(self.combo_multiplier - 1, len(self.combo_indicators) - 1)
            indicator = self.combo_indicators[index]
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

    def _draw_visual_effects(self) -> None:
        """Draw active visual effects."""
        for effect in self.visual_effects:
            if effect['type'] == 'momentum_glow':
                s = pygame.Surface((self.settings.screen_width, self.settings.screen_height))
                s.set_alpha(int(64 * effect['intensity'] * (effect['duration'] / 2.0)))
                s.fill(effect['color'])
                self.screen.blit(s, (0, 0))
            elif effect['type'] == 'critical_momentum':
                if self.critical_moment_overlay:
                    self.critical_moment_overlay.set_alpha(
                        int(255 * effect['intensity'] * (effect['duration'] / 3.0))
                    )
                    self.screen.blit(self.critical_moment_overlay, (0, 0))
            elif effect['type'] == 'combo':
                s = pygame.Surface((self.settings.screen_width, self.settings.screen_height))
                s.set_alpha(int(128 * (effect['duration'] / 1.5)))
                s.fill(effect['color'])
                self.screen.blit(s, (0, 0))

    def _draw_particles(self) -> None:
        """Draw particle effects."""
        for particle in self.momentum_particles:
            if 'momentum' in self.particle_images:
                img = self.particle_images['momentum'].copy()
                img.set_alpha(particle['alpha'])
                self.screen.blit(img, (particle['x'], particle['y']))

    def _draw_analytics_overlay(self) -> None:
        """Draw analytics overlays."""
        # Placeholder for actual implementation
        pass

    def _draw_analytics_alerts(self) -> None:
        """Draw active analytics alerts."""
        y_offset = 100
        for alert in self.analytics_alerts:
            alert_surface = self.font_small.render(alert['message'], True, (255, 255, 255))
            alert_rect = alert_surface.get_rect(
                center=(self.settings.screen_width // 2, y_offset)
            )

            # Draw alert background
            if self.analytics_alert_bg:
                bg_rect = self.analytics_alert_bg.get_rect(center=alert_rect.center)
                self.analytics_alert_bg.set_alpha(int(alert['alpha']))
                self.screen.blit(self.analytics_alert_bg, bg_rect)

            # Draw alert text
            alert_surface.set_alpha(int(alert['alpha']))
            self.screen.blit(alert_surface, alert_rect)
            y_offset += 40

    def cleanup(self) -> None:
        """Clean up evolved mode resources."""
        try:
            super().cleanup()
            # Clear resources
            self.background_image = None
            self.power_up_overlay = None
            self.combo_indicators = []
            self.momentum_indicator = None
            self.critical_moment_overlay = None
            self.analytics_alert_bg = None
            self.particle_images.clear()
            logging.info("EvolvedMode cleanup completed")
        except Exception as e:
            logging.error(f"Error during cleanup in EvolvedMode: {e}")
