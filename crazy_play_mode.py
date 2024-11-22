# crazy_play_mode.py

from typing import Dict, List, Optional, Tuple, Union, Any
import pygame
import random
import logging
import os
from datetime import datetime, timedelta
from base_game_mode import BaseGameMode
from utils import load_sound, load_image

class CrazyPlayMode(BaseGameMode):
    """
    Enhanced Crazy Play mode with exciting but physically implementable features.
    
    This game mode extends the base bubble hockey gameplay with additional features
    while ensuring all features are physically possible on the actual hardware.
    
    Features:
    - Bonus points and multipliers based on timing and skill
    - Quick strike challenges that encourage fast play
    - Combo scoring system for consecutive goals
    - Comeback mechanics to keep games exciting
    - Final minute frenzy mode for intense endings
    - Enhanced visual and sound effects
    
    Game Balance:
    - All timing windows account for physical player movement
    - Bonus opportunities require skill but remain achievable
    - Score multipliers are capped to maintain competitive balance
    - Special events are timed to avoid interference with normal play
    
    Hardware Considerations:
    - All features work within the physical constraints of the table
    - Sensor timing accounts for mechanical delays
    - Effects and sounds complement but don't overshadow gameplay
    
    Attributes:
        MAX_PARTICLES (int): Maximum number of particles to render (default: 100)
        COMBO_WINDOW (float): Time window in seconds for combo scoring (default: 10.0)
        MAX_COMBO_MULTIPLIER (int): Maximum combo multiplier (default: 3)
        SOUND_COOLDOWN (float): Minimum time between sounds in seconds (default: 3.0)
        
    Note:
        All timing-based features account for the physical limitations of the
        bubble hockey table, ensuring features don't encourage unsafe play.
    """
    
    # Class constants with clear documentation
    MAX_PARTICLES: int = 100  # Performance-optimized particle limit
    COMBO_WINDOW: float = 10.0  # Realistic window for physical play
    MAX_COMBO_MULTIPLIER: int = 3  # Balance between excitement and fairness
    SOUND_COOLDOWN: float = 3.0  # Prevent sound overlap and spam

    def __init__(self, game):
        """
        Initialize Crazy Play mode with enhanced features.
        
        Args:
            game: The main game instance this mode is attached to
            
        Raises:
            pygame.error: If critical assets fail to load
            OSError: If required directories are not accessible
            ValueError: If game settings are invalid
        """
        try:
            super().__init__(game)
            
            # Core scoring features with validation
            self.current_goal_value: int = self._validate_goal_value(1)
            self.first_goal_opportunity: bool = True
            self.first_goal_window: float = self._validate_window(
                self.settings.period_length * 0.15
            )
            self.frenzy_window: float = self._validate_window(
                max(30, self.settings.period_length * 0.1)
            )
            
            # Initialize timing trackers
            self.last_goal_time: Optional[datetime] = None
            self.combo_count: int = 0
            
            # Challenge states with clear typing
            self.quick_strike_active: bool = False
            self.quick_strike_deadline: Optional[datetime] = None
            self.frenzy_mode: bool = False
            
            # Event timing system
            self._init_event_system()
            
            # Override base settings with validation
            self.max_periods = self._validate_periods(5)
            self.clock = self._validate_clock(self.settings.period_length)
            
            # Visual effects system
            self._init_visual_systems()
            
            # Statistics tracking
            self.stats = self._initialize_stats()
            
            # Asset loading with error handling
            self._load_all_assets()
            
            # Analytics system initialization
            self._init_analytics_system()
            
            # Comeback tracking system
            self._init_comeback_system()
            
            logging.info("CrazyPlayMode initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize CrazyPlayMode: {e}")
            raise

    def _init_event_system(self) -> None:
        """Initialize the event timing system with validated defaults."""
        self.next_event_time = datetime.now() + timedelta(seconds=15)
        self.event_duration: Optional[datetime] = None
        self.last_sound_time = datetime.now()
        self.last_random_sound_time = datetime.now().timestamp()
        self.next_random_sound_interval = self._get_validated_sound_interval()

    def _init_visual_systems(self) -> None:
        """Initialize visual effect systems with memory management."""
        self.visual_effects: List[Dict[str, Any]] = []
        self.particle_systems: List[Dict[str, Any]] = []
        self.active_animations: List[Dict[str, Any]] = []
        
        # Set reasonable limits for memory management
        self._max_effects = 10
        self._max_particles_per_system = self.MAX_PARTICLES // 2

    def _init_analytics_system(self) -> None:
        """Initialize analytics system with validated parameters."""
        self.show_analytics = True
        self.analytics_overlay_position = 'dynamic'
        self.analytics_alert_queue: List[Dict[str, Any]] = []
        self.last_analytics_update = datetime.now()
        self.analytics_update_interval = self._validate_update_interval(0.5)
        self.last_probabilities = {'red': 0.5, 'blue': 0.5}

    def _init_comeback_system(self) -> None:
        """Initialize comeback tracking system."""
        self.comeback_active = False
        self.comeback_start_score: Optional[Dict[str, int]] = None
        self.comeback_threshold = 3  # Goals needed for comeback
        self.comeback_timeout = 120.0  # Seconds to complete comeback

    def _load_all_assets(self) -> None:
        """
        Load all game assets with comprehensive error handling.
        
        Raises:
            pygame.error: If critical assets fail to load
            OSError: If asset directories are not accessible
        """
        try:
            self.load_assets()  # Visual assets
            self.load_crazy_sounds()  # Sound assets
        except Exception as e:
            logging.error(f"Asset loading failed: {e}")
            self._init_fallback_assets()
            raise

    def _initialize_stats(self) -> Dict[str, int]:
        """
        Initialize statistics tracking with zero values.
        
        Returns:
            Dict[str, int]: Initialized statistics dictionary
        """
        return {
            'bonus_points_earned': 0,
            'quick_strikes_attempted': 0,
            'quick_strikes_successful': 0,
            'frenzy_goals': 0,
            'comeback_goals': 0,
            'critical_goals': 0,
            'max_combo': 0,
            'total_bonus_multiplier': 0,
            'comebacks_started': 0,
            'comebacks_completed': 0,
            'frenzy_mode_activations': 0,
            'perfect_strikes': 0  # Goals scored within 2 seconds of opportunity
        }

    # Validation methods
    def _validate_goal_value(self, value: int) -> int:
        """Validate goal value is within acceptable range."""
        if not 1 <= value <= 5:
            logging.warning(f"Invalid goal value {value}, using default of 1")
            return 1
        return value

    def _validate_window(self, seconds: float) -> float:
        """Validate time window is physically achievable."""
        min_window = 5.0  # Minimum realistic window
        max_window = self.settings.period_length * 0.25  # Max 25% of period
        if not min_window <= seconds <= max_window:
            logging.warning(f"Invalid window {seconds}, clamping to range")
            return max(min_window, min(seconds, max_window))
        return seconds

    def _validate_periods(self, periods: int) -> int:
        """Validate number of periods is reasonable."""
        if not 3 <= periods <= 7:
            logging.warning(f"Invalid periods {periods}, using default of 5")
            return 5
        return periods

    def _validate_clock(self, time: float) -> float:
        """Validate clock time is within acceptable range."""
        if not 60 <= time <= 600:
            logging.warning(f"Invalid clock time {time}, using default of 180")
            return 180.0
        return float(time)

    def _validate_update_interval(self, interval: float) -> float:
        """Validate update interval is reasonable."""
        if not 0.1 <= interval <= 2.0:
            logging.warning(f"Invalid update interval {interval}, using default of 0.5")
            return 0.5
        return interval

    def _get_validated_sound_interval(self) -> float:
        """Get validated random sound interval."""
        min_interval = max(5.0, self.settings.random_sound_min_interval)
        max_interval = min(30.0, self.settings.random_sound_max_interval)
        return random.uniform(min_interval, max_interval)

    def load_assets(self) -> None:
        """
        Load all visual assets with comprehensive error handling.
        
        This method handles loading of all visual elements including:
        - Background and overlay images
        - UI indicators and frames
        - Particle effect sprites
        - Animation sequences
        
        Each asset category has dedicated error handling and fallbacks.
        
        Raises:
            pygame.error: If critical assets cannot be loaded
            OSError: If asset directories are inaccessible
        """
        try:
            self._load_background()
            self._load_overlays()
            self._load_indicators()
            self._load_particles()
            logging.info("Visual assets loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load visual assets: {e}")
            self._init_fallback_assets()
            raise

    def _load_background(self) -> None:
        """
        Load background assets with error tracking.
        
        Raises:
            pygame.error: If background image fails to load
        """
        try:
            path = os.path.join('assets', 'crazy_play', 'images', 'background.png')
            self.background = load_image(path)
            if self.background is None:
                raise pygame.error(f"Failed to load background from {path}")
            
            # Scale background to screen size if needed
            if (self.background.get_width() != self.settings.screen_width or 
                self.background.get_height() != self.settings.screen_height):
                self.background = pygame.transform.scale(
                    self.background,
                    (self.settings.screen_width, self.settings.screen_height)
                )
        except Exception as e:
            logging.error(f"Background load failed: {e}")
            self.background = self._create_fallback_surface(
                (self.settings.screen_width, self.settings.screen_height),
                self.settings.bg_color
            )

    def _load_overlays(self) -> None:
        """
        Load overlay assets with individual error handling.
        
        Loads various overlay images used for special effects and UI.
        Creates appropriate fallbacks for each failed load.
        """
        self.overlays: Dict[str, Optional[pygame.Surface]] = {}
        overlay_specs = {
            'frenzy': ('frenzy.png', (255, 0, 0, 64)),
            'quick_strike': ('quick_strike.png', (255, 255, 0, 64)),
            'critical_moment': ('critical_moment.png', (255, 0, 0, 96)),
            'comeback': ('comeback.png', (255, 215, 0, 64))
        }

        for name, (filename, fallback_color) in overlay_specs.items():
            try:
                path = os.path.join('assets', 'crazy_play', 'images', filename)
                overlay = load_image(path)
                if overlay is None:
                    raise pygame.error(f"Failed to load overlay {filename}")
                self.overlays[name] = overlay
            except Exception as e:
                logging.warning(f"Overlay {name} load failed: {e}")
                self.overlays[name] = self._create_fallback_surface(
                    (self.settings.screen_width, self.settings.screen_height),
                    fallback_color
                )

    def _load_indicators(self) -> None:
        """
        Load UI indicator assets with fallbacks.
        
        Creates fallback indicators for score, bonus, and status displays
        if image loading fails.
        """
        try:
            base_path = os.path.join('assets', 'crazy_play', 'images')
            
            # Load UI frames and indicators
            self.ui_elements = {
                'bonus': load_image(os.path.join(base_path, 'bonus.png')),
                'analytics': load_image(os.path.join(base_path, 'analytics_frame.png')),
                'momentum': load_image(os.path.join(base_path, 'momentum.png')),
                'comeback': load_image(os.path.join(base_path, 'comeback.png'))
            }
            
            # Validate each loaded element
            for name, element in self.ui_elements.items():
                if element is None:
                    raise pygame.error(f"Failed to load UI element: {name}")
                    
        except Exception as e:
            logging.error(f"UI element loading failed: {e}")
            self._init_fallback_indicators()

    def _load_particles(self) -> None:
        """
        Load particle effect assets with size optimization.
        
        Creates and caches appropriately sized particle sprites for
        various effects. Includes error handling and fallback generation.
        """
        particle_types = {
            'spark': {'size': (8, 8), 'color': (255, 255, 0)},
            'star': {'size': (12, 12), 'color': (255, 255, 255)},
            'trail': {'size': (6, 6), 'color': (255, 140, 0)},
            'comeback': {'size': (10, 10), 'color': (255, 215, 0)}
        }
        
        self.particle_images = {}
        base_path = os.path.join('assets', 'crazy_play', 'particles')
        
        for p_type, specs in particle_types.items():
            try:
                path = os.path.join(base_path, f"{p_type}.png")
                image = load_image(path)
                
                if image is not None:
                    # Scale particle image if needed
                    if (image.get_width() != specs['size'][0] or 
                        image.get_height() != specs['size'][1]):
                        image = pygame.transform.scale(image, specs['size'])
                    self.particle_images[p_type] = image
                else:
                    raise pygame.error(f"Failed to load particle: {p_type}")
                    
            except Exception as e:
                logging.warning(f"Particle {p_type} load failed: {e}")
                self.particle_images[p_type] = self._create_fallback_particle(
                    p_type, specs['size'], specs['color']
                )

    def load_crazy_sounds(self) -> None:
        """
        Load sound effects with volume normalization.
        
        Loads and configures all sound effects, ensuring consistent
        volume levels and proper error handling.
        """
        sound_specs = {
            'bonus': {'file': 'bonus_activated.wav', 'volume': 0.7},
            'quick_strike': {'file': 'quick_strike.wav', 'volume': 0.8},
            'combo': {'file': 'combo_goal.wav', 'volume': 0.8},
            'frenzy': {'file': 'frenzy.wav', 'volume': 0.9},
            'comeback_started': {'file': 'comeback_started.wav', 'volume': 0.8},
            'comeback_complete': {'file': 'comeback_complete.wav', 'volume': 1.0}
        }
        
        self.crazy_sounds = {}
        
        for sound_name, specs in sound_specs.items():
            try:
                path = os.path.join('assets', 'sounds', specs['file'])
                sound = load_sound(path)
                
                if sound is not None:
                    sound.set_volume(specs['volume'])
                    self.crazy_sounds[sound_name] = sound
                else:
                    raise pygame.error(f"Failed to load sound: {sound_name}")
                    
            except Exception as e:
                logging.warning(f"Sound {sound_name} load failed: {e}")
                self.crazy_sounds[sound_name] = None

    def _create_fallback_surface(
        self, 
        size: Tuple[int, int], 
        color: Union[Tuple[int, int, int], Tuple[int, int, int, int]]
    ) -> pygame.Surface:
        """
        Create a fallback surface with specified properties.
        
        Args:
            size: Dimensions as (width, height)
            color: RGB or RGBA color tuple
            
        Returns:
            pygame.Surface: Basic colored surface
        """
        if len(color) == 4:  # RGBA color
            surface = pygame.Surface(size, pygame.SRCALPHA)
        else:  # RGB color
            surface = pygame.Surface(size)
        surface.fill(color)
        return surface

    def _create_fallback_particle(
        self,
        particle_type: str,
        size: Tuple[int, int],
        color: Tuple[int, int, int]
    ) -> pygame.Surface:
        """
        Create a fallback particle sprite.
        
        Args:
            particle_type: Type of particle to create
            size: Dimensions of particle sprite
            color: RGB color tuple for particle
            
        Returns:
            pygame.Surface: Basic particle sprite
        """
        surface = pygame.Surface(size, pygame.SRCALPHA)
        
        if particle_type in ['spark', 'star']:
            # Draw a star shape
            points = []
            center = (size[0] // 2, size[1] // 2)
            for i in range(8):
                angle = i * (2 * math.pi / 8)
                radius = size[0] // 2 - 1
                x = center[0] + int(math.cos(angle) * radius)
                y = center[1] + int(math.sin(angle) * radius)
                points.append((x, y))
            pygame.draw.polygon(surface, color, points)
        else:
            # Draw a simple circle
            radius = min(size[0], size[1]) // 2 - 1
            pygame.draw.circle(
                surface,
                color,
                (size[0] // 2, size[1] // 2),
                radius
            )
            
        return surface

    def _init_fallback_assets(self) -> None:
        """Initialize complete set of fallback assets."""
        # Create basic background
        self.background = self._create_fallback_surface(
            (self.settings.screen_width, self.settings.screen_height),
            self.settings.bg_color
        )
        
        # Initialize overlay fallbacks
        self._init_fallback_overlays()
        
        # Initialize indicator fallbacks
        self._init_fallback_indicators()
        
        # Clear particle images
        self.particle_images = {}
        
        logging.warning("Using fallback assets - visual quality will be reduced")

    def _init_fallback_overlays(self) -> None:
        """Initialize basic overlay surfaces."""
        screen_size = (self.settings.screen_width, self.settings.screen_height)
        
        self.overlays = {
            'frenzy': self._create_fallback_surface(screen_size, (255, 0, 0, 64)),
            'quick_strike': self._create_fallback_surface(screen_size, (255, 255, 0, 64)),
            'critical_moment': self._create_fallback_surface(screen_size, (255, 0, 0, 96)),
            'comeback': self._create_fallback_surface(screen_size, (255, 215, 0, 64))
        }

    def _init_fallback_indicators(self) -> None:
        """Initialize basic indicator surfaces."""
        self.ui_elements = {
            'bonus': self._create_fallback_surface((100, 50), (255, 215, 0)),
            'analytics': self._create_fallback_surface((200, 150), (0, 0, 0, 180)),
            'momentum': self._create_fallback_surface((100, 20), (255, 140, 0)),
            'comeback': self._create_fallback_surface((150, 40), (255, 215, 0))
        }

    def update(self) -> None:
        """
        Update game state for the current frame.
        
        Handles all state updates including:
        - Game mode specific features
        - Analytics updates
        - Visual effects
        - Sound effects
        - Event timing
        
        This method ensures all updates occur in a specific order to maintain
        game consistency and prevent race conditions.
        """
        if self.game.state_machine.state != self.game.state_machine.states.PLAYING:
            return

        # Get time values once for consistent updates
        current_time = datetime.now()
        dt = self.game.clock.get_time() / 1000.0  # Delta time in seconds

        try:
            # Core gameplay updates
            self._update_gameplay_state(current_time, dt)
            
            # Systems updates in priority order
            self._update_analytics(current_time)
            self._update_visual_effects(dt)
            self._update_sound_system(current_time)
            self._update_events(current_time)
            
            # Parent class updates
            super().update()
            
        except Exception as e:
            logging.error(f"Error in game update: {e}")
            # Continue game loop but log the error

    def _update_gameplay_state(self, current_time: datetime, dt: float) -> None:
        """
        Update core gameplay mechanics and states.
        
        Args:
            current_time: Current datetime for timing calculations
            dt: Time elapsed since last frame in seconds
        """
        # Update clock
        if not self.intermission_clock:
            self.clock = max(0, self.clock - dt)

        # Check for final frenzy mode
        if not self.frenzy_mode and self.clock <= self.frenzy_window:
            self._start_final_minute_frenzy()
            
        # Check if first goal opportunity has expired
        if self.first_goal_opportunity:
            time_elapsed = self.settings.period_length - self.clock
            if time_elapsed > self.first_goal_window:
                self.first_goal_opportunity = False
                logging.info("First goal opportunity expired")
        
        # Update quick strike challenge
        if self.quick_strike_active:
            if current_time >= self.quick_strike_deadline:
                self._end_quick_strike(success=False)
            
        # Update event duration
        if self.event_duration and current_time >= self.event_duration:
            self._end_current_event()

        # Update comeback tracking
        if self.comeback_active:
            self._update_comeback_status()

    def _update_analytics(self, current_time: datetime) -> None:
        """
        Update analytics state and generate insights.
        
        Args:
            current_time: Current datetime for timing calculations
        """
        if current_time - self.last_analytics_update >= timedelta(
            seconds=self.analytics_update_interval
        ):
            if not self.game.current_analysis:
                return
                
            analysis = self.game.current_analysis
            
            # Process momentum shifts
            if 'momentum' in analysis:
                momentum = analysis['momentum']['current_state']
                if momentum['team'] and momentum['intensity'] in ['strong', 'overwhelming']:
                    self._handle_momentum_shift(momentum)
            
            # Process win probability changes
            if 'win_probability' in analysis:
                self._handle_probability_changes(analysis['win_probability'])
            
            # Process pattern detection
            if 'patterns' in analysis:
                self._handle_scoring_patterns(analysis['patterns'])
                
            self.last_analytics_update = current_time

    def _update_events(self, current_time: datetime) -> None:
        """
        Update event system state.
        
        Args:
            current_time: Current datetime for timing calculations
        """
        # Check for new random events
        if current_time >= self.next_event_time and not self.frenzy_mode:
            self._trigger_random_event()
            # Set next event time (between 20-40 seconds)
            self.next_event_time = current_time + timedelta(
                seconds=random.randint(20, 40)
            )

    def _trigger_random_event(self) -> None:
        """
        Trigger a random game event.
        
        Randomly selects and initiates one of the available special events,
        with weights adjusted based on game state and recent events.
        """
        # Define event weights based on game state
        weights = self._calculate_event_weights()
        
        events = [
            (self._start_quick_strike, weights['quick_strike']),
            (self._activate_bonus_goal, weights['bonus_goal']),
            (self._start_combo_challenge, weights['combo'])
        ]
        
        # Select event based on weights
        total_weight = sum(weight for _, weight in events)
        random_val = random.uniform(0, total_weight)
        
        current_weight = 0
        selected_event = None
        
        for event, weight in events:
            current_weight += weight
            if random_val <= current_weight:
                selected_event = event
                break
        
        if selected_event:
            selected_event()

    def _calculate_event_weights(self) -> Dict[str, float]:
        """
        Calculate event weights based on game state.
        
        Returns:
            Dict[str, float]: Weight values for each event type
        """
        weights = {
            'quick_strike': 1.0,
            'bonus_goal': 1.0,
            'combo': 1.0
        }
        
        # Adjust weights based on score difference
        score_diff = abs(self.score['red'] - self.score['blue'])
        if score_diff >= 3:
            # Favor comeback mechanics for trailing team
            weights['bonus_goal'] *= 1.5
        
        # Adjust based on time remaining
        time_ratio = self.clock / self.settings.period_length
        if time_ratio < 0.3:  # Last 30% of period
            weights['quick_strike'] *= 1.3  # Encourage fast play
            
        return weights

    def _start_quick_strike(self) -> None:
        """
        Start a quick strike challenge.
        
        Initiates a timed challenge where players must score quickly
        for bonus points.
        """
        self.quick_strike_active = True
        self.quick_strike_deadline = datetime.now() + timedelta(seconds=15)
        self.stats['quick_strikes_attempted'] += 1
        
        # Activate visual and sound effects
        self._add_visual_effect('quick_strike', 3.0)
        self._play_sound('quick_strike')
        
        self.active_event = "QUICK STRIKE CHALLENGE! SCORE IN 15 SECONDS!"

    def _activate_bonus_goal(self) -> None:
        """
        Activate bonus goal scoring.
        
        Increases point value for the next goal scored.
        """
        self.current_goal_value = random.randint(2, 3)
        self.event_duration = datetime.now() + timedelta(seconds=20)
        
        # Activate effects
        self._add_visual_effect('bonus', 2.0)
        self._play_sound('bonus')
        
        self.active_event = f"{self.current_goal_value}X POINTS PER GOAL!"

    def _start_combo_challenge(self) -> None:
        """
        Start a combo goal challenge.
        
        Initiates a period where consecutive goals increase in value.
        """
        self.combo_count = 0
        self.event_duration = datetime.now() + timedelta(seconds=30)
        
        # Activate effects
        self._add_visual_effect('combo', 2.0)
        self._play_sound('bonus')
        
        self.active_event = "COMBO CHALLENGE! QUICK GOALS FOR BONUS POINTS!"

    def _end_quick_strike(self, success: bool = False) -> None:
        """
        End the quick strike challenge.
        
        Args:
            success: Whether the challenge was completed successfully
        """
        if not self.quick_strike_active:
            return
            
        self.quick_strike_active = False
        self.quick_strike_deadline = None
        
        if success:
            self.stats['quick_strikes_successful'] += 1
            self._add_analytics_alert("QUICK STRIKE SUCCESS!", 'achievement', 2.0)
        
        self.active_event = None

    def _end_current_event(self) -> None:
        """End the current special event."""
        self.current_goal_value = 1
        self.event_duration = None
        if not self.frenzy_mode:  # Don't clear frenzy message
            self.active_event = None

    def handle_goal(self, team: str) -> None:
        """
        Handle goal scoring with all bonuses and special events.
        
        Processes goal scoring including all special bonuses and effects:
        - First goal bonus
        - Quick strike bonus
        - Comeback bonus
        - Combo bonus
        - Frenzy mode multiplier
        
        Args:
            team: The team that scored ('red' or 'blue')
            
        Note:
            All point multipliers are applied in a specific order to ensure
            consistent scoring across all game states.
        """
        current_time = datetime.now()
        points = self.current_goal_value
        bonuses: List[str] = []
        
        try:
            # Calculate base points and bonuses
            points, bonus_info = self._calculate_goal_points(team, current_time)
            bonuses.extend(bonus_info)
            
            # Update game state
            self._update_goal_state(team, points, current_time)
            
            # Handle special events
            self._handle_goal_events(team, current_time)
            
            # Generate goal effects
            self._create_goal_effects(team, points, bonuses)
            
        except Exception as e:
            logging.error(f"Error handling goal: {e}")
            # Fallback to basic goal handling
            super().handle_goal(team)

    def _calculate_goal_points(
        self, 
        team: str, 
        current_time: datetime
    ) -> Tuple[int, List[str]]:
        """
        Calculate total points and bonuses for a goal.
        
        Args:
            team: Scoring team
            current_time: Time of goal
            
        Returns:
            Tuple containing:
            - Total points for the goal
            - List of bonus descriptions
        """
        points = self.current_goal_value
        bonuses = []
        
        # First goal bonus
        if self.first_goal_opportunity:
            points, bonus_text = self._calculate_first_goal_bonus()
            bonuses.append(bonus_text)
            self.first_goal_opportunity = False
        
        # Quick strike bonus
        if self.quick_strike_active:
            points *= 2
            bonuses.append("QUICK STRIKE!")
            self._end_quick_strike(success=True)
        
        # Combo bonus
        if self.combo_count > 0:
            combo_points, combo_text = self._calculate_combo_bonus(current_time)
            points += combo_points
            if combo_text:
                bonuses.append(combo_text)
        
        # Comeback bonus
        comeback_points = self._calculate_comeback_bonus(team)
        if comeback_points > 0:
            points += comeback_points
            bonuses.append(f"COMEBACK +{comeback_points}!")
            self.stats['comeback_goals'] += 1
        
        # Final minute frenzy
        if self.frenzy_mode:
            points *= 2
            bonuses.append("FRENZY")
            self.stats['frenzy_goals'] += 1
            
        return points, bonuses

    def _calculate_first_goal_bonus(self) -> Tuple[int, str]:
        """
        Calculate bonus for scoring the first goal quickly.
        
        Returns:
            Tuple containing:
            - Bonus points awarded
            - Bonus description text
        """
        time_taken = self.settings.period_length - self.clock
        max_bonus = 3
        
        # Calculate bonus based on speed
        bonus = max(1, int(max_bonus * (1 - time_taken / self.first_goal_window)))
        
        # Award perfect bonus for very fast goals
        if time_taken <= 2.0:  # 2 seconds or less
            bonus += 1
            self.stats['perfect_strikes'] += 1
            
        self.stats['bonus_points_earned'] += bonus
        return self.current_goal_value + bonus, f"FIRST GOAL +{bonus}!"

    def _update_goal_state(self, team: str, points: int, current_time: datetime) -> None:
        """
        Update game state after a goal.
        
        Args:
            team: Scoring team
            points: Points to award
            current_time: Time of goal
        """
        # Update score
        self.score[team] += points
        self.last_goal_time = current_time
        
        # Update combo tracking
        if self.last_goal_time:
            time_since_last = (current_time - self.last_goal_time).total_seconds()
            if time_since_last < self.COMBO_WINDOW:
                self.combo_count += 1
                self.stats['max_combo'] = max(self.stats['max_combo'], self.combo_count)
            else:
                self.combo_count = 1
        else:
            self.combo_count = 1
        
        # Update analytics after goal
        if self.game.current_analysis:
            if self.game.current_analysis.get('is_critical_moment'):
                self.handle_critical_moment(self.game.current_analysis)

    def _start_final_minute_frenzy(self) -> None:
        """
        Activate final minute frenzy mode.
        
        Triggers special event where all goals are worth double points.
        Includes visual and sound effects to enhance excitement.
        """
        self.frenzy_mode = True
        self.stats['frenzy_mode_activations'] += 1
        
        # Create dramatic effect
        self._add_visual_effect('frenzy', 3.0)
        self._play_sound('frenzy')
        
        # Show notification
        self.active_event = "FINAL MINUTE FRENZY! ALL GOALS WORTH DOUBLE!"
        self._add_analytics_alert("FINAL MINUTE FRENZY!", 'frenzy', 3.0)
        
        # Start particle effects
        self._create_frenzy_particles()

    def _create_frenzy_particles(self) -> None:
        """Create particle effects for frenzy mode activation."""
        if 'spark' not in self.particle_images:
            return
            
        particles = []
        for _ in range(20):
            particle = {
                'image': 'spark',
                'x': random.randint(0, self.settings.screen_width),
                'y': random.randint(0, self.settings.screen_height),
                'dx': random.uniform(-100, 100),
                'dy': random.uniform(-100, 100),
                'life': random.uniform(1.0, 2.0),
                'max_life': 2.0,
                'alpha': 255,
                'rotation': random.uniform(0, 360),
                'rotation_speed': random.uniform(-180, 180)
            }
            particles.append(particle)
            
        self.particle_systems.append({
            'particles': particles,
            'type': 'frenzy',
            'end_time': datetime.now() + timedelta(seconds=3)
        })

    def _update_comeback_status(self) -> None:
        """
        Update comeback tracking and status.
        
        Tracks active comeback attempts and triggers appropriate
        effects when comebacks are completed.
        """
        if not self.comeback_active:
            return
            
        # Check if comeback is still possible
        max_score = max(self.score['red'], self.score['blue'])
        min_score = min(self.score['red'], self.score['blue'])
        score_diff = max_score - min_score
        
        if score_diff == 0:  # Comeback completed
            self.comeback_active = False
            self.stats['comebacks_completed'] += 1
            
            # Determine comeback team
            comeback_team = 'red' if self.score['red'] == max_score else 'blue'
            
            # Create effects
            self._handle_comeback_completion(comeback_team)
        elif score_diff > self.comeback_threshold:
            # Comeback failed
            self.comeback_active = False
            self.comeback_start_score = None

    def _handle_comeback_completion(self, team: str) -> None:
        """
        Handle effects for a completed comeback.
        
        Args:
            team: Team that completed the comeback
        """
        # Play sound effect
        self._play_sound('comeback_complete')
        
        # Create visual effects
        self._add_visual_effect('comeback', 3.0)
        self._create_comeback_particles(team)
        
        # Show notifications
        self.active_event = "COMEBACK COMPLETE!"
        self._add_analytics_alert("INCREDIBLE COMEBACK!", 'comeback', 3.0)
        
        # Log achievement
        logging.info(f"Comeback completed by {team} team")

    def _handle_goal_events(self, team: str, current_time: datetime) -> None:
        """
        Handle special events triggered by goals.
        
        Args:
            team: Scoring team
            current_time: Time of goal
        """
        # Check for comeback initiation
        if not self.comeback_active:
            max_score = max(self.score['red'], self.score['blue'])
            min_score = min(self.score['red'], self.score['blue'])
            if max_score - min_score >= self.comeback_threshold:
                self.comeback_active = True
                self.comeback_start_score = self.score.copy()
                self.stats['comebacks_started'] += 1
                self._play_sound('comeback_started')
                
        # Handle quick response goals
        if self.last_goal_time:
            response_time = (current_time - self.last_goal_time).total_seconds()
            if response_time <= 5.0:  # Quick response threshold
                self._handle_quick_response(team)

    def _handle_quick_response(self, team: str) -> None:
        """
        Handle quick response goal effects.
        
        Args:
            team: Team that scored the quick response
        """
        # Create visual effect
        self._add_visual_effect('quick_response', 2.0)
        
        # Add bonus points
        bonus = 1
        self.score[team] += bonus
        self.stats['bonus_points_earned'] += bonus
        
        # Show notification
        self._add_analytics_alert("QUICK RESPONSE!", 'response', 2.0)

    def _update_visual_effects(self, dt: float) -> None:
        """
        Update all visual effects for the current frame.
        
        Handles updating of:
        - Particle systems
        - Screen overlays
        - Animations
        - UI effects
        
        Args:
            dt: Time elapsed since last frame in seconds
            
        Note:
            Uses frame-independent timing to ensure consistent
            animation speeds regardless of frame rate.
        """
        try:
            # Update particle systems
            self._update_particle_systems(dt)
            
            # Update active effects
            self._update_active_effects(dt)
            
            # Update animations
            self._update_animations(dt)
            
            # Clean up expired effects
            self._cleanup_effects()
            
        except Exception as e:
            logging.error(f"Error updating visual effects: {e}")
            self._reset_visual_systems()

    def _update_particle_systems(self, dt: float) -> None:
        """
        Update particle physics and properties.
        
        Args:
            dt: Time elapsed since last frame
        """
        current_time = datetime.now()
        
        # Remove expired systems
        self.particle_systems = [
            system for system in self.particle_systems
            if current_time < system['end_time']
        ]
        
        # Update remaining particles with physics
        for system in self.particle_systems:
            self._update_particles_physics(system['particles'], dt)
            
            # Apply system-specific updates
            if system.get('type') == 'frenzy':
                self._update_frenzy_particles(system['particles'], dt)
            elif system.get('type') == 'comeback':
                self._update_comeback_particles(system['particles'], dt)

    def _update_particles_physics(self, particles: List[Dict], dt: float) -> None:
        """
        Update particle physics including movement and lifetime.
        
        Args:
            particles: List of particle dictionaries
            dt: Time elapsed since last frame
        """
        screen_rect = pygame.Rect(0, 0, self.settings.screen_width, self.settings.screen_height)
        
        for particle in particles[:]:  # Copy list to allow removal
            # Update lifetime
            particle['life'] -= dt
            if particle['life'] <= 0:
                particles.remove(particle)
                continue
            
            # Update position
            particle['x'] += particle['dx'] * dt
            particle['y'] += particle['dy'] * dt
            
            # Update rotation if present
            if 'rotation' in particle:
                particle['rotation'] += particle.get('rotation_speed', 0) * dt
            
            # Update alpha based on lifetime
            particle['alpha'] = int(255 * (particle['life'] / particle['max_life']))
            
            # Optional screen boundary checks
            if not screen_rect.collidepoint(particle['x'], particle['y']):
                # Either remove or bounce particle
                if particle.get('bounce', False):
                    self._bounce_particle(particle, screen_rect)
                else:
                    particles.remove(particle)

    def _bounce_particle(self, particle: Dict, screen_rect: pygame.Rect) -> None:
        """
        Bounce particle off screen boundaries.
        
        Args:
            particle: Particle dictionary
            screen_rect: Screen boundary rectangle
        """
        # Horizontal bounds
        if particle['x'] < screen_rect.left:
            particle['x'] = screen_rect.left
            particle['dx'] *= -0.8  # Energy loss
        elif particle['x'] > screen_rect.right:
            particle['x'] = screen_rect.right
            particle['dx'] *= -0.8
        
        # Vertical bounds
        if particle['y'] < screen_rect.top:
            particle['y'] = screen_rect.top
            particle['dy'] *= -0.8
        elif particle['y'] > screen_rect.bottom:
            particle['y'] = screen_rect.bottom
            particle['dy'] *= -0.8

    def _update_active_effects(self, dt: float) -> None:
        """
        Update active visual effects.
        
        Args:
            dt: Time elapsed since last frame
        """
        # Update effect durations
        self.visual_effects = [
            effect for effect in self.visual_effects
            if effect['duration'] > 0
        ]
        
        for effect in self.visual_effects:
            effect['duration'] -= dt
            
            # Update effect-specific properties
            if effect['type'] == 'frenzy':
                effect['intensity'] = min(1.0, effect['duration'] / 3.0)
            elif effect['type'] == 'comeback':
                effect['scale'] = 1.0 + (1.0 - effect['duration'] / 2.0) * 0.5

    def _update_animations(self, dt: float) -> None:
        """
        Update animation frames and timing.
        
        Args:
            dt: Time elapsed since last frame
        """
        current_time = datetime.now()
        
        # Update animation frames
        self.active_animations = [
            anim for anim in self.active_animations
            if current_time < anim['end_time']
        ]
        
        for anim in self.active_animations:
            # Calculate current frame
            elapsed = (current_time - anim['start_time']).total_seconds()
            anim['frame'] = int(elapsed * anim['fps']) % len(anim['frames'])
            
            # Update animation properties
            if 'properties' in anim:
                self._update_animation_properties(anim, elapsed)

    def _update_animation_properties(self, anim: Dict, elapsed: float) -> None:
        """
        Update animation-specific properties.
        
        Args:
            anim: Animation dictionary
            elapsed: Time elapsed since animation start
        """
        props = anim['properties']
        
        if 'scale' in props:
            progress = elapsed / (anim['end_time'] - anim['start_time']).total_seconds()
            props['current_scale'] = props['start_scale'] + (
                props['end_scale'] - props['start_scale']
            ) * progress
            
        if 'rotation' in props:
            props['current_rotation'] = props['rotation_speed'] * elapsed

    def _cleanup_effects(self) -> None:
        """Clean up expired effects and manage memory."""
        # Limit total particles
        total_particles = sum(len(system['particles']) for system in self.particle_systems)
        if total_particles > self.MAX_PARTICLES:
            reduction_factor = self.MAX_PARTICLES / total_particles
            for system in self.particle_systems:
                system['particles'] = system['particles'][:int(len(system['particles']) * reduction_factor)]
        
        # Remove empty systems
        self.particle_systems = [
            system for system in self.particle_systems
            if system['particles']
        ]
        
        # Limit active animations
        if len(self.active_animations) > 10:  # Arbitrary limit
            self.active_animations = self.active_animations[-10:]

    def _reset_visual_systems(self) -> None:
        """Reset all visual systems to a clean state."""
        self.visual_effects.clear()
        self.particle_systems.clear()
        self.active_animations.clear()
        logging.warning("Visual effects systems reset due to error")

    def _update_sound_system(self, current_time: datetime) -> None:
        """
        Update sound system and handle sound timing.
        
        Args:
            current_time: Current datetime for timing
        """
        # Check sound cooldowns
        if (current_time - self.last_sound_time).total_seconds() >= self.SOUND_COOLDOWN:
            if hasattr(self, '_queued_sounds'):
                self._play_queued_sounds()
        
        # Handle random sounds
        if (current_time.timestamp() - self.last_random_sound_time >= 
            self.next_random_sound_interval):
            self._play_random_sound()
            self.last_random_sound_time = current_time.timestamp()
            self.next_random_sound_interval = self._get_next_sound_interval()

    def _play_sound(self, sound_name: str, force: bool = False) -> None:
        """
        Play a sound effect with cooldown handling.
        
        Args:
            sound_name: Name of sound to play
            force: Whether to ignore cooldown
        """
        current_time = datetime.now()
        
        if force or (current_time - self.last_sound_time).total_seconds() >= self.SOUND_COOLDOWN:
            if sound_name in self.crazy_sounds and self.crazy_sounds[sound_name]:
                try:
                    self.crazy_sounds[sound_name].play()
                    self.last_sound_time = current_time
                except pygame.error as e:
                    logging.warning(f"Failed to play sound {sound_name}: {e}")
        else:
            # Queue sound for later if we're in cooldown
            if not hasattr(self, '_queued_sounds'):
                self._queued_sounds = []
            self._queued_sounds.append(sound_name)

    def _play_queued_sounds(self) -> None:
        """Play any queued sound effects."""
        if not hasattr(self, '_queued_sounds'):
            return
            
        for sound_name in self._queued_sounds[:]:
            if sound_name in self.crazy_sounds and self.crazy_sounds[sound_name]:
                try:
                    self.crazy_sounds[sound_name].play()
                    self._queued_sounds.remove(sound_name)
                except pygame.error as e:
                    logging.warning(f"Failed to play queued sound {sound_name}: {e}")
                    
        if not self._queued_sounds:
            del self._queued_sounds

    def _play_random_sound(self) -> None:
        """Play a random sound effect from available sounds."""
        if not self.game.sounds_enabled:
            return
            
        available_sounds = []
        
        # Get available game sounds
        if self.game.sounds.get('random_sounds'):
            available_sounds.extend(
                [s for s in self.game.sounds['random_sounds'] if s is not None]
            )
            
        # Add crazy mode sounds
        available_sounds.extend(
            [s for s in self.crazy_sounds.values() if s is not None]
        )
        
        if available_sounds:
            try:
                sound = random.choice(available_sounds)
                sound.play()
            except pygame.error as e:
                logging.warning(f"Failed to play random sound: {e}")

    def _get_next_sound_interval(self) -> float:
        """
        Get next random sound interval.
        
        Returns:
            float: Time until next random sound in seconds
        """
        min_interval = max(5.0, self.settings.random_sound_min_interval)
        max_interval = min(30.0, self.settings.random_sound_max_interval)
        return random.uniform(min_interval, max_interval)

    def draw(self) -> None:
        """
        Draw the game screen for the current frame.
        
        Renders all game elements in the following order:
        1. Background
        2. Base game elements
        3. Game mode specific elements
        4. Visual effects and overlays
        5. UI elements and text
        6. Analytics overlay (if enabled)
        
        Note:
            Uses layered rendering to ensure proper visual hierarchy
            and effect composition.
        """
        try:
            # Create temporary surface for effect compositing
            temp_surface = pygame.Surface(
                (self.settings.screen_width, self.settings.screen_height),
                pygame.SRCALPHA
            )
            
            # Draw background elements
            self._draw_background(temp_surface)
            
            # Draw base game elements
            self._draw_base_elements(temp_surface)
            
            # Draw game mode specific elements
            self._draw_game_elements(temp_surface)
            
            # Draw visual effects
            self._draw_effects(temp_surface)
            
            # Draw UI elements
            self._draw_ui_elements(temp_surface)
            
            # Draw analytics if enabled
            if self.show_analytics:
                self._draw_analytics_overlay(temp_surface)
            
            # Final composite to screen
            self.screen.blit(temp_surface, (0, 0))
            
        except Exception as e:
            logging.error(f"Error in draw cycle: {e}")
            # Fallback to basic drawing
            super().draw()

    def _draw_background(self, surface: pygame.Surface) -> None:
        """
        Draw background elements.
        
        Args:
            surface: Surface to draw on
        """
        # Draw base background
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(self.settings.bg_color)
            
        # Draw any active background effects
        if self.frenzy_mode and 'frenzy' in self.overlays:
            overlay = self.overlays['frenzy'].copy()
            overlay.set_alpha(100)
            surface.blit(overlay, (0, 0))

    def _draw_base_elements(self, surface: pygame.Surface) -> None:
        """
        Draw base game elements.
        
        Args:
            surface: Surface to draw on
        """
        # Draw scoreboard
        self._draw_scoreboard(surface)
        
        # Draw period indicator
        self._draw_period_info(surface)
        
        # Draw timer
        self._draw_timer(surface)

    def _draw_scoreboard(self, surface: pygame.Surface) -> None:
        """
        Draw enhanced scoreboard with effects.
        
        Args:
            surface: Surface to draw on
        """
        # Draw score background
        score_bg = pygame.Surface((300, 80), pygame.SRCALPHA)
        score_bg.fill((0, 0, 0, 180))
        score_pos = ((self.settings.screen_width - 300) // 2, 20)
        surface.blit(score_bg, score_pos)
        
        # Draw team scores with appropriate colors
        red_score = self.font_large.render(str(self.score['red']), True, (255, 50, 50))
        blue_score = self.font_large.render(str(self.score['blue']), True, (50, 50, 255))
        
        # Calculate positions
        center_x = self.settings.screen_width // 2
        score_y = 35
        spacing = 100
        
        surface.blit(red_score, (center_x - spacing - red_score.get_width(), score_y))
        surface.blit(blue_score, (center_x + spacing, score_y))
        
        # Draw active modifiers
        if self.current_goal_value > 1:
            modifier_text = f"×{self.current_goal_value}"
            modifier_surface = self.font_small.render(modifier_text, True, (255, 215, 0))
            surface.blit(modifier_surface, (center_x - modifier_surface.get_width()//2, score_y + 40))

    def _draw_game_elements(self, surface: pygame.Surface) -> None:
        """
        Draw game mode specific elements.
        
        Args:
            surface: Surface to draw on
        """
        # Draw quick strike indicator if active
        if self.quick_strike_active:
            self._draw_quick_strike(surface)
        
        # Draw combo counter if active
        if self.combo_count > 1:
            self._draw_combo_counter(surface)
        
        # Draw comeback progress if active
        if self.comeback_active:
            self._draw_comeback_progress(surface)
        
        # Draw frenzy mode indicator
        if self.frenzy_mode:
            self._draw_frenzy_indicator(surface)

    def _draw_quick_strike(self, surface: pygame.Surface) -> None:
        """
        Draw quick strike challenge interface.
        
        Args:
            surface: Surface to draw on
        """
        if not self.quick_strike_deadline:
            return
        
        remaining = (self.quick_strike_deadline - datetime.now()).total_seconds()
        if remaining <= 0:
            return
        
        # Draw challenge background
        challenge_bg = pygame.Surface((400, 100), pygame.SRCALPHA)
        challenge_bg.fill((0, 0, 0, 150))
        pos = ((self.settings.screen_width - 400) // 2, 200)
        surface.blit(challenge_bg, pos)
        
        # Draw timer with pulsing effect
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.3 + 0.7
        color = (int(255 * pulse), int(215 * pulse), 0)
        
        timer_text = self.font_large.render(f"{int(remaining)}s", True, color)
        timer_pos = (
            self.settings.screen_width // 2 - timer_text.get_width() // 2,
            220
        )
        surface.blit(timer_text, timer_pos)
        
        # Draw challenge label
        label_text = self.font_small.render("QUICK STRIKE!", True, color)
        label_pos = (
            self.settings.screen_width // 2 - label_text.get_width() // 2,
            260
        )
        surface.blit(label_text, label_pos)

    def _draw_combo_counter(self, surface: pygame.Surface) -> None:
        """
        Draw combo counter with effects.
        
        Args:
            surface: Surface to draw on
        """
        # Create combo text with glow effect
        combo_text = f"COMBO ×{self.combo_count}"
        
        # Draw glow
        glow_size = int(40 * min(self.combo_count / self.MAX_COMBO_MULTIPLIER, 1.0))
        glow_surface = pygame.Surface((300 + glow_size*2, 60 + glow_size*2), pygame.SRCALPHA)
        glow_color = (255, 140, 0, 100)
        
        for i in range(glow_size, 0, -2):
            alpha = int(100 * (i / glow_size))
            pygame.draw.rect(
                glow_surface,
                (*glow_color[:3], alpha),
                (glow_size-i, glow_size-i, 300+i*2, 60+i*2),
                border_radius=10
            )
        
        # Draw combo text
        combo_surface = self.font_large.render(combo_text, True, (255, 255, 255))
        text_pos = (
            glow_surface.get_width()//2 - combo_surface.get_width()//2,
            glow_surface.get_height()//2 - combo_surface.get_height()//2
        )
        glow_surface.blit(combo_surface, text_pos)
        
        # Position on screen
        pos = (
            self.settings.screen_width//2 - glow_surface.get_width()//2,
            self.settings.screen_height - 100
        )
        surface.blit(glow_surface, pos)

    def _draw_comeback_progress(self, surface: pygame.Surface) -> None:
        """
        Draw comeback progress indicator.
        
        Args:
            surface: Surface to draw on
        """
        if not self.comeback_start_score:
            return
            
        # Calculate progress
        start_diff = abs(
            self.comeback_start_score['red'] - self.comeback_start_score['blue']
        )
        current_diff = abs(self.score['red'] - self.score['blue'])
        progress = 1 - (current_diff / start_diff)
        
        # Draw progress bar
        bar_width = 200
        bar_height = 20
        pos = (20, self.settings.screen_height - 40)
        
        # Background
        pygame.draw.rect(
            surface,
            (50, 50, 50),
            (*pos, bar_width, bar_height),
            border_radius=5
        )
        
        # Progress
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            pygame.draw.rect(
                surface,
                (255, 215, 0),
                (*pos, progress_width, bar_height),
                border_radius=5
            )
        
        # Label
        label = self.font_small.render("COMEBACK", True, (255, 255, 255))
        surface.blit(label, (20, self.settings.screen_height - 60))

    def _draw_frenzy_indicator(self, surface: pygame.Surface) -> None:
        """
        Draw frenzy mode indicator.
        
        Args:
            surface: Surface to draw on
        """
        # Create pulsing effect
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 0.3 + 0.7
        
        # Draw frenzy text with glow
        text = "FRENZY MODE"
        glow_colors = [
            (255, 0, 0, int(100 * pulse)),
            (255, 100, 0, int(80 * pulse)),
            (255, 200, 0, int(60 * pulse))
        ]
        
        text_surface = self.font_large.render(text, True, (255, 255, 255))
        
        for color in glow_colors:
            glow = self.font_large.render(text, True, color)
            offset = glow_colors.index(color) + 1
            pos = (
                10,
                10 + offset
            )
            surface.blit(glow, pos)
            
        surface.blit(text_surface, (10, 10))

    def _draw_effects(self, surface: pygame.Surface) -> None:
        """
        Draw all visual effects.
        
        Args:
            surface: Surface to draw on
        """
        # Draw particle systems
        for system in self.particle_systems:
            self._draw_particle_system(surface, system)
            
        # Draw active effects
        for effect in self.visual_effects:
            self._draw_effect(surface, effect)
            
        # Draw active animations
        for animation in self.active_animations:
            self._draw_animation(surface, animation)

    def _draw_particle_system(self, surface: pygame.Surface, system: Dict) -> None:
        """
        Draw a particle system.
        
        Args:
            surface: Surface to draw on
            system: Particle system dictionary
        """
        for particle in system['particles']:
            if particle.get('alpha', 255) <= 0:
                continue
                
            image = self.particle_images.get(particle.get('image', 'spark'))
            if not image:
                continue
                
            # Apply particle transformations
            p_surface = image.copy()
            
            # Apply alpha
            p_surface.set_alpha(particle['alpha'])
            
            # Apply rotation if present
            if 'rotation' in particle:
                p_surface = pygame.transform.rotate(
                    p_surface, 
                    particle['rotation']
                )
            
            # Draw particle
            surface.blit(
                p_surface,
                (
                    int(particle['x'] - p_surface.get_width()//2),
                    int(particle['y'] - p_surface.get_height()//2)
                )
            )

    def _draw_effect(self, surface: pygame.Surface, effect: Dict) -> None:
        """
        Draw a visual effect.
        
        Args:
            surface: Surface to draw on
            effect: Effect dictionary
        """
        if effect['type'] == 'frenzy':
            self._draw_frenzy_effect(surface, effect)
        elif effect['type'] == 'comeback':
            self._draw_comeback_effect(surface, effect)
        elif effect['type'] == 'quick_strike':
            self._draw_quick_strike_effect(surface, effect)

    def _draw_animation(self, surface: pygame.Surface, animation: Dict) -> None:
        """
        Draw an animation frame.
        
        Args:
            surface: Surface to draw on
            animation: Animation dictionary
        """
        if animation['frame'] >= len(animation['frames']):
            return
            
        frame = animation['frames'][animation['frame']]
        
        # Apply animation properties
        if 'properties' in animation:
            props = animation['properties']
            
            if 'scale' in props:
                frame = pygame.transform.scale(
                    frame,
                    (
                        int(frame.get_width() * props['current_scale']),
                        int(frame.get_height() * props['current_scale'])
                    )
                )
                
            if 'rotation' in props:
                frame = pygame.transform.rotate(
                    frame,
                    props['current_rotation']
                )
        
        # Draw frame at specified position
        surface.blit(
            frame,
            (
                animation['x'] - frame.get_width()//2,
                animation['y'] - frame.get_height()//2
            )
        )

    def _draw_ui_elements(self, surface: pygame.Surface) -> None:
        """
        Draw UI elements and text.
        
        Args:
            surface: Surface to draw on
        """
        # Draw active event text
        if self.active_event:
            self._draw_event_text(surface)
        
        # Draw analytics alerts
        if self.show_analytics:
            self._draw_analytics_alerts(surface)

    def _draw_analytics_overlay(self, surface: pygame.Surface) -> None:
        """
        Draw analytics overlay with dynamic positioning.
        
        Args:
            surface: Surface to draw on
            
        Note:
            Positions overlay based on current game state and
            screen activity to minimize interference with gameplay.
        """
        if not self.game.current_analysis:
            return
            
        analysis = self.game.current_analysis
        position = self._calculate_analytics_position()
        
        try:
            # Create analytics surface with transparency
            analytics_surface = pygame.Surface((300, 200), pygame.SRCALPHA)
            analytics_surface.fill((0, 0, 0, 180))
            
            y_offset = 10  # Starting vertical position
            
            # Draw win probability
            if 'win_probability' in analysis:
                self._draw_win_probability(
                    analytics_surface,
                    analysis['win_probability'],
                    y_offset
                )
                y_offset += 30
            
            # Draw momentum indicator
            if 'momentum' in analysis:
                self._draw_momentum_indicator(
                    analytics_surface,
                    analysis['momentum']['current_state'],
                    y_offset
                )
                y_offset += 30
            
            # Draw pattern detection
            if 'patterns' in analysis:
                self._draw_pattern_info(
                    analytics_surface,
                    analysis['patterns'],
                    y_offset
                )
                y_offset += 30
            
            # Draw critical moment indicator
            if analysis.get('is_critical_moment'):
                self._draw_critical_indicator(
                    analytics_surface,
                    y_offset
                )
            
            # Draw final surface at calculated position
            surface.blit(analytics_surface, position)
            
        except Exception as e:
            logging.error(f"Error drawing analytics overlay: {e}")

    def _calculate_analytics_position(self) -> Tuple[int, int]:
        """
        Calculate optimal position for analytics overlay.
        
        Returns:
            Tuple containing x, y coordinates for overlay
            
        Note:
            Positions overlay to avoid interference with active
            game elements and effects.
        """
        if self.analytics_overlay_position == 'dynamic':
            # Check game state for optimal positioning
            if self.frenzy_mode:
                # Move overlay down during frenzy mode
                return (10, self.settings.screen_height - 220)
            elif self.quick_strike_active:
                # Move overlay to opposite side during quick strike
                return (self.settings.screen_width - 310, 10)
            else:
                # Default position
                return (10, 10)
        elif self.analytics_overlay_position == 'top-right':
            return (self.settings.screen_width - 310, 10)
        elif self.analytics_overlay_position == 'bottom-left':
            return (10, self.settings.screen_height - 220)
        elif self.analytics_overlay_position == 'bottom-right':
            return (self.settings.screen_width - 310, self.settings.screen_height - 220)
        else:  # top-left default
            return (10, 10)

    def _draw_win_probability(
        self,
        surface: pygame.Surface,
        probabilities: Dict[str, float],
        y_offset: int
    ) -> None:
        """
        Draw win probability visualization.
        
        Args:
            surface: Surface to draw on
            probabilities: Win probabilities for each team
            y_offset: Vertical position to start drawing
        """
        # Draw probability bars
        bar_width = 280
        bar_height = 20
        
        # Background bar
        pygame.draw.rect(
            surface,
            (50, 50, 50),
            (10, y_offset, bar_width, bar_height),
            border_radius=5
        )
        
        # Red team probability
        red_width = int(bar_width * probabilities['red'])
        if red_width > 0:
            pygame.draw.rect(
                surface,
                (255, 50, 50),
                (10, y_offset, red_width, bar_height),
                border_radius=5
            )
        
        # Blue team probability
        blue_width = int(bar_width * probabilities['blue'])
        if blue_width > 0:
            pygame.draw.rect(
                surface,
                (50, 50, 255),
                (10 + bar_width - blue_width, y_offset, blue_width, bar_height),
                border_radius=5
            )
        
        # Draw percentages
        red_text = f"{probabilities['red']:.0%}"
        blue_text = f"{probabilities['blue']:.0%}"
        
        red_surface = self.font_small.render(red_text, True, (255, 255, 255))
        blue_surface = self.font_small.render(blue_text, True, (255, 255, 255))
        
        surface.blit(red_surface, (15, y_offset + 25))
        surface.blit(blue_surface, (bar_width - blue_surface.get_width() + 5, y_offset + 25))

    def _draw_momentum_indicator(
        self,
        surface: pygame.Surface,
        momentum: Dict,
        y_offset: int
    ) -> None:
        """
        Draw momentum indicator with visual effects.
        
        Args:
            surface: Surface to draw on
            momentum: Momentum state information
            y_offset: Vertical position to start drawing
        """
        if not momentum['team']:
            return
            
        # Create gradient effect based on intensity
        intensity_colors = {
            'overwhelming': (255, 0, 0),
            'strong': (255, 140, 0),
            'moderate': (255, 215, 0)
        }
        
        color = intensity_colors.get(momentum['intensity'], (255, 255, 255))
        
        # Draw momentum bar
        bar_width = 280
        bar_height = 15
        
        # Calculate fill based on momentum score
        fill_width = int(bar_width * abs(momentum['score']) / 100)
        
        pygame.draw.rect(
            surface,
            (50, 50, 50),
            (10, y_offset, bar_width, bar_height),
            border_radius=3
        )
        
        pygame.draw.rect(
            surface,
            color,
            (
                10 if momentum['team'] == 'red' else 10 + bar_width - fill_width,
                y_offset,
                fill_width,
                bar_height
            ),
            border_radius=3
        )
        
        # Draw momentum text
        text = f"MOMENTUM: {momentum['team'].upper()} ({momentum['intensity'].upper()})"
        text_surface = self.font_small.render(text, True, color)
        surface.blit(text_surface, (15, y_offset + 20))

    def _draw_pattern_info(
        self,
        surface: pygame.Surface,
        patterns: Dict,
        y_offset: int
    ) -> None:
        """
        Draw detected gameplay patterns.
        
        Args:
            surface: Surface to draw on
            patterns: Pattern analysis data
            y_offset: Vertical position to start drawing
        """
        if 'scoring_runs' not in patterns:
            return
            
        runs = patterns['scoring_runs']
        
        if runs.get('current_run', {}).get('length', 0) >= 3:
            run = runs['current_run']
            text = f"HOT STREAK: {run['team'].upper()} x{run['length']}"
            
            # Pulse effect
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.3 + 0.7
            color = (int(255 * pulse), int(140 * pulse), 0)
            
            text_surface = self.font_small.render(text, True, color)
            surface.blit(text_surface, (15, y_offset))

    def _draw_critical_indicator(
        self,
        surface: pygame.Surface,
        y_offset: int
    ) -> None:
        """
        Draw critical moment indicator with effects.
        
        Args:
            surface: Surface to draw on
            y_offset: Vertical position to start drawing
        """
        # Pulse effect for critical moment
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 0.4 + 0.6
        color = (int(255 * pulse), int(50 * pulse), int(50 * pulse))
        
        text = "CRITICAL MOMENT!"
        text_surface = self.font_small.render(text, True, color)
        surface.blit(text_surface, (15, y_offset))

    def _draw_analytics_alerts(self, surface: pygame.Surface) -> None:
        """
        Draw analytics alert messages.
        
        Args:
            surface: Surface to draw on
        """
        current_time = datetime.now()
        
        # Update alert queue
        self.analytics_alert_queue = [
            alert for alert in self.analytics_alert_queue
            if current_time < alert['end_time']
        ]
        
        # Draw active alerts
        y_offset = 100
        for alert in self.analytics_alert_queue:
            # Calculate fade out
            time_left = (alert['end_time'] - current_time).total_seconds()
            if time_left < 0.5:  # Fade out in last 0.5 seconds
                alpha = int(255 * (time_left / 0.5))
            else:
                alpha = 255
            
            # Draw alert background
            if self.ui_elements.get('analytics'):
                bg = self.ui_elements['analytics'].copy()
                bg.set_alpha(int(alpha * 0.7))
                surface.blit(bg, (10, y_offset))
            
            # Draw alert text
            text_surface = self.font_small.render(
                alert['message'],
                True,
                self._get_alert_color(alert['type'])
            )
            text_surface.set_alpha(alpha)
            
            surface.blit(
                text_surface,
                (20, y_offset + 10)
            )
            
            y_offset += 50

    def _get_alert_color(self, alert_type: str) -> Tuple[int, int, int]:
        """
        Get color for alert type.
        
        Args:
            alert_type: Type of alert
            
        Returns:
            RGB color tuple
        """
        colors = {
            'achievement': (255, 215, 0),  # Gold
            'momentum': (255, 140, 0),     # Orange
            'pattern': (0, 255, 255),      # Cyan
            'comeback': (255, 100, 255),   # Pink
            'frenzy': (255, 50, 50),       # Red
            'response': (50, 255, 50)      # Green
        }
        return colors.get(alert_type, (255, 255, 255))  # White default

    def _add_analytics_alert(
        self,
        message: str,
        alert_type: str,
        duration: float
    ) -> None:
        """
        Add a new analytics alert.
        
        Args:
            message: Alert message to display
            alert_type: Type of alert for styling
            duration: How long to display the alert in seconds
        """
        self.analytics_alert_queue.append({
            'message': message,
            'type': alert_type,
            'end_time': datetime.now() + timedelta(seconds=duration)
        })
        
        # Limit queue size
        if len(self.analytics_alert_queue) > 5:
            self.analytics_alert_queue = self.analytics_alert_queue[-5:]

    def cleanup(self) -> None:
        """
        Clean up resources and perform final cleanup tasks.
        
        Ensures proper cleanup of:
        - Base game resources
        - Sound effects
        - Visual assets
        - Particle systems
        - Statistics logging
        """
        try:
            # Call base class cleanup first
            super().cleanup()
            
            # Stop all sounds
            for sound in self.crazy_sounds.values():
                if sound:
                    sound.stop()
            
            # Clear sound references
            self.crazy_sounds.clear()
            
            # Clear all surfaces
            for surface_name in ['background', 'overlay']:
                if hasattr(self, surface_name) and getattr(self, surface_name):
                    surface = getattr(self, surface_name)
                    surface = None
                    setattr(self, surface_name, None)
            
            # Clear particle images
            for image in self.particle_images.values():
                if image:
                    image = None
            self.particle_images.clear()
            
            # Clear effect queues
            self.visual_effects.clear()
            self.particle_systems.clear()
            self.active_animations.clear()
            
            # Log final statistics
            logging.info('CrazyPlayMode cleanup completed')
            logging.info(f"Final stats: {self.stats}")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
