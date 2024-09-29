# menu.py

import pygame
import sys
import os
import subprocess
import logging
from utils import load_image, load_sound

class Menu:
    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.load_assets()
        self.init_menu()
        self.start_game = False
        self.selected_mode = None
        # Update notification flag
        self.update_available = False
        self.check_for_updates()
        # Timer for volcano animation
        self.volcano_animation_timer = 0
        self.volcano_frame = 0
        self.animation_interval = 100  # Milliseconds between frames

    def load_assets(self):
        # Load fonts
        self.font_title = pygame.font.Font('assets/fonts/PressStart2P-Regular.ttf', 36)
        self.font_small = pygame.font.Font('assets/fonts/PressStart2P-Regular.ttf', 20)

        # Load images based on current theme
        theme_path = f'assets/themes/{self.settings.current_theme}'
        self.images = {
            'volcano_eruption_frames': [load_image(f'{theme_path}/images/volcano_eruption_frames/frame_{i}.png') for i in range(0, 60)],
        }

        # Load sounds
        self.sounds = {
            'button_click': load_sound('assets/sounds/button_click.wav'),
        }

    def check_for_updates(self):
        """Check if an update is available by looking for the flag file."""
        if os.path.exists('update_available.flag'):
            self.update_available = True
            logging.info('Update available.')
        else:
            self.update_available = False

    def init_menu(self):
        # Initialize menu elements
        # Create menu buttons
        self.classic_button_text = self.font_title.render('1. CLASSIC', True, (255, 140, 0))
        self.evolved_button_text = self.font_title.render('2. EVOLVED', True, (255, 140, 0))
        self.crazy_play_button_text = self.font_title.render('3. CRAZY PLAY', True, (255, 140, 0))
        self.check_updates_button_text = self.font_title.render('Check for Updates', True, (255, 140, 0))
        self.exit_button_text = self.font_title.render('Exit', True, (255, 140, 0))

        # Button rectangles for detecting clicks
        self.classic_button_rect = self.classic_button_text.get_rect(center=(self.settings.screen_width // 2, 150))
        self.evolved_button_rect = self.evolved_button_text.get_rect(center=(self.settings.screen_width // 2, 220))
        self.crazy_play_button_rect = self.crazy_play_button_text.get_rect(center=(self.settings.screen_width // 2, 290))
        self.check_updates_button_rect = self.check_updates_button_text.get_rect(center=(self.settings.screen_width // 2, 360))
        self.exit_button_rect = self.exit_button_text.get_rect(center=(self.settings.screen_width // 2, 430))

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
            elif self.check_updates_button_rect.collidepoint(pos):
                self.sounds['button_click'].play()
                self.initiate_update()
            elif self.exit_button_rect.collidepoint(pos):
                self.sounds['button_click'].play()
                pygame.quit()
                sys.exit()
        elif event.type == pygame.KEYDOWN:
            # Optionally handle keyboard input if desired
            pass

    def update(self):
        # Update volcano animation timer
        self.volcano_animation_timer += self.settings.clock_tick
        if self.volcano_animation_timer >= self.animation_interval:
            self.volcano_frame = (self.volcano_frame + 1) % len(self.images['volcano_eruption_frames'])
            self.volcano_animation_timer = 0

    def draw(self):
        self.screen.fill((0, 0, 0))
        # Draw volcano animation
        volcano_frame_image = self.images['volcano_eruption_frames'][self.volcano_frame]
        self.screen.blit(volcano_frame_image, (0, 0))

        # Draw title
        title_text = self.font_title.render('BOILING POINT BUBBLE HOCKEY', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 50))
        self.screen.blit(title_text, title_rect)

        # Draw menu buttons
        self.screen.blit(self.classic_button_text, self.classic_button_rect)
        self.screen.blit(self.evolved_button_text, self.evolved_button_rect)
        self.screen.blit(self.crazy_play_button_text, self.crazy_play_button_rect)
        self.screen.blit(self.check_updates_button_text, self.check_updates_button_rect)
        self.screen.blit(self.exit_button_text, self.exit_button_rect)

        # Display update notification if available
        if self.update_available:
            update_text = "Update Available!"
            update_surface = self.font_small.render(update_text, True, (255, 0, 0))
            update_rect = update_surface.get_rect(center=(self.settings.screen_width // 2, 120))
            self.screen.blit(update_surface, update_rect)

    def reset(self):
        self.start_game = False
        self.selected_mode = None

    def initiate_update(self):
        """Initiate the update process."""
        logging.info('User initiated update from menu.')
        # Display updating message
        updating_text = "Updating... Please wait."
        text_surface = self.font_title.render(updating_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2))
        self.screen.blit(text_surface, text_rect)
        pygame.display.flip()
        # Perform the update
        try:
            # Navigate to the project directory
            os.chdir('/home/pi/bubble_hockey')
            # Pull the latest changes from the repository
            subprocess.run(['git', 'pull'], check=True)
            # Remove the update flag
            if os.path.exists('update_available.flag'):
                os.remove('update_available.flag')
            logging.info('Game updated successfully.')
            # Restart the game
            self.restart_game()
        except subprocess.CalledProcessError as e:
            logging.error(f'Update failed: {e}')
            # Display error message
            error_text = "Update failed. Check logs."
            error_surface = self.font_small.render(error_text, True, (255, 0, 0))
            error_rect = error_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2 + 50))
            self.screen.blit(error_surface, error_rect)
            pygame.display.flip()
            pygame.time.delay(3000)  # Pause for 3 seconds

    def restart_game(self):
        """Restart the game application."""
        logging.info('Restarting game...')
        pygame.quit()
        os.execv(sys.executable, ['python3'] + sys.argv)
