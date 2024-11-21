# crazy_play_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging
import random
from datetime import datetime, timedelta
from utils import load_sound

class CrazyPlayMode(BaseGameMode):
    """Crazy Play mode with exciting but physically implementable features."""
    
    def __init__(self, game):
        super().__init__(game)
        logging.info("Crazy Play mode initialized")
        
        # Core scoring features
        self.current_goal_value = 1
        self.first_goal_opportunity = True  # Track first goal opportunity
        self.first_goal_window = self.settings.period_length * 0.15  # 15% of period length
        self.frenzy_window = max(30, self.settings.period_length * 0.1)  # 10% of period or minimum 30 seconds
        self.last_goal_time = None
        self.combo_count = 0
        
        # Challenge states
        self.quick_strike_active = False
        self.quick_strike_deadline = None
        self.frenzy_mode = False  # For final minute
        
        # Event timing
        self.next_event_time = datetime.now() + timedelta(seconds=15)
        self.event_duration = None
        self.last_sound_time = datetime.now()
        self.sound_cooldown = 3
        
        # Override base settings
        self.max_periods = 5  # Longer games
        self.clock = self.settings.period_length
        
        # Analytics enhancements
        self.analytics_events = []
        self.show_analytics = True
        self.analytics_overlay_position = 'dynamic'
        self.analytics_alert_queue = []
        self.last_analytics_update = datetime.now()
        self.analytics_update_interval = 0.5
        
        # Visual effects system
        self.visual_effects = []
        self.particle_systems = []
        self.active_animations = []
        
        # Enhanced statistics tracking
        self.stats = {
            'bonus_points_earned': 0,
            'quick_strikes_attempted': 0,
            'quick_strikes_successful': 0,
            'frenzy_goals': 0,
            'comeback_goals': 0,
            'critical_goals': 0,
            'max_combo': 0,
            'total_bonus_multiplier': 0
        }
        
        # Load assets and sounds
        self.load_assets()
        self.load_crazy_sounds()
        
        # Initialize random sound timing variables
        self.last_random_sound_time = datetime.now().timestamp()
        self.next_random_sound_interval = self.get_next_random_sound_interval()

    def load_assets(self):
        """Load assets specific to Crazy Play mode"""
        try:
            # Load background and UI elements
            self.background = pygame.image.load('assets/crazy_play/images/background.png')
            self.overlay = pygame.image.load('assets/crazy_play/images/overlay.png')
            self.bonus_indicator = pygame.image.load('assets/crazy_play/images/bonus.png')
            self.frenzy_overlay = pygame.image.load('assets/crazy_play/images/frenzy.png')
            self.quick_strike_overlay = pygame.image.load('assets/crazy_play/images/quick_strike.png')
            
            # Load analytics-specific assets
            self.analytics_frame = pygame.image.load('assets/crazy_play/images/analytics_frame.png')
            self.momentum_indicator = pygame.image.load('assets/crazy_play/images/momentum_indicator.png')
            
            # Load particle effects
            self.particle_images = {
                'spark': pygame.image.load('assets/crazy_play/particles/spark.png'),
                'star': pygame.image.load('assets/crazy_play/particles/star.png'),
                'trail': pygame.image.load('assets/crazy_play/particles/trail.png')
            }
            
            logging.info("Crazy Play mode assets loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Crazy Play mode assets: {e}")
            self._init_fallback_assets()

    def load_crazy_sounds(self):
        """Load sound effects specific to crazy mode."""
        self.crazy_sounds = {
            'bonus': load_sound('assets/sounds/bonus_activated.wav'),
            'quick_strike': load_sound('assets/sounds/quick_strike.wav'),
            'combo': load_sound('assets/sounds/combo_goal.wav'),
            'frenzy': load_sound('assets/sounds/frenzy.wav')
        }
        logging.info("Crazy Play mode sounds loaded successfully")

    def _init_fallback_assets(self):
        """Initialize basic fallback assets if loading fails"""
        self.background = pygame.Surface((self.settings.screen_width, self.settings.screen_height))
        self.background.fill((0, 0, 0))
        self.overlay = self.background.copy()
        self.bonus_indicator = pygame.Surface((100, 50))
        self.frenzy_overlay = self.background.copy()
        self.quick_strike_overlay = pygame.Surface((150, 75))
        self.analytics_frame = pygame.Surface((200, 150))
        self.momentum_indicator = pygame.Surface((100, 20))
        self.particle_images = {}

    def update(self):
        """Update the game state."""
        super().update()
        
        current_time = datetime.now()
        
        # Update analytics if interval has passed
        if (current_time - self.last_analytics_update).total_seconds() >= self.analytics_update_interval:
            self._update_analytics()
            self.last_analytics_update = current_time
        
        # Check for final frenzy mode
        if not self.frenzy_mode and self.clock <= self.frenzy_window:
            self._start_final_minute_frenzy()
            
        # Check if first goal opportunity has expired
        if self.first_goal_opportunity and (self.settings.period_length - self.clock) > self.first_goal_window:
            self.first_goal_opportunity = False
        
        # Check for new random events
        if current_time >= self.next_event_time:
            self._trigger_random_event()
            
        # Update quick strike challenge
        if self.quick_strike_active and current_time >= self.quick_strike_deadline:
            self._end_quick_strike()
            
        # Update event duration
        if self.event_duration and current_time >= self.event_duration:
            self._end_current_event()
        
        # Update visual effects
        self._update_visual_effects()
        
        # Update analytics alerts
        self._update_analytics_alerts()
        
        # Handle random sounds
        if (self.game.sounds_enabled and 
            self.game.sounds.get('random_sounds') and 
            (current_time.timestamp() - self.last_random_sound_time) >= self.next_random_sound_interval):
            self.play_random_sound()
            self.last_random_sound_time = current_time.timestamp()
            self.next_random_sound_interval = self.get_next_random_sound_interval()

    def _update_analytics(self):
        """Update analytics state and generate insights"""
        if not self.game.current_analysis:
            return
            
        analysis = self.game.current_analysis
        
        # Process momentum shifts
        if 'momentum' in analysis:
            momentum = analysis['momentum']['current_state']
            if momentum['team'] and momentum['intensity'] in ['strong', 'overwhelming']:
                self._handle_momentum_shift(momentum)
        
        # Process pattern detection
        if 'patterns' in analysis and analysis['patterns'].get('scoring_runs'):
            self._handle_scoring_patterns(analysis['patterns']['scoring_runs'])
        
        # Process win probability changes
        if 'win_probability' in analysis:
            self._handle_probability_changes(analysis['win_probability'])

    def _handle_momentum_shift(self, momentum):
        """Handle significant momentum shifts"""
        team = momentum['team']
        intensity = momentum['intensity']
        
        if intensity == 'overwhelming':
            message = f"MASSIVE MOMENTUM SHIFT: {team.upper()} TEAM!"
            self._add_analytics_alert(message, 'momentum', 3.0)
            self._trigger_effect('momentum_shift', team)

    def _handle_scoring_patterns(self, patterns):
        """Handle detected scoring patterns"""
        if patterns.get('current_run', {}).get('length', 0) >= 3:
            run = patterns['current_run']
            message = f"HOT STREAK: {run['team'].upper()} x{run['length']}!"
            self._add_analytics_alert(message, 'pattern', 2.5)

    def _handle_probability_changes(self, probabilities):
        """Handle significant win probability changes"""
        threshold = 0.25  # 25% change threshold
        
        if hasattr(self, 'last_probabilities'):
            for team in ['red', 'blue']:
                change = abs(probabilities[team] - self.last_probabilities[team])
                if change >= threshold:
                    message = f"BIG SWING: {team.upper()} TEAM {probabilities[team]:.1%} WIN CHANCE!"
                    self._add_analytics_alert(message, 'probability', 2.0)
        
        self.last_probabilities = probabilities.copy()

    def _update_visual_effects(self):
        """Update all visual effects"""
        # Update particle systems
        for system in self.particle_systems[:]:
            if datetime.now() >= system['end_time']:
                self.particle_systems.remove(system)
            else:
                self._update_particle_system(system)
        
        # Update animations
        for anim in self.active_animations[:]:
            if datetime.now() >= anim['end_time']:
                self.active_animations.remove(anim)
            else:
                anim['frame'] = int(
                    (datetime.now() - anim['start_time']).total_seconds() 
                    * anim['fps']
                ) % len(anim['frames'])

    def _update_particle_system(self, system):
        """Update particles in a particle system"""
        dt = self.game.clock.get_time() / 1000.0
        for particle in system['particles'][:]:
            particle['life'] -= dt
            if particle['life'] <= 0:
                system['particles'].remove(particle)
            else:
                particle['x'] += particle['dx'] * dt
                particle['y'] += particle['dy'] * dt
                particle['alpha'] = int(255 * (particle['life'] / particle['max_life']))

    def _update_analytics_alerts(self):
        """Update analytics alert system"""
        current_time = datetime.now()
        
        # Remove expired alerts
        self.analytics_alert_queue = [
            alert for alert in self.analytics_alert_queue
            if current_time < alert['end_time']
        ]
        
        # Update alert positions
        y_offset = 100
        for alert in self.analytics_alert_queue:
            alert['y'] = y_offset
            y_offset += 40

    def _trigger_random_event(self):
        """Trigger a random game event."""
        events = [
            self._start_quick_strike,
            self._activate_bonus_goal,
            self._start_combo_challenge
        ]
        
        # Don't start new events in final frenzy
        if not self.frenzy_mode:
            event = random.choice(events)
            event()
        
        # Set next event time (between 20-40 seconds)
        self.next_event_time = datetime.now() + timedelta(seconds=random.randint(20, 40))

    def _start_quick_strike(self):
        """Start a quick strike challenge."""
        self.quick_strike_active = True
        self.quick_strike_deadline = datetime.now() + timedelta(seconds=15)
        self.active_event = "QUICK STRIKE CHALLENGE! SCORE IN 15 SECONDS!"
        self._play_sound('quick_strike')
        self.stats['quick_strikes_attempted'] += 1

    def _activate_bonus_goal(self):
        """Activate bonus goal scoring."""
        self.current_goal_value = random.choice([2, 3])
        self.event_duration = datetime.now() + timedelta(seconds=20)
        self.active_event = f"{self.current_goal_value}X POINTS PER GOAL!"
        self._play_sound('bonus')

    def _start_combo_challenge(self):
        """Start a combo goal challenge."""
        self.combo_count = 0
        self.event_duration = datetime.now() + timedelta(seconds=30)
        self.active_event = "COMBO CHALLENGE! QUICK GOALS FOR BONUS POINTS!"
        self._play_sound('bonus')

    def _start_final_minute_frenzy(self):
        """Activate final minute frenzy mode."""
        self.frenzy_mode = True
        self.active_event = "FINAL MINUTE FRENZY! ALL GOALS WORTH DOUBLE!"
        self._play_sound('frenzy')
        self._add_analytics_alert("FINAL MINUTE FRENZY ACTIVATED!", 'frenzy', 3.0)

    def handle_goal(self, team):
        """Handle goal scoring with all bonuses."""
        current_time = datetime.now()
        points = self.current_goal_value
        bonuses = []
        
        # Calculate all bonuses
        if self.first_goal_opportunity:
            # Scale bonus based on how quickly they scored
            time_taken = self.settings.period_length - self.clock
            max_bonus = 3
            bonus = max(1, int(max_bonus * (1 - time_taken / self.first_goal_window)))
            points += bonus
            bonuses.append(f"FIRST GOAL +{bonus}!")
            self.first_goal_opportunity = False
            self.stats['bonus_points_earned'] += bonus
        
        # Quick strike bonus
        if self.quick_strike_active:
            points *= 2
            bonuses.append("QUICK STRIKE!")
            self.quick_strike_active = False
            self.stats['quick_strikes_successful'] += 1
            
        # Comeback bonus
        comeback_bonus = self._calculate_comeback_bonus(team)
        if comeback_bonus > 0:
            points += comeback_bonus
            bonuses.append(f"COMEBACK +{comeback_bonus}!")
            self.stats['comeback_goals'] += 1
            
        # Combo bonus
        if self.combo_count > 0:
            time_since_last = (current_time - self.last_goal_time).total_seconds()
            if time_since_last < 10:  # 10 seconds for combo
                self.combo_count += 1
                combo_bonus = min(self.combo_count - 1, 3)
                points += combo_bonus
                bonuses.append(f"COMBO x{self.combo_count}")
                self._play_sound('combo')
                self.stats['max_combo'] = max(self.stats['max_combo'], self.combo_count)
            else:
                self.combo_count = 1
        else:
            self.combo_count = 1
            
        # Final minute frenzy
        if self.frenzy_mode:
            points *= 2
            bonuses.append("FRENZY")
            self.stats['frenzy_goals'] += 1
            
        # Update score and display
        self.score[team] += points
        self.last_goal_time = current_time
        self.stats['total_bonus_multiplier'] += (points / self.current_goal_value - 1)
        
        # Show all active bonuses
        if bonuses:
            bonus_text = " + ".join(bonuses)
            self.active_event = f"{points} POINTS! {bonus_text}"
        else:
            self.active_event = f"{points} POINTS!"

    def _calculate_comeback_bonus(self, team):
        """Calculate comeback bonus based on score difference and time."""
        if team == 'red':
            score_diff = self.score['blue'] - self.score['red']
        else:
            score_diff = self.score['red'] - self.score['blue']
            
        if score_diff <= 0:
            return 0
            
        time_factor = min(1.0, (self.settings.period_length - self.clock) / self.settings.period_length * 4)
        score_factor = min(1.0, score_diff / 5)
        
        bonus = round(min(3, score_factor * time_factor * 3))
        return bonus

    def _end_current_event(self):
        """End the current special event."""
        self.current_goal_value = 1
        self.event_duration = None
        if not self.frenzy_mode:  # Don't clear frenzy message
            self.active_event = None

    def _play_sound(self, sound_name):
        """Play a sound effect with cooldown."""
        current_time = datetime.now()
        if (current_time - self.last_sound_time).total_seconds() >= self.sound_cooldown:
            if sound_name in self.crazy_sounds and self.crazy_sounds[sound_name]:
                self.crazy_sounds[sound_name].play()
                self.last_sound_time = current_time

    def draw(self):
        """Draw the game screen."""
        # Draw background
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(self.settings.bg_color)

        # Draw base game elements
        super().draw()
        
        # Draw quick strike challenge if active
        if self.quick_strike_active:
            self._draw_quick_strike()
        
        # Draw frenzy mode overlay
        if self.frenzy_mode and self.frenzy_overlay:
            overlay = self.frenzy_overlay.copy()
            overlay.set_alpha(100)
            self.screen.blit(overlay, (0, 0))
        
        # Draw analytics overlays if enabled
        if self.show_analytics:
            self._draw_analytics_alerts()
        
        # Draw active event text
        if self.active_event:
            self._draw_event_text()
            
        # Draw visual effects
        self._draw_particle_systems()
        self._draw_active_animations()

    def _draw_quick_strike(self):
        """Draw quick strike challenge elements"""
        if not self.quick_strike_deadline:
            return
            
        remaining = (self.quick_strike_deadline - datetime.now()).total_seconds()
        if remaining > 0:
            if self.quick_strike_overlay:
                self.screen.blit(self.quick_strike_overlay, (0, 0))
            
            # Draw timer
            timer_text = self.font_large.render(f"{int(remaining)}s", True, (255, 255, 0))
            timer_rect = timer_text.get_rect(center=(self.settings.screen_width // 2, 240))
            self.screen.blit(timer_text, timer_rect)

    def _draw_event_text(self):
        """Draw active event text with effects"""
        text_surface = self.font_large.render(self.active_event, True, (255, 140, 0))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 200))
        self.screen.blit(text_surface, text_rect)

    def get_next_random_sound_interval(self):
        """Get the next random sound interval."""
        min_interval = self.settings.random_sound_min_interval
        max_interval = self.settings.random_sound_max_interval
        return random.uniform(min_interval, max_interval)

    def play_random_sound(self):
        """Play a random sound."""
        if self.game.sounds_enabled and self.game.sounds.get('random_sounds'):
            random_sound = random.choice(self.game.sounds['random_sounds'])
            random_sound.play()
            logging.info("Random sound played")

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        self.crazy_sounds = {}
        self.background = None
        self.overlay = None
        self.bonus_indicator = None
        self.frenzy_overlay = None
        self.quick_strike_overlay = None
        self.particle_images = {}
        logging.info('Crazy Play mode cleanup completed')
        
        # Log final statistics
        logging.info(f"Final stats: {json.dumps(self.stats, indent=2)}")
