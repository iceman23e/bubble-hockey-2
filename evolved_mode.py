# evolved_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging
import random
import json
from datetime import datetime, timedelta

class EvolvedMode(BaseGameMode):
    """Evolved game mode with additional features and full analytics integration."""
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
        
        # Analytics-specific features
        self.momentum_effects_enabled = True
        self.show_analytics = True
        self.analytics_overlay_position = 'dynamic'  # Changes based on gameplay
        self.critical_moment_effects = []
        
        # Visual effect trackers
        self.visual_effects = []
        self.momentum_particles = []
        self.analytics_alerts = []
        
        # Enhanced statistics tracking
        self.stats = {
            'power_ups_used': 0,
            'taunts_triggered': 0,
            'max_streak': 0,
            'comeback_attempts': 0,
            'successful_comebacks': 0,
            'critical_moments': 0
        }
        
        # Load evolved mode configuration
        self._load_evolved_config()

    def _load_evolved_config(self):
        """Load evolved mode specific configuration"""
        try:
            config_path = 'assets/evolved/config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.effect_intensity = config.get('effect_intensity', 1.0)
                    self.momentum_threshold = config.get('momentum_threshold', 0.5)
                    self.analytics_update_rate = config.get('analytics_update_rate', 1.0)
            else:
                logging.warning("Evolved mode config not found, using defaults")
                self.effect_intensity = 1.0
                self.momentum_threshold = 0.5
                self.analytics_update_rate = 1.0
        except Exception as e:
            logging.error(f"Error loading evolved mode config: {e}")

    def load_assets(self):
        """Load assets specific to Evolved mode."""
        try:
            # Load background and UI elements
            self.background_image = pygame.image.load('assets/evolved/images/jumbotron.png')
            self.power_up_overlay = pygame.image.load('assets/evolved/images/power_up_overlay.png')
            
            # Load combo indicators
            self.combo_indicators = [
                pygame.image.load(f'assets/evolved/images/combo_{i}.png')
                for i in range(1, self.max_combo_multiplier + 1)
            ]
            
            # Load analytics-specific assets
            self.momentum_indicator = pygame.image.load('assets/evolved/images/momentum_indicator.png')
            self.critical_moment_overlay = pygame.image.load('assets/evolved/images/critical_moment.png')
            self.analytics_alert_bg = pygame.image.load('assets/evolved/images/alert_background.png')
            
            # Load particle effects
            self.particle_images = {
                'momentum': pygame.image.load('assets/evolved/images/momentum_particle.png'),
                'power_up': pygame.image.load('assets/evolved/images/power_up_particle.png'),
                'critical': pygame.image.load('assets/evolved/images/critical_particle.png')
            }
            
            logging.debug("Evolved mode assets loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load evolved mode assets: {e}")
            self.background_image = None
            self.power_up_overlay = None
            self.combo_indicators = []
            self._init_fallback_assets()

    def _init_fallback_assets(self):
        """Initialize basic shapes as fallback assets"""
        self.momentum_indicator = self._create_fallback_surface((100, 20), (255, 140, 0))
        self.critical_moment_overlay = self._create_fallback_surface((200, 50), (255, 0, 0))
        self.analytics_alert_bg = self._create_fallback_surface((150, 40), (0, 0, 0))

    def _create_fallback_surface(self, size, color):
        """Create a basic surface as fallback"""
        surface = pygame.Surface(size)
        surface.fill(color)
        return surface

    def update(self):
        """Update the game state with enhanced analytics integration."""
        super().update()
        
        if self.game.state_machine.state == self.game.state_machine.states.PLAYING:
            dt = self.game.clock.get_time() / 1000.0
            
            # Update timers
            self._update_timers(dt)
            
            # Update visual effects
            self._update_visual_effects(dt)
            
            # Handle analytics-driven events
            if self.game.current_analysis:
                self._handle_analytics_update(self.game.current_analysis)
            
            # Update particle effects
            self._update_particles(dt)
            
            # Update analytics alerts
            self._update_analytics_alerts(dt)

    def _update_timers(self, dt):
        """Update all timers for evolved mode features."""
        if self.taunts_enabled:
            self.taunt_timer += dt
            
        if self.power_ups_enabled:
            self.power_up_timer += dt

    def _update_visual_effects(self, dt):
        """Update visual effects based on game state"""
        # Update existing effects
        self.visual_effects = [effect for effect in self.visual_effects
                             if effect['duration'] > 0]
        for effect in self.visual_effects:
            effect['duration'] -= dt

        # Update momentum particles if momentum is high
        if (self.game.current_analysis and 
            self.game.current_analysis['momentum']['current_state']['intensity'] in ['strong', 'overwhelming']):
            self._spawn_momentum_particles()

    def _update_particles(self, dt):
        """Update particle effects"""
        for particle in self.momentum_particles[:]:
            particle['life'] -= dt
            if particle['life'] <= 0:
                self.momentum_particles.remove(particle)
            else:
                particle['x'] += particle['dx'] * dt
                particle['y'] += particle['dy'] * dt
                particle['alpha'] = min(255, int(255 * (particle['life'] / particle['max_life'])))

    def _update_analytics_alerts(self, dt):
        """Update analytics-driven alerts"""
        for alert in self.analytics_alerts[:]:
            alert['duration'] -= dt
            if alert['duration'] <= 0:
                self.analytics_alerts.remove(alert)

    def _handle_analytics_update(self, analysis):
        """Handle updates from analytics system"""
        # Check for momentum shifts
        if analysis['momentum']['current_state']['team']:
            self._handle_momentum_effects(analysis['momentum'])
            
        # Check for critical moments
        if analysis['is_critical_moment']:
            self._handle_critical_moment(analysis)
            
        # Check for significant pattern detection
        if 'patterns' in analysis:
            self._handle_pattern_detection(analysis['patterns'])

    def _handle_momentum_effects(self, momentum):
        """Handle momentum-based visual effects"""
        if not self.momentum_effects_enabled:
            return
            
        team = momentum['current_state']['team']
        intensity = momentum['current_state']['intensity']
        
        if intensity in ['strong', 'overwhelming']:
            color = (255, 0, 0) if team == 'red' else (0, 0, 255)
            self._add_visual_effect('momentum_glow', color, 2.0)
            
            if momentum['current_state']['score'] > self.momentum_threshold:
                self._spawn_momentum_particles()

    def _spawn_momentum_particles(self):
        """Create momentum particle effects"""
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

    def _handle_pattern_detection(self, patterns):
        """Handle detected gameplay patterns"""
        if patterns.get('scoring_runs', {}).get('current_run', {}).get('length', 0) >= 3:
            run = patterns['scoring_runs']['current_run']
            self._add_analytics_alert(
                f"Hot Streak: {run['team'].upper()} x{run['length']}!",
                3.0,
                'streak'
            )

    def _add_visual_effect(self, effect_type, color, duration):
        """Add a new visual effect"""
        self.visual_effects.append({
            'type': effect_type,
            'color': color,
            'duration': duration,
            'intensity': self.effect_intensity
        })

    def _add_analytics_alert(self, message, duration, alert_type):
        """Add a new analytics alert"""
        self.analytics_alerts.append({
            'message': message,
            'duration': duration,
            'type': alert_type,
            'alpha': 255
        })

    def handle_goal(self, team):
        """Handle goal scoring with enhanced features."""
        super().handle_goal(team)
        
        current_time = datetime.now()
        
        # Enhanced combo system
        if self.combos_enabled:
            if self.last_goal_time:
                time_since_last = (current_time - self.last_goal_time).total_seconds()
                if time_since_last < self.settings.combo_time_window:
                    self.streak_count += 1
                    self.combo_multiplier = min(self.streak_count, self.max_combo_multiplier)
                    if self.combo_multiplier > 1:
                        self.active_event = f"COMBO x{self.combo_multiplier}!"
                        self._add_visual_effect('combo', (255, 255, 0), 1.5)
                else:
                    self.streak_count = 1
                    self.combo_multiplier = 1
            
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

        logging.info(f"Goal scored with combo multiplier: {self.combo_multiplier}")

    def handle_critical_moment(self, analysis):
        """Handle critical game moments with enhanced effects."""
        super().handle_critical_moment(analysis)
        
        if not analysis['is_critical_moment']:
            return
            
        self.stats['critical_moments'] += 1
        
        # Add visual effects based on the type of critical moment
        if analysis['momentum']['current_state']['intensity'] == 'overwhelming':
            self._add_visual_effect('critical_momentum', (255, 140, 0), 3.0)
            self._add_analytics_alert("Momentum Shift!", 2.0, 'momentum')
            
        if self.clock <= 60 and abs(self.score['red'] - self.score['blue']) <= 1:
            self._add_visual_effect('critical_time', (255, 0, 0), 3.0)
            self._add_analytics_alert("Final Minute - Close Game!", 2.0, 'time')

    def draw(self):
        """Draw the evolved game screen with enhanced visuals."""
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

    def _draw_visual_effects(self):
        """Draw active visual effects"""
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

    def _draw_particles(self):
        """Draw particle effects"""
        for particle in self.momentum_particles:
            if 'momentum' in self.particle_images:
                img = self.particle_images['momentum'].copy()
                img.set_alpha(particle['alpha'])
                self.screen.blit(img, (particle['x'], particle['y']))

    def _draw_analytics_alerts(self):
        """Draw active analytics alerts"""
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

    def cleanup(self):
        """Clean up evolved mode resources."""
        super().cleanup()
        self.background_image = None
        self.power_up_overlay = None
        self.combo_indicators = []
        self.momentum_indicator = None
        self.critical_moment_overlay = None
        self.analytics_alert_bg = None
        self.particle_images = {}
        logging.info("Evolved mode cleanup completed")
