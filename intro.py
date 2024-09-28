# intro.py

import pygame
import random
from utils import load_image, load_sound
import logging

class Intro:
    def __init__(self, screen, settings):
        self.screen = screen
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
        self.text_slices = []
        self.drips = []
        self.melting_surface = None  # Pre-rendered surface for the melting text

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.intro_state == 'system_ready':
                self.show_progress_bar = True

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
                self.lava_animation_frame = len(self.images['lava_flow_frames']) - 1  # Hold on the last frame
                self.lava_animation_done = True
            if self.lava_animation_done:
                self.intro_state = 'bedwards_presents'
                self.sounds['lava_flow'].stop()
                # Initialize melting effect
                self.init_melting_effect()
        elif self.intro_state == 'bedwards_presents':
            # Update melting effect
            self.update_melting_effect()
            if not self.text_slices and not self.drips:
                # Once melting is done, proceed to matrix code
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
        if self.intro_state == 'system_ready':
            self.screen.fill((0, 0, 0))
            text = self.font_msdos.render('System Ready', True, (0, 255, 0))
            self.screen.blit(text, (50, 250))
            if self.cursor_visible:
                cursor = self.font_msdos.render('_', True, (0, 255, 0))
                self.screen.blit(cursor, (text.get_width() + 50, 250))
        elif self.intro_state == 'progress_bar':
            self.screen.fill((0, 0, 0))
            text = self.font_msdos.render('System Ready', True, (0, 255, 0))
            self.screen.blit(text, (50, 250))
            pygame.draw.rect(self.screen, (0, 255, 0), (50, 280, int(self.progress * 14), 20))
        elif self.intro_state == 'lava_transition':
            # Draw lava flow animation
            frame = self.images['lava_flow_frames'][self.lava_animation_frame]
            self.screen.blit(frame, (0, 0))
        elif self.intro_state == 'bedwards_presents':
            self.screen.fill((0, 0, 0))
            # Draw melting text effect
            self.draw_melting_effect()
        elif self.intro_state == 'matrix_code':
            self.draw_matrix_code()

    # Melting effect methods (same as before)

    def init_melting_effect(self):
        # Render the text onto a surface
        text_surface = self.font_title.render('Bedwards Productions Presents', True, (255, 69, 0))
        text_width, text_height = text_surface.get_size()
        # Position the text at the center
        self.text_x = (self.settings.screen_width - text_width) // 2
        self.text_y = (self.settings.screen_height - text_height) // 2

        # Pre-render the text surface to minimize per-frame rendering
        self.melting_surface = pygame.Surface((text_width, text_height), pygame.SRCALPHA)
        self.melting_surface.blit(text_surface, (0, 0))

        # Break the text surface into vertical slices
        slice_width = 4  # Wider slices for better performance
        for x in range(0, text_width, slice_width):
            rect = pygame.Rect(x, 0, slice_width, text_height)
            slice_image = self.melting_surface.subsurface(rect).copy()
            slice_dict = {
                'image': slice_image,
                'x': self.text_x + x,
                'y': self.text_y,
                'speed': random.uniform(0.3, 0.8),  # Slower initial speed
                'acceleration': random.uniform(0.02, 0.05),  # Less acceleration
                'drip_timer': random.uniform(0.5, 1.5),  # Time before a drip forms
                'finished': False,
            }
            self.text_slices.append(slice_dict)

    def update_melting_effect(self):
        # Update each text slice
        for slice_dict in self.text_slices:
            if not slice_dict['finished']:
                # Update position
                slice_dict['y'] += slice_dict['speed']
                # Increase speed (simulate acceleration)
                slice_dict['speed'] += slice_dict['acceleration']
                # Randomly decide to create a drip
                slice_dict['drip_timer'] -= self.clock.get_time() / 1000
                if slice_dict['drip_timer'] <= 0:
                    self.create_drip(slice_dict)
                    slice_dict['drip_timer'] = random.uniform(0.5, 1.5)
                # Check if the slice has moved off-screen
                if slice_dict['y'] > self.settings.screen_height:
                    slice_dict['finished'] = True
        # Remove finished slices
        self.text_slices = [s for s in self.text_slices if not s['finished']]

        # Update drips
        for drip in self.drips:
            drip['y'] += drip['speed']
            drip['speed'] += drip['acceleration']
            # Optionally fade out the drips
            drip['alpha'] -= 5
            if drip['alpha'] <= 0 or drip['y'] > self.settings.screen_height:
                drip['finished'] = True
            else:
                drip['image'].set_alpha(drip['alpha'])
        # Remove finished drips
        self.drips = [d for d in self.drips if not d['finished']]

    def draw_melting_effect(self):
        # Draw each text slice
        for slice_dict in self.text_slices:
            self.screen.blit(slice_dict['image'], (slice_dict['x'], slice_dict['y']))
        # Draw drips
        for drip in self.drips:
            self.screen.blit(drip['image'], (drip['x'], drip['y']))

    def create_drip(self, slice_dict):
        # Create a small drip that detaches from the slice
        drip_width = slice_dict['image'].get_width()
        drip_height = random.randint(5, 10)
        drip_image = pygame.Surface((drip_width, drip_height), pygame.SRCALPHA)
        color = (255, random.randint(0, 69), 0)  # Darker for better performance
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
        self.drips.append(drip_dict)

    # Matrix code methods (same as before)

    def init_matrix_code(self):
        # Initialize matrix code effect
        self.matrix_columns = []
        font_width, font_height = self.font_matrix.size('A')
        columns = self.settings.screen_width // font_width
        for i in range(columns):
            x = i * font_width
            y = random.randint(-self.settings.screen_height, 0)
            speed = random.randint(4, 7)  # Faster speed for better performance
            self.matrix_columns.append({'x': x, 'y': y, 'speed': speed})
        self.intro_timer = 0  # Reset intro timer

    def update_matrix_code(self):
        for column in self.matrix_columns:
            column['y'] += column['speed']
            if column['y'] > self.settings.screen_height:
                column['y'] = random.randint(-self.settings.screen_height, 0)
                column['speed'] = random.randint(4, 7)

    def draw_matrix_code(self):
        self.screen.fill((0, 0, 0))
        for column in self.matrix_columns:
            char = random.choice(self.matrix_chars)
            color = (255, random.randint(0, 140), 0)  # Lava colors
            text = self.font_matrix.render(char, True, color)
            self.screen.blit(text, (column['x'], column['y']))
