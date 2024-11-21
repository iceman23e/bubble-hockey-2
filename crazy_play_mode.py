# crazy_play_mode.py

from base_game_mode import BaseGameMode
import pygame
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from utils import load_sound, load_image

class CrazyPlayMode(BaseGameMode):
    """
    Crazy Play mode with exciting but physically implementable features.
    
    This game mode extends the base bubble hockey gameplay with additional features:
    - Bonus points and multipliers
    - Quick strike challenges
    - Combo scoring system
    - Comeback mechanics
    - Final minute frenzy mode
    - Enhanced visual and sound effects
    
    The mode maintains game balance while adding excitement through achievable
    bonus opportunities and special events.
    """
    
    # Class constants
    MAX_PARTICLES: int = 100
    COMBO_WINDOW: float = 10.0  # seconds for combo timing
    MAX_COMBO_MULTIPLIER: int = 3
    SOUND_COOLDOWN: float = 3.0

    def __init__(self, game):
        """
        Initialize Crazy Play mode.
        
        Args:
            game: The main game instance this mode is attached to
        """
        super().__init__(game)
        logging.info("Crazy Play mode initialized")
        
        # Core scoring features
        self.current_goal_value: int = 1
        self.first_goal_opportunity: bool = True
        self.first_goal_window: float = self.settings.period_length * 0.15  # 15% of period length
        self.frenzy_window: float = max(30, self.settings.period_length * 0.1)  # 10% of period or minimum 30 seconds
        self.last_goal_time: Optional[datetime] = None
        self.combo_count: int = 0
        
        # Challenge states
        self.quick_strike_active: bool = False
        self.quick_strike_deadline: Optional[datetime] = None
        self.frenzy_mode: bool = False  # For final minute
        
        # Event timing
        self.next_event_time: datetime = datetime.now() + timedelta(seconds=15)
        self.event_duration: Optional[datetime] = None
        self.last_sound_time: datetime = datetime.now()
        
        # Override base settings
        self.max_periods: int = 5  # Longer games
        self.clock: float = self.settings.period_length
        
        # Visual effects system
        self.visual_effects: List[Dict] = []
        self.particle_systems: List[Dict] = []
        self.active_animations: List[Dict] = []
        
        # Enhanced statistics tracking
        self.stats: Dict[str, int] = {
            'bonus_points_earned': 0,
            'quick_strikes_attempted': 0,
            'quick_strikes_successful': 0,
            'frenzy_goals': 0,
            'comeback_goals': 0,
            'critical_goals': 0,
            'max_combo': 0,
            'total_bonus_multiplier': 0,
            'comebacks_started': 0,
            'comebacks_completed': 0
        }
        
        # Load assets and sounds
        self.load_assets()
        self.load_crazy_sounds()

        # Initialize analytics display settings
        self.show_analytics: bool = True
        self.analytics_overlay_position: str = 'dynamic'
        self.analytics_alert_queue: List[Dict] = []
        self.last_analytics_update: datetime = datetime.now()
        self.analytics_update_interval: float = 0.5

        # Initialize random sound timing variables
        self.last_random_sound_time: float = datetime.now().timestamp()
        self.next_random_sound_interval: float = self.get_next_random_sound_interval()

        # Initialize comeback tracking
        self.comeback_active: bool = False
        self.comeback_start_score: Optional[Dict[str, int]] = None

        logging.debug("Crazy Play mode initialization complete")

    def load_assets(self) -> None:
        """
        Load all visual assets for the game mode.
        
        Handles loading of background images, overlays, indicators,
        and particle effects. Provides fallback assets if loading fails.
        """
        try:
            self._load_background()
            self._load_overlays()
            self._load_indicators()
            self._load_particles()
            logging.info("Crazy Play mode assets loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load assets: {e}")
            self._init_fallback_assets()

    def _load_background(self) -> None:
        """Load background asset with fallback."""
        try:
            self.background = load_image('assets/crazy_play/images/background.png')
        except (pygame.error, FileNotFoundError) as e:
            logging.error(f"Failed to load background: {e}")
            self.background = self._create_fallback_surface(
                (self.settings.screen_width, self.settings.screen_height),
                self.settings.bg_color
            )

    def _load_overlays(self) -> None:
        """Load overlay assets with individual fallbacks."""
        try:
            self.overlay = load_image('assets/crazy_play/images/overlay.png')
            self.frenzy_overlay = load_image('assets/crazy_play/images/frenzy.png')
            self.quick_strike_overlay = load_image('assets/crazy_play/images/quick_strike.png')
            self.critical_moment_overlay = load_image('assets/crazy_play/images/critical_moment.png')
        except (pygame.error, FileNotFoundError) as e:
            logging.error(f"Failed to load overlays: {e}")
            self._init_fallback_overlays()

    def _load_indicators(self) -> None:
        """Load indicator assets with fallbacks."""
        try:
            self.bonus_indicator = load_image('assets/crazy_play/images/bonus.png')
            self.analytics_frame = load_image('assets/crazy_play/images/analytics_frame.png')
            self.momentum_indicator = load_image('assets/crazy_play/images/momentum_indicator.png')
            self.comeback_indicator = load_image('assets/crazy_play/images/comeback.png')
        except (pygame.error, FileNotFoundError) as e:
            logging.error(f"Failed to load indicators: {e}")
            self._init_fallback_indicators()

    def _load_particles(self) -> None:
        """
        Load particle effect assets with fallbacks.
        
        Loads all particle images used for visual effects.
        Creates fallback surfaces if loading fails.
        """
        particle_types = ['spark', 'star', 'trail', 'comeback']
        self.particle_images = {}
        
        for p_type in particle_types:
            try:
                self.particle_images[p_type] = load_image(
                    f'assets/crazy_play/particles/{p_type}.png'
                )
            except (pygame.error, FileNotFoundError) as e:
                logging.error(f"Failed to load particle {p_type}: {e}")
                self.particle_images[p_type] = self._create_fallback_particle(p_type)

    def _create_fallback_particle(self, particle_type: str) -> pygame.Surface:
        """
        Create a fallback particle surface.
        
        Args:
            particle_type: Type of particle to create fallback for
        
        Returns:
            A pygame Surface with basic particle visualization
        """
        colors = {
            'spark': (255, 255, 0),  # Yellow
            'star': (255, 255, 255),  # White
            'trail': (255, 140, 0),  # Orange
            'comeback': (255, 215, 0)  # Gold
        }
        
        surface = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(
            surface,
            colors.get(particle_type, (255, 255, 255)),
            (4, 4),
            4
        )
        return surface

    def _init_fallback_assets(self) -> None:
        """Initialize basic fallback assets when loading fails."""
        self.background = self._create_fallback_surface(
            (self.settings.screen_width, self.settings.screen_height),
            self.settings.bg_color
        )
        self._init_fallback_overlays()
        self._init_fallback_indicators()
        self.particle_images = {}

    def _init_fallback_overlays(self) -> None:
        """Initialize fallback overlay surfaces."""
        dimensions = (self.settings.screen_width, self.settings.screen_height)
        self.overlay = self._create_fallback_surface(dimensions, (0, 0, 0, 128))
        self.frenzy_overlay = self._create_fallback_surface(dimensions, (255, 0, 0, 64))
        self.quick_strike_overlay = self._create_fallback_surface(dimensions, (255, 255, 0, 64))
        self.critical_moment_overlay = self._create_fallback_surface(dimensions, (255, 0, 0, 96))

    def _init_fallback_indicators(self) -> None:
        """Initialize fallback indicator surfaces."""
        self.bonus_indicator = self._create_fallback_surface((100, 50), (255, 215, 0))
        self.analytics_frame = self._create_fallback_surface((200, 150), (0, 0, 0, 180))
        self.momentum_indicator = self._create_fallback_surface((100, 20), (255, 140, 0))
        self.comeback_indicator = self._create_fallback_surface((150, 40), (255, 215, 0))

    def _create_fallback_surface(
        self, 
        size: Tuple[int, int], 
        color: Union[Tuple[int, int, int], Tuple[int, int, int, int]]
    ) -> pygame.Surface:
        """
        Create a basic surface as fallback for failed asset loading.
        
        Args:
            size: Tuple of (width, height) for the surface
            color: RGB or RGBA color tuple
            
        Returns:
            A pygame Surface filled with the specified color
        """
        if len(color) == 4:  # RGBA color
            surface = pygame.Surface(size, pygame.SRCALPHA)
        else:  # RGB color
            surface = pygame.Surface(size)
        surface.fill(color)
        return surface

    def load_crazy_sounds(self) -> None:
        """
        Load sound effects specific to crazy mode.
        
        Handles loading of all sound effects with error checking.
        Sets to None if loading fails.
        """
        sound_files = {
            'bonus': 'bonus_activated.wav',
            'quick_strike': 'quick_strike.wav',
            'combo': 'combo_goal.wav',
            'frenzy': 'frenzy.wav',
            'comeback_started': 'comeback_started.wav',
            'comeback_complete': 'comeback_complete.wav'
        }
        
        self.crazy_sounds = {}
        for sound_name, filename in sound_files.items():
            try:
                self.crazy_sounds[sound_name] = load_sound(f'assets/sounds/{filename}')
            except (pygame.error, FileNotFoundError) as e:
                logging.error(f"Failed to load sound {filename}: {e}")
                self.crazy_sounds[sound_name] = None
        
        logging.info("Crazy Play mode sounds loaded successfully")

    def update(self) -> None:
        """
        Update game state for the current frame.
        
        Handles all state updates including:
        - Game mode specific features
        - Analytics updates
        - Visual effects
        - Sound effects
        - Event timing
        """
        if self.game.state_machine.state != self.game.state_machine.states.PLAYING:
            return

        # Update base game elements
        super().update()
        
        current_time = datetime.now()
        
        # Update analytics if interval has passed
        if (current_time - self.last_analytics_update).total_seconds() >= self.analytics_update_interval:
            self._update_analytics()
            self.last_analytics_update = current_time
        
        # Core gameplay updates
        self._update_gameplay_state(current_time)
        
        # Systems updates
        self._update_visual_effects()
        self._update_analytics_alerts()
        self._update_sound_system(current_time)

    def _update_gameplay_state(self, current_time: datetime) -> None:
        """
        Update core gameplay mechanics and states.
        
        Args:
            current_time: Current datetime for timing calculations
        """
        # Check for final frenzy mode
        if not self.frenzy_mode and self.clock <= self.frenzy_window:
            self._start_final_minute_frenzy()
            
        # Check if first goal opportunity has expired
        if self.first_goal_opportunity and (self.settings.period_length - self.clock) > self.first_goal_window:
            self.first_goal_opportunity = False
        
        # Check for new random events
        if current_time >= self.next_event_time:
            self._trigger_random_event()
            
        # Update quick strike challenge
        if self.quick_strike_active and current_time >= self.quick_strike_deadline:
            self._end_quick_strike()
            
        # Update event duration
        if self.event_duration and current_time >= self.event_duration:
            self._end_current_event()

    def _update_analytics(self) -> None:
        """
        Update analytics state and generate insights.
        
        Processes current game state to:
        - Track momentum shifts
        - Detect scoring patterns
        - Monitor win probability changes
        - Generate relevant alerts and effects
        """
        if not self.game.current_analysis:
            return
            
        analysis = self.game.current_analysis
        
        # Process momentum shifts
        if 'momentum' in analysis:
            momentum = analysis['momentum']['current_state']
            if momentum['team'] and momentum['intensity'] in ['strong', 'overwhelming']:
                self._handle_momentum_shift(momentum)
        
        # Process pattern detection
        if 'patterns' in analysis and analysis['patterns'].get('scoring_runs'):
            self._handle_scoring_patterns(analysis['patterns']['scoring_runs'])
        
        # Process win probability changes
        if 'win_probability' in analysis:
            self._handle_probability_changes(analysis['win_probability'])

    def _handle_momentum_shift(self, momentum: Dict) -> None:
        """
        Handle significant momentum shifts.

        Args:
            momentum: Dictionary containing momentum state information including
                     team and intensity values
        """
        team = momentum['team']
        intensity = momentum['intensity']
        
        if intensity == 'overwhelming':
            message = f"MASSIVE MOMENTUM SHIFT: {team.upper()} TEAM!"
            self._add_analytics_alert(message, 'momentum', 3.0)
            self._trigger_effect('momentum_shift', team)

    def _handle_scoring_patterns(self, patterns: Dict) -> None:
        """
        Handle detected scoring patterns.

        Args:
            patterns: Dictionary containing scoring pattern information
        """
        if patterns.get('current_run', {}).get('length', 0) >= 3:
            run = patterns['current_run']
            message = f"HOT STREAK: {run['team'].upper()} x{run['length']}!"
            self._add_analytics_alert(message, 'pattern', 2.5)

    def _handle_probability_changes(self, probabilities: Dict[str, float]) -> None:
        """
        Handle significant win probability changes.

        Args:
            probabilities: Dictionary containing win probabilities for each team
        """
        threshold = 0.25  # 25% change threshold
        
        if hasattr(self, 'last_probabilities'):
            for team in ['red', 'blue']:
                change = abs(probabilities[team] - self.last_probabilities[team])
                if change >= threshold:
                    message = f"BIG SWING: {team.upper()} TEAM {probabilities[team]:.1%} WIN CHANCE!"
                    self._add_analytics_alert(message, 'probability', 2.0)
        
        self.last_probabilities = probabilities.copy()

    def _calculate_comeback_bonus(self, team: str) -> int:
        """
        Calculate comeback bonus based on score difference and time.

        Args:
            team: The team to calculate bonus for ('red' or 'blue')

        Returns:
            int: The calculated bonus points (0-3)
        """
        if team == 'red':
            score_diff = self.score['blue'] - self.score['red']
        else:
            score_diff = self.score['red'] - self.score['blue']
            
        if score_diff <= 0:
            return 0
            
        time_factor = min(1.0, (self.settings.period_length - self.clock) / self.settings.period_length * 4)
        score_factor = min(1.0, score_diff / 5)
        
        bonus = round(min(3, score_factor * time_factor * 3))
        return bonus

    def _check_comeback_status(self, team: str) -> None:
        """
        Check and update comeback status.

        Tracks when a team initiates a comeback attempt (down by 3+ points)
        and when they complete it (tie or take lead). Triggers appropriate
        sound effects and visual notifications.

        Args:
            team: The team to check ('red' or 'blue')
        """
        if team == 'red':
            score_diff = self.score['blue'] - self.score['red']
        else:
            score_diff = self.score['red'] - self.score['blue']

        # Start tracking comeback if down by 3 or more
        if score_diff >= 3 and not self.comeback_active:
            self.comeback_active = True
            self.comeback_start_score = self.score.copy()
            self.stats['comebacks_started'] += 1
            self._play_sound('comeback_started')
            self._add_analytics_alert(f"{team.upper()} TEAM COMEBACK ATTEMPT!", 'comeback', 2.0)

        # Check if comeback is complete
        elif self.comeback_active and score_diff <= 0:
            self.comeback_active = False
            self.stats['comebacks_completed'] += 1
            self._play_sound('comeback_complete')
            self._add_analytics_alert("COMEBACK COMPLETE!", 'comeback', 3.0)
            self._trigger_effect('comeback_complete', team)

    def _trigger_random_event(self) -> None:
        """
        Trigger a random game event.
        
        Randomly selects and initiates one of the available special events,
        unless the game is in frenzy mode.
        """
        events = [
            self._start_quick_strike,
            self._activate_bonus_goal,
            self._start_combo_challenge
        ]
        
        # Don't start new events in final frenzy
        if not self.frenzy_mode:
            event = random.choice(events)
            event()
        
        # Set next event time (between 20-40 seconds)
        self.next_event_time = datetime.now() + timedelta(seconds=random.randint(20, 40))

    def _start_quick_strike(self) -> None:
        """Start a quick strike challenge."""
        self.quick_strike_active = True
        self.quick_strike_deadline = datetime.now() + timedelta(seconds=15)
        self.active_event = "QUICK STRIKE CHALLENGE! SCORE IN 15 SECONDS!"
        self._play_sound('quick_strike')
        self.stats['quick_strikes_attempted'] += 1

    def _activate_bonus_goal(self) -> None:
        """Activate bonus goal scoring."""
        self.current_goal_value = random.choice([2, 3])
        self.event_duration = datetime.now() + timedelta(seconds=20)
        self.active_event = f"{self.current_goal_value}X POINTS PER GOAL!"
        self._play_sound('bonus')

    def _start_combo_challenge(self) -> None:
        """Start a combo goal challenge."""
        self.combo_count = 0
        self.event_duration = datetime.now() + timedelta(seconds=30)
        self.active_event = "COMBO CHALLENGE! QUICK GOALS FOR BONUS POINTS!"
        self._play_sound('bonus')

    def _start_final_minute_frenzy(self) -> None:
        """Activate final minute frenzy mode."""
        self.frenzy_mode = True
        self.active_event = "FINAL MINUTE FRENZY! ALL GOALS WORTH DOUBLE!"
        self._play_sound('frenzy')
        self._add_analytics_alert("FINAL MINUTE FRENZY ACTIVATED!", 'frenzy', 3.0)

    def _end_quick_strike(self) -> None:
        """End the quick strike challenge."""
        if self.quick_strike_active:
            self.quick_strike_active = False
            self.quick_strike_deadline = None
            self.active_event = None

    def _end_current_event(self) -> None:
        """End the current special event."""
        self.current_goal_value = 1
        self.event_duration = None
        if not self.frenzy_mode:  # Don't clear frenzy message
            self.active_event = None

    def handle_goal(self, team: str) -> None:
        """
        Handle goal scoring with all bonuses.

        Processes goal scoring including all special bonuses and effects:
        - First goal bonus
        - Quick strike bonus
        - Comeback bonus
        - Combo bonus
        - Frenzy mode multiplier

        Args:
            team: The team that scored ('red' or 'blue')
        """
        current_time = datetime.now()
        points = self.current_goal_value
        bonuses = []
        
        # Calculate all bonuses
        if self.first_goal_opportunity:
            points, bonus_text = self._calculate_first_goal_bonus()
            bonuses.append(bonus_text)
        
        # Quick strike bonus
        if self.quick_strike_active:
            points *= 2
            bonuses.append("QUICK STRIKE!")
            self.quick_strike_active = False
            self.stats['quick_strikes_successful'] += 1
            
        # Comeback bonus
        comeback_bonus = self._calculate_comeback_bonus(team)
        if comeback_bonus > 0:
            points += comeback_bonus
            bonuses.append(f"COMEBACK +{comeback_bonus}!")
            self.stats['comeback_goals'] += 1
            
        # Call base class goal handling
        super().handle_goal(team)
            
        # Combo bonus
        if self.combo_count > 0:
            points, combo_text = self._process_combo_bonus(current_time)
            if combo_text:
                bonuses.append(combo_text)
            
        # Final minute frenzy
        if self.frenzy_mode:
            points *= 2
            bonuses.append("FRENZY")
            self.stats['frenzy_goals'] += 1
            
        # Update score and display
        self.score[team] += points
        self.last_goal_time = current_time
        self.stats['total_bonus_multiplier'] += (points / self.current_goal_value - 1)
        
        # Check comeback status
        self._check_comeback_status(team)
        
        # Show all active bonuses
        if bonuses:
            bonus_text = " + ".join(bonuses)
            self.active_event = f"{points} POINTS! {bonus_text}"
        else:
            self.active_event = f"{points} POINTS!"

        # Update analytics after goal
        if self.game.current_analysis:
            analysis = self.game.current_analysis
            if analysis.get('is_critical_moment'):
                self.handle_critical_moment(analysis)

    def _calculate_first_goal_bonus(self) -> Tuple[int, str]:
        """
        Calculate first goal bonus based on timing.

        Returns:
            Tuple[int, str]: The bonus points and bonus text
        """
        time_taken = self.settings.period_length - self.clock
        max_bonus = 3
        bonus = max(1, int(max_bonus * (1 - time_taken / self.first_goal_window)))
        self.first_goal_opportunity = False
        self.stats['bonus_points_earned'] += bonus
        return self.current_goal_value + bonus, f"FIRST GOAL +{bonus}!"

    def _process_combo_bonus(self, current_time: datetime) -> Tuple[int, Optional[str]]:
        """
        Process combo bonus for rapid scoring.

        Args:
            current_time: Current datetime for timing calculations

        Returns:
            Tuple[int, Optional[str]]: The points after combo and combo text if applicable
        """
        points = self.current_goal_value
        combo_text = None
        
        if self.last_goal_time:
            time_since_last = (current_time - self.last_goal_time).total_seconds()
            if time_since_last < self.COMBO_WINDOW:
                self.combo_count += 1
                combo_bonus = min(self.combo_count - 1, self.MAX_COMBO_MULTIPLIER)
                points += combo_bonus
                combo_text = f"COMBO x{self.combo_count}"
                self._play_sound('combo')
                self.stats['max_combo'] = max(self.stats['max_combo'], self.combo_count)
            else:
                self.combo_count = 1
        else:
            self.combo_count = 1
            
        return points, combo_text

    def handle_critical_moment(self, analysis: Dict) -> None:
        """
        Handle critical moments with visual effects.

        Args:
            analysis: Dictionary containing current game analysis data
        """
        super().handle_critical_moment(analysis)
        self.stats['critical_goals'] += 1
        
        # Add intensity-based effects
        if analysis['momentum']['current_state']['intensity'] == 'overwhelming':
            self._add_visual_effect('critical_momentum', (255, 140, 0), 3.0)
            self._add_analytics_alert("Massive Momentum Shift!", 2.0, 'momentum')
        
        # Add time-based effects
        if self.clock <= 60 and abs(self.score['red'] - self.score['blue']) <= 1:
            self._add_visual_effect('critical_time', (255, 0, 0), 3.0)
            self._add_analytics_alert("Critical Moment - Close Game!", 2.0, 'time')

    def _trigger_effect(self, effect_type: str, team: str) -> None:
        """
        Trigger visual effect based on type.

        Args:
            effect_type: Type of effect to trigger
            team: Team the effect is associated with ('red' or 'blue')
        """
        if effect_type == 'comeback_complete':
            self._create_comeback_particles(team)
            self._add_visual_effect('comeback', (255, 215, 0), 3.0)  # Golden color for comeback

    def _create_comeback_particles(self, team: str) -> None:
        """
        Create particles for comeback completion effect.

        Args:
            team: Team that completed the comeback ('red' or 'blue')
        """
        if 'comeback' not in self.particle_images:
            return

        particles = []
        for _ in range(20):  # Create 20 particles
            particle = {
                'image': 'comeback',
                'x': random.randint(0, self.settings.screen_width),
                'y': random.randint(0, self.settings.screen_height),
                'dx': random.uniform(-100, 100),
                'dy': random.uniform(-100, 100),
                'life': random.uniform(1.0, 2.0),
                'max_life': 2.0,
                'alpha': 255
            }
            particles.append(particle)

        self.particle_systems.append({
            'particles': particles,
            'end_time': datetime.now() + timedelta(seconds=2)
        })

    def _play_sound(self, sound_name: str) -> None:
        """
        Play a sound effect with cooldown.

        Args:
            sound_name: Name of the sound effect to play
        """
        current_time = datetime.now()
        if (current_time - self.last_sound_time).total_seconds() >= self.SOUND_COOLDOWN:
            if sound_name in self.crazy_sounds and self.crazy_sounds[sound_name]:
                self.crazy_sounds[sound_name].play()
                self.last_sound_time = current_time

    def _update_sound_system(self, current_time: datetime) -> None:
        """
        Update sound system and handle random sounds.

        Args:
            current_time: Current datetime for timing calculations
        """
        if (self.game.sounds_enabled and 
            current_time.timestamp() - self.last_random_sound_time >= self.next_random_sound_interval):
            self.play_random_sound()
            self.last_random_sound_time = current_time.timestamp()
            self.next_random_sound_interval = self.get_next_random_sound_interval()

    def _update_visual_effects(self) -> None:
        """
        Update all visual effects for the current frame.
        
        Updates both particle systems and animations, removing expired effects
        and updating positions and states of active ones.
        """
        self._update_particle_systems()
        self._update_animations()

    def _update_particle_systems(self) -> None:
        """Update and maintain particle systems."""
        # Remove expired systems
        self.particle_systems = [
            system for system in self.particle_systems
            if datetime.now() < system['end_time']
        ]
        
        # Limit total particles across all systems
        total_particles = sum(len(system['particles']) for system in self.particle_systems)
        if total_particles > self.MAX_PARTICLES:
            factor = self.MAX_PARTICLES / total_particles
            for system in self.particle_systems:
                system['particles'] = system['particles'][:int(len(system['particles']) * factor)]
        
        # Update remaining particles
        for system in self.particle_systems:
            self._update_particle_system(system)

    def _update_particle_system(self, system: Dict) -> None:
        """
        Update particles in a particle system.

        Args:
            system: Dictionary containing particle system data
        """
        dt = self.game.clock.get_time() / 1000.0
        system['particles'] = [
            {**p, 
             'life': p['life'] - dt,
             'x': p['x'] + p['dx'] * dt,
             'y': p['y'] + p['dy'] * dt,
             'alpha': int(255 * (p['life'] / p['max_life']))
            }
            for p in system['particles']
            if p['life'] > 0
        ]

    def _update_animations(self) -> None:
        """Update animation frames and timing."""
        current_time = datetime.now()
        self.active_animations = [
            anim for anim in self.active_animations
            if current_time < anim['end_time']
        ]
        
        for anim in self.active_animations:
            anim['frame'] = int(
                (current_time - anim['start_time']).total_seconds() 
                * anim['fps']
            ) % len(anim['frames'])

    def draw(self) -> None:
        """
        Draw the game screen for the current frame.
        
        Renders all game elements in the following order:
        1. Background
        2. Base game elements
        3. Game mode specific elements
        4. Visual effects and overlays
        5. UI elements and text
        """
        # Draw background
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(self.settings.bg_color)

        # Draw base game elements
        super().draw()
        
        # Draw mode-specific elements
        self._draw_game_elements()
        
        # Draw effects and overlays
        self._draw_effects()
        
        # Draw UI elements
        self._draw_ui_elements()

    def _draw_game_elements(self) -> None:
        """Draw game mode specific elements."""
        if self.quick_strike_active:
            self._draw_quick_strike()
        
        if self.frenzy_mode and self.frenzy_overlay:
            overlay = self.frenzy_overlay.copy()
            overlay.set_alpha(100)
            self.screen.blit(overlay, (0, 0))

    def _draw_effects(self) -> None:
        """Draw all visual effects."""
        self._draw_visual_effects()
        self._draw_particle_systems()
        
        if self.show_analytics:
            self._draw_analytics_alerts()

    def _draw_ui_elements(self) -> None:
        """Draw UI elements and text."""
        if self.active_event:
            self._draw_event_text()

    def _draw_quick_strike(self) -> None:
        """
        Draw quick strike challenge elements.
        
        Displays the countdown timer and visual overlay for
        the quick strike challenge.
        """
        if not self.quick_strike_deadline:
            return
            
        remaining = (self.quick_strike_deadline - datetime.now()).total_seconds()
        if remaining > 0:
            if self.quick_strike_overlay:
                self.screen.blit(self.quick_strike_overlay, (0, 0))
            
            timer_text = self.font_large.render(f"{int(remaining)}s", True, (255, 255, 0))
            timer_rect = timer_text.get_rect(center=(self.settings.screen_width // 2, 240))
            self.screen.blit(timer_text, timer_rect)

    def _draw_visual_effects(self) -> None:
        """Draw active visual effects."""
        for effect in self.visual_effects:
            if effect['type'] == 'critical_momentum':
                s = pygame.Surface((self.settings.screen_width, self.settings.screen_height))
                s.set_alpha(int(128 * (effect['duration'] / 3.0)))
                s.fill(effect['color'])
                self.screen.blit(s, (0, 0))
            elif effect['type'] == 'critical_time':
                if self.critical_moment_overlay:
                    self.critical_moment_overlay.set_alpha(
                        int(255 * (effect['duration'] / 3.0))
                    )
                    self.screen.blit(self.critical_moment_overlay, (0, 0))

    def _draw_particle_systems(self) -> None:
        """Draw all active particle systems."""
        for system in self.particle_systems:
            for particle in system['particles']:
                if particle['image'] in self.particle_images:
                    img = self.particle_images[particle['image']].copy()
                    img.set_alpha(particle['alpha'])
                    self.screen.blit(img, (particle['x'], particle['y']))

    def _draw_event_text(self) -> None:
        """Draw active event text with effects."""
        text_surface = self.font_large.render(self.active_event, True, (255, 140, 0))
        text_rect = text_surface.get_rect(center=(self.settings.screen_width // 2, 200))
        self.screen.blit(text_surface, text_rect)

    def _add_analytics_alert(self, message: str, alert_type: str, duration: float) -> None:
        """
        Add a new analytics alert.

        Args:
            message: Alert message to display
            alert_type: Type of alert for styling
            duration: Duration to display the alert in seconds
        """
        self.analytics_alert_queue.append({
            'message': message,
            'type': alert_type,
            'duration': duration,
            'end_time': datetime.now() + timedelta(seconds=duration)
        })

    def get_next_random_sound_interval(self) -> float:
        """
        Get the next random sound interval.

        Returns:
            float: Time in seconds until next random sound
        """
        return random.uniform(
            self.settings.random_sound_min_interval,
            self.settings.random_sound_max_interval
        )

    def play_random_sound(self) -> None:
        """Play a random sound effect from available sounds."""
        if not self.game.sounds_enabled:
            return
            
        available_sounds = []
        if self.game.sounds.get('random_sounds'):
            available_sounds.extend(self.game.sounds['random_sounds'])
        if self.crazy_sounds:
            available_sounds.extend(list(self.crazy_sounds.values()))
                
        if available_sounds:
            sound = random.choice(available_sounds)
            if sound:
                sound.play()
                logging.debug("Random sound played")

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
        # Call base class cleanup first
        super().cleanup()
        
        # Stop any playing sounds
        for sound in self.crazy_sounds.values():
            if sound:
                sound.stop()
        
        # Clear sound references
        self.crazy_sounds.clear()
        
        # Unload pygame surfaces
        for surface_name in ['background', 'overlay', 'bonus_indicator', 
                           'frenzy_overlay', 'quick_strike_overlay']:
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
        
        logging.info('Crazy Play mode cleanup completed')
        logging.info(f"Final stats: {self.stats}")
