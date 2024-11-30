# intro.py

import pygame
import random
from utils import load_image, load_sound
import logging

class Intro:
    def __init__(self, screen_manager, settings):
        self.screen_manager = screen_manager
        self.settings = settings
        self.clock = pygame.time.Clock()
        self.load_assets()
        self.init_intro()
        self.is_finished = False

    def load_assets(self):
        # Load fonts
        self.font_msdos = pygame.font.Font('assets/fonts/Perfect DOS VGA 437.ttf', 24)
        self.font_title = pygame.font.Font('assets/fonts/PressStart2P-Regular.ttf', 36)
        self.font_matrix = pygame.font.Font('assets/fonts/VCR_OSD_MONO_1.001.ttf', 24)

        # Load images
        self.images = {
            'lava_flow_frames': [load_image(f'assets/images/lava_flow_frames/frame_{i}.png') for i in range(0, 30)],
        }

        # Load sounds
        self.sounds = {
            'lava_flow': load_sound('assets/sounds/lava_flow.wav'),
        }

        # Matrix code characters
        self.matrix_chars = [chr(i) for i in range(33, 126)]  # ASCII characters from '!' to '~'

    def init_intro(self):
        self.intro_state = 'system_ready'
        self.progress = 0
        self.show_progress_bar = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.lava_animation_frame = 0
        self.lava_animation_done = False
        self.intro_timer = 0
        self.melting_started = False
        self.matrix_code_started = False
        self.matrix_code_columns = []
        logging.debug('Intro initialized')

        # Variables for the melting effect
        self.text_slices = {'red': [], 'blue': []}
        self.drips = {'red': [], 'blue': []}
        self.melting_surface = None  # Pre-rendered surface for the melting text

        # Register click zones for both screens
        for screen in ['red', 'blue']:
            self.screen_manager.register_touch_zone(
                screen,
                'start_intro',
                pygame.Rect(0, 0, self.settings.screen_width, self.settings.screen_height),
                self.handle_click
            )

    def handle_click(self, screen, pos):
        """Handle click events on either screen"""
        if self.intro_state == 'system_ready':
            self.show_progress_bar = True

    def handle_event(self, event):
        """Handle events (kept for compatibility)"""
        # Event handling is now primarily done through screen_manager's touch zones
        pass

    def update(self):
        if self.intro_state == 'system_ready':
            # Blink the cursor
            self.cursor_timer += self.clock.get_time()
            if self.cursor_timer >= 500:  # Cursor blinks every 500ms
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
        elif self.intro_state == 'progress_bar':
            # Update progress bar
            self.progress += 0.5  # Adjust speed as needed
            if self.progress >= 100:
                self.intro_state = 'lava_transition'
                self.sounds['lava_flow'].play()
        elif self.intro_state == 'lava_transition':
            # Update lava flow animation
            self.lava_animation_frame += 1
            if self.lava_animation_frame >= len(self.images['lava_flow_frames']):
                self.lava_animation_frame = len(self.images['lava_flow_frames']) - 1
                self.lava_animation_done = True
            if self.lava_animation_done:
                self.intro_state = 'bedwards_presents'
                self.sounds['lava_flow'].stop()
                # Initialize melting effect for both screens
                self.init_melting_effect()
        elif self.intro_state == 'bedwards_presents':
            # Update melting effect for both screens
            self.update_melting_effect()
            if not any(self.text_slices.values()) and not any(self.drips.values()):
                # Once melting is done on both screens, proceed to matrix code
                self.intro_state = 'matrix_code'
        elif self.intro_state == 'matrix_code':
            # Start matrix code transition
            if not self.matrix_code_started:
                self.init_matrix_code()
                self.matrix_code_started = True
            self.update_matrix_code()
            # Transition to main menu after some time
            self.intro_timer += self.clock.get_time()
            if self.intro_timer >= 3000:  # 3 seconds of matrix code
                self.is_finished = True

    def draw(self):
        """Draw the intro sequence on both screens"""
        for screen in ['red', 'blue']:
            # Clear the screen
            self.screen_manager.clear_screen(screen)
            screen_surface = self.screen_manager.get_screen(screen)

            if self.intro_state == 'system_ready':
                text = self.font_msdos.render('System Ready', True, (0, 255, 0))
                screen_surface.blit(text, (50, 250))
                if self.cursor_visible:
                    cursor = self.font_msdos.render('_', True, (0, 255, 0))
                    screen_surface.blit(cursor, (text.get_width() + 50, 250))

            elif self.intro_state == 'progress_bar':
                text = self.font_msdos.render('System Ready', True, (0, 255, 0))
                screen_surface.blit(text, (50, 250))
                pygame.draw.rect(screen_surface, (0, 255, 0), (50, 280, int(self.progress * 14), 20))

            elif self.intro_state == 'lava_transition':
                frame = self.images['lava_flow_frames'][self.lava_animation_frame]
                screen_surface.blit(frame, (0, 0))

            elif self.intro_state == 'bedwards_presents':
                # Draw melting effect specific to this screen
                self.draw_melting_effect(screen)

            elif self.intro_state == 'matrix_code':
                self.draw_matrix_code(screen)

            # Update the specific screen
            self.screen_manager.update_display(screen)

    def init_melting_effect(self):
        """Initialize melting effect for both screens"""
        text_surface = self.font_title.render('Bedwards Productions Presents', True, (255, 69, 0))
        text_width, text_height = text_surface.get_size()
        self.text_x = (self.settings.screen_width - text_width) // 2
        self.text_y = (self.settings.screen_height - text_height) // 2

        self.melting_surface = pygame.Surface((text_width, text_height), pygame.SRCALPHA)
        self.melting_surface.blit(text_surface, (0, 0))

        # Initialize slices for both screens
        for screen in ['red', 'blue']:
            slice_width = 4
            for x in range(0, text_width, slice_width):
                rect = pygame.Rect(x, 0, slice_width, text_height)
                slice_image = self.melting_surface.subsurface(rect).copy()
                slice_dict = {
                    'image': slice_image,
                    'x': self.text_x + x,
                    'y': self.text_y,
                    'speed': random.uniform(0.3, 0.8),
                    'acceleration': random.uniform(0.02, 0.05),
                    'drip_timer': random.uniform(0.5, 1.5),
                    'finished': False,
                }
                self.text_slices[screen].append(slice_dict)

    def update_melting_effect(self):
        """Update melting effect for both screens"""
        for screen in ['red', 'blue']:
            # Update each text slice
            for slice_dict in self.text_slices[screen]:
                if not slice_dict['finished']:
                    slice_dict['y'] += slice_dict['speed']
                    slice_dict['speed'] += slice_dict['acceleration']
                    slice_dict['drip_timer'] -= self.clock.get_time() / 1000
                    if slice_dict['drip_timer'] <= 0:
                        self.create_drip(screen, slice_dict)
                        slice_dict['drip_timer'] = random.uniform(0.5, 1.5)
                    if slice_dict['y'] > self.settings.screen_height:
                        slice_dict['finished'] = True

            # Remove finished slices
            self.text_slices[screen] = [s for s in self.text_slices[screen] if not s['finished']]

            # Update drips
            for drip in self.drips[screen]:
                drip['y'] += drip['speed']
                drip['speed'] += drip['acceleration']
                drip['alpha'] -= 5
                if drip['alpha'] <= 0 or drip['y'] > self.settings.screen_height:
                    drip['finished'] = True
                else:
                    drip['image'].set_alpha(drip['alpha'])

            # Remove finished drips
            self.drips[screen] = [d for d in self.drips[screen] if not d['finished']]

    def draw_melting_effect(self, screen):
        """Draw melting effect for a specific screen"""
        screen_surface = self.screen_manager.get_screen(screen)
        # Draw each text slice
        for slice_dict in self.text_slices[screen]:
            screen_surface.blit(slice_dict['image'], (slice_dict['x'], slice_dict['y']))
        # Draw drips
        for drip in self.drips[screen]:
            screen_surface.blit(drip['image'], (drip['x'], drip['y']))

    def create_drip(self, screen, slice_dict):
        """Create a drip effect for a specific screen"""
        drip_width = slice_dict['image'].get_width()
        drip_height = random.randint(5, 10)
        drip_image = pygame.Surface((drip_width, drip_height), pygame.SRCALPHA)
        color = (255, random.randint(0, 69), 0)
        pygame.draw.ellipse(drip_image, color, [0, 0, drip_width, drip_height])
        drip_dict = {
            'image': drip_image,
            'x': slice_dict['x'],
            'y': slice_dict['y'] + slice_dict['image'].get_height(),
            'speed': slice_dict['speed'],
            'acceleration': slice_dict['acceleration'],
            'alpha': 255,
            'finished': False,
        }
        self.drips[screen].append(drip_dict)

    def init_matrix_code(self):
        """Initialize matrix code effect for both screens"""
        self.matrix_columns = {'red': [], 'blue': []}
        font_width, font_height = self.font_matrix.size('A')
        columns = self.settings.screen_width // font_width
        
        for screen in ['red', 'blue']:
            for i in range(columns):
                x = i * font_width
                y = random.randint(-self.settings.screen_height, 0)
                speed = random.randint(4, 7)
                self.matrix_columns[screen].append({'x': x, 'y': y, 'speed': speed})
        self.intro_timer = 0

    def update_matrix_code(self):
        """Update matrix code effect for both screens"""
        for screen in ['red', 'blue']:
            for column in self.matrix_columns[screen]:
                column['y'] += column['speed']
                if column['y'] > self.settings.screen_height:
                    column['y'] = random.randint(-self.settings.screen_height, 0)
                    column['speed'] = random.randint(4, 7)

    def draw_matrix_code(self, screen):
        """Draw matrix code effect for a specific screen"""
        screen_surface = self.screen_manager.get_screen(screen)
        screen_surface.fill((0, 0, 0))
        for column in self.matrix_columns[screen]:
            char = random.choice(self.matrix_chars)
            color = (255, random.randint(0, 140), 0)
            text = self.font_matrix.render(char, True, color)
            screen_surface.blit(text, (column['x'], column['y']))

    def run(self):
        """Run the intro sequence"""
        while not self.is_finished:
            self.clock.tick(60)
            self.update()
            self.draw()
