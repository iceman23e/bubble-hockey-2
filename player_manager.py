# player_manager.py
import pygame
from typing import Optional, List, Tuple, Dict
from enum import Enum
import logging

class PlayerManagerState(Enum):
    MAIN = "main"
    CREATE_PLAYER = "create"
    SELECT_RED_PLAYER = "select_red"    # Added separate states for each team
    SELECT_BLUE_PLAYER = "select_blue"  # to enforce selection order
    VIEW_STATS = "stats"
    VIEW_RANKINGS = "rankings"
    VIEW_ACHIEVEMENTS = "achievements"

class PlayerManager:
    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.state = PlayerManagerState.MAIN
        self.red_player: Optional[Player] = None
        self.blue_player: Optional[Player] = None
        self.player_list_offset = 0
        self.search_text = ""
        self.loading_animation_frame = 0
        self.selection_error: Optional[str] = None  # For displaying error messages
        self.error_display_time = 0
        
    def select_player(self, player: Player, team: str) -> bool:
        """
        Select a player for a specific team.
        
        Args:
            player: Player to select
            team: Team ('red' or 'blue') to assign player to
            
        Returns:
            bool: True if selection was successful, False if player already selected
        """
        try:
            # Verify valid team
            if team not in ['red', 'blue']:
                raise ValueError(f"Invalid team: {team}")
                
            # Check if player is already selected by other team
            if ((team == 'red' and self.blue_player and self.blue_player.id == player.id) or
                (team == 'blue' and self.red_player and self.red_player.id == player.id)):
                self.selection_error = "Player already selected by other team"
                self.error_display_time = pygame.time.get_ticks()
                return False
                
            # Assign player to team
            if team == 'red':
                self.red_player = player
                self.state = PlayerManagerState.SELECT_BLUE_PLAYER  # Move to blue selection
            else:
                self.blue_player = player
                # Both players selected, could trigger next menu state here
                
            logging.info(f"Player {player.name} selected for {team} team")
            return True
            
        except Exception as e:
            logging.error(f"Error in player selection: {e}")
            self.selection_error = "Error selecting player"
            self.error_display_time = pygame.time.get_ticks()
            return False

    def get_selected_players(self) -> Tuple[Optional[Player], Optional[Player]]:
        """Get currently selected players."""
        return self.red_player, self.blue_player

    def clear_selections(self) -> None:
        """Clear all player selections."""
        self.red_player = None
        self.blue_player = None
        self.state = PlayerManagerState.SELECT_RED_PLAYER  # Reset to red selection
        self.selection_error = None

    def draw(self):
        """Draw the player management interface."""
        if self.state == PlayerManagerState.MAIN:
            self._draw_main_menu()
        elif self.state == PlayerManagerState.CREATE_PLAYER:
            self._draw_create_player()
        elif self.state in [PlayerManagerState.SELECT_RED_PLAYER, PlayerManagerState.SELECT_BLUE_PLAYER]:
            self._draw_player_selection()
        elif self.state == PlayerManagerState.VIEW_STATS:
            self._draw_player_stats()
        elif self.state == PlayerManagerState.VIEW_RANKINGS:
            self._draw_rankings()
        elif self.state == PlayerManagerState.VIEW_ACHIEVEMENTS:
            self._draw_achievements()

    def _draw_player_selection(self):
        """Draw the player selection screen."""
        # Clear screen
        self.screen.fill(self.settings.bg_color)
        
        # Draw header based on current selection state
        header_text = "Select RED Player" if self.state == PlayerManagerState.SELECT_RED_PLAYER else "Select BLUE Player"
        header_color = (255, 0, 0) if self.state == PlayerManagerState.SELECT_RED_PLAYER else (0, 0, 255)
        self._draw_header(header_text, header_color)
        
        # Draw current selections
        self._draw_selected_players()
        
        # Draw player list
        self._draw_player_list()
        
        # Draw error message if exists and not expired
        if self.selection_error and pygame.time.get_ticks() - self.error_display_time < 3000:
            self._draw_error_message()

    def _draw_selected_players(self):
        """Draw the currently selected players."""
        # Draw Red player selection
        if self.red_player:
            self._draw_player_box(self.red_player, "RED", (255, 0, 0), (20, 100))
            
        # Draw Blue player selection
        if self.blue_player:
            self._draw_player_box(self.blue_player, "BLUE", (0, 0, 255), (self.settings.screen_width - 220, 100))

    def _draw_player_box(self, player: Player, team: str, color: Tuple[int, int, int], pos: Tuple[int, int]):
        """Draw a selected player's info box."""
        # Draw box background
        box_rect = pygame.Rect(pos[0], pos[1], 200, 100)
        pygame.draw.rect(self.screen, color, box_rect, border_radius=10)
        
        # Draw player info
        rank_number, rank = self.game.ranking_system.elo_to_visible_rank(
            player.elo,
            player.stats.total_matches
        )
        
        name_text = self.font_small.render(player.name, True, (255, 255, 255))
        rank_text = self.font_small.render(f"Rank {rank_number}", True, (255, 255, 255))
        
        self.screen.blit(name_text, (pos[0] + 10, pos[1] + 10))
        self.screen.blit(rank_text, (pos[0] + 10, pos[1] + 40))

    def _draw_error_message(self):
        """Draw any error messages."""
        if not self.selection_error:
            return
            
        error_surface = self.font_small.render(self.selection_error, True, (255, 0, 0))
        error_rect = error_surface.get_rect(center=(self.settings.screen_width // 2, self.settings.screen_height - 50))
        self.screen.blit(error_surface, error_rect)
