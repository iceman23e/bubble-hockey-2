# crazy_play_mode.py

from base_game_mode import BaseGameMode
import pygame
import logging
import random
from datetime import datetime, timedelta

def load_sound(file_path):
    """Utility function to load a sound file."""
    try:
        return pygame.mixer.Sound(file_path)
    except pygame.error as e:
        logging.error(f"Could not load sound file {file_path}: {e}")
        return None

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
        
        # Load assets and sounds
        self.load_assets()
        self.load_crazy_sounds()
        
        # Initialize random sound timing variables
        self.last_random_sound_time = datetime.now().timestamp()
        self.next_random_sound_interval = self.get_next_random_sound_interval()

    def load_assets(self):
        """Load assets specific to Crazy Play mode."""
        # Ensure that pygame has been initialized before loading images
        if not pygame.get_init():
            pygame.init()
        self.background_image = pygame.image.load('assets/crazy_play/images/crazy_background.png')
        # Load other crazy play mode assets as needed

    def load_crazy_sounds(self):
        """Load sound effects specific to crazy mode."""
        self.crazy_sounds = {
            'bonus': load_sound('assets/sounds/bonus_activated.wav'),
            'quick_strike': load_sound('assets/sounds/quick_strike.wav'),
            'combo': load_sound('assets/sounds/combo_goal.wav'),
            'frenzy': load_sound('assets/sounds/frenzy.wav'),
        }

    def update(self):
        """Update the game state."""
        # Handle clock updates based on puck possession
        if self.game.puck_possession == 'in_play':
            dt = self.game.clock.tick(60) / 1000.0
            
            # Handle intermission clock if active
            if self.intermission_clock is not None:
                self.intermission_clock -= dt
                if self.intermission_clock <= 0:
                    self.intermission_clock = None
                    logging.info("Intermission ended")
            else:
                self.clock -= dt
    
        else:
            # Maintain frame rate without decrementing clock
            self.game.clock.tick(60)
        
        super().update()
        
        current_time = datetime.now()
        
        # Check for final frenzy mode
        if not self.frenzy_mode and self.clock <= self.frenzy_window:
            self._start_final_minute_frenzy()
            
        # Check if first goal opportunity has expired
        if self.first_goal_opportunity and (self.settings.period_length - self.clock) > self.first_goal_window:
            self.first_goal_opportunity = False
        
        # Check if it's time for a new random event
        if current_time >= self.next_event_time:
            self._trigger_random_event()
            
        # Update quick strike challenge if active
        if self.quick_strike_active and current_time >= self.quick_strike_deadline:
            self._end_quick_strike()
            
        # Update event duration
        if self.event_duration and current_time >= self.event_duration:
            self._end_current_event()
        
        # Handle random sounds
        if self.game.sounds_enabled and self.game.sounds.get('random_sounds'):
            if (current_time.timestamp() - self.last_random_sound_time) >= self.next_random_sound_interval:
                self.play_random_sound()
                self.last_random_sound_time = current_time.timestamp()
                self.next_random_sound_interval = self.get_next_random_sound_interval()

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

    def handle_goal(self, team):
        """Handle goal scoring with various bonuses."""
        current_time = datetime.now()
        points = self.current_goal_value
        
        # Calculate all bonuses
        bonuses = []
        
        # First goal bonus (only within time window)
        if self.first_goal_opportunity:
            # Scale bonus based on how quickly they scored
            time_taken = self.settings.period_length - self.clock
            max_bonus = 3
            bonus = max(1, int(max_bonus * (1 - time_taken / self.first_goal_window)))
            points += bonus
            bonuses.append(f"FIRST GOAL +{bonus}!")
            self.first_goal_opportunity = False
        
        # Quick strike bonus
        if self.quick_strike_active:
            points *= 2
            bonuses.append("QUICK STRIKE!")
            self.quick_strike_active = False
            
        # Comeback bonus
        comeback_bonus = self._calculate_comeback_bonus(team)
        if comeback_bonus > 0:
            points += comeback_bonus
            bonuses.append(f"COMEBACK +{comeback_bonus}!")
            
        # Combo bonus
        if self.combo_count > 0:
            time_since_last = (current_time - self.last_goal_time).total_seconds()
            if time_since_last < 10:  # 10 seconds for combo
                self.combo_count += 1
                combo_bonus = min(self.combo_count - 1, 3)
                points += combo_bonus
                bonuses.append(f"COMBO x{self.combo_count}")
                self._play_sound('combo')
            else:
                self.combo_count = 1
        else:
            self.combo_count = 1
            
        # Final minute frenzy
        if self.frenzy_mode:
            points *= 2
            bonuses.append("FRENZY")
            
        # Update score and display
        self.score[team] += points
        self.last_goal_time = current_time
        
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
            
        # Calculate bonus based on score difference and time remaining
        # Maximum bonus is 3 points when down by 5+ with less than 25% of period remaining
        time_factor = min(1.0, (self.settings.period_length - self.clock) / self.settings.period_length * 4)
        score_factor = min(1.0, score_diff / 5)
        
        bonus = round(min(3, score_factor * time_factor * 3))
        return bonus

    def _play_sound(self, sound_name):
        """Play a sound effect with cooldown."""
        current_time = datetime.now()
        if (current_time - self.last_sound_time).total_seconds() >= self.sound_cooldown:
            if sound_name in self.crazy_sounds and self.crazy_sounds[sound_name]:
                self.crazy_sounds[sound_name].play()
                self.last_sound_time = current_time

    def handle_period_end(self):
        """Handle the end of a period."""
        super().handle_period_end()
        self.first_goal_opportunity = True
        self.frenzy_mode = False
        self.combo_count = 0
        self._end_current_event()

    def _end_current_event(self):
        """End the current special event."""
        self.current_goal_value = 1
        self.event_duration = None
        if not self.frenzy_mode:  # Don't clear frenzy message
            self.active_event = None

    def _end_quick_strike(self):
        """End quick strike challenge."""
        if self.quick_strike_active:
            self.quick_strike_active = False
            self.active_event = "QUICK STRIKE CHALLENGE FAILED!"

    def draw(self):
        """Draw the game screen with crazy mode elements."""
        # Draw base game elements
        super().draw()
        
        # Draw current event/bonus notification
        if self.active_event:
            event_text = self.font_large.render(self.active_event, True, (255, 140, 0))
            event_rect = event_text.get_rect(center=(self.settings.screen_width // 2, 200))
            self.screen.blit(event_text, event_rect)
            
        # Draw quick strike timer if active
        if self.quick_strike_active:
            remaining = (self.quick_strike_deadline - datetime.now()).total_seconds()
            if remaining > 0:
                timer_text = self.font_small.render(f"QUICK STRIKE: {int(remaining)}s", True, (255, 255, 0))
                timer_rect = timer_text.get_rect(center=(self.settings.screen_width // 2, 240))
                self.screen.blit(timer_text, timer_rect)

        # Draw current goal value if different from 1
        if self.current_goal_value > 1 or self.frenzy_mode:
            goal_value = self.current_goal_value * (2 if self.frenzy_mode else 1)
            value_text = self.font_small.render(f"Goals Worth: {goal_value} Points!", True, (255, 255, 0))
            value_rect = value_text.get_rect(center=(self.settings.screen_width // 2, 280))
            self.screen.blit(value_text, value_rect)

    def play_random_sound(self):
        """Play a random sound."""
        if self.game.sounds_enabled and self.game.sounds.get('random_sounds'):
            random_sound = random.choice(self.game.sounds['random_sounds'])
            random_sound.play()
            logging.info("Random sound played")

    def get_next_random_sound_interval(self):
        """Get the next random sound interval."""
        min_interval = self.settings.random_sound_min_interval
        max_interval = self.settings.random_sound_max_interval
        return random.uniform(min_interval, max_interval)

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        self.crazy_sounds = {}
