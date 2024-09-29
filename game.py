# game.py

import pygame
import sys
import os
import json
from utils import load_image, load_sound
from settings import Settings
from database import Database
import logging
import random
from datetime import datetime, timedelta

class Game:
    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.clock = pygame.time.Clock()
        self.db = Database()
        self.current_game_id = None
        self.load_assets()
        self.mode = None
        self.gameplay = None
        self.is_over = False
        self.sounds_enabled = True
        self.font_small = pygame.font.Font('assets/fonts/Pixellari.ttf', 20)

    def load_assets(self):
        # Load theme configuration
        theme_path = f'assets/themes/{self.settings.current_theme}'
        theme_config_path = os.path.join(theme_path, 'theme.json')
        if os.path.exists(theme_config_path):
            with open(theme_config_path, 'r') as f:
                self.theme_data = json.load(f)
        else:
            self.theme_data = {}

        # Load fonts
        self.font_small = self.load_theme_font('font_small', 'assets/fonts/Pixellari.ttf', 20)

        # Load images
        self.taunt_button_image = self.load_theme_image('taunt_button', 'assets/images/taunt_button.png')
        self.power_up_icon_image = self.load_theme_image('power_up_icon', 'assets/images/power_up_icon.png')
        # Other images...

        # Load sounds
        self.sounds = {
            'taunts': self.load_theme_sounds('taunts', 'assets/sounds/taunts', 5),
            'random_sounds': self.load_theme_sounds('random_sounds', 'assets/sounds/random_sounds', 5),
            # Other sounds...
        }

    def load_theme_image(self, asset_name, default_path):
        asset_path = self.theme_data.get('assets', {}).get(asset_name, 'default')
        if asset_path == 'default':
            return load_image(default_path)
        else:
            return load_image(os.path.join(f'assets/themes/{self.settings.current_theme}', asset_path))

    def load_theme_sound(self, asset_name, default_path):
        asset_path = self.theme_data.get('assets', {}).get(asset_name, 'default')
        if asset_path == 'default':
            return load_sound(default_path)
        else:
            return load_sound(os.path.join(f'assets/themes/{self.settings.current_theme}', asset_path))

    def load_theme_sounds(self, asset_name, default_dir, count):
        sounds = []
        for i in range(1, count + 1):
            sound_key = f'{asset_name}_{i}'
            sound_path = self.theme_data.get('assets', {}).get(sound_key, 'default')
            if sound_path == 'default':
                sound_file = f'{default_dir}/{asset_name}_{i}.wav'
            else:
                sound_file = os.path.join(f'assets/themes/{self.settings.current_theme}', sound_path)
            sounds.append(load_sound(sound_file))
        return sounds

    def load_theme_font(self, asset_name, default_path, size):
        font_path = self.theme_data.get('assets', {}).get(asset_name, 'default')
        if font_path == 'default':
            return pygame.font.Font(default_path, size)
        else:
            return pygame.font.Font(os.path.join(f'assets/themes/{self.settings.current_theme}', font_path), size)

    def set_mode(self, mode):
        self.mode = mode
        self.is_over = False
        if mode == 'classic':
            self.gameplay = ClassicMode(self)
        elif mode == 'evolved':
            self.gameplay = EvolvedMode(self)
        elif mode == 'crazy_play':
            self.gameplay = CrazyPlayMode(self)
        # Record game start in the database
        self.current_game_id = self.db.start_new_game(self.mode)

    def handle_event(self, event):
        # Pass events to gameplay
        self.gameplay.handle_event(event)

    def update(self):
        self.gameplay.update()
        if self.gameplay.is_over:
            self.is_over = True
            # Record game end in database
            self.db.end_game(self.current_game_id, self.gameplay.score)

    def draw(self):
        self.gameplay.draw(self.screen)

    def record_goal(self, team):
        current_time = datetime.now()
        self.db.cursor.execute('''
            INSERT INTO goal_events (game_id, team, time)
            VALUES (?, ?, ?)
        ''', (self.current_game_id, team, current_time))
        self.db.conn.commit()

    def play_taunt(self, player_team):
        if self.sounds_enabled and self.settings.taunts_enabled:
            taunt_sound = random.choice(self.sounds['taunts'])
            taunt_sound.play()
            # Optionally record taunt usage for stats

    def play_random_sound(self):
        if self.sounds_enabled and self.settings.random_sounds_enabled:
            random_sound = random.choice(self.sounds['random_sounds'])
            random_sound.play()

    def cleanup(self):
        # Cleanup resources
        self.db.close()

    def get_game_status(self):
        # Return current game status for web display
        status = {
            'score': self.gameplay.score,
            'period': self.gameplay.period,
            'max_periods': self.gameplay.max_periods,
            'clock': self.gameplay.clock,
            'active_event': getattr(self.gameplay, 'active_event', None)
        }
        return status

# Game Mode Classes

