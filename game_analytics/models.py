# game_analytics/models.py

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

@dataclass
class GameState:
    """Current game state data structure"""
    score: Dict[str, int]
    period: int
    clock: float
    game_id: int
    mode: str
    is_running_clock: bool
    max_periods: int = 3
    period_length: float = 180.0  # 3 minutes default
    
    def validate(self) -> bool:
        """Validate game state data"""
        try:
            # Score validation
            assert isinstance(self.score, dict)
            assert 'red' in self.score and 'blue' in self.score
            assert isinstance(self.score['red'], int) and isinstance(self.score['blue'], int)
            assert self.score['red'] >= 0 and self.score['blue'] >= 0
            
            # Period validation
            assert isinstance(self.period, int)
            assert 1 <= self.period <= self.max_periods
            
            # Clock validation
            assert isinstance(self.clock, (int, float))
            assert 0 <= self.clock <= self.period_length
            
            # Game ID validation
            assert isinstance(self.game_id, int)
            assert self.game_id > 0
            
            # Mode validation
            assert isinstance(self.mode, str)
            assert self.mode in ['classic', 'evolved', 'crazy_play']
            
            # Clock type validation
            assert isinstance(self.is_running_clock, bool)
            
            return True
            
        except AssertionError:
            return False

    def to_dict(self) -> Dict:
        """Convert game state to dictionary"""
        return {
            'score': self.score,
            'period': self.period,
            'clock': self.clock,
            'game_id': self.game_id,
            'mode': self.mode,
            'is_running_clock': self.is_running_clock,
            'max_periods': self.max_periods,
            'period_length': self.period_length
        }

@dataclass
class GoalEvent:
    """Goal event data structure"""
    time: float
    period: int
    team: str
    score_after: Dict[str, int]
    timestamp: datetime = None
    time_since_last: Optional[float] = None
    
    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def validate(self) -> bool:
        """Validate goal event data"""
        try:
            assert isinstance(self.time, (int, float))
            assert isinstance(self.period, int)
            assert self.team in ['red', 'blue']
            assert isinstance(self.score_after, dict)
            assert 'red' in self.score_after and 'blue' in self.score_after
            assert isinstance(self.score_after['red'], int)
            assert isinstance(self.score_after['blue'], int)
            if self.time_since_last is not None:
                assert isinstance(self.time_since_last, (int, float))
            return True
        except AssertionError:
            return False

    def to_dict(self) -> Dict:
        """Convert goal event to dictionary"""
        return {
            'time': self.time,
            'period': self.period,
            'team': self.team,
            'score_after': self.score_after,
            'timestamp': self.timestamp.isoformat(),
            'time_since_last': self.time_since_last
        }

@dataclass
class AnalyticsConfig:
    """Configuration for analytics system"""
    min_games_basic: int = 30
    min_games_advanced: int = 300
    momentum_window: int = 60
    quick_response_window: int = 30
    scoring_run_threshold: int = 3
    cache_size: int = 128
    critical_moment_threshold: float = 60.0
    close_game_threshold: int = 2
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            assert isinstance(self.min_games_basic, int) and self.min_games_basic > 0
            assert isinstance(self.min_games_advanced, int) and self.min_games_advanced > self.min_games_basic
            assert isinstance(self.momentum_window, int) and self.momentum_window > 0
            assert isinstance(self.quick_response_window, int) and self.quick_response_window > 0
            assert isinstance(self.scoring_run_threshold, int) and self.scoring_run_threshold > 1
            assert isinstance(self.cache_size, int) and self.cache_size > 0
            assert isinstance(self.critical_moment_threshold, (int, float)) and self.critical_moment_threshold > 0
            assert isinstance(self.close_game_threshold, int) and self.close_game_threshold > 0
            return True
        except AssertionError:
            return False

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return {
            'min_games_basic': self.min_games_basic,
            'min_games_advanced': self.min_games_advanced,
            'momentum_window': self.momentum_window,
            'quick_response_window': self.quick_response_window,
            'scoring_run_threshold': self.scoring_run_threshold,
            'cache_size': self.cache_size,
            'critical_moment_threshold': self.critical_moment_threshold,
            'close_game_threshold': self.close_game_threshold
        }
