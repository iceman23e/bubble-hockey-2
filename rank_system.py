# rank_system.py
from enum import Enum
from typing import Tuple, Optional
import math

class HaloRank(Enum):
    """Halo 2-style ranks with corresponding image paths."""
    RANK_1 = ("Apprentice", "assets/ranks/rank1.png")
    RANK_10 = ("Private", "assets/ranks/rank10.png")
    RANK_20 = ("Corporal", "assets/ranks/rank20.png")
    RANK_30 = ("Sergeant", "assets/ranks/rank30.png")
    RANK_35 = ("Lieutenant", "assets/ranks/rank35.png")
    RANK_40 = ("Captain", "assets/ranks/rank40.png")
    RANK_45 = ("Major", "assets/ranks/rank45.png")
    RANK_50 = ("Commander", "assets/ranks/rank50.png")
    # Add all Halo 2 ranks...

class RankingSystem:
    """Enhanced ranking system with visible ranks and analytics integration."""
    
    def __init__(self, analytics_engine):
        self.analytics = analytics_engine
        self.min_elo = 1000
        self.max_elo = 3000
        self.placement_matches_required = 5
        
    def elo_to_visible_rank(self, elo: float, matches_played: int) -> Tuple[int, HaloRank]:
        """Convert ELO to visible rank (1-50)."""
        if matches_played < self.placement_matches_required:
            return (0, None)  # Unranked
            
        # Normalize ELO to 1-50 scale
        normalized = (elo - self.min_elo) / (self.max_elo - self.min_elo)
        rank_number = math.ceil(normalized * 50)
        rank_number = max(1, min(50, rank_number))
        
        # Find corresponding Halo rank
        for rank in HaloRank:
            if rank_number <= int(rank.name.split('_')[1]):
                return (rank_number, rank)
                
        return (50, HaloRank.RANK_50)
        
    def get_handicap_settings(self, player1: 'Player', player2: 'Player') -> dict:
        """Calculate handicap settings based on skill gap."""
        rank_diff = abs(player1.elo - player2.elo)
        lower_ranked = player1 if player1.elo < player2.elo else player2
        
        # Base handicap settings
        settings = {
            'power_up_frequency_modifier': 1.0,
            'power_up_duration_modifier': 1.0,
            'combo_window_modifier': 1.0,
            'points_modifier': 1.0
        }
        
        if rank_diff > 300:  # Significant skill gap
            # Calculate modifiers based on skill gap
            modifier = min(1.5, 1 + (rank_diff / 1000))  # Cap at 50% boost
            
            settings = {
                'power_up_frequency_modifier': 1/modifier,  # More frequent power-ups
                'power_up_duration_modifier': modifier,     # Longer lasting power-ups
                'combo_window_modifier': modifier,         # Larger combo window
                'points_modifier': modifier               # More points per goal
            }
            
        return settings

    def integrate_match_analytics(self, match_id: str) -> dict:
        """Pull relevant data from analytics for ranking adjustments."""
        analytics_data = self.analytics.get_match_analytics(match_id)
        
        # Factor in analytics data for ranking adjustments
        return {
            'momentum_factor': analytics_data.get('momentum', {}).get('dominance_ratio', 1.0),
            'critical_goals': analytics_data.get('patterns', {}).get('critical_goals', 0),
            'comeback_factor': analytics_data.get('patterns', {}).get('comeback_completed', False),
            'skill_indicators': {
                'quick_reactions': analytics_data.get('timing_patterns', {}).get('quick_response_rate', 0),
                'combo_efficiency': analytics_data.get('scoring_patterns', {}).get('combo_success_rate', 0),
                'power_up_usage': analytics_data.get('power_up_efficiency', 1.0)
            }
        }
