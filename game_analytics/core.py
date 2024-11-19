# game_analytics/core.py

import logging
from typing import Dict, Optional
from datetime import datetime
from .models import GameState, GoalEvent, AnalyticsConfig
from .probability import WinProbabilityTracker
from .patterns import PatternAnalyzer
from .momentum import MomentumTracker
from .events import AnalyticsEventSystem, SensorType
from .exceptions import (
    AnalyticsError, 
    InsufficientDataError, 
    InvalidGameStateError
)

class GameAnalytics:
    """Main analytics system that coordinates all components"""
    
    def __init__(self, db, config: Optional[AnalyticsConfig] = None):
        """
        Initialize the analytics system
        
        Args:
            db: Database connection
            config: Optional analytics configuration
        """
        self.db = db
        self.config = config or AnalyticsConfig()
        
        # Initialize components
        self.win_probability = WinProbabilityTracker(db, self.config)
        self.pattern_analyzer = PatternAnalyzer(self.config)
        self.momentum_tracker = MomentumTracker(self.config)
        self.event_system = AnalyticsEventSystem()
        
        self.current_game_state = None
        self.last_goal_time = None
        
        # Set up logging
        self.logger = logging.getLogger('analytics.core')
        self._setup_logging()
        
        # Register event handlers
        self._register_event_handlers()
        
        self.logger.info("Game Analytics System initialized")

    def _setup_logging(self):
        """Set up logging configuration"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _register_event_handlers(self):
        """Register handlers for different event types"""
        self.event_system.register_handler(
            SensorType.GOALS,
            self._handle_goal_event
        )
        self.event_system.register_handler(
            SensorType.TIME,
            self._handle_time_event
        )

    def update(self, new_state: GameState) -> Dict:
        """
        Update analytics with new game state
        
        Args:
            new_state: New game state to analyze
            
        Returns:
            Dict containing current analytics
            
        Raises:
            InvalidGameStateError: If game state is invalid
        """
        try:
            if not new_state.validate():
                raise InvalidGameStateError("Invalid game state")
                
            self.current_game_state = new_state
            
            # Process the new state
            win_probs = self.win_probability.calculate_win_probability(new_state)
            patterns = self.pattern_analyzer.get_current_patterns()
            momentum = self.momentum_tracker.get_momentum_analysis()
            
            # Check for critical moments
            is_critical = self._check_critical_moment()
            
            analysis = {
                'win_probability': win_probs,
                'patterns': patterns,
                'momentum': momentum,
                'is_critical_moment': is_critical,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save analysis to database
            self._save_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error updating analytics: {e}")
            raise

    def record_goal(self, team: str, game_state: GameState) -> Dict:
        """
        Record a goal and update all analytics
        
        Args:
            team: Team that scored ('red' or 'blue')
            game_state: Current game state
            
        Returns:
            Dict containing updated analytics
        """
        try:
            current_time = datetime.now()
            
            # Create goal event
            goal = GoalEvent(
                time=game_state.clock,
                period=game_state.period,
                team=team,
                score_after=game_state.score.copy(),
                timestamp=current_time,
                time_since_last=(current_time - self.last_goal_time).total_seconds()
                if self.last_goal_time else None
            )
            
            # Process goal through event system
            self.event_system.process_sensor_data(SensorType.GOALS, goal)
            
            self.last_goal_time = current_time
            
            # Return updated analysis
            return self.update(game_state)
            
        except Exception as e:
            self.logger.error(f"Error recording goal: {e}")
            raise

    def _handle_goal_event(self, event):
        """Handle goal events from event system"""
        try:
            goal = event.data
            self.pattern_analyzer.add_goal(goal)
            self.momentum_tracker.add_goal(goal)
            
        except Exception as e:
            self.logger.error(f"Error handling goal event: {e}")

    def _handle_time_event(self, event):
        """Handle time update events"""
        try:
            # Update time-based analytics
            if self.current_game_state:
                self.current_game_state.clock = event.data
                
        except Exception as e:
            self.logger.error(f"Error handling time event: {e}")

    def _check_critical_moment(self) -> bool:
        """Determine if current game state is a critical moment"""
        if not self.current_game_state:
            return False
            
        state = self.current_game_state
        score_diff = abs(state.score['red'] - state.score['blue'])
        
        # Criteria for critical moments
        is_close_game = score_diff <= self.config.close_game_threshold
        is_final_minutes = state.clock <= self.config.critical_moment_threshold
        has_strong_momentum = (self.momentum_tracker.get_momentum_analysis()
                             ['current_state']['intensity'] in ['strong', 'overwhelming'])
        
        return (is_close_game and is_final_minutes) or has_strong_momentum

    def _save_analysis(self, analysis: Dict):
        """Save analysis to database"""
        try:
            if self.current_game_state:
                self.db.save_game_state(
                    self.current_game_state.game_id,
                    {
                        'analysis': analysis,
                        'timestamp': datetime.now().isoformat()
                    }
                )
        except Exception as e:
            self.logger.error(f"Error saving analysis: {e}")

    def get_analytics_summary(self) -> Dict:
        """Get current analytics summary"""
        if not self.current_game_state:
            return {}
            
        return {
            'win_probability': self.win_probability.calculate_win_probability(
                self.current_game_state
            ),
            'patterns': self.pattern_analyzer.get_current_patterns(),
            'momentum': self.momentum_tracker.get_momentum_analysis(),
            'is_critical_moment': self._check_critical_moment(),
            'game_stats': self._get_game_stats()
        }

    def _get_game_stats(self) -> Dict:
        """Get current game statistics"""
        if not self.current_game_state:
            return {}
            
        return {
            'total_goals': len(self.pattern_analyzer.goals),
            'goals_per_period': self.pattern_analyzer.get_current_patterns()['goal_distribution']['by_period'],
            'scoring_runs': self.pattern_analyzer.get_current_patterns()['scoring_runs'],
            'momentum_shifts': self.momentum_tracker.get_momentum_analysis()['momentum_shifts'],
            'game_id': self.current_game_state.game_id,
            'mode': self.current_game_state.mode
        }

    def cleanup(self):
        """Clean up analytics system resources"""
        self.event_system.clear_handlers()
        self.logger.info("Analytics system cleaned up")
