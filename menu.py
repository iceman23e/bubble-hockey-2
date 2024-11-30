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
        # Initialize click handlers
        self.register_touch_zones()

    def register_touch_zones(self):
        """Register touch zones for both screens."""
        for screen in ['red', 'blue']:
            # Main menu buttons
            self.screen_manager.register_touch_zone(screen, 'classic', self.classic_button_rect, self.handle_button_click)
            self.screen_manager.register_touch_zone(screen, 'evolved', self.evolved_button_rect, self.handle_button_click)
            self.screen_manager.register_touch_zone(screen, 'crazy_play', self.crazy_play_button_rect, self.handle_button_click)
            self.screen_manager.register_touch_zone(screen, 'analytics_config', self.analytics_config_button_rect, self.handle_button_click)
            self.screen_manager.register_touch_zone(screen, 'analytics_viewer', self.analytics_viewer_button_rect, self.handle_button_click)
            self.screen_manager.register_touch_zone(screen, 'check_updates', self.check_updates_button_rect, self.handle_button_click)
            self.screen_manager.register_touch_zone(screen, 'exit', self.exit_button_rect, self.handle_button_click)
            # Back button
            self.screen_manager.register_touch_zone(screen, 'back', self.back_button_rect, self.handle_button_click)

    def handle_button_click(self, screen, pos):
        """Handle button clicks from either screen."""
        if self.state == 'select_mode':
            self.handle_mode_selection(screen, pos)
        elif self.state == 'select_theme':
            self.handle_theme_selection(screen, pos)
        elif self.state in ['analytics_config', 'analytics_viewer']:
            self.handle_analytics_selection(screen, pos)

    def handle_mode_selection(self, screen, pos):
        if self.classic_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.selected_mode = 'classic'
            if self.settings.classic_mode_theme_selection:
                self.state = 'select_theme'
                self.init_theme_buttons()
            else:
                self.start_game = True
        elif self.evolved_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.selected_mode = 'evolved'
            self.state = 'select_theme'
            self.init_theme_buttons()
        elif self.crazy_play_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.selected_mode = 'crazy_play'
            self.state = 'select_theme'
            self.init_theme_buttons()
        elif self.analytics_config_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.state = 'analytics_config'
        elif self.analytics_viewer_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.state = 'analytics_viewer'
        elif self.check_updates_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.initiate_update()
        elif self.exit_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            pygame.quit()
            sys.exit()

    def handle_theme_selection(self, screen, pos):
        if self.back_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.state = 'select_mode'
            self.selected_mode = None
        else:
            for idx, rect in enumerate(self.theme_button_rects):
                if rect.collidepoint(pos):
                    self.sounds['button_click'].play()
                    self.selected_theme = self.available_themes[idx]
                    self.start_game = True
                    break

    def handle_analytics_selection(self, screen, pos):
        if self.back_button_rect.collidepoint(pos):
            self.sounds['button_click'].play()
            self.state = 'select_mode'

    def load_assets(self):
        """Load all necessary assets."""
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

    def init_menu(self):
        """Initialize menu elements."""
        # Same initialization as before, but store render results
        self._init_button_text()
        self._init_button_rects()

    def _init_button_text(self):
        """Initialize all button text renders."""
        # Create menu buttons
        self.classic_button_text = self.font_title.render('1. CLASSIC', True, (255, 140, 0))
        self.evolved_button_text = self.font_title.render('2. EVOLVED', True, (255, 140, 0))
        self.crazy_play_button_text = self.font_title.render('3. CRAZY PLAY', True, (255, 140, 0))
        self.analytics_config_button_text = self.font_title.render('Analytics Config', True, (255, 140, 0))
        self.analytics_viewer_button_text = self.font_title.render('Analytics Viewer', True, (255, 140, 0))
        self.check_updates_button_text = self.font_title.render('Check for Updates', True, (255, 140, 0))
        self.exit_button_text = self.font_title.render('Exit', True, (255, 140, 0))
        self.back_button_text = self.font_title.render('Back', True, (255, 140, 0))

    def _init_button_rects(self):
        """Initialize button rectangles for all screens."""
        # Calculate vertical spacing
        start_y = 120
        spacing = 60

        # Button rectangles for detecting clicks
        self.classic_button_rect = self.classic_button_text.get_rect(
            center=(self.settings.screen_width // 2, start_y)
        )
        self.evolved_button_rect = self.evolved_button_text.get_rect(
            center=(self.settings.screen_width // 2, start_y + spacing)
        )
        self.crazy_play_button_rect = self.crazy_play_button_text.get_rect(
            center=(self.settings.screen_width // 2, start_y + spacing * 2)
        )
        self.analytics_config_button_rect = self.analytics_config_button_text.get_rect(
            center=(self.settings.screen_width // 2, start_y + spacing * 3)
        )
        self.analytics_viewer_button_rect = self.analytics_viewer_button_text.get_rect(
            center=(self.settings.screen_width // 2, start_y + spacing * 4)
        )
        self.check_updates_button_rect = self.check_updates_button_text.get_rect(
            center=(self.settings.screen_width // 2, start_y + spacing * 5)
        )
        self.exit_button_rect = self.exit_button_text.get_rect(
            center=(self.settings.screen_width // 2, start_y + spacing * 6)
        )
        self.back_button_rect = self.back_button_text.get_rect(
            center=(self.settings.screen_width // 2, self.settings.screen_height - 50)
        )

        # Theme selection buttons will be initialized when needed
        self.theme_buttons = []
        self.theme_button_rects = []

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
            # Clear screen
            self.screen_manager.clear_screen(screen)
            current_screen = self.screen_manager.get_screen(screen)

            # Draw volcano animation
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
                current_screen.blit(self.back_button_text, self.back_button_rect)

            # Update the display
            self.screen_manager.update_display(screen)

    def _draw_mode_selection(self, screen):
        """Draw mode selection menu on specified screen."""
        # Draw menu buttons
        screen.blit(self.classic_button_text, self.classic_button_rect)
        screen.blit(self.evolved_button_text, self.evolved_button_rect)
        screen.blit(self.crazy_play_button_text, self.crazy_play_button_rect)
        screen.blit(self.analytics_config_button_text, self.analytics_config_button_rect)
        screen.blit(self.analytics_viewer_button_text, self.analytics_viewer_button_rect)
        screen.blit(self.check_updates_button_text, self.check_updates_button_rect)
        screen.blit(self.exit_button_text, self.exit_button_rect)

        # Display update notification if available
        if self.update_available:
            update_text = "Update Available!"
            update_surface = self.font_small.render(update_text, True, (255, 0, 0))
            update_rect = update_surface.get_rect(center=(self.settings.screen_width // 2, 120))
            screen.blit(update_surface, update_rect)

    # ... [Rest of the Menu class methods remain the same, just update screen references] ...
    
    def handle_event(self, event):
        """Legacy event handler for compatibility."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and self.state != 'select_mode':
                self.state = 'select_mode'
                self.selected_mode = None
                self.sounds['button_click'].play()

    def _draw_analytics_config(self, screen):
        """Draw the analytics configuration screen on specified screen."""
        # Draw section title
        title_text = self.font_title.render('ANALYTICS CONFIGURATION', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 80))
        screen.blit(title_text, title_rect)

        # Draw main settings
        y_pos = 150
        settings_to_display = [
            ('Show Analytics Overlay', self.settings.show_analytics_overlay),
            ('Overlay Position', self.settings.analytics_config['overlay_position']),
            ('Min Games (Basic)', self.settings.analytics_config['min_games_basic']),
            ('Min Games (Advanced)', self.settings.analytics_config['min_games_advanced']),
            ('Momentum Window', f"{self.settings.analytics_config['momentum_window']}s"),
            ('Critical Moment Threshold', f"{self.settings.analytics_config['critical_moment_threshold']}s")
        ]

        for setting, value in settings_to_display:
            text = self.font_small.render(f"{setting}: {value}", True, (255, 255, 255))
            rect = text.get_rect(midleft=(self.settings.screen_width // 4, y_pos))
            screen.blit(text, rect)
            y_pos += 40

        # Note: Actual configuration is handled through the web interface
        web_note = self.font_small.render(
            "For detailed configuration, use the web interface", 
            True, 
            (255, 140, 0)
        )
        web_note_rect = web_note.get_rect(center=(self.settings.screen_width // 2, y_pos + 40))
        screen.blit(web_note, web_note_rect)

    def _draw_analytics_viewer(self, screen):
        """Draw the analytics viewer screen on specified screen."""
        # Draw section title
        title_text = self.font_title.render('ANALYTICS VIEWER', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 80))
        screen.blit(title_text, title_rect)

        # Draw overview section
        y_pos = 150
        if hasattr(self, 'game') and hasattr(self.game, 'db'):
            stats = self.game.db.get_game_stats()
            total_games = len(stats) if stats else 0
            
            overview_data = [
                ('Total Games Played', total_games),
                ('Recent Games', len([s for s in stats if s['date_time'] >= '2024-01-01']) if stats else 0)
            ]

            for label, value in overview_data:
                text = self.font_small.render(f"{label}: {value}", True, (255, 255, 255))
                rect = text.get_rect(midleft=(self.settings.screen_width // 4, y_pos))
                screen.blit(text, rect)
                y_pos += 40

            # Draw web interface note
            web_note = self.font_small.render(
                "For detailed analytics, use the web interface", 
                True, 
                (255, 140, 0)
            )
            web_note_rect = web_note.get_rect(center=(self.settings.screen_width // 2, y_pos + 40))
            screen.blit(web_note, web_note_rect)
        else:
            no_data_text = self.font_small.render(
                "No analytics data available", 
                True, 
                (255, 255, 255)
            )
            no_data_rect = no_data_text.get_rect(center=(self.settings.screen_width // 2, 200))
            screen.blit(no_data_text, no_data_rect)

    def _draw_theme_selection(self, screen):
        """Draw the theme selection screen on specified screen."""
        # Clear the screen
        screen.fill((0, 0, 0))
        
        # Draw title
        title_text = self.font_title.render('SELECT THEME', True, (255, 140, 0))
        title_rect = title_text.get_rect(center=(self.settings.screen_width // 2, 80))
        screen.blit(title_text, title_rect)
        
        # Draw theme buttons
        for theme_text, theme_rect in zip(self.theme_buttons, self.theme_button_rects):
            screen.blit(theme_text, theme_rect)

    def init_theme_buttons(self):
        """Initialize theme selection buttons."""
        self.theme_buttons = []
        self.theme_button_rects = []
        y_start = 150
        y_offset = 70
        
        for idx, theme in enumerate(self.available_themes):
            theme_text = self.font_title.render(f"{idx + 1}. {theme.upper()}", True, (255, 140, 0))
            theme_rect = theme_text.get_rect(center=(self.settings.screen_width // 2, y_start + idx * y_offset))
            self.theme_buttons.append(theme_text)
            self.theme_button_rects.append(theme_rect)
            
            # Register touch zones for theme buttons
            for screen in ['red', 'blue']:
                self.screen_manager.register_touch_zone(
                    screen,
                    f'theme_{idx}',
                    theme_rect,
                    self.handle_button_click,
                    active=(self.state == 'select_theme')
                )

    def load_available_themes(self):
        """Load available themes from themes directory."""
        themes_dir = 'assets/themes/'
        themes = [d for d in os.listdir(themes_dir) if os.path.isdir(os.path.join(themes_dir, d))]
        return themes

    def check_for_updates(self):
        """Check if an update is available by looking for the flag file."""
        if os.path.exists('update_available.flag'):
            self.update_available = True
            logging.info('Update available.')
        else:
            self.update_available = False

    def initiate_update(self):
        """Initiate the update process."""
        logging.info('User initiated update from menu.')
        
        # Display updating message on both screens
        updating_text = "Updating... Please wait."
        text_surface = self.font_title.render(updating_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2))
        
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
            error_rect = error_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height // 2 + 50))
            
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

    def reset(self):
        """Reset menu state."""
        self.start_game = False
        self.selected_mode = None
        self.selected_theme = None
        self.state = 'select_mode'
        # Re-register touch zones
        self.register_touch_zones()
        # Check for updates
        self.check_for_updates()
