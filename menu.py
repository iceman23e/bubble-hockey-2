# menu.py

import pygame
from utils import load_image, load_sound
import logging

class Menu:
    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.load_assets()
        self.init_menu()
        self.start_game = False
        self.selected_mode = None

    def load_assets(self):
        # Load fonts
        self.font_title = pygame.font.Font('assets/fonts/PressStart2P-Regular.ttf', 36)

        # Load images based on current theme
        theme_path = f'assets/themes/{self.settings.current_theme}'
        self.images = {
            'volcano_eruption_frames': [load_image(f'{theme_path}/images/volcano_eruption_frames/frame_{i}.png') for i in range(0, 60)],
        }

        # Load sounds
        self.sounds = {
            'button_click': load_sound('assets/sounds/button_click.wav'),
        }

    def init_menu(self):
        # Initialize menu elements
        self.volcano_frame = 0
        self.volcano_animation_timer = 0

        # Create menu buttons
        self.classic_button_text = self.font_title.render('1. CLASSIC', True, (255, 140, 0))
        self.evolved_button_text = self.font_title.render('2. EVOLVED', True, (255, 140, 0))
        self.crazy_play_button_text = self.font_title.render('3. CRAZY PLAY', True, (255, 140, 0))
        self.settings_button_text = self.font_title.render('Settings', True, (255, 140, 0))

        # Button rectangles for detecting clicks
        self.classic_button_rect = self.classic_button_text.get_rect(center=(self.settings.screen_width // 2, 100))
        self.evolved_button_rect = self.evolved_button_text.get_rect(center=(self.settings.screen_width // 2, 150))
        self.crazy_play_button_rect = self.crazy_play_button_text.get_rect(center=(self.settings.screen_width // 2, 200))
        self.settings_button_rect = self.settings_button_text.get_rect(center=(1400, 280))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            if self.classic_button_rect.collidepoint(pos):
                self.sounds['button_click'].play()
                self.selected_mode = 'classic'
                self.start_game = True
            elif self.evolved_button_rect.collidepoint(pos):
                self.sounds['button_click'].play()
                self.selected_mode = 'evolved'
                self.start_game = True
            elif self.crazy_play_button_rect.collidepoint(pos):
                self.sounds['button_click'].play()
                self.selected_mode = 'crazy_play'
                self.start_game = True
            elif self.settings_button_rect.collidepoint(pos):
                self.sounds['button_click'].play()
                # Open settings menu (if implemented)

    def update(self):
        # Update volcano animation timer
        self.volcano_animation_timer += self.settings.clock_tick
        if self.volcano_animation_timer >= 100:  # Change frame every 100ms
            self.volcano_frame = (self.volcano_frame + 1) % len(self.images['volcano_eruption_frames'])
            self.volcano_animation_timer = 0

    def draw(self):
        self.screen.fill((0, 0, 0))
        # Draw volcano animation
        volcano_frame_image = self.images['volcano_eruption_frames'][self.volcano_frame]
        self.screen.blit(volcano_frame_image, (0, 0))

        # Draw title
        title_text = self.font_title.render('BOILING POINT BUBBLE HOCKEY', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 20))
        self.screen.blit(title_text, title_rect)

        # Draw menu buttons
        self.screen.blit(self.classic_button_text, self.classic_button_rect)
        self.screen.blit(self.evolved_button_text, self.evolved_button_rect)
        self.screen.blit(self.crazy_play_button_text, self.crazy_play_button_rect)
        self.screen.blit(self.settings_button_text, self.settings_button_rect)

    def reset(self):
        self.start_game = False
        self.selected_mode = None
