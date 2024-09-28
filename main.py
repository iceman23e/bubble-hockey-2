# main.py

import pygame
import sys
from settings import Settings
from web_server import run_web_server
import threading
from intro import Intro
from menu import Menu
from game import Game

def main():
    pygame.init()
    # Load settings
    settings = Settings()

    # Set up the display
    screen = pygame.display.set_mode((settings.screen_width, settings.screen_height))
    pygame.display.set_caption('Boiling Point Bubble Hockey')

    # Initialize modules
    intro = Intro(screen, settings)
    menu = Menu(screen, settings)
    game = Game(screen, settings)

    # Start the web server in a separate thread
    web_thread = threading.Thread(target=run_web_server, args=(settings, game))
    web_thread.daemon = True
    web_thread.start()

    # Main loop
    clock = pygame.time.Clock()
    state = 'intro'

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.cleanup()
                pygame.quit()
                sys.exit()
            else:
                if state == 'intro':
                    intro.handle_event(event)
                elif state == 'menu':
                    menu.handle_event(event)
                elif state == 'game':
                    game.handle_event(event)

        if state == 'intro':
            intro.update()
            intro.draw()
            if intro.is_finished:
                state = 'menu'
        elif state == 'menu':
            menu.update()
            menu.draw()
            if menu.start_game:
                # Set game mode based on menu selection
                game.set_mode(menu.selected_mode)
                state = 'game'
        elif state == 'game':
            game.update()
            game.draw()
            if game.is_over:
                state = 'menu'
                menu.reset()

        pygame.display.flip()
        clock.tick(60)  # Limit to 60 FPS

if __name__ == '__main__':
    main()
