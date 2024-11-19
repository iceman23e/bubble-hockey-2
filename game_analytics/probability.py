# game_analytics/probability.py

import math
from functools import lru_cache
from typing import Dict, List, Optional
import logging
from .exceptions import InsufficientDataError
from .models import GameState, AnalyticsConfig

class WinProbabilityTracker:
    """Tracks and calculates win probabilities based on game state"""
    
    def __init__(self, db, config: AnalyticsConfig):
        self.db = db
        self.config = config
        self.historical_patterns = {}
        self.weights = {
            'score_diff': 0.4,
            'time_remaining_ratio': 0.2,
            'period_progress': 0.1,
            'momentum_factor': 0.2,
            'historical_pattern': 0.1
        }
        self._load_historical_patterns()
        
    def _load_historical_patterns(self) -> None:
        """Load historical game patterns from database"""
        try:
            games = self.db.get_game_stats(None)
            self.total_games = len(games) if games else 0
            
            if self.total_games >= self.config.min_games_basic:
                self._load_basic_patterns()
                
            if self.total_games >= self.config.min_games_advanced:
                self._load_advanced_patterns()
                
        except Exception as e:
            logging.error(f"Error loading historical patterns: {e}")
            self.total_games = 0

    @lru_cache(maxsize=128)
    def calculate_win_probability(self, state: GameState) -> Dict[str, float]:
        """Calculate current win probability for both teams"""
        if not state.validate():
            raise ValueError("Invalid game state")
            
        if self.total_games < self.config.min_games_basic:
            return self._calculate_basic_probability(state)
        elif self.total_games < self.config.min_games_advanced:
            return self._calculate_intermediate_probability(state)
        else:
            return self._calculate_advanced_probability(state)

    def _calculate_basic_probability(self, state: GameState) -> Dict[str, float]:
        """Calculate basic win probability based on score and time"""
        score_diff = state.score['red'] - state.score['blue']
        time_remaining = state.clock
        period = state.period
        
        # Base probability calculation
        base_prob = 0.5 + (score_diff * 0.1)
        
        # Time factor adjustment
        time_factor = time_remaining / (period * state.period_length)
        
        # Adjust probability based on time remaining
        if score_diff > 0:
            red_prob = base_prob + ((1 - base_prob) * (1 - time_factor))
        elif score_diff < 0:
            red_prob = base_prob * time_factor
        else:
            red_prob = 0.5
            
        # Ensure probabilities are valid
        red_prob = max(0.01, min(0.99, red_prob))
        
        return {
            'red': red_prob,
            'blue': 1 - red_prob
        }

    def _calculate_advanced_probability(self, state: GameState) -> Dict[str, float]:
        """Advanced probability calculation using weighted features"""
        features = self._calculate_features(state)
        
        # Calculate weighted sum
        z = sum(self.weights[k] * v for k, v in features.items())
        
        # Apply logistic function
        probability = 1 / (1 + math.exp(-z))
        
        # Apply confidence adjustment based on historical data
        confidence = min(1.0, self.total_games / self.config.min_games_advanced)
        adjusted_prob = (probability * confidence) + (0.5 * (1 - confidence))
        
        return {
            'red': adjusted_prob,
            'blue': 1 - adjusted_prob
        }

    def _calculate_features(self, state: GameState) -> Dict[str, float]:
        """Calculate features for probability calculation"""
        score_diff = state.score['red'] - state.score['blue']
        time_remaining = state.clock
        period = state.period
        
        return {
            'score_diff': self._normalize_score_diff(score_diff),
            'time_remaining_ratio': time_remaining / (period * state.period_length),
            'period_progress': period / state.max_periods,
            'momentum_factor': self._get_momentum_factor(state),
            'historical_pattern': self._get_historical_pattern(score_diff, period)
        }

    @staticmethod
    def _normalize_score_diff(score_diff: int) -> float:
        """Normalize score differential to [-1, 1] range"""
        return math.tanh(score_diff / 3.0)  # 3 goals is considered a significant lead

    def _get_momentum_factor(self, state: GameState) -> float:
        """Calculate momentum factor based on recent scoring patterns"""
        recent_goals = self.db.get_recent_goals(state.game_id, window=60)
        if not recent_goals:
            return 0.0
            
        red_goals = sum(1 for goal in recent_goals if goal.team == 'red')
        blue_goals = len(recent_goals) - red_goals
        
        return math.tanh((red_goals - blue_goals) / 2.0)

    def _get_historical_pattern(self, score_diff: int, period: int) -> float:
        """Get historical win rate for similar situations"""
        if not self.historical_patterns:
            return 0.0
            
        pattern_key = (score_diff, period)
        if pattern_key in self.historical_patterns:
            return self.historical_patterns[pattern_key]
            
        return 0.5  # Default to even probability if no pattern exists