class ClassicMode:
    def __init__(self, game):
        self.game = game
        self.period = 1
        self.max_periods = 3
        self.period_length = game.settings.period_length
        self.clock = self.period_length
        self.score = {'red': 0, 'blue': 0}
        self.is_over = False
        self.sounds_enabled = game.sounds_enabled
        self.taunt_button_rect = pygame.Rect(1300, 10, 100, 50)  # Position of taunt button
        if self.sounds_enabled:
            self.game.sounds['period_start'].play()
        # For random sounds
        self.random_sound_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if self.taunt_button_rect.collidepoint(pos):
                # Determine which player pressed the taunt button
                player_team = 'red' if pos[0] < self.game.settings.screen_width / 2 else 'blue'
                self.game.play_taunt(player_team)

    def update(self):
        # Update game clock
        delta_time = self.game.clock.tick(60) / 1000  # Convert milliseconds to seconds
        self.clock -= delta_time
        if self.clock <= 0:
            if self.period < self.max_periods:
                self.period += 1
                self.clock = self.period_length
                if self.sounds_enabled:
                    self.game.sounds['period_end'].play()
                    self.game.sounds['period_start'].play()
            else:
                # End game
                self.is_over = True
                if self.sounds_enabled:
                    self.game.sounds['period_end'].play()
        # Handle random sounds
        self.update_random_sounds(delta_time)

    def update_random_sounds(self, delta_time):
        if self.game.settings.random_sounds_enabled:
            self.random_sound_timer += delta_time
            if self.random_sound_timer >= self.game.settings.random_sound_frequency:
                self.random_sound_timer = 0
                self.game.play_random_sound()

    def draw(self, screen):
        # Draw the gameplay elements
        # Enhanced game screen with arcade-style visuals
        screen.fill(self.game.settings.bg_color)  # Background color
        # Draw taunt button
        screen.blit(self.game.taunt_button_image, self.taunt_button_rect)

        # Display score, period, and clock with modern styling
        score_text = self.game.font_small.render(f"Red: {self.score['red']} - Blue: {self.score['blue']}", True, (255, 255, 255))
        period_text = self.game.font_small.render(f"Period: {self.period}/{self.max_periods}", True, (255, 255, 255))
        clock_text = self.game.font_small.render(f"Time Left: {int(self.clock)}s", True, (255, 255, 255))

        # Position text centrally with a jumbotron style
        screen.blit(score_text, (self.game.settings.screen_width // 2 - score_text.get_width() // 2, 20))
        screen.blit(period_text, (self.game.settings.screen_width // 2 - period_text.get_width() // 2, 50))
        screen.blit(clock_text, (self.game.settings.screen_width // 2 - clock_text.get_width() // 2, 80))

    def goal_scored(self, team):
        self.score[team] += 1
        if self.sounds_enabled:
            self.game.sounds['goal_scored'].play()
        self.game.record_goal(team)

class EvolvedMode(ClassicMode):
    def __init__(self, game):
        super().__init__(game)
        # Initialize combo goal variables
        self.combo_timer = None
        self.combo_count = 0
        self.last_goal_time = None
        self.last_goal_team = None

    def goal_scored(self, team):
        super().goal_scored(team)
        current_time = datetime.now()
        # Check for combo goals
        if self.game.settings.combo_goals_enabled:
            if self.last_goal_team == team and self.last_goal_time:
                time_diff = (current_time - self.last_goal_time).total_seconds()
                if time_diff <= self.game.settings.combo_time_window:
                    self.combo_count += 1
                    # Apply combo reward
                    self.apply_combo_reward(team)
                else:
                    self.combo_count = 1  # Reset combo count
            else:
                self.combo_count = 1  # Start new combo

            self.last_goal_time = current_time
            self.last_goal_team = team

    def apply_combo_reward(self, team):
        # Ensure combo count does not exceed maximum stack
        if self.combo_count > self.game.settings.combo_max_stack:
            self.combo_count = self.game.settings.combo_max_stack

        # Determine reward based on settings
        if self.game.settings.combo_reward_type == 'extra_point':
            self.score[team] += 1  # Add extra point
        elif self.game.settings.combo_reward_type == 'power_up':
            # Add a power-up to the player's queue (implementation depends on power-up system)
            pass

class CrazyPlayMode(EvolvedMode):
    def __init__(self, game):
        super().__init__(game)
        self.power_up_icon_rect = pygame.Rect(1200, 10, 100, 50)  # Position of power-up icon
        self.active_power_up = None
        self.power_up_queue = []
        self.power_up_available = False

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if self.power_up_icon_rect.collidepoint(pos):
                if self.power_up_available:
                    self.activate_power_up()

    def update(self):
        super().update()
        # Random power-up logic
        # Implement as per game design

    def apply_combo_reward(self, team):
        if self.game.settings.combo_reward_type == 'extra_point':
            self.score[team] += 1  # Add extra point
        elif self.game.settings.combo_reward_type == 'power_up':
            # Add a power-up to the player's queue
            self.power_up_queue.append('some_power_up')  # Replace with actual power-up
            self.power_up_available = True
        if self.combo_count > self.game.settings.combo_max_stack:
            self.combo_count = self.game.settings.combo_max_stack

    def activate_power_up(self):
        if self.power_up_queue:
            power_up = self.power_up_queue.pop(0)
            # Activate the power-up (implementation depends on power-up system)
            self.power_up_available = bool(self.power_up_queue)

    def draw(self, screen):
        super().draw(screen)
        # Draw power-up icon if available
        if self.power_up_available:
            screen.blit(self.game.power_up_icon_image, self.power_up_icon_rect)
