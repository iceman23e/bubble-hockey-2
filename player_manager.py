# player_manager.py

from typing import Optional, List, Tuple, Dict
import pygame
import logging
import json
import os
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Tuple
from player import Player

class PlayerManagerState(Enum):
    PLAYER_SELECT = "select"  # Only state we need for now - player selection

class PlayerManager:
    def __init__(self, screen_manager, settings, player_db, game):
        self.screen_manager = screen_manager
        self.settings = settings
        self.player_db = player_db
        self.game = game

        # Load last match data if available
        try:
            if os.path.exists('last_match.json'):
                with open('last_match.json', 'r') as f:
                    data = json.load(f)
                    self.last_match_players = (data.get('red_id'), data.get('blue_id'))
            else:
                self.last_match_players = (None, None)
        except Exception as e:
            logging.error(f"Error loading last match data: {e}")
            self.last_match_players = (None, None)

        self.state = PlayerManagerState.PLAYER_SELECT
        self.red_player: Optional[Player] = None
        self.blue_player: Optional[Player] = None
        
        # Screen-specific UI state
        self.search_text = {"red": "", "blue": ""}
        self.list_offset = {"red": 0, "blue": 0}
        self.error_messages = {"red": None, "blue": None}
        self.error_times = {"red": 0, "blue": 0}
        
        # Load fonts
        try:
            self.font_title = pygame.font.Font('assets/fonts/PressStart2P-Regular.ttf', 24)
            self.font_small = pygame.font.Font('assets/fonts/Perfect DOS VGA 437.ttf', 18)
        except Exception as e:
            logging.error(f"Error loading fonts: {e}")
            raise

        # Register touch zones
        self.register_touch_zones()

    def register_touch_zones(self):
        """Register touch zones for both screens."""
        for screen in ['red', 'blue']:
            # Register the list area for selection
            self.screen_manager.register_touch_zone(
                screen,
                'player_list',
                pygame.Rect(20, 200, self.settings.screen_width - 40, self.settings.screen_height - 240),
                self.handle_list_touch
            )
            
            # Register the "Last Match" button if available
            if all(self.last_match_players):
                self.screen_manager.register_touch_zone(
                    screen,
                    'last_match',
                    pygame.Rect((self.settings.screen_width - 200) // 2,
                              self.settings.screen_height - 50,
                              200, 40),
                    self.handle_last_match_touch
                )

    def handle_list_touch(self, screen, pos):
        """Handle touch events in the player list."""
        list_rect = pygame.Rect(20, 200, self.settings.screen_width - 40, self.settings.screen_height - 240)
        
        if list_rect.collidepoint(pos):
            # Calculate which player was clicked
            y_offset = pos[1] - list_rect.y
            clicked_index = self.list_offset[screen] + (y_offset // 50)
            
            # Get filtered player list
            filtered_players = self._get_filtered_players(self.search_text[screen])
            
            # Select player if valid index
            if 0 <= clicked_index < len(filtered_players):
                self.select_player(filtered_players[clicked_index], screen)

    def handle_last_match_touch(self, screen, pos):
        """Handle touch events on the last match button."""
        if all(self.last_match_players):
            self.load_last_match_players()

    def select_player(self, player: Player, team: str) -> bool:
        """Select a player for a specific team."""
        try:
            if team not in ['red', 'blue']:
                raise ValueError(f"Invalid team: {team}")
                
            # Check if player is already selected by other team
            if ((team == 'red' and self.blue_player and self.blue_player.id == player.id) or
                (team == 'blue' and self.red_player and self.red_player.id == player.id)):
                self._set_error(team, "Player already selected")
                return False
                
            # Assign player
            if team == 'red':
                self.red_player = player
            else:
                self.blue_player = player
                
            logging.info(f"Player {player.name} selected for {team} team")
            return True
            
        except Exception as e:
            logging.error(f"Error in player selection: {e}")
            self._set_error(team, "Error selecting player")
            return False

    def _set_error(self, team: str, message: str) -> None:
        """Set error message for a team."""
        self.error_messages[team] = message
        self.error_times[team] = pygame.time.get_ticks()

    def draw(self) -> None:
        """Draw the player management interface on both screens."""
        if self.state == PlayerManagerState.PLAYER_SELECT:
            for screen in ['red', 'blue']:
                # Get the screen surface
                current_screen = self.screen_manager.get_screen(screen)
                
                # Clear screen with team color
                bg_color = (64, 0, 0) if screen == 'red' else (0, 0, 64)
                current_screen.fill(bg_color)
                
                # Draw the selection interface
                self._draw_selection_interface(current_screen, screen)
                
                # Update the display
                self.screen_manager.update_display(screen)

    def _draw_selection_interface(self, screen, team: str) -> None:
        """Draw the player selection interface for a specific screen."""
        # Draw header
        header_text = f"Select {team.upper()} Player"
        header_color = (255, 0, 0) if team == "red" else (0, 0, 255)
        text_surface = self.font_title.render(header_text, True, header_color)
        text_rect = text_surface.get_rect(centerx=self.settings.screen_width // 2, top=20)
        screen.blit(text_surface, text_rect)
        
        # Draw selected player if any
        player = self.red_player if team == "red" else self.blue_player
        if player:
            self._draw_selected_player(screen, player, team)
        
        # Draw player list
        self._draw_player_list(screen, team)
        
        # Draw error message if exists
        self._draw_error_message(screen, team)
        
        # Draw "Last Match" button if available
        if all(self.last_match_players):
            self._draw_last_match_button(screen)

    def _draw_selected_player(self, screen, player: Player, team: str) -> None:
        """Draw the currently selected player's info."""
        # Background box
        box_rect = pygame.Rect(20, 60, self.settings.screen_width - 40, 80)
        color = (128, 0, 0) if team == "red" else (0, 0, 128)
        pygame.draw.rect(screen, color, box_rect, border_radius=10)
        
        # Player info
        rank_number, rank = self.game.ranking_system.elo_to_visible_rank(
            player.elo,
            player.stats.total_matches
        )
        
        name_text = self.font_small.render(player.name, True, (255, 255, 255))
        rank_text = self.font_small.render(f"Rank {rank_number}", True, (255, 255, 255))
        stats_text = self.font_small.render(
            f"W/L: {player.stats.wins}/{player.stats.losses}",
            True, (255, 255, 255)
        )
        
        screen.blit(name_text, (box_rect.x + 10, box_rect.y + 10))
        screen.blit(rank_text, (box_rect.x + 10, box_rect.y + 35))
        screen.blit(stats_text, (box_rect.x + 10, box_rect.y + 55))

    def _draw_player_list(self, screen, team: str) -> None:
        """Draw the scrollable player list."""
        list_rect = pygame.Rect(
            20, 200,
            self.settings.screen_width - 40,
            self.settings.screen_height - 240
        )
        pygame.draw.rect(screen, (0, 0, 0), list_rect)
        
        # Get filtered player list
        search = self.search_text[team]
        players = self._get_filtered_players(search)
        
        if not players:
            # Show "No players found" message
            no_results_text = self.font_small.render(
                "No players found", True, (128, 128, 128)
            )
            text_rect = no_results_text.get_rect(center=list_rect.center)
            screen.blit(no_results_text, text_rect)
            return
        
        # Draw visible players
        y_pos = list_rect.y + 5
        offset = self.list_offset[team]
        for player in players[offset:offset + 6]:
            if y_pos + 45 > list_rect.bottom:
                break
                
            self._draw_player_item(screen, player, team, y_pos)
            y_pos += 50

    def _draw_player_item(self, screen, player: Player, team: str, y_pos: int) -> None:
        """Draw a single player item in the list."""
        item_rect = pygame.Rect(25, y_pos, self.settings.screen_width - 50, 45)
        
        # Draw player info
        name_text = self.font_small.render(player.name, True, (255, 255, 255))
        rank_number, _ = self.game.ranking_system.elo_to_visible_rank(
            player.elo,
            player.stats.total_matches
        )
        rank_text = self.font_small.render(f"Rank {rank_number}", True, (200, 200, 200))
        
        screen.blit(name_text, (item_rect.x + 5, item_rect.y + 5))
        screen.blit(rank_text, (item_rect.x + 5, item_rect.y + 25))

    def _draw_error_message(self, screen, team: str) -> None:
        """Draw error message if exists and not expired."""
        error = self.error_messages[team]
        if not error:
            return
            
        # Check if error message has expired (3 second display)
        if pygame.time.get_ticks() - self.error_times[team] > 3000:
            self.error_messages[team] = None
            return
            
        error_surface = self.font_small.render(error, True, (255, 0, 0))
        error_rect = error_surface.get_rect(
            centerx=self.settings.screen_width // 2,
            bottom=self.settings.screen_height - 10
        )
        screen.blit(error_surface, error_rect)

    def _draw_last_match_button(self, screen) -> None:
        """Draw the "Last Match Players" quick select button."""
        button_rect = pygame.Rect(
            (self.settings.screen_width - 200) // 2,
            self.settings.screen_height - 50,
            200, 40
        )
        
        # Draw button background
        pygame.draw.rect(screen, (0, 128, 0), button_rect, border_radius=5)
        
        # Draw button text
        text = self.font_small.render("Last Match Players", True, (255, 255, 255))
        text_rect = text.get_rect(center=button_rect.center)
        screen.blit(text, text_rect)

    def handle_keyboard(self, event: pygame.event.Event) -> None:
        """Handle keyboard events for search."""
        # Get the team based on which screen is being interacted with
        team = None
        if hasattr(event, 'window'):
            window_id = event.window
            for screen_id, display_id in self.screen_manager.displays.items():
                if display_id == window_id:
                    team = screen_id
                    break
        
        if not team:
            return
            
        if event.type == pygame.KEYDOWN:
            # Handle backspace
            if event.key == pygame.K_BACKSPACE:
                self.search_text[team] = self.search_text[team][:-1]
                self.list_offset[team] = 0
            # Handle escape to clear search
            elif event.key == pygame.K_ESCAPE:
                self.search_text[team] = ""
                self.list_offset[team] = 0
        
        # Handle regular text input
        elif event.type == pygame.TEXTINPUT:
            if len(self.search_text[team]) < 20:
                self.search_text[team] += event.text
                self.list_offset[team] = 0

    def _get_filtered_players(self, search: str) -> List[Player]:
        """Get list of players filtered by search text."""
        players = self.player_db.get_players()
        if not search:
            return players
            
        search = search.lower()
        return [p for p in players if search in p.name.lower()]

    def get_selected_players(self) -> Tuple[Optional[Player], Optional[Player]]:
        """Get currently selected players."""
        return self.red_player, self.blue_player

    def are_players_selected(self) -> bool:
        """Check if both players are selected."""
        return bool(self.red_player and self.blue_player)

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.red_player and self.blue_player:
            self.store_last_match()
            
        self.error_messages = {"red": None, "blue": None}
        self.red_player = None
        self.blue_player = None
        
        # Clear touch zones
        for screen in ['red', 'blue']:
            self.screen_manager.active_touch_zones[screen].clear()
        
        logging.info("PlayerManager cleanup complete")
