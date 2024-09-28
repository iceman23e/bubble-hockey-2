# game.py

import pygame
import sys
import os
from utils import load_image, load_sound
from settings import Settings
from database import Database
import logging
import random
from datetime import datetime

class Game:
    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.clock = pygame.time.Clock()
        self.db = Database()
        self.current_game_id = None  # To track the current game in the database
        self.load_assets()
        self.mode = None
        self.gameplay = None
        self.is_over = False

    def load_assets(self):
        # Load fonts
        self.font_small = pygame.font.Font('assets/fonts/Pixellari.ttf', 20)

        # Load sounds
        self.sounds = {
            'period_start': load_sound('assets/sounds/period_start.wav'),
            'period_end': load_sound('assets/sounds/period_end.wav'),
            'goal_scored': load_sound('assets/sounds/goal_scored.wav'),
            'countdown_timer': load_sound('assets/sounds/countdown_timer.wav'),
            'taunts': [load_sound(f'assets/sounds/taunt_{i}.wav') for i in range(1, 6)],  # Assuming 5 taunts
            'lucky_shot': load_sound('assets/sounds/lucky_shot.wav'),
            'goalie_interference': load_sound('assets/sounds/goalie_interference.wav'),
            'power_play': load_sound('assets/sounds/power_play.wav'),
            'momentum_shift': load_sound('assets/sounds/momentum_shift.wav'),
            'button_click': load_sound('assets/sounds/button_click.wav'),
            # Load other sounds...
        }

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

    def cleanup(self):
        # Cleanup resources
        self.db.close()

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
        self.sounds_enabled = True  # Assuming sounds can be toggled
        if self.sounds_enabled:
            self.game.sounds['period_start'].play()

    def handle_event(self, event):
        pass  # Handle game events if needed

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
        # Handle other updates like goal detection

    def draw(self, screen):
        # Draw the gameplay elements
        # For simplicity, let's display the score and period
        screen.fill((0, 0, 0))
        score_text = self.game.font_small.render(f"Red: {self.score['red']} - Blue: {self.score['blue']}", True, (255, 255, 255))
        period_text = self.game.font_small.render(f"Period: {self.period}/{self.max_periods}", True, (255, 255, 255))
        clock_text = self.game.font_small.render(f"Time Left: {int(self.clock)}s", True, (255, 255, 255))
        screen.blit(score_text, (10, 10))
        screen.blit(period_text, (10, 40))
        screen.blit(clock_text, (10, 70))

    def goal_scored(self, team):
        self.score[team] += 1
        if self.sounds_enabled:
            self.game.sounds['goal_scored'].play()
        self.game.record_goal(team)

class EvolvedMode(ClassicMode):
    def __init__(self, game):
        super().__init__(game)
        self.taunt_timer = 0
        self.taunt_frequency = game.settings.taunt_frequency

    def update(self):
        super().update()
        # Taunt logic
        self.taunt_timer += self.game.clock.get_time() / 1000
        if self.taunt_timer >= self.taunt_frequency:
            self.taunt_timer = 0
            taunt_sound = random.choice(self.game.sounds['taunts'])
            if self.sounds_enabled:
                taunt_sound.play()

class CrazyPlayMode(EvolvedMode):
    def __init__(self, game):
        super().__init__(game)
        self.power_up_timer = 0
        self.power_up_frequency = game.settings.power_up_frequency
        self.active_power_up = None

    def update(self):
        super().update()
        # Power-up logic
        self.power_up_timer += self.game.clock.get_time() / 1000
        if self.power_up_timer >= self.power_up_frequency:
            self.power_up_timer = 0
            self.trigger_power_up()

    def trigger_power_up(self):
        power_ups = ['lucky_shot', 'goalie_interference', 'power_play', 'momentum_shift']
        self.active_power_up = random.choice(power_ups)
        if self.sounds_enabled:
            self.game.sounds[self.active_power_up].play()
        # Implement power-up effects as needed

    def draw(self, screen):
        super().draw(screen)
        if self.active_power_up:
            power_up_text = self.game.font_small.render(f"Power-Up: {self.active_power_up.replace('_', ' ').title()}", True, (255, 255, 0))
            screen.blit(power_up_text, (10, 100))
