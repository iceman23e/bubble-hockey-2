# main.py

import os
import pygame
import sys
import logging
from settings import Settings
from screen_manager import ScreenManager
from intro import Intro
from menu import Menu
from game import Game
from gpio import GPIOHandler

def main():
    """Main entry point for the Bubble Hockey game."""
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    
    try:
        # Initialize screen manager and GPIO handler
        screen_manager = ScreenManager(settings)
        gpio_handler = GPIOHandler(settings)
        
        # Initialize game components
        intro = Intro(screen_manager, settings)
        menu = Menu(screen_manager, settings)
        game = None
        
        # Run intro sequence
        intro.run()
        
        # Main loop setup
        running = True
        in_menu = True
        clock = pygame.time.Clock()
        
        # Main game loop
        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue
                
                # Let screen manager handle touch events first
                if screen_manager.handle_event(event):
                    continue
                
                # Handle menu/game events
                if in_menu:
                    menu.handle_event(event)
                    if menu.start_game:
                        # Update theme settings if needed
                        if menu.selected_theme:
                            settings.current_theme = menu.selected_theme
                            settings.save_settings()
                        else:
                            menu.selected_theme = settings.current_theme
                        
                        # Initialize and start game
                        game = Game(screen_manager, settings, gpio_handler)
                        game.set_mode(menu.selected_mode)
                        in_menu = False
                        menu.start_game = False
                else:
                    game.handle_event(event)
                    if game.is_over:
                        in_menu = True
                        menu.reset()
                        menu.check_for_updates()
            
            # Clear displays
            screen_manager.clear_all_screens()
            
            # Update and draw current state
            if in_menu:
                menu.update()
                menu.draw()
            else:
                game.update()
                game.draw()
            
            # Update displays
            screen_manager.update_display()
            
            # Maintain frame rate
            clock.tick(60)
            settings.clock_tick = clock.get_time()
        
        # Cleanup on normal exit
        if game:
            game.cleanup()
        gpio_handler.cleanup()
        screen_manager.cleanup()
        pygame.quit()
        sys.exit()
        
    except Exception as e:
        # Log error and exit gracefully
        logging.error(f"Fatal error: {e}")
        pygame.quit()
        sys.exit(1)

if __name__ == "__main__":
    main()
