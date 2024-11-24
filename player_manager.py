# player_manager.py
import pygame
from typing import Optional, List
from enum import Enum

class PlayerManagerState(Enum):
    MAIN = "main"
    CREATE_PLAYER = "create"
    SELECT_PLAYER = "select"
    VIEW_STATS = "stats"
    VIEW_RANKINGS = "rankings"
    VIEW_ACHIEVEMENTS = "achievements"

class PlayerManager:
    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.state = PlayerManagerState.MAIN
        self.selected_player: Optional[Player] = None
        self.player_list_offset = 0
        self.search_text = ""
        self.loading_animation_frame = 0
        
    def draw(self):
        """Draw the player management interface."""
        if self.state == PlayerManagerState.MAIN:
            self._draw_main_menu()
        elif self.state == PlayerManagerState.CREATE_PLAYER:
            self._draw_create_player()
        elif self.state == PlayerManagerState.SELECT_PLAYER:
            self._draw_player_selection()
        elif self.state == PlayerManagerState.VIEW_STATS:
            self._draw_player_stats()
        elif self.state == PlayerManagerState.VIEW_RANKINGS:
            self._draw_rankings()
        elif self.state == PlayerManagerState.VIEW_ACHIEVEMENTS:
            self._draw_achievements()
            
    def _draw_player_stats(self):
        """Draw detailed player statistics with visualizations."""
        if not self.selected_player:
            return
            
        # Draw rank emblem
        rank_number, rank = ranking_system.elo_to_visible_rank(
            self.selected_player.elo,
            self.selected_player.stats.total_matches
        )
        
        # Draw radar chart of player skills
        self._draw_skill_radar_chart(
            [
                self.selected_player.stats.power_up_efficiency,
                self.selected_player.stats.quick_response_goals / max(1, self.selected_player.stats.total_matches),
                self.selected_player.stats.comeback_wins / max(1, self.selected_player.stats.total_matches),
                self.selected_player.stats.avg_goals_per_match / 5  # Normalize to 0-1
            ],
            ['Power-Ups', 'Quick Goals', 'Comebacks', 'Scoring']
        )
        
        # Draw match history graph
        self._draw_match_history_graph()
        
        # Draw achievements
        self._draw_achievement_showcase()
