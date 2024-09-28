# utils.py

import pygame
import logging

def load_image(path):
    try:
        image = pygame.image.load(path).convert_alpha()
        return image
    except Exception as e:
        logging.error(f'Failed to load image {path}: {e}')
        return None

def load_sound(path):
    try:
        sound = pygame.mixer.Sound(path)
        return sound
    except Exception as e:
        logging.error(f'Failed to load sound {path}: {e}')
        return None
