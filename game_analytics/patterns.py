# game_analytics/patterns.py

from collections import deque
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import logging
from .models import GoalEvent, GameState, AnalyticsConfig

class PatternAnalyzer:
    """Analyzes game patterns and trends"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self.goals: List[GoalEvent] = []
        self.scoring_runs: List[List[GoalEvent]] = []
        self.current_run: List[GoalEvent] = []
        self.recent_goals: deque = deque(maxlen=10)  # Keep last 10 goals for quick access
        self.logger = logging.getLogger('analytics.patterns')

    def add_goal(self, goal: GoalEvent) -> Dict:
        """
        Add a new goal and analyze patterns
        
        Args:
            goal: The goal event to analyze
            
        Returns:
            Dict containing current patterns and analysis
        """
        if not goal.validate():
            self.logger.error("Invalid goal event data")
            raise ValueError("Invalid goal event")

        self.goals.append(goal)
        self.recent_goals.append(goal)
        
        # Update pattern analysis
        scoring_run = self._analyze_scoring_run(goal)
        response_goal = self._analyze_response_goal(goal)
        critical_goal = self._analyze_critical_goal(goal)
        
        return {
            'scoring_run': scoring_run,
            'response_goal': response_goal,
            'critical_goal': critical_goal,
            'current_patterns': self.get_current_patterns()
        }

    def _analyze_scoring_run(self, goal: GoalEvent) -> Optional[Dict]:
        """Analyze if this goal is part of a scoring run"""
        if not self.current_run:
            self.current_run = [goal]
            return None
            
        if self.current_run[-1].team == goal.team:
            self.current_run.append(goal)
            if len(self.current_run) >= self.config.scoring_run_threshold:
                run_info = {
                    'team': goal.team,
                    'goals': len(self.current_run),
                    'duration': self.current_run[-1].time - self.current_run[0].time,
                    'started_period': self.current_run[0].period
                }
                self.scoring_runs.append(self.current_run[:])
                return run_info
        else:
            self.current_run = [goal]
        
        return None

    @lru_cache(maxsize=128)
    def _analyze_response_goal(self, goal: GoalEvent) -> Optional[Dict]:
        """Analyze if this is a quick response goal"""
        if len(self.goals) < 2:
            return None
            
        last_goal = self.goals[-2]
        if last_goal.team != goal.team and goal.time_since_last is not None:
            if goal.time_since_last <= self.config.quick_response_window:
                return {
                    'team': goal.team,
                    'response_time': goal.time_since_last,
                    'period': goal.period
                }
        return None

    def _analyze_critical_goal(self, goal: GoalEvent) -> Optional[Dict]:
        """Analyze if this is a critical goal"""
        score_diff = abs(goal.score_after['red'] - goal.score_after['blue'])
        
        is_critical = (
            score_diff <= self.config.close_game_threshold or  # Close game
            goal.time <= self.config.critical_moment_threshold  # Late game
        )
        
        if is_critical:
            return {
                'team': goal.team,
                'score_diff': score_diff,
                'time_remaining': goal.time,
                'period': goal.period,
                'type': 'tying' if score_diff == 0 else 'go_ahead' if score_diff == 1 else 'insurance'
            }
        return None

    def get_current_patterns(self) -> Dict:
        """Get current game patterns"""
        return {
            'scoring_runs': self._analyze_scoring_runs(),
            'goal_distribution': self._analyze_goal_distribution(),
            'timing_patterns': self._analyze_timing_patterns(),
            'team_patterns': self._analyze_team_patterns()
        }

    def _analyze_scoring_runs(self) -> Dict:
        """Analyze all scoring runs in the game"""
        return {
            'total_runs': len(self.scoring_runs),
            'current_run': {
                'team': self.current_run[-1].team if self.current_run else None,
                'length': len(self.current_run)
            },
            'longest_run': max((len(run) for run in self.scoring_runs), default=0),
            'runs_by_team': {
                'red': sum(1 for run in self.scoring_runs if run[0].team == 'red'),
                'blue': sum(1 for run in self.scoring_runs if run[0].team == 'blue')
            }
        }

    def _analyze_goal_distribution(self) -> Dict:
        """Analyze how goals are distributed through the game"""
        periods = {}
        for goal in self.goals:
            if goal.period not in periods:
                periods[goal.period] = {'red': 0, 'blue': 0}
            periods[goal.period][goal.team] += 1
            
        return {
            'by_period': periods,
            'total_goals': len(self.goals),
            'goals_by_team': {
                'red': sum(1 for goal in self.goals if goal.team == 'red'),
                'blue': sum(1 for goal in self.goals if goal.team == 'blue')
            }
        }

    def _analyze_timing_patterns(self) -> Dict:
        """Analyze timing patterns of goals"""
        intervals = [g.time_since_last for g in self.goals if g.time_since_last is not None]
        
        return {
            'avg_interval': sum(intervals) / len(intervals) if intervals else 0,
            'quick_goals': sum(1 for i in intervals if i <= self.config.quick_response_window),
            'longest_drought': max(intervals, default=0),
            'early_goals': sum(1 for g in self.goals if g.time >= (g.period * 180 - 30)),
            'late_goals': sum(1 for g in self.goals if g.time <= 30)
        }

    def _analyze_team_patterns(self) -> Dict:
        """Analyze team-specific patterns"""
        return {
            'response_goals': {
                'red': sum(1 for i in range(1, len(self.goals))
                          if self.goals[i].team == 'red' 
                          and self.goals[i-1].team == 'blue'
                          and self.goals[i].time_since_last <= self.config.quick_response_window),
                'blue': sum(1 for i in range(1, len(self.goals))
                          if self.goals[i].team == 'blue'
                          and self.goals[i-1].team == 'red'
                          and self.goals[i].time_since_last <= self.config.quick_response_window)
            },
            'comebacks': self._analyze_comebacks()
        }

    def _analyze_comebacks(self) -> Dict:
        """Analyze comeback attempts and successes"""
        comebacks = {'red': 0, 'blue': 0}
        comeback_attempts = {'red': 0, 'blue': 0}
        
        for i, goal in enumerate(self.goals[:-1]):
            score_diff = goal.score_after['red'] - goal.score_after['blue']
            if abs(score_diff) >= 2:  # Two or more goal deficit
                trailing_team = 'blue' if score_diff > 0 else 'red'
                comeback_attempts[trailing_team] += 1
                
                # Check if they eventually tied or took the lead
                for future_goal in self.goals[i+1:]:
                    future_diff = future_goal.score_after['red'] - future_goal.score_after['blue']
                    if (trailing_team == 'red' and future_diff >= 0) or \
                       (trailing_team == 'blue' and future_diff <= 0):
                        comebacks[trailing_team] += 1
                        break
        
        return {
            'successful': comebacks,
            'attempts': comeback_attempts
        }
