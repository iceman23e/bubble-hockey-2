# main.py

import pygame
import sys
from settings import Settings
from intro import Intro
from menu import Menu
from game import Game

def main():
    # Initialize Pygame
    pygame.init()
    settings = Settings()
    # Set up the display with the configured screen width and height
    screen = pygame.display.set_mode((settings.screen_width, settings.screen_height))
    pygame.display.set_caption("Boiling Point Bubble Hockey")

    # Display the intro screen
    intro = Intro(screen, settings)
    intro.run()  # Run the intro sequence

    # Create instances of Menu and Game
    menu = Menu(screen, settings)
    game = None  # Will be initialized when starting the game

    # Main loop control variables
    running = True
    in_menu = True  # Indicates whether we are in the menu or the game

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False  # Exit the main loop

            if in_menu:
                # Pass events to the menu
                menu.handle_event(event)
                if menu.start_game:
                    # User selected to start the game
                    game = Game(screen, settings)
                    game.set_mode(menu.selected_mode)  # Set the game mode based on menu selection
                    in_menu = False  # Switch to game mode
                    menu.start_game = False  # Reset the flag
            else:
                # Pass events to the game
                game.handle_event(event)
                if game.is_over:
                    # Game is over, return to menu
                    in_menu = True  # Switch back to menu
                    menu.check_for_updates()  # Check for updates when returning to menu

        if in_menu:
            # Update and display the menu
            menu.update()  # Update any animations or timers in the menu
            menu.draw()    # Draw the menu elements on the screen
        else:
            # Update and draw the game
            game.update()  # Update the game state
            game.draw()    # Draw the game elements on the screen

        # Update the display
        pygame.display.flip()

    # Clean up and exit
    if game:
        game.cleanup()  # Perform any necessary cleanup
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
