# menu.py

import pygame
import sys
import os
import subprocess
import logging
from utils import load_image, load_sound

class Menu:
    def __init__(self, screen_manager, settings):
        self.screen_manager = screen_manager
        self.settings = settings
        self.load_assets()
        self.init_menu()
        self.start_game = False
        self.selected_mode = None
        self.selected_theme = None
        self.state = 'select_mode'  # 'select_mode', 'select_theme', 'analytics_config', or 'analytics_viewer'
        
        # Update notification flag
        self.update_available = False
        self.check_for_updates()
        
        # Timer for volcano animation
        self.volcano_animation_timer = 0
        self.volcano_frame = 0
        self.animation_interval = 100  # Milliseconds between frames
        
        # Register touch zones
        self.register_touch_zones()

    def load_assets(self):
        """Load all assets needed for the menu."""
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

        # Load available themes
        self.available_themes = self.load_available_themes()

    def register_touch_zones(self):
        """Register touch zones for both screens."""
        for screen in ['red', 'blue']:
            start_y = 120
            spacing = 60
            
            # Main menu buttons
            if self.state == 'select_mode':
                self.screen_manager.register_touch_zone(
                    screen, 'classic',
                    pygame.Rect(0, start_y - 20, self.settings.screen_width, 40),
                    self.handle_button_click
                )
                self.screen_manager.register_touch_zone(
                    screen, 'evolved',
                    pygame.Rect(0, start_y + spacing - 20, self.settings.screen_width, 40),
                    self.handle_button_click
                )
                self.screen_manager.register_touch_zone(
                    screen, 'crazy_play',
                    pygame.Rect(0, start_y + spacing * 2 - 20, self.settings.screen_width, 40),
                    self.handle_button_click
                )
                self.screen_manager.register_touch_zone(
                    screen, 'analytics_config',
                    pygame.Rect(0, start_y + spacing * 3 - 20, self.settings.screen_width, 40),
                    self.handle_button_click
                )
                self.screen_manager.register_touch_zone(
                    screen, 'analytics_viewer',
                    pygame.Rect(0, start_y + spacing * 4 - 20, self.settings.screen_width, 40),
                    self.handle_button_click
                )
                self.screen_manager.register_touch_zone(
                    screen, 'check_updates',
                    pygame.Rect(0, start_y + spacing * 5 - 20, self.settings.screen_width, 40),
                    self.handle_button_click
                )
                self.screen_manager.register_touch_zone(
                    screen, 'exit',
                    pygame.Rect(0, start_y + spacing * 6 - 20, self.settings.screen_width, 40),
                    self.handle_button_click
                )

            # Back button for non-main states
            if self.state != 'select_mode':
                self.screen_manager.register_touch_zone(
                    screen, 'back',
                    pygame.Rect(0, self.settings.screen_height - 70, self.settings.screen_width, 40),
                    self.handle_button_click
                )

    def handle_button_click(self, screen, pos):
        """Handle button click events."""
        # Play click sound
        if self.sounds['button_click']:
            self.sounds['button_click'].play()

        # Get the zone that was clicked from the event data
        zone_id = None
        for zone in self.screen_manager.active_touch_zones[screen].values():
            if zone['rect'].collidepoint(pos):
                zone_id = next(key for key, value in self.screen_manager.active_touch_zones[screen].items() 
                             if value == zone)
                break

        if not zone_id:
            return

        # Handle the click based on the zone
        if zone_id == 'classic':
            self.selected_mode = 'classic'
            if self.settings.classic_mode_theme_selection:
                self.state = 'select_theme'
                self.init_theme_buttons()
            else:
                self.start_game = True
        elif zone_id == 'evolved':
            self.selected_mode = 'evolved'
            self.state = 'select_theme'
            self.init_theme_buttons()
        elif zone_id == 'crazy_play':
            self.selected_mode = 'crazy_play'
            self.state = 'select_theme'
            self.init_theme_buttons()
        elif zone_id == 'analytics_config':
            self.state = 'analytics_config'
        elif zone_id == 'analytics_viewer':
            self.state = 'analytics_viewer'
        elif zone_id == 'check_updates':
            self.initiate_update()
        elif zone_id == 'exit':
            pygame.quit()
            sys.exit()
        elif zone_id == 'back':
            self.state = 'select_mode'
            self.selected_mode = None
        elif zone_id.startswith('theme_'):
            theme_idx = int(zone_id.split('_')[1])
            if 0 <= theme_idx < len(self.available_themes):
                self.selected_theme = self.available_themes[theme_idx]
                self.start_game = True

        # Re-register touch zones for new state
        self.register_touch_zones()

    def load_available_themes(self):
        """Load available themes from themes directory."""
        themes_dir = 'assets/themes/'
        themes = [d for d in os.listdir(themes_dir) if os.path.isdir(os.path.join(themes_dir, d))]
        return themes

    def init_theme_buttons(self):
        """Initialize theme selection buttons."""
        y_start = 150
        y_offset = 70
        
        # Register touch zones for theme buttons
        for idx, theme in enumerate(self.available_themes):
            for screen in ['red', 'blue']:
                self.screen_manager.register_touch_zone(
                    screen,
                    f'theme_{idx}',
                    pygame.Rect(0, y_start + idx * y_offset - 20, 
                              self.settings.screen_width, 40),
                    self.handle_button_click
                )

    def update(self):
        """Update menu state."""
        # Update volcano animation timer
        self.volcano_animation_timer += self.settings.clock_tick
        if self.volcano_animation_timer >= self.animation_interval:
            self.volcano_frame = (self.volcano_frame + 1) % len(self.images['volcano_eruption_frames'])
            self.volcano_animation_timer = 0

    def draw(self):
        """Draw menu on both screens."""
        for screen in ['red', 'blue']:
            current_screen = self.screen_manager.get_screen(screen)
            
            # Draw volcano animation background
            volcano_frame_image = self.images['volcano_eruption_frames'][self.volcano_frame]
            current_screen.blit(volcano_frame_image, (0, 0))

            # Draw title
            title_text = self.font_title.render('BOILING POINT BUBBLE HOCKEY', True, (255, 140, 0))
            title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 50))
            current_screen.blit(title_text, title_rect)

            if self.state == 'select_mode':
                self._draw_mode_selection(current_screen)
            elif self.state == 'select_theme':
                self._draw_theme_selection(current_screen)
            elif self.state == 'analytics_config':
                self._draw_analytics_config(current_screen)
            elif self.state == 'analytics_viewer':
                self._draw_analytics_viewer(current_screen)

            # Draw back button for non-main states
            if self.state != 'select_mode':
                self._draw_back_button(current_screen)

            # Update the display
            self.screen_manager.update_display(screen)

    def _draw_mode_selection(self, screen):
        """Draw mode selection menu."""
        start_y = 120
        spacing = 60

        # Draw menu buttons
        buttons = [
            ('1. CLASSIC', self.selected_mode == 'classic'),
            ('2. EVOLVED', self.selected_mode == 'evolved'),
            ('3. CRAZY PLAY', self.selected_mode == 'crazy_play'),
            ('Analytics Config', False),
            ('Analytics Viewer', False),
            ('Check for Updates', False),
            ('Exit', False)
        ]

        for i, (text, selected) in enumerate(buttons):
            color = (255, 255, 0) if selected else (255, 140, 0)
            text_surface = self.font_title.render(text, True, color)
            text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, start_y + spacing * i))
            screen.blit(text_surface, text_rect)

        # Display update notification if available
        if self.update_available:
            update_text = "Update Available!"
            update_surface = self.font_small.render(update_text, True, (255, 0, 0))
            update_rect = update_surface.get_rect(center=(self.settings.screen_width // 2, 90))
            screen.blit(update_surface, update_rect)

    def _draw_theme_selection(self, screen):
        """Draw theme selection screen."""
        # Draw section title
        title_text = self.font_title.render('SELECT THEME', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 80))
        screen.blit(title_text, title_rect)

        # Draw theme buttons
        y_start = 150
        y_offset = 70
        for idx, theme in enumerate(self.available_themes):
            color = (255, 255, 0) if self.selected_theme == theme else (255, 140, 0)
            theme_text = self.font_title.render(f"{idx + 1}. {theme.upper()}", True, color)
            theme_rect = theme_text.get_rect(center=(self.settings.screen_width // 2, y_start + idx * y_offset))
            screen.blit(theme_text, theme_rect)

    def _draw_back_button(self, screen):
        """Draw back button."""
        text = self.font_title.render('Back', True, (255, 140, 0))
        rect = text.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height - 50))
        screen.blit(text, rect)

    def _draw_analytics_config(self, screen):
        """Draw analytics configuration screen."""
        # Draw section title
        title_text = self.font_title.render('ANALYTICS CONFIGURATION', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 80))
        screen.blit(title_text, title_rect)

        # Draw settings
        y_pos = 150
        settings_to_display = [
            ('Show Analytics Overlay', self.settings.show_analytics_overlay),
            ('Overlay Position', self.settings.analytics_config['overlay_position']),
            ('Min Games (Basic)', self.settings.analytics_config['min_games_basic']),
            ('Min Games (Advanced)', self.settings.analytics_config['min_games_advanced']),
            ('Momentum Window', f"{self.settings.analytics_config['momentum_window']}s"),
            ('Critical Moment Threshold', 
             f"{self.settings.analytics_config['critical_moment_threshold']}s")
        ]

        for setting, value in settings_to_display:
            text = self.font_small.render(f"{setting}: {value}", True, (255, 255, 255))
            rect = text.get_rect(midleft=(self.settings.screen_width // 4, y_pos))
            screen.blit(text, rect)
            y_pos += 40

        # Draw web interface note
        web_note = self.font_small.render(
            "For detailed configuration, use the web interface", 
            True, 
            (255, 140, 0)
        )
        web_note_rect = web_note.get_rect(center=(self.settings.screen_width // 2, y_pos + 40))
        screen.blit(web_note, web_note_rect)

    def _draw_analytics_viewer(self, screen):
        """Draw analytics viewer screen."""
        # Draw section title
        title_text = self.font_title.render('ANALYTICS VIEWER', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 80))
        screen.blit(title_text, title_rect)

        # Draw web interface note
        web_note = self.font_small.render(
            "For detailed analytics, use the web interface", 
            True, 
            (255, 140, 0)
        )
        web_note_rect = web_note.get_rect(center=(self.settings.screen_width // 2, 150))
        screen.blit(web_note, web_note_rect)

    def check_for_updates(self):
        """Check if an update is available."""
        if os.path.exists('update_available.flag'):
            self.update_available = True
            logging.info('Update available.')
        else:
            self.update_available = False

    def initiate_update(self):
        """Start the update process."""
        logging.info('User initiated update from menu.')
        
        # Display updating message on both screens
        updating_text = "Updating... Please wait."
        text_surface = self.font_title.render(updating_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                self.settings.screen_height // 2))

    for screen in ['red', 'blue']:
            current_screen = self.screen_manager.get_screen(screen)
            current_screen.fill((0, 0, 0))
            current_screen.blit(text_surface, text_rect)
            self.screen_manager.update_display(screen)
        
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
            # Display error message on both screens
            error_text = "Update failed. Check logs."
            error_surface = self.font_small.render(error_text, True, (255, 0, 0))
            error_rect = error_surface.get_rect(center=(self.settings.screen_width // 2, 
                                                      self.settings.screen_height // 2 + 50))
            
            for screen in ['red', 'blue']:
                current_screen = self.screen_manager.get_screen(screen)
                current_screen.blit(error_surface, error_rect)
                self.screen_manager.update_display(screen)
            
            pygame.time.delay(3000)  # Pause for 3 seconds

    def restart_game(self):
        """Restart the game application."""
        logging.info('Restarting game...')
        pygame.quit()
        os.execv(sys.executable, ['python3'] + sys.argv)

    def handle_event(self, event):
        """Legacy event handler for compatibility with main game loop."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and self.state != 'select_mode':
                if self.sounds['button_click']:
                    self.sounds['button_click'].play()
                self.state = 'select_mode'
                self.selected_mode = None
                # Re-register touch zones for new state
                self.register_touch_zones()

    def reset(self):
        """Reset menu state."""
        self.start_game = False
        self.selected_mode = None
        self.selected_theme = None
        self.state = 'select_mode'
        # Re-register touch zones for main menu
        self.register_touch_zones()
        # Check for updates
        self.check_for_updates()
