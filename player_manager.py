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
    def __init__(self, screen, settings, player_db, game):
        self.screen = screen
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
            logging.error(f"Error loading last match data: {e    def cleanup(self) -> None:
        """Clean up resources before exiting."""
        # Store last match if we have selected players
        if self.red_player and self.blue_player:
            self.store_last_match()
            
        # Clear any error messages
        self.error_messages = {"red": None, "blue": None}
        
        # Clear references
        self.red_player = None
        self.blue_player = None
        self.screen = None  # Let pygame handle actual surface cleanup
        
        logging.info("PlayerManager cleanup complete")")
            self.last_match_players = (None, None)
        self.state = PlayerManagerState.PLAYER_SELECT
        self.red_player: Optional[Player] = None
        self.blue_player: Optional[Player] = None
        
        # Split screen management
        self.red_side = pygame.Rect(0, 0, settings.screen_width // 2, settings.screen_height)
        self.blue_side = pygame.Rect(settings.screen_width // 2, 0, 
                                   settings.screen_width // 2, settings.screen_height)
        
        # Last match tracking
        self.last_match_players: Tuple[Optional[str], Optional[str]] = (None, None)
        
        # UI state
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

    def select_player(self, player: Player, team: str) -> bool:
        """
        Select a player for a specific team.
        
        Args:
            player: Player to select
            team: Team ('red' or 'blue') to assign player to
            
        Returns:
            bool: True if selection was successful
        """
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

    def get_selected_players(self) -> Tuple[Optional[Player], Optional[Player]]:
        """Get currently selected players."""
        return self.red_player, self.blue_player

    def are_players_selected(self) -> bool:
        """Check if both players are selected."""
        return bool(self.red_player and self.blue_player)

    def store_last_match(self) -> None:
        """Store the current players as last match players and save to file."""
        if self.red_player and self.blue_player:
            self.last_match_players = (self.red_player.id, self.blue_player.id)
            try:
                with open('last_match.json', 'w') as f:
                    json.dump({
                        'red_id': self.red_player.id,
                        'blue_id': self.blue_player.id,
                        'timestamp': datetime.now().isoformat()
                    }, f)
                logging.info("Last match data saved successfully")
            except Exception as e:
                logging.error(f"Error saving last match data: {e}")

    def load_last_match_players(self) -> bool:
        """Load the players from the last match."""
        if not all(self.last_match_players):
            return False
            
        try:
            red_id, blue_id = self.last_match_players
            self.red_player = self.player_db.get_player(red_id)
            self.blue_player = self.player_db.get_player(blue_id)
            return bool(self.red_player and self.blue_player)
        except Exception as e:
            logging.error(f"Error loading last match players: {e}")
            return False

    def clear_selections(self) -> None:
        """Clear all player selections."""
        self.red_player = None
        self.blue_player = None
        self.search_text = {"red": "", "blue": ""}
        self.list_offset = {"red": 0, "blue": 0}
        self.error_messages = {"red": None, "blue": None}

    def cleanup(self) -> None:
        """Clean up resources before exiting."""
        # Store last match if we have selected players
        if self.red_player and self.blue_player:
            self.store_last_match()
            
        # Clear any error messages
        self.error_messages = {"red": None, "blue": None}
        
        # Clear references
        self.red_player = None
        self.blue_player = None
        self.screen = None  # Let pygame handle actual surface cleanup
        
        logging.info("PlayerManager cleanup complete")

    def draw(self) -> None:
        """Draw the player management interface."""
        # Clear screen
        self.screen.fill(self.settings.bg_color)
        
        if self.state == PlayerManagerState.PLAYER_SELECT:
            self._draw_player_selection()
        elif self.state == PlayerManagerState.VIEW_STATS:
            self._draw_player_stats()
        elif self.state == PlayerManagerState.VIEW_RANKINGS:
            self._draw_rankings()
        elif self.state == PlayerManagerState.VIEW_ACHIEVEMENTS:
            self._draw_achievements()

    def _draw_player_selection(self) -> None:
        """Draw the split-screen player selection interface."""
        # Draw red side
        pygame.draw.rect(self.screen, (64, 0, 0), self.red_side)
        self._draw_selection_side("red")
        
        # Draw blue side
        pygame.draw.rect(self.screen, (0, 0, 64), self.blue_side)
        self._draw_selection_side("blue")
        
        # Draw center divider
        pygame.draw.line(self.screen, (255, 255, 255),
                        (self.settings.screen_width // 2, 0),
                        (self.settings.screen_width // 2, self.settings.screen_height),
                        2)
        
        # Draw "Last Match" button if available
        if all(self.last_match_players):
            self._draw_last_match_button()

    def _draw_selection_side(self, team: str) -> None:
        """Draw one team's selection interface."""
        base_x = 0 if team == "red" else self.settings.screen_width // 2
        
        # Draw header
        header_text = f"Select {team.upper()} Player"
        header_color = (255, 0, 0) if team == "red" else (0, 0, 255)
        text_surface = self.font_title.render(header_text, True, header_color)
        text_rect = text_surface.get_rect(
            centerx=base_x + self.settings.screen_width // 4,
            top=20
        )
        self.screen.blit(text_surface, text_rect)
        
        # Draw selected player if any
        player = self.red_player if team == "red" else self.blue_player
        if player:
            self._draw_selected_player(player, team, base_x)
        
        # Draw player list
        self._draw_player_list(team, base_x)
        
        # Draw error message if exists and not expired
        self._draw_error_message(team, base_x)

    def _draw_selected_player(self, player: Player, team: str, base_x: int) -> None:
        """Draw the currently selected player's info."""
        # Background box
        box_rect = pygame.Rect(base_x + 20, 60, 
                             (self.settings.screen_width // 2) - 40, 80)
        color = (128, 0, 0) if team == "red" else (0, 0, 128)
        pygame.draw.rect(self.screen, color, box_rect, border_radius=10)
        
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
        
        self.screen.blit(name_text, (box_rect.x + 10, box_rect.y + 10))
        self.screen.blit(rank_text, (box_rect.x + 10, box_rect.y + 35))
        self.screen.blit(stats_text, (box_rect.x + 10, box_rect.y + 55))

    def _draw_player_list(self, team: str, base_x: int) -> None:
        """
        Draw the scrollable player list.
        
        Args:
            team: Which team's list to draw ('red' or 'blue')
            base_x: Base x position for drawing
            
        Displays filtered players based on search text with proper scrolling
        and highlighting for selected players.
        """
        list_rect = pygame.Rect(
            base_x + 20, 200,  # Moved down to accommodate search bar
            (self.settings.screen_width // 2) - 40,
            self.settings.screen_height - 240  # Adjusted for new position
        )
        pygame.draw.rect(self.screen, (0, 0, 0), list_rect)
        
        # Get filtered player list
        search = self.search_text[team]
        players = self._get_filtered_players(search)
        
        if not players:
            # Show "No players found" message
            no_results_text = self.font_small.render(
                "No players found", True, (128, 128, 128)
            )
            text_rect = no_results_text.get_rect(center=list_rect.center)
            self.screen.blit(no_results_text, text_rect)
            return
            
        # Draw visible players
        y_pos = list_rect.y + 5
        offset = self.list_offset[team]
        for player in players[offset:offset + 6]:  # Show 6 players at a time
            if y_pos + 45 > list_rect.bottom:
                break
                
            self._draw_player_item(player, team, base_x, y_pos)
            y_pos += 50

    def _draw_player_item(self, player: Player, team: str, base_x: int, y_pos: int) -> None:
        """Draw a single player item in the list."""
        item_rect = pygame.Rect(
            base_x + 25, y_pos,
            (self.settings.screen_width // 2) - 50, 45
        )
        
        # Highlight if hovered
        if item_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(self.screen, (64, 64, 64), item_rect)
        
        # Draw player info
        name_text = self.font_small.render(player.name, True, (255, 255, 255))
        rank_number, _ = self.game.ranking_system.elo_to_visible_rank(
            player.elo,
            player.stats.total_matches
        )
        rank_text = self.font_small.render(f"Rank {rank_number}", True, (200, 200, 200))
        
        self.screen.blit(name_text, (item_rect.x + 5, item_rect.y + 5))
        self.screen.blit(rank_text, (item_rect.x + 5, item_rect.y + 25))

    def _draw_error_message(self, team: str, base_x: int) -> None:
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
            centerx=base_x + self.settings.screen_width // 4,
            bottom=self.settings.screen_height - 10
        )
        self.screen.blit(error_surface, error_rect)

    def _draw_last_match_button(self) -> None:
        """Draw the "Last Match Players" quick select button."""
        button_rect = pygame.Rect(
            (self.settings.screen_width - 200) // 2,
            self.settings.screen_height - 50,
            200, 40
        )
        
        # Draw button background
        pygame.draw.rect(self.screen, (0, 128, 0), button_rect, border_radius=5)
        
        # Draw button text
        text = self.font_small.render("Last Match Players", True, (255, 255, 255))
        text_rect = text.get_rect(center=button_rect.center)
        self.screen.blit(text, text_rect)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle input events."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Determine which side was clicked
            mouse_pos = pygame.mouse.get_pos()
            if mouse_pos[0] < self.settings.screen_width // 2:
                self._handle_side_click("red", mouse_pos)
            else:
                self._handle_side_click("blue", mouse_pos)
                
            # Check for last match button click
            if all(self.last_match_players):
                button_rect = pygame.Rect(
                    (self.settings.screen_width - 200) // 2,
                    self.settings.screen_height - 50,
                    200, 40
                )
                if button_rect.collidepoint(mouse_pos):
                    self.load_last_match_players()
                    
        elif event.type == pygame.MOUSEWHEEL:
            # Handle scrolling for the side the mouse is over
            mouse_pos = pygame.mouse.get_pos()
            team = "red" if mouse_pos[0] < self.settings.screen_width // 2 else "blue"
            self.list_offset[team] = max(0, self.list_offset[team] - event.y)

    def _handle_side_click(self, team: str, pos: Tuple[int, int]) -> None:
        """Handle click events for one side of the screen."""
        # Adjust x position for blue side to match list item calculation
        if team == "blue":
            pos = (pos[0] - self.settings.screen_width // 2, pos[1])
            
        # Check if click is in player list area
        list_rect = pygame.Rect(20, 160,
                              (self.settings.screen_width // 2) - 40,
                              self.settings.screen_height - 200)

        if list_rect.collidepoint(pos):
            # Calculate which player was clicked
            y_offset = pos[1] - list_rect.y
            clicked_index = self.list_offset[team] + (y_offset // 50)
            
            # Get filtered player list
            filtered_players = self._get_filtered_players(self.search_text[team])
            
            # Select player if valid index
            if 0 <= clicked_index < len(filtered_players):
                self.select_player(filtered_players[clicked_index], team)

    def _get_filtered_players(self, search: str) -> List[Player]:
        """Get list of players filtered by search text."""
        players = self.player_db.get_players()
        if not search:
            return players
            
        search = search.lower()
        return [p for p in players if search in p.name.lower()]

    def handle_keyboard(self, event: pygame.event.Event) -> None:
        """
        Handle keyboard events for search.
        
        Args:
            event: Pygame event to handle
        
        The currently focused side (red/blue) is determined by mouse position.
        Handles both text input and special keys like backspace.
        """
        # Only process text input when a search bar is active
        mouse_pos = pygame.mouse.get_pos()
        team = "red" if mouse_pos[0] < self.settings.screen_width // 2 else "blue"
        
        if event.type == pygame.KEYDOWN:
            # Handle backspace
            if event.key == pygame.K_BACKSPACE:
                self.search_text[team] = self.search_text[team][:-1]
                self.list_offset[team] = 0  # Reset scroll position
            # Handle escape to clear search
            elif event.key == pygame.K_ESCAPE:
                self.search_text[team] = ""
                self.list_offset[team] = 0
        
        # Handle regular text input
        elif event.type == pygame.TEXTINPUT:
            if len(self.search_text[team]) < 20:  # Limit search text length
                self.search_text[team] += event.text
                self.list_offset[team] = 0  # Reset scroll position
