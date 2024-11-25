# base_game_mode.py

# Standard library imports
import pygame
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union, TypedDict
from uuid import uuid4
import math
import json
import os

# Local imports
from game_states import GameState
from player import Player
from rank_system import RankingSystem
from match_result_handler import MatchResult, MatchResultHandler
from utils import load_image, load_sound, load_font

# NEW: Added TypedDict for game state tracking
class GameStateData(TypedDict):
    """Type definition for game state data."""
    score: Dict[str, int]
    period: int
    clock: float
    possession: Optional[str]
    power_up_active: bool
    combo_active: bool

# NEW: Added game mode configuration
class GameModeConfig:
    """Configuration settings for game modes."""
    DEFAULT_PERIOD_LENGTH = 180  # 3 minutes
    DEFAULT_INTERMISSION_LENGTH = 60
    DEFAULT_OVERTIME_LENGTH = 180
    MIN_PERIOD_LENGTH = 60
    MAX_PERIOD_LENGTH = 600
    MIN_PERIODS = 1
    MAX_PERIODS = 7
    QUICK_RESPONSE_WINDOW = 10.0
    CRITICAL_MOMENT_THRESHOLD = 60.0

class BaseGameMode:
    """Base class for game modes with integrated player tracking and ranking."""
    
    def __init__(self, game: Any) -> None:
        """
        Initialize the base game mode.
        
        Args:
            game: The main game instance this mode is attached to.
        
        Raises:
            ValueError: If game settings are invalid.
        """
        try:
            self.game = game
            self.screen = game.screen
            self.settings = game.settings

            # Initialize fonts
            try:
                self.font_small = load_font('assets/fonts/Perfect DOS VGA 437.ttf', 24)
                self.font_large = load_font('assets/fonts/PressStart2P-Regular.ttf', 36)
                self.font_title = load_font('assets/fonts/VCR_OSD_MONO_1.001.ttf', 24)
                
                if not all([self.font_small, self.font_large, self.font_title]):
                    raise ValueError("Failed to load one or more fonts")
            except Exception as e:
                logging.error(f"Error loading fonts: {e}")
                raise

            # NEW: Initialize sounds
            self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
            self.sound_enabled = True
            self.load_sounds()

            # Initialize match-specific attributes
            self.score: Dict[str, int] = {'red': 0, 'blue': 0}
            self.period: int = 1
            self.max_periods: int = self._validate_periods(self.settings.max_periods)
            self.clock: float = self._validate_clock(self.settings.period_length)
            self.is_over: bool = False

            # Player and match tracking
            self.match_id = str(uuid4())
            self.red_player: Optional[Player] = None
            self.blue_player: Optional[Player] = None
            self.current_scorers: Dict[str, Player] = {}  # team: player
            self.match_start_time = datetime.now()

            # Last goal tracking
            self.last_goal_time: Optional[datetime] = None
            self.last_goal_team: Optional[str] = None
            self.last_goal_scorer: Optional[Player] = None

            # NEW: Enhanced state tracking
            self.game_state: GameStateData = {
                'score': self.score,
                'period': self.period,
                'clock': self.clock,
                'possession': None,
                'power_up_active': False,
                'combo_active': False
            }

            # Combo and power-up tracking
            self.combo_count: int = 0
            self.power_up_active: bool = False
            self.power_up_end_time: Optional[datetime] = None
            self.active_event: Optional[str] = None

            # Clock management
            self.in_overtime: bool = False
            self.intermission_clock: Optional[float] = None

            # Analytics display settings
            self.show_analytics: bool = True
            self.analytics_overlay_position: str = 'top-left'
            
            # NEW: Analytics state tracking
            self.analytics_update_timer: float = 0.0
            self.analytics_update_interval: float = 0.1  # 100ms updates
            self.last_analytics_update = datetime.now()

            # Load theme-specific analytics settings
            self._load_theme_analytics_settings()

            # NEW: Initialize game mode specific settings
            self._init_mode_settings()

            logging.info(f"BaseGameMode initialized with match ID: {self.match_id}")

        except Exception as e:
            logging.error(f"Failed to initialize BaseGameMode: {e}")
            raise

    # NEW: Added mode-specific initialization
    def _init_mode_settings(self) -> None:
        """Initialize mode-specific settings and configurations."""
        self.mode_config = GameModeConfig()
        self.mode_specific_stats: Dict[str, Any] = {}
        self.mode_modifiers: Dict[str, float] = {
            'scoring': 1.0,
            'power_up_frequency': 1.0,
            'combo_window': 1.0
        }

    def load_sounds(self) -> None:
        """
        Load all game sounds.
        
        Loads and initializes all sound effects used in the base game mode.
        Handles missing files gracefully and logs any loading errors.
        
        Sound effects include:
        - Goal scoring
        - Period start/end
        - Game over
        - Power-up activation
        - Critical moments
        """
        try:
            sound_files = {
                'goal': 'assets/sounds/goal_scored.wav',
                'period_start': 'assets/sounds/period_start.wav',
                'period_end': 'assets/sounds/period_end.wav',
                'game_over': 'assets/sounds/game_over.wav',
                'power_up': 'assets/sounds/power_up.wav',
                'critical': 'assets/sounds/critical_moment.wav'
            }
            
            for sound_name, file_path in sound_files.items():
                self.sounds[sound_name] = load_sound(file_path)
                
            logging.info("Game sounds loaded successfully")
        except Exception as e:
            logging.error(f"Error loading sounds: {e}")
            self.sounds = {}

    def play_sound(self, sound_name: str) -> None:
        """
        Play a sound effect if enabled.
        
        Args:
            sound_name: Name of the sound effect to play
            
        The method checks if:
        - Sound effects are enabled
        - The requested sound exists
        - The sound file loaded successfully
        
        Handles any playback errors gracefully.
        """
        try:
            if (self.sound_enabled and 
                sound_name in self.sounds and 
                self.sounds[sound_name]):
                self.sounds[sound_name].play()
        except Exception as e:
            logging.error(f"Error playing sound {sound_name}: {e}")

    def _validate_periods(self, periods: int) -> int:
        """
        Validate the number of periods.
        
        Args:
            periods: Number of periods to validate
            
        Returns:
            int: Valid number of periods
            
        Ensures the number of periods is:
        - Within allowed minimum/maximum
        - A positive integer
        - Compatible with game mode settings
        
        Logs a warning and returns default value if invalid.
        """
        if not isinstance(periods, int) or not GameModeConfig.MIN_PERIODS <= periods <= GameModeConfig.MAX_PERIODS:
            logging.warning(f"Invalid max_periods {periods}, defaulting to 3")
            return 3
        return periods

    def _validate_clock(self, period_length: float) -> float:
        """
        Validate the period length.
        
        Args:
            period_length: Length of period in seconds
            
        Returns:
            float: Valid period length
            
        Ensures period length is:
        - Within allowed minimum/maximum
        - A positive number
        - Compatible with game mode settings
        
        Logs a warning and returns default value if invalid.
        """
        if not isinstance(period_length, (int, float)) or not GameModeConfig.MIN_PERIOD_LENGTH <= period_length <= GameModeConfig.MAX_PERIOD_LENGTH:
            logging.warning(f"Invalid period_length {period_length}, defaulting to {GameModeConfig.DEFAULT_PERIOD_LENGTH}")
            return GameModeConfig.DEFAULT_PERIOD_LENGTH
        return float(period_length)

    def _load_theme_analytics_settings(self) -> None:
        """
        Load analytics display settings from the current theme.
        
        Loads and validates:
        - Analytics overlay position
        - Display preferences
        - Theme-specific analytics settings
        
        Settings are loaded from the theme configuration file
        and validated before being applied. Invalid settings
        fall back to defaults.
        """
        try:
            theme_config = self.game.theme_data
            if 'analytics' in theme_config:
                analytics_config = theme_config['analytics']
                self.analytics_overlay_position = analytics_config.get(
                    'overlay_position', 'top-left'
                )
                self.show_analytics = analytics_config.get(
                    'show_analytics', True
                )
                
                # NEW: Load additional analytics settings
                self.analytics_update_interval = analytics_config.get(
                    'update_interval', 0.1
                )
                self.analytics_display_options = analytics_config.get(
                    'display_options', {
                        'show_win_probability': True,
                        'show_momentum': True,
                        'show_patterns': True
                    }
                )
        except Exception as e:
            logging.error(f"Error loading theme analytics settings: {e}")
            # Fall back to defaults if loading fails
            self.analytics_overlay_position = 'top-left'
            self.show_analytics = True
            self.analytics_update_interval = 0.1
            self.analytics_display_options = {
                'show_win_probability': True,
                'show_momentum': True,
                'show_patterns': True
            }
            
    def set_players(self, red_player: Player, blue_player: Player) -> None:
        """
        Set the players for the current match.
        
        Args:
            red_player: Player on red team
            blue_player: Player on blue team
        """
        try:
            self.red_player = red_player
            self.blue_player = blue_player
            logging.info(f"Match players set - Red: {red_player.name}, Blue: {blue_player.name}")
        except Exception as e:
            logging.error(f"Error setting players: {e}")
            raise

    def get_current_player(self, team: str) -> Optional[Player]:
        """Get the current player for the specified team."""
        if team == 'red':
            return self.red_player
        elif team == 'blue':
            return self.blue_player
        return None

    def _get_player_positions(self) -> Dict[str, Tuple[int, int]]:
        """Calculate screen positions for player information display."""
        screen_width = self.settings.screen_width
        screen_height = self.settings.screen_height
        
        return {
            'red': (10, screen_height - 30),
            'blue': (screen_width - 200, screen_height - 30),
            'red_score': (screen_width // 4, 50),
            'blue_score': (3 * screen_width // 4, 50)
        }

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events specific to the game mode.
        
        This method processes various game events including:
        - Pause/unpause game
        - Toggle analytics overlay
        - Player-specific inputs
        - Special game events
        
        Args:
            event: The pygame event to handle
            
        Events can trigger:
        - State changes
        - Sound effects
        - Visual effects
        - Analytics updates
        - Player stat updates
        """
        try:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and self.game.state_machine.can('pause_game'):
                    self.game.state_machine.pause_game()
                    self._handle_pause_state(True)
                elif event.key == pygame.K_p and self.game.state_machine.can('resume_game'):
                    self.game.state_machine.resume_game()
                    self._handle_pause_state(False)
                elif event.key == pygame.K_a:  # Toggle analytics overlay
                    self.show_analytics = not self.show_analytics
                    
            # NEW: Handle player-specific events
            self._handle_player_events(event)
            
        except Exception as e:
            logging.error(f"Error handling event {event}: {e}")

    def _handle_pause_state(self, is_paused: bool) -> None:
        """
        Handle game pause/unpause state changes.
        
        Args:
            is_paused: True if game is being paused, False if resuming
            
        Updates:
        - Game state
        - UI elements
        - Sound states
        - Player statistics
        """
        try:
            if is_paused:
                self.play_sound('pause')
                # Store pause time for accurate stat tracking
                self._pause_time = datetime.now()
            else:
                self.play_sound('resume')
                # Adjust tracked times for pause duration
                if hasattr(self, '_pause_time'):
                    pause_duration = (datetime.now() - self._pause_time).total_seconds()
                    self._adjust_tracked_times(pause_duration)
        except Exception as e:
            logging.error(f"Error handling pause state: {e}")

    def _handle_player_events(self, event: pygame.event.Event) -> None:
        """
        Handle player-specific input events.
        
        Args:
            event: The pygame event to process
            
        Processes:
        - Player controls
        - Power-up activation
        - Special moves
        - Player interactions
        """
        # Implementation depends on specific player controls
        pass

    def update(self) -> None:
        """
        Update the game mode state.
        
        This method handles all per-frame updates including:
        - Clock management (game time and intermission)
        - Power-up status and duration
        - Combo timer updates
        - Player statistics tracking
        - Analytics data collection
        - Period transitions
        
        The update loop maintains game flow and ensures proper
        state transitions between periods, intermissions, and
        game end conditions.
        """
        try:
            if self.game.state_machine.state != GameState.PLAYING:
                return

            # Get delta time for this frame
            dt = self.game.clock.get_time() / 1000.0

            # Update timers and states
            self._update_timers(dt)
            self._update_game_state(dt)
            self._update_players(dt)
            
            # Update analytics
            self._update_analytics(dt)

            # Check for state transitions
            self._check_state_transitions()

        except Exception as e:
            logging.error(f"Error during update in BaseGameMode: {e}")

    def _update_timers(self, dt: float) -> None:
        """
        Update all game timers.
        
        Args:
            dt: Delta time since last frame in seconds
            
        Updates:
        - Game clock
        - Intermission timer
        - Power-up durations
        - Combo windows
        - Analytics timers
        """
        try:
            # Update appropriate clock based on game state
            if self.intermission_clock is not None:
                self.intermission_clock = max(0, self.intermission_clock - dt)
                if self.intermission_clock <= 0:
                    self._end_intermission()
            else:
                self.clock = max(0, self.clock - dt)

            # Update other timers
            if self.power_up_active and self.power_up_end_time:
                if datetime.now() >= self.power_up_end_time:
                    self._end_power_up()

            # Update analytics timer
            self.analytics_update_timer += dt
            if self.analytics_update_timer >= self.analytics_update_interval:
                self._process_analytics_update()
                self.analytics_update_timer = 0

        except Exception as e:
            logging.error(f"Error updating timers: {e}")

    def _update_game_state(self, dt: float) -> None:
        """
        Update core game state.
        
        Args:
            dt: Delta time since last frame in seconds
            
        Updates:
        - Score tracking
        - Period status
        - Player positions
        - Game events
        - Power-up states
        """
        try:
            # Update possession tracking
            self.game_state['possession'] = self.game.puck_possession
            
            # Update active states
            self.game_state['power_up_active'] = self.power_up_active
            self.game_state['combo_active'] = self.combo_count > 1
            
            # Check for critical moments
            if self._is_critical_moment():
                self._handle_critical_moment()

        except Exception as e:
            logging.error(f"Error updating game state: {e}")

    def _update_players(self, dt: float) -> None:
        """
        Update player states and statistics.
        
        Args:
            dt: Delta time since last frame in seconds
            
        Updates:
        - Player positions
        - Possession time
        - Zone time
        - Power-up usage
        - Other player metrics
        """
        try:
            if not (self.red_player and self.blue_player):
                return

            # Update possession stats
            if self.game.puck_possession == 'red':
                self.red_player.stats.possession_time += dt
            elif self.game.puck_possession == 'blue':
                self.blue_player.stats.possession_time += dt

            # Update power-up stats
            if self.power_up_active:
                player = self.get_current_player(self.game.puck_possession)
                if player:
                    player.stats.power_up_time += dt

        except Exception as e:
            logging.error(f"Error updating players: {e}")

    def _update_intermission(self, dt: float) -> None:
        """
        Update intermission timer and handle transitions.
        
        Args:
            dt: Delta time since last frame in seconds.
            
        The intermission period provides a break between game periods
        and handles proper game flow transitions.
        """
        self.intermission_clock = max(0, self.intermission_clock - dt)
        if self.intermission_clock <= 0:
            self.intermission_clock = None
            logging.info("Intermission ended")
            
            # Start new period
            if self.game.state_machine.can('resume_game'):
                self.game.state_machine.resume_game()

    def _update_game_clock(self, dt: float) -> None:
        """
        Update the main game clock.
        
        Args:
            dt: Delta time since last frame in seconds.
            
        Handles the main game time tracking and ensures accurate
        period timing.
        """
        self.clock = max(0, self.clock - dt)

    def _update_player_stats(self, dt: float) -> None:
        """
        Update player statistics during gameplay.
        
        Args:
            dt: Delta time since last frame in seconds.
            
        Tracks various player statistics including:
        - Time in possession
        - Time in offensive/defensive zones
        - Power-up effectiveness
        - Quick response times
        - Other gameplay metrics
        """
        if not (self.red_player and self.blue_player):
            return
            
        try:
            # Update possession time
            if self.game.puck_possession == 'red':
                self.red_player.stats.possession_time += dt
            elif self.game.puck_possession == 'blue':
                self.blue_player.stats.possession_time += dt
                
            # Update other time-based stats
            self._update_zone_times(dt)
            self._update_power_up_stats(dt)
            
        except Exception as e:
            logging.error(f"Error updating player stats: {e}")

    def _update_zone_times(self, dt: float) -> None:
        """
        Update time spent in different zones for each player.
        
        Args:
            dt: Delta time since last frame in seconds.
            
        Tracks offensive and defensive zone time for both players
        based on puck position.
        """
        # Implementation depends on how zones are tracked
        pass

    def _update_power_up_stats(self, dt: float) -> None:
        """
        Update power-up related statistics.
        
        Args:
            dt: Delta time since last frame in seconds.
            
        Tracks power-up effectiveness and usage patterns for
        player statistics.
        """
        if self.power_up_active and self.power_up_end_time:
            current_player = self.get_current_player(self.game.puck_possession)
            if current_player:
                current_player.stats.power_up_time += dt

    def handle_goal(self, team: str) -> None:
        """
        Handle goal scoring logic with player tracking and stats updates.
        
        This method processes all aspects of a scored goal including:
        - Score updates
        - Player statistics
        - Combo system
        - Power-up interactions
        - Analytics tracking
        - Rating adjustments
        
        Args:
            team: The team that scored ('red' or 'blue')
            
        Raises:
            ValueError: If the team name is invalid
            
        The goal's value may be modified by:
        - Active power-ups
        - Combo multipliers
        - Critical moment bonuses
        """
        try:
            if team not in ['red', 'blue']:
                raise ValueError(f"Invalid team name '{team}'")

            current_time = datetime.now()
            scoring_player = self.get_current_player(team)
            
            if not scoring_player:
                logging.warning(f"Goal scored by {team} but no player assigned")
                return

            # Calculate points and update score
            points = self._calculate_goal_points(team, current_time)
            self.score[team] += points
            
            # Update goal tracking
            self.last_goal_time = current_time
            self.last_goal_team = team
            self.last_goal_scorer = scoring_player
            
            # Update stats and create goal event
            self._process_goal_event(scoring_player, team, points)
            
            # Play goal sound
            self.play_sound('goal')
            
            # Update display
            self._show_goal_message(team, points)
            
            logging.info(
                f"Goal scored by {scoring_player.name} ({team}) - "
                f"Points: {points}, Score: Red {self.score['red']}, "
                f"Blue {self.score['blue']}"
            )

        except Exception as e:
            logging.error(f"Error handling goal for team '{team}': {e}")

    def _calculate_goal_points(self, team: str, current_time: datetime) -> int:
        """
        Calculate points for a goal including all bonuses.
        
        Args:
            team: Team that scored
            current_time: Time of goal
            
        Returns:
            int: Total points for the goal
            
        Points calculation considers:
        - Base goal value (1 point)
        - Combo multiplier if active
        - Power-up bonuses
        - Critical moment bonuses
        """
        try:
            points = 1  # Base goal value

            # Apply combo multiplier
            if self.settings.combo_goals_enabled and self.last_goal_time:
                time_since_last = (current_time - self.last_goal_time).total_seconds()
                if time_since_last <= self.settings.combo_time_window:
                    self.combo_count = min(self.combo_count + 1, self.settings.combo_max_stack)
                    if self.combo_count > 1:
                        points *= self.combo_count
                        self.active_event = f"COMBO x{self.combo_count}!"
                else:
                    self.combo_count = 1

            # Apply power-up multiplier
            if self.power_up_active and self.current_power_up == 'goal_multiplier':
                points *= 2

            # Apply critical moment bonus
            if self._is_critical_moment():
                points += 1
                self.active_event = "CRITICAL GOAL!"

            return points

        except Exception as e:
            logging.error(f"Error calculating goal points: {e}")
            return 1  # Return base points on error

    def _process_goal_event(self, 
                          scoring_player: Player, 
                          team: str, 
                          points: int) -> None:
        """
        Process all aspects of a goal event.
        
        Args:
            scoring_player: Player who scored
            team: Team that scored
            points: Points earned for the goal
            
        Updates:
        - Player statistics
        - Match history
        - Analytics data
        - Achievement tracking
        """
        try:
            # Update basic stats
            scoring_player.stats.total_goals += 1
            scoring_player.stats.total_points += points
            
            # Record goal in analytics
            if self.game.current_analysis:
                self.game.analytics.record_goal(
                    team=team,
                    player_id=scoring_player.id,
                    points=points,
                    game_state=self._get_current_game_state()
                )
            
            # Check for quick response
            if self.last_goal_time and self.last_goal_team != team:
                response_time = (datetime.now() - self.last_goal_time).total_seconds()
                if response_time <= GameModeConfig.QUICK_RESPONSE_WINDOW:
                    scoring_player.stats.quick_response_goals += 1
                    self.active_event = "QUICK RESPONSE!"
            
            # Update special stats
            if self.power_up_active:
                scoring_player.stats.power_up_goals += 1
            if self._is_critical_moment():
                scoring_player.stats.critical_goals += 1
            
            # Check achievements
            self._check_goal_achievements(scoring_player, points)

        except Exception as e:
            logging.error(f"Error processing goal event: {e}")

    def _is_critical_moment(self) -> bool:
        """
        Determine if the current game state is a critical moment.
        
        Returns:
            bool: True if current moment is critical
            
        Critical moments include:
        - Final minute of play
        - Close game (1 goal difference)
        - Potential comeback situations
        - High momentum situations
        """
        try:
            # Time-based critical moments
            if self.clock <= GameModeConfig.CRITICAL_MOMENT_THRESHOLD:
                return True

            # Score-based critical moments
            score_diff = abs(self.score['red'] - self.score['blue'])
            if score_diff <= 1:
                return True

            # Analytics-based critical moments
            if self.game.current_analysis:
                if self.game.current_analysis.get('is_critical_moment'):
                    return True

            return False

        except Exception as e:
            logging.error(f"Error checking critical moment: {e}")
            return False

    def _show_goal_message(self, team: str, points: int) -> None:
        """
        Display goal message and effects.
        
        Args:
            team: Team that scored
            points: Points earned for the goal
            
        Displays:
        - Goal announcement
        - Points earned
        - Special effects
        - Bonus indicators
        """
        try:
            message = f"{points} POINT{'S' if points > 1 else ''}"
            if self.combo_count > 1:
                message += f" - COMBO x{self.combo_count}!"
            elif self._is_critical_moment():
                message += " - CRITICAL GOAL!"
            elif self.power_up_active:
                message += " - POWER-UP BONUS!"
                
            self.active_event = message

        except Exception as e:
            logging.error(f"Error showing goal message: {e}")

    def _process_goal_analytics(self, team: str, points: int) -> None:
        """
        Process analytics data for a scored goal.
        
        Updates analytics system with goal information and
        retrieves updated analysis for game state tracking.
        
        Args:
            team: Team that scored
            points: Points earned for the goal
        """
        try:
            if not self.game.current_analysis:
                return
                
            # Record goal in analytics
            self.game.analytics.record_goal(
                team=team,
                points=points,
                time=self.clock,
                period=self.period,
                score=self.score.copy(),
                power_up_active=self.power_up_active,
                combo_count=self.combo_count
            )
            
            # Check for momentum shifts
            momentum = self.game.current_analysis['momentum']['current_state']
            if momentum['intensity'] in ['strong', 'overwhelming']:
                self._handle_momentum_shift(momentum)
                
        except Exception as e:
            logging.error(f"Error processing goal analytics: {e}")

    def handle_period_end(self) -> None:
        """
        Handle the end of a period with player stat tracking.
        
        This method manages:
        - Period transitions
        - Overtime handling
        - Intermission timing
        - Player statistics updates
        - Analytics processing
        - State machine transitions
        
        The flow changes based on:
        - Current period number
        - Score status (tie/non-tie)
        - Game mode settings
        - Player performance
        
        Also handles end-of-period achievements and stats.
        """
        try:
            # Play period end sound
            self.play_sound('period_end')
            
            # Update player period stats
            self._update_period_stats()

            if self.period < self.max_periods:
                self._start_next_period()
            elif not self.in_overtime and self.score['red'] == self.score['blue']:
                self._start_overtime()
            else:
                self._end_game()

        except Exception as e:
            logging.error(f"Error handling period end: {e}")

    def _start_next_period(self) -> None:
        """
        Start the next period of play.
        
        Handles:
        - Period counter increment
        - Clock reset
        - Intermission timing
        - State transitions
        - Analytics updates
        - Player stat resets
        """
        try:
            self.period += 1
            self.clock = self.settings.period_length
            self.intermission_clock = self.settings.intermission_length
            logging.info(f"Starting period {self.period}")
            
            # Reset period-specific states
            self.combo_count = 0
            self.power_up_active = False
            self.power_up_end_time = None
            
            if self.game.state_machine.can('start_intermission'):
                self.game.state_machine.start_intermission()
                self.play_sound('period_end')
                
            # Update analytics
            if self.game.current_analysis:
                self.game.analytics.on_period_start(self.period)

        except Exception as e:
            logging.error(f"Error starting next period: {e}")

    def _start_overtime(self) -> None:
        """
        Start overtime period.
        
        Handles:
        - Overtime clock setup
        - State transitions
        - Special overtime rules
        - Analytics updates
        - Player stat tracking
        """
        try:
            self.in_overtime = True
            self.clock = self.settings.overtime_length
            self.intermission_clock = self.settings.intermission_length
            logging.info("Game tied - going to overtime")
            
            # Reset overtime-specific states
            self.combo_count = 0
            self.power_up_active = False
            self.power_up_end_time = None
            
            if self.game.state_machine.can('start_intermission'):
                self.game.state_machine.start_intermission()
                self.play_sound('period_end')
                
            # Update analytics for overtime
            if self.game.current_analysis:
                self.game.analytics.on_overtime_start()

        except Exception as e:
            logging.error(f"Error starting overtime: {e}")

    def _update_period_stats(self) -> None:
        """
        Update player statistics at the end of a period.
        
        Updates:
        - Goals per period
        - Power-up efficiency
        - Zone time
        - Possession time
        - Period-specific achievements
        - Other period-based metrics
        """
        try:
            if not (self.red_player and self.blue_player):
                return
                
            period_data = {
                'red': {
                    'goals': self.score['red'],
                    'power_ups_used': self.red_player.stats.power_ups_used,
                    'possession_time': self.red_player.stats.possession_time,
                    'zone_time': getattr(self.red_player.stats, 'zone_time', 0),
                    'shots_taken': getattr(self.red_player.stats, 'shots_taken', 0)
                },
                'blue': {
                    'goals': self.score['blue'],
                    'power_ups_used': self.blue_player.stats.power_ups_used,
                    'possession_time': self.blue_player.stats.possession_time,
                    'zone_time': getattr(self.blue_player.stats, 'zone_time', 0),
                    'shots_taken': getattr(self.blue_player.stats, 'shots_taken', 0)
                }
            }
            
            # Store period stats for each player
            self.red_player.add_period_stats(self.period, period_data['red'])
            self.blue_player.add_period_stats(self.period, period_data['blue'])
            
            # Check period-specific achievements
            self._check_period_achievements()
            
        except Exception as e:
            logging.error(f"Error updating period stats: {e}")

    def _end_game(self) -> None:
        """
        Handle game end conditions and cleanup.
        
        Processes:
        - Final score
        - Match result
        - Player statistics
        - Achievements
        - Analytics data
        - State transitions
        """
        try:
            self.is_over = True
            if self.game.state_machine.can('end_game'):
                self.game.state_machine.end_game()
                
            # Determine winner
            if self.score['red'] > self.score['blue']:
                winner = 'red'
                winner_player = self.red_player
                loser_player = self.blue_player
            elif self.score['blue'] > self.score['red']:
                winner = 'blue'
                winner_player = self.blue_player
                loser_player = self.red_player
            else:
                winner = 'tie'
                winner_player = None
                loser_player = None

            # Create match result
            self._create_match_result(winner, winner_player, loser_player)
            
            # Play end game sound
            self.play_sound('game_over')
            
            # Update display
            self.active_event = (
                f"{winner.upper()} TEAM WINS!" 
                if winner != 'tie' else 
                "GAME ENDED IN A TIE!"
            )

            logging.info(
                f"Game ended. Winner: {winner}, "
                f"Final score - Red: {self.score['red']}, Blue: {self.score['blue']}"
            )

        except Exception as e:
            logging.error(f"Error ending game: {e}")

    def _create_match_result(self, 
                           winner: str,
                           winner_player: Optional[Player],
                           loser_player: Optional[Player]) -> None:
        """
        Create and process the match result.
        
        Args:
            winner: Winning team ('red', 'blue', or 'tie')
            winner_player: The winning Player object
            loser_player: The losing Player object
            
        Creates and processes:
        - Match result record
        - Rating updates
        - Achievement checks
        - Analytics summary
        - Match history
        """
        try:
            match_result = MatchResult(
                match_id=self.match_id,
                red_player=self.red_player,
                blue_player=self.blue_player,
                winner=winner,
                red_score=self.score['red'],
                blue_score=self.score['blue'],
                match_date=datetime.now(),
                game_mode=self.__class__.__name__,
                analytics_data=self.game.current_analysis
            )

            # Process match result if not a tie
            if winner != 'tie' and winner_player and loser_player:
                self.game.match_result_handler.process_result(
                    winner=winner_player,
                    loser=loser_player,
                    match_result=match_result
                )

            # Final analytics update
            if self.game.current_analysis:
                self.game.analytics.on_game_end(match_result)

            # Check end-game achievements
            self._check_end_game_achievements()

        except Exception as e:
            logging.error(f"Error creating match result: {e}")

    def _update_final_player_stats(self,
                                 player: Player,
                                 team: str,
                                 match_duration: float) -> None:
        """
        Update final match statistics for a player.
        
        Args:
            player: Player to update
            team: Player's team ('red' or 'blue')
            match_duration: Total match duration in seconds
            
        Updates:
        - Match completion stats
        - Efficiency metrics
        - Historical averages
        - Achievement progress
        """
        try:
            stats = player.stats
            
            # Update match stats
            stats.matches_played += 1
            if self.score[team] > self.score['blue' if team == 'red' else 'red']:
                stats.wins += 1
            elif self.score[team] < self.score['blue' if team == 'red' else 'red']:
                stats.losses += 1
            else:
                stats.draws += 1
                
            # Calculate efficiency metrics
            if stats.power_ups_collected > 0:
                stats.power_up_efficiency = (
                    stats.power_up_goals / stats.power_ups_collected
                )
                
            # Update averages
            stats.avg_goals_per_match = (
                stats.total_goals / stats.matches_played
            )
            
            stats.avg_points_per_match = (
                stats.total_points / stats.matches_played
            )
            
        except Exception as e:
            logging.error(f"Error updating final stats for {player.name}: {e}")

    def draw(self) -> None:
        """
        Draw all game elements including player information.
        
        This method handles the rendering of:
        - Score display
        - Player information
        - Game state indicators
        - Power-up status
        - Analytics overlay
        - Active events
        - Time and period information
        - Player stats and ranks
        
        The display updates dynamically based on:
        - Current game state
        - Player performance
        - Analytics insights
        - Special events
        """
        try:
            # Draw base game elements
            self._draw_scores()
            self._draw_period_info()
            self._draw_game_status()
            self._draw_player_info()
            
            # Draw conditional elements
            if self.power_up_active:
                self._draw_power_up_status()
            if self.active_event:
                self._draw_active_event()
            if self.show_analytics and self.game.current_analysis:
                self._draw_analytics_overlay()

        except Exception as e:
            logging.error(f"Error during draw in BaseGameMode: {e}")

    def _draw_scores(self) -> None:
        """
        Draw the current score with player information.
        
        Displays:
        - Team scores
        - Player names
        - Current ranks
        - Active bonuses
        - Score animations
        """
        try:
            score_text = self.font_large.render(
                f"Red: {self.score['red']}  Blue: {self.score['blue']}",
                True,
                (255, 255, 255)
            )
            score_rect = score_text.get_rect(center=(self.settings.screen_width // 2, 50))
            self.screen.blit(score_text, score_rect)
            
            # Draw player names and ranks if available
            if self.red_player:
                self._draw_player_score_info(self.red_player, 'red')
            if self.blue_player:
                self._draw_player_score_info(self.blue_player, 'blue')

        except Exception as e:
            logging.error(f"Error drawing scores: {e}")

    def _draw_player_score_info(self, player: Player, team: str) -> None:
        """
        Draw detailed player information next to score.
        
        Args:
            player: Player to display info for
            team: Player's team ('red' or 'blue')
            
        Displays:
        - Player name
        - Current rank
        - Recent achievements
        - Active bonuses
        """
        try:
            positions = self._get_player_positions()
            pos = positions[team]
            
            # Get player's rank
            rank_number, rank = self.game.ranking_system.elo_to_visible_rank(
                player.elo,
                player.stats.total_matches
            )
            
            # Create player info text
            player_text = self.font_small.render(
                f"{player.name} (Rank {rank_number})",
                True,
                (255, 50, 50) if team == 'red' else (50, 50, 255)
            )
            
            # Position based on team
            if team == 'red':
                self.screen.blit(player_text, pos)
            else:
                text_rect = player_text.get_rect(right=self.settings.screen_width - 10)
                text_rect.topleft = pos
                self.screen.blit(player_text, text_rect)

        except Exception as e:
            logging.error(f"Error drawing player score info: {e}")

    def _draw_period_info(self) -> None:
        """
        Draw period and time information.
        
        Displays:
        - Current period
        - Time remaining
        - Overtime indicator
        - Intermission status
        - Critical moment warnings
        """
        try:
            # Draw period text
            period_text = self._get_period_display_text()
            period_surface = self.font_small.render(period_text, True, (255, 255, 255))
            period_rect = period_surface.get_rect(
                center=(self.settings.screen_width // 2, 100)
            )
            self.screen.blit(period_surface, period_rect)

            # Draw time display
            time_text = self._get_time_display_text()
            time_color = (255, 255, 0) if self.clock <= 60 else (255, 255, 255)
            time_surface = self.font_small.render(time_text, True, time_color)
            time_rect = time_surface.get_rect(
                center=(self.settings.screen_width // 2, 130)
            )
            self.screen.blit(time_surface, time_rect)

        except Exception as e:
            logging.error(f"Error drawing period info: {e}")

    def _get_period_display_text(self) -> str:
        """Get the appropriate period display text."""
        if self.in_overtime:
            return "OVERTIME"
        return f"Period: {self.period}/{self.max_periods}"

    def _get_time_display_text(self) -> str:
        """Get the appropriate time display text."""
        if self.intermission_clock is not None:
            return f"Intermission: {int(self.intermission_clock)}s"
        if self.clock <= 60:
            return f"FINAL MINUTE: {int(self.clock)}s"
        return f"Time Remaining: {int(self.clock)}s"

    def _draw_game_status(self) -> None:
        """
        Draw current game status information.
        
        Displays:
        - Puck possession
        - Current events
        - Game state
        - Active modifiers
        - Special conditions
        """
        try:
            # Draw possession info
            possession = self.game.puck_possession
            possession_text = (
                f"Puck Possession: {possession.capitalize()}" 
                if possession else 
                "Puck Possession: Unknown"
            )
            possession_surface = self.font_small.render(
                possession_text,
                True,
                (255, 255, 255)
            )
            possession_rect = possession_surface.get_rect(
                center=(self.settings.screen_width // 2, 160)
            )
            self.screen.blit(possession_surface, possession_rect)
            
            # Draw possession indicator if applicable
            if possession and possession in ['red', 'blue']:
                player = self.get_current_player(possession)
                if player:
                    self._draw_possession_indicator(player, possession)

        except Exception as e:
            logging.error(f"Error drawing game status: {e}")

    def _draw_possession_indicator(self, player: Player, team: str) -> None:
        """
        Draw an indicator showing which player has possession.
        
        Args:
            player: Player with possession
            team: Player's team ('red' or 'blue')
            
        Displays a visual indicator of:
        - Current possession
        - Duration of possession
        - Player-specific effects
        """
        try:
            positions = self._get_player_positions()
            pos = positions[team]
            
            # Draw indicator arrow
            indicator = "▼"
            indicator_surface = self.font_small.render(
                indicator,
                True,
                (255, 50, 50) if team == 'red' else (50, 50, 255)
            )
            
            if team == 'red':
                self.screen.blit(indicator_surface, (pos[0], pos[1] + 20))
            else:
                indicator_rect = indicator_surface.get_rect(
                    right=self.settings.screen_width - 10,
                    top=pos[1] + 20
                )
                self.screen.blit(indicator_surface, indicator_rect)

        except Exception as e:
            logging.error(f"Error drawing possession indicator: {e}")

    def cleanup(self) -> None:
        """
        Clean up resources and finalize match data.
        
        This method:
        - Saves final match statistics
        - Updates player rankings
        - Stores match history
        - Cleans up resources
        - Saves analytics data
        - Processes achievements
        - Ensures proper resource deallocation
        """
        try:
            # Finalize match statistics
            self._finalize_match_stats()
            
            # Save match result if valid game
            if self.red_player and self.blue_player:
                self.game.match_result_handler.save_match(self.match_id)
            
            # Clear resources
            self._clear_game_resources()
            
            logging.info(f"BaseGameMode cleanup completed for match {self.match_id}")
            
        except Exception as e:
            logging.error(f"Error during cleanup in BaseGameMode: {e}")
        finally:
            # Ensure critical resources are cleared
            self._ensure_cleanup()

    def _clear_game_resources(self) -> None:
        """Clear all game resources safely."""
        try:
            self.power_up_active = False
            self.power_up_end_time = None
            self.active_event = None
            self.combo_count = 0
            
            # Clear sound resources
            for sound in self.sounds.values():
                if sound:
                    sound.stop()
                    
        except Exception as e:
            logging.error(f"Error clearing game resources: {e}")

    def _ensure_cleanup(self) -> None:
        """Ensure critical resources are properly cleaned up."""
        try:
            # Clear player references
            self.red_player = None
            self.blue_player = None
            
            # Clear any remaining sounds
            self.sounds.clear()
            
            # Clear any remaining events
            self.active_event = None
            
        except Exception as e:
            logging.error(f"Error in final cleanup: {e}")
