# screen_manager.py

import pygame
import os
import logging
from typing import Dict, Tuple, Optional, Literal

class ScreenManager:
    """Manages dual screen setup for bubble hockey game."""
    
    def __init__(self, settings):
        """Initialize dual screen management."""
        self.settings = settings
        self.screens: Dict[str, pygame.Surface] = {}
        self.displays: Dict[str, int] = {}
        self.active_touch_zones: Dict[str, Dict] = {'red': {}, 'blue': {}}
        
        # Initialize screens
        self._initialize_displays()
        
    def _initialize_displays(self) -> None:
        """Initialize both displays with proper configuration."""
        try:
            # Set up environment for touchscreens
            os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
            os.environ['SDL_MOUSEDRV'] = 'TSLIB'
            
            # Initialize pygame if not already done
            if not pygame.get_init():
                pygame.init()
            
            # Get available displays
            num_displays = pygame.display.get_num_displays()
            if num_displays < 2:
                raise RuntimeError(f"Found only {num_displays} display(s). Two displays required.")
            
            # Initialize both screens
            for i, side in enumerate(['red', 'blue']):
                try:
                    # Create display surface for each screen
                    display_surface = pygame.display.set_mode(
                        (self.settings.screen_width, self.settings.screen_height),
                        pygame.RESIZABLE | pygame.SHOWN,
                        display=i
                    )
                    self.screens[side] = display_surface
                    self.displays[side] = i
                    logging.info(f"Initialized {side} display on screen {i}")
                except pygame.error as e:
                    logging.error(f"Failed to initialize {side} display: {e}")
                    raise
                    
            # Set caption for both displays
            pygame.display.set_caption("Boiling Point Bubble Hockey - Red Team", display=self.displays['red'])
            pygame.display.set_caption("Boiling Point Bubble Hockey - Blue Team", display=self.displays['blue'])
            
        except Exception as e:
            logging.error(f"Display initialization failed: {e}")
            raise
            
    def register_touch_zone(self, screen: str, zone_id: str, rect: pygame.Rect, 
                           callback, active: bool = True) -> None:
        """Register a touch-interactive zone on a specific screen."""
        if screen not in self.active_touch_zones:
            raise ValueError(f"Invalid screen identifier: {screen}")
            
        self.active_touch_zones[screen][zone_id] = {
            'rect': rect,
            'callback': callback,
            'active': active
        }
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle input events for both screens.
        Returns True if event was handled.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            display_index = pygame.display.get_window_from_id(event.windowID)
            
            # Determine which screen was touched
            screen = next(
                (side for side, idx in self.displays.items() if idx == display_index),
                None
            )
            
            if screen and screen in self.active_touch_zones:
                return self._handle_touch(screen, pos)
                
        return False
        
    def _handle_touch(self, screen: str, pos: Tuple[int, int]) -> bool:
        """Handle touch event on a specific screen."""
        for zone_info in self.active_touch_zones[screen].values():
            if zone_info['active'] and zone_info['rect'].collidepoint(pos):
                zone_info['callback'](screen, pos)
                return True
        return False
        
    def clear_screen(self, screen: str, color: Optional[Tuple[int, int, int]] = None) -> None:
        """Clear a specific screen with optional background color."""
        if screen not in self.screens:
            raise ValueError(f"Invalid screen identifier: {screen}")
            
        color = color or self.settings.bg_color
        self.screens[screen].fill(color)
        
    def clear_all_screens(self, color: Optional[Tuple[int, int, int]] = None) -> None:
        """Clear all screens with optional background color."""
        for screen in self.screens:
            self.clear_screen(screen, color)
            
    def blit_to_screen(self, screen: str, surface: pygame.Surface, position: Tuple[int, int]) -> None:
        """Blit a surface to a specific screen."""
        if screen not in self.screens:
            raise ValueError(f"Invalid screen identifier: {screen}")
            
        self.screens[screen].blit(surface, position)
        
    def update_display(self, screen: Optional[str] = None) -> None:
        """Update specific screen or all screens if none specified."""
        if screen:
            if screen not in self.screens:
                raise ValueError(f"Invalid screen identifier: {screen}")
            pygame.display.update(display=self.displays[screen])
        else:
            pygame.display.flip()
            
    def get_screen(self, screen: str) -> pygame.Surface:
        """Get the surface for a specific screen."""
        if screen not in self.screens:
            raise ValueError(f"Invalid screen identifier: {screen}")
        return self.screens[screen]
        
    def cleanup(self) -> None:
        """Clean up screen manager resources."""
        self.active_touch_zones = {'red': {}, 'blue': {}}
        # Additional cleanup if needed
