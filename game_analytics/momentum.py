# game_analytics/momentum.py

from collections import deque
from typing import Dict, Optional, List
import math
from datetime import datetime, timedelta
import logging
from .models import GoalEvent, GameState, AnalyticsConfig

class MomentumTracker:
    """Tracks and analyzes game momentum"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self.recent_goals: deque = deque()
        self.current_momentum: Optional[str] = None
        self.momentum_score = 0  # -100 to 100, negative is blue momentum
        self.momentum_history: List[Dict] = []
        self.logger = logging.getLogger('analytics.momentum')
        
    def add_goal(self, goal: GoalEvent) -> Dict:
        """
        Add a goal and update momentum analysis
        
        Args:
            goal: The goal event to analyze
            
        Returns:
            Dict containing current momentum analysis
        """
        current_time = goal.timestamp
        
        # Remove old goals outside the window
        while (self.recent_goals and 
               (current_time - self.recent_goals[0].timestamp) > 
               timedelta(seconds=self.config.momentum_window)):
            self.recent_goals.popleft()
            
        self.recent_goals.append(goal)
        
        # Calculate new momentum
        momentum_state = self._calculate_momentum()
        
        # Record momentum history
        self.momentum_history.append({
            'timestamp': current_time,
            'momentum_score': self.momentum_score,
            'team': self.current_momentum,
            'trigger': 'goal',
            'team_scored': goal.team
        })
        
        return momentum_state
        
    def _calculate_momentum(self) -> Dict:
        """Calculate current momentum based on recent goals and patterns"""
        if not self.recent_goals:
            self._reset_momentum()
            return self._get_momentum_state()
            
        # Count recent goals by team
        red_goals = sum(1 for goal in self.recent_goals if goal.team == 'red')
        blue_goals = len(self.recent_goals) - red_goals
        
        # Base momentum score on goal differential
        base_score = (red_goals - blue_goals) * 33.3  # Scale to roughly -100 to 100
        
        # Apply time decay to older goals
        time_weighted_score = self._apply_time_weights(base_score)
        
        # Apply streak multiplier
        streak_multiplier = self._calculate_streak_multiplier()
        
        # Calculate final momentum score
        self.momentum_score = time_weighted_score * streak_multiplier
        
        # Determine momentum team
        if abs(self.momentum_score) >= 33:  # Threshold for momentum shift
            self.current_momentum = 'red' if self.momentum_score > 0 else 'blue'
        else:
            self.current_momentum = None
            
        return self._get_momentum_state()
        
    def _apply_time_weights(self, base_score: float) -> float:
        """Apply time-based weights to momentum calculation"""
        if not self.recent_goals:
            return 0.0
            
        latest_time = self.recent_goals[-1].timestamp
        weighted_sum = 0
        weight_sum = 0
        
        for goal in self.recent_goals:
            # Calculate time difference in seconds
            time_diff = (latest_time - goal.timestamp).total_seconds()
            
            # Apply exponential decay
            weight = math.exp(-time_diff / (self.config.momentum_window / 2))
            goal_value = 1 if goal.team == 'red' else -1
            
            weighted_sum += goal_value * weight
            weight_sum += weight
            
        return (weighted_sum / weight_sum) * 100 if weight_sum > 0 else 0
        
    def _calculate_streak_multiplier(self) -> float:
        """Calculate multiplier based on consecutive goals"""
        if len(self.recent_goals) < 2:
            return 1.0
            
        streak = 1
        max_streak = 1
        current_team = self.recent_goals[-1].team
        
        # Count consecutive goals
        for goal in reversed(list(self.recent_goals)[:-1]):
            if goal.team == current_team:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                break
                
        # Apply diminishing returns to streak multiplier
        return min(1.5, 1 + (max_streak - 1) * 0.1)
        
    def _reset_momentum(self):
        """Reset momentum tracking"""
        self.momentum_score = 0
        self.current_momentum = None
        
    def _get_momentum_state(self) -> Dict:
        """Get current momentum state"""
        return {
            'team': self.current_momentum,
            'score': self.momentum_score,
            'recent_goals': len(self.recent_goals),
            'intensity': self._calculate_intensity(),
            'duration': self._calculate_momentum_duration(),
            'trend': self._calculate_momentum_trend()
        }
        
    def _calculate_intensity(self) -> str:
        """Calculate the intensity of current momentum"""
        abs_score = abs(self.momentum_score)
        if abs_score >= 80:
            return 'overwhelming'
        elif abs_score >= 60:
            return 'strong'
        elif abs_score >= 33:
            return 'moderate'
        else:
            return 'neutral'
            
    def _calculate_momentum_duration(self) -> Optional[float]:
        """Calculate how long current momentum has lasted"""
        if not self.momentum_history:
            return None
            
        current_team = self.current_momentum
        if not current_team:
            return 0
            
        duration = 0
        for state in reversed(self.momentum_history):
            if state['team'] != current_team:
                break
            duration += 1
            
        return duration * (self.config.momentum_window / len(self.momentum_history))
        
    def _calculate_momentum_trend(self) -> str:
        """Calculate the trend of momentum changes"""
        if len(self.momentum_history) < 2:
            return 'stable'
            
        recent_scores = [state['momentum_score'] 
                        for state in self.momentum_history[-3:]]
        
        if len(recent_scores) < 2:
            return 'stable'
            
        avg_change = sum(b - a 
                        for a, b in zip(recent_scores[:-1], recent_scores[1:])) / (len(recent_scores) - 1)
        
        if abs(avg_change) < 10:
            return 'stable'
        return 'increasing' if avg_change > 0 else 'decreasing'
        
    def get_momentum_analysis(self) -> Dict:
        """Get detailed momentum analysis"""
        return {
            'current_state': self._get_momentum_state(),
            'momentum_shifts': self._analyze_momentum_shifts(),
            'dominant_team': self._calculate_dominant_team(),
            'momentum_stats': self._calculate_momentum_stats()
        }
        
    def _analyze_momentum_shifts(self) -> Dict:
        """Analyze momentum shifts during the game"""
        shifts = []
        prev_team = None
        
        for state in self.momentum_history:
            if state['team'] != prev_team and state['team'] is not None:
                shifts.append({
                    'timestamp': state['timestamp'],
                    'from_team': prev_team,
                    'to_team': state['team'],
                    'trigger': state['trigger']
                })
                prev_team = state['team']
                
        return {
            'total_shifts': len(shifts),
            'shifts': shifts,
            'avg_duration': self._calculate_avg_momentum_duration(shifts)
        }
        
    def _calculate_dominant_team(self) -> Optional[str]:
        """Calculate which team has had momentum more often"""
        if not self.momentum_history:
            return None
            
        red_time = sum(1 for state in self.momentum_history 
                      if state['team'] == 'red')
        blue_time = sum(1 for state in self.momentum_history 
                       if state['team'] == 'blue')
                       
        if abs(red_time - blue_time) < len(self.momentum_history) * 0.1:
            return None
        return 'red' if red_time > blue_time else 'blue'
        
    def _calculate_avg_momentum_duration(self, shifts: List[Dict]) -> Optional[float]:
        """Calculate average duration of momentum periods"""
        if not shifts:
            return None
            
        durations = []
        for i in range(len(shifts) - 1):
            duration = (shifts[i + 1]['timestamp'] - 
                       shifts[i]['timestamp']).total_seconds()
            durations.append(duration)
            
        return sum(durations) / len(durations) if durations else None
        
    def _calculate_momentum_stats(self) -> Dict:
        """Calculate various momentum statistics"""
        return {
            'avg_momentum_score': sum(state['momentum_score'] 
                                    for state in self.momentum_history) / len(self.momentum_history)
                                    if self.momentum_history else 0,
            'max_momentum_score': max((abs(state['momentum_score']) 
                                     for state in self.momentum_history), default=0),
            'momentum_distribution': {
                'red': sum(1 for state in self.momentum_history 
                          if state['team'] == 'red') / len(self.momentum_history)
                          if self.momentum_history else 0,
                'blue': sum(1 for state in self.momentum_history 
                           if state['team'] == 'blue') / len(self.momentum_history)
                           if self.momentum_history else 0,
                'neutral': sum(1 for state in self.momentum_history 
                             if state['team'] is None) / len(self.momentum_history)
                             if self.momentum_history else 0
            }
        }
