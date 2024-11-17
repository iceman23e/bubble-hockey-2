# game_states.py

from enum import Enum
from transitions import Machine
import logging
from datetime import datetime
import json
import os
import time

class GameState(Enum):
    """Enum defining all possible game states"""
    INITIALIZING = 'initializing'
    WAITING_FOR_PLAYERS = 'waiting_for_players'
    COUNTDOWN = 'countdown'
    PLAYING = 'playing'
    GOAL_SCORED = 'goal_scored'
    PERIOD_END = 'period_end'
    INTERMISSION = 'intermission'
    GAME_OVER = 'game_over'
    ERROR = 'error'
    DIAGNOSTICS = 'diagnostics'
    PAUSED = 'paused'

class GameStateMachine:
    """Handles game state transitions and validation"""
    
    def __init__(self, game):
        self.game = game
        self.error_count = 0
        self.last_state_save = datetime.now()
        self.previous_state = None
        self.state_history = []
        self.max_history = 10
        
        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=GameState,
            initial=GameState.INITIALIZING,
            auto_transitions=False,
            before_state_change=[self._validate_state_change, self._store_previous_state],
            after_state_change=[self._log_state_change, self._check_save_state, self._update_history]
        )

        # Define transitions
        self._define_transitions()
        logging.info("Game state machine initialized")

    def _define_transitions(self):
        """Define all possible state transitions"""
        # Initial game setup transitions
        self.machine.add_transition(
            'start_game',
            GameState.INITIALIZING,
            GameState.WAITING_FOR_PLAYERS,
            conditions=['are_sensors_ready'],
            after=['notify_game_start']
        )

        self.machine.add_transition(
            'players_ready',
            GameState.WAITING_FOR_PLAYERS,
            GameState.COUNTDOWN,
            conditions=['is_puck_ready']
        )

        self.machine.add_transition(
            'countdown_complete',
            GameState.COUNTDOWN,
            GameState.PLAYING
        )

        # Gameplay transitions
        self.machine.add_transition(
            'goal_scored',
            GameState.PLAYING,
            GameState.GOAL_SCORED,
            after=['process_goal']
        )

        self.machine.add_transition(
            'resume_play',
            [GameState.GOAL_SCORED, GameState.PAUSED],
            GameState.PLAYING,
            conditions=['is_puck_ready']
        )

        self.machine.add_transition(
            'end_period',
            GameState.PLAYING,
            GameState.PERIOD_END,
            after=['process_period_end']
        )

        self.machine.add_transition(
            'start_intermission',
            GameState.PERIOD_END,
            GameState.INTERMISSION
        )

        self.machine.add_transition(
            'next_period',
            GameState.INTERMISSION,
            GameState.PLAYING,
            conditions=['is_puck_ready', 'has_periods_remaining']
        )

        self.machine.add_transition(
            'end_game',
            [GameState.PLAYING, GameState.PERIOD_END],
            GameState.GAME_OVER,
            after=['process_game_end']
        )

        # Error handling transitions
        self.machine.add_transition(
            'handle_error',
            '*',  # from any state
            GameState.ERROR,
            before=['log_error'],
            after=['attempt_recovery']
        )

        self.machine.add_transition(
            'start_diagnostics',
            '*',
            GameState.DIAGNOSTICS
        )

        self.machine.add_transition(
            'exit_diagnostics',
            GameState.DIAGNOSTICS,
            GameState.INITIALIZING
        )

        # Pause handling
        self.machine.add_transition(
            'pause_game',
            GameState.PLAYING,
            GameState.PAUSED
        )

    def _validate_state_change(self, event):
        """Validate state change before it occurs"""
        try:
            if event.transition.dest == GameState.PLAYING:
                if not self._validate_game_conditions():
                    raise ValueError("Invalid game conditions")
            
            self.error_count = 0
            return True
            
        except Exception as e:
            logging.error(f"State change validation failed: {e}")
            self.error_count += 1
            if self.error_count >= self.game.settings.max_error_count:
                self.handle_error()
            return False

    def _validate_game_conditions(self):
        """Validate game conditions"""
        if not hasattr(self.game, 'gameplay'):
            return False
            
        gameplay = self.game.gameplay
        if not gameplay:
            return False

        # Check score validity
        if not (0 <= gameplay.score['red'] <= 99 and 
                0 <= gameplay.score['blue'] <= 99):
            return False
        
        # Check period validity
        if not (1 <= gameplay.period <= gameplay.max_periods):
            return False
            
        # Check clock validity
        if not (0 <= gameplay.clock <= self.game.settings.period_length):
            return False
            
        return True

    def _store_previous_state(self, event):
        """Store the previous state before transition"""
        self.previous_state = event.transition.source

    def _log_state_change(self, event):
        """Log state change after it occurs"""
        logging.info(f"Game state changed from {event.transition.source} to {event.transition.dest}")

    def _check_save_state(self, event):
        """Check if we should save state"""
        now = datetime.now()
        if (now - self.last_state_save).total_seconds() >= self.game.settings.state_save_interval:
            self.save_state()
            self.last_state_save = now

    def _update_history(self, event):
        """Update state history"""
        self.state_history.append({
            'time': datetime.now().isoformat(),
            'from_state': event.transition.source,
            'to_state': event.transition.dest
        })
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)

    def save_state(self):
        """Save current state to file"""
        if not self.game.gameplay:
            return

        state_data = {
            'state': self.state.value,
            'timestamp': datetime.now().isoformat(),
            'score': self.game.gameplay.score,
            'period': self.game.gameplay.period,
            'clock': self.game.gameplay.clock,
            'history': self.state_history
        }
        
        # Write to temporary file first
        temp_file = 'game_state.json.tmp'
        try:
            with open(temp_file, 'w') as f:
                json.dump(state_data, f)
            # Atomic rename
            os.rename(temp_file, 'game_state.json')
            logging.debug("Game state saved successfully")
        except Exception as e:
            logging.error(f"Failed to save game state: {e}")

    def load_state(self):
        """Load saved state if available"""
        try:
            with open('game_state.json', 'r') as f:
                state_data = json.load(f)
            
            if self._validate_state_data(state_data):
                self.state_history = state_data.get('history', [])
                return state_data
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Could not load saved state: {e}")
            return None

    def _validate_state_data(self, state_data):
        """Validate loaded state data"""
        required_keys = ['state', 'timestamp', 'score', 'period', 'clock']
        if not all(key in state_data for key in required_keys):
            return False
            
        # Check if state data is too old
        saved_time = datetime.fromisoformat(state_data['timestamp'])
        if (datetime.now() - saved_time).total_seconds() > 3600:  # 1 hour
            return False
            
        return True

    def attempt_recovery(self):
        """Attempt to recover from error state"""
        try:
            # Try to reset GPIO
            self.game.gpio_handler.reset_sensors()
            
            # Try to restore last known good state
            state_data = self.load_state()
            if state_data:
                self.game.gameplay.score = state_data['score']
                self.game.gameplay.period = state_data['period']
                self.game.gameplay.clock = state_data['clock']
                
                # Return to previous state
                if self.previous_state:
                    self.machine.set_state(self.previous_state)
                    logging.info("Successfully recovered from error state")
                    return True
            
            # If recovery fails, restart game
            logging.warning("Recovery failed, restarting game")
            self.machine.set_state(GameState.INITIALIZING)
            return False
            
        except Exception as e:
            logging.error(f"Recovery attempt failed: {e}")
            return False

    # State check conditions
    def is_puck_ready(self):
        """Check if puck is ready to start play"""
        return self.game.puck_possession in ['red', 'blue', 'in_play']

    def are_sensors_ready(self):
        """Check if all sensors are functioning"""
        return self.game.gpio_handler.are_sensors_healthy()

    def has_periods_remaining(self):
        """Check if there are periods remaining"""
        return self.game.gameplay.period < self.game.gameplay.max_periods

    # Event processors
    def process_goal(self):
        """Process goal scored event"""
        if self.game.gameplay:
            self.game.gameplay.handle_goal()

    def process_period_end(self):
        """Process period end event"""
        if self.game.gameplay:
            self.game.gameplay.handle_period_end()

    def process_game_end(self):
        """Process game end event"""
        if self.game.gameplay:
            self.game.gameplay.handle_game_end()

    def notify_game_start(self):
        """Notify game start"""
        logging.info("Game starting")
        if hasattr(self.game, 'sounds') and 'game_start' in self.game.sounds:
            self.game.sounds['game_start'].play()
