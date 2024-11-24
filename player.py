# player.py
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

@dataclass
class PlayerStats:
    """Detailed player statistics."""
    total_goals: int = 0
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    highest_combo: int = 0
    power_ups_collected: int = 0
    power_up_efficiency: float = 0.0
    quick_response_goals: int = 0
    comeback_wins: int = 0
    critical_goals: int = 0
    avg_goals_per_match: float = 0.0
    favorite_game_mode: str = "classic"
    best_opponent: Optional[str] = None
    rival: Optional[str] = None
    win_streaks: List[int] = None
    best_win_streak: int = 0
    current_win_streak: int = 0

class Player:
    def __init__(self, player_id: str, name: str):
        self.id = player_id
        self.name = name
        self.elo = 1500
        self.stats = PlayerStats()
        self.match_history: List[str] = []  # Match IDs
        self.achievements: List[str] = []
        self.preferred_team: Optional[str] = None
        self.created_at = datetime.now()
        self.last_match = None
        self.rank_progression: List[tuple] = []  # [(datetime, rank)]
        
    def update_stats_from_analytics(self, analytics_data: Dict):
        """Update player stats using analytics data."""
        match_stats = analytics_data.get('player_stats', {}).get(self.id, {})
        
        self.stats.total_goals += match_stats.get('goals', 0)
        self.stats.power_ups_collected += match_stats.get('power_ups', 0)
        self.stats.quick_response_goals += match_stats.get('quick_responses', 0)
        
        # Update averages
        if self.stats.total_matches > 0:
            self.stats.avg_goals_per_match = (
                self.stats.total_goals / self.stats.total_matches
            )
            
        # Check for achievements
        self._check_achievements(match_stats)
        
    def _check_achievements(self, match_stats: Dict):
        """Check and award achievements based on performance."""
        if match_stats.get('comeback_win'):
            self._award_achievement('comeback_king')
        if match_stats.get('perfect_game'):  # No goals allowed
            self._award_achievement('perfect_defense')
        if match_stats.get('max_combo', 0) >= 5:
            self._award_achievement('combo_master')
