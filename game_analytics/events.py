# game_analytics/events.py

from enum import Enum
from typing import Callable, Dict, List, Any
import logging
from .exceptions import InvalidSensorDataError

class SensorType(Enum):
    """Types of sensors/data inputs"""
    GOALS = "goals"
    TIME = "time"
    POSSESSION = "possession"
    SHOTS = "shots"
    PLAYER_POSITIONS = "player_positions"

class AnalyticsEvent:
    """Represents an analytics event"""
    def __init__(self, sensor_type: SensorType, data: Any, timestamp=None):
        self.sensor_type = sensor_type
        self.data = data
        self.timestamp = timestamp or datetime.now()

class AnalyticsEventSystem:
    """Event system for handling sensor data and analytics updates"""
    
    def __init__(self):
        self.handlers: Dict[SensorType, List[Callable]] = {
            sensor_type: [] for sensor_type in SensorType
        }
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging for the event system"""
        self.logger = logging.getLogger('analytics.events')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def register_handler(self, sensor_type: SensorType, 
                        handler: Callable) -> None:
        """
        Register a new handler for a sensor type
        
        Args:
            sensor_type: Type of sensor data this handler processes
            handler: Callback function to handle the data
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")
            
        self.handlers[sensor_type].append(handler)
        self.logger.info(f"Registered new handler for {sensor_type.value}")

    def unregister_handler(self, sensor_type: SensorType, 
                          handler: Callable) -> None:
        """
        Unregister a handler for a sensor type
        
        Args:
            sensor_type: Type of sensor data
            handler: Handler to remove
        """
        if handler in self.handlers[sensor_type]:
            self.handlers[sensor_type].remove(handler)
            self.logger.info(f"Unregistered handler for {sensor_type.value}")

    def process_sensor_data(self, sensor_type: SensorType, 
                           data: Any) -> None:
        """
        Process new sensor data
        
        Args:
            sensor_type: Type of sensor data
            data: The sensor data to process
        
        Raises:
            InvalidSensorDataError: If data validation fails
        """
        try:
            self._validate_sensor_data(sensor_type, data)
            event = AnalyticsEvent(sensor_type, data)
            
            for handler in self.handlers[sensor_type]:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"Handler error for {sensor_type.value}: {e}")
                    
            self.logger.debug(f"Processed {sensor_type.value} data successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing {sensor_type.value} data: {e}")
            raise InvalidSensorDataError(f"Invalid {sensor_type.value} data: {e}")

    def _validate_sensor_data(self, sensor_type: SensorType, 
                            data: Any) -> None:
        """
        Validate sensor data based on type
        
        Args:
            sensor_type: Type of sensor data
            data: The data to validate
            
        Raises:
            InvalidSensorDataError: If validation fails
        """
        if sensor_type == SensorType.GOALS:
            if not isinstance(data, (dict, GoalEvent)):
                raise InvalidSensorDataError("Goal data must be dict or GoalEvent")
        elif sensor_type == SensorType.TIME:
            if not isinstance(data, (int, float)):
                raise InvalidSensorDataError("Time data must be numeric")
        elif sensor_type == SensorType.POSSESSION:
            if not isinstance(data, str) or data not in ['red', 'blue', 'in_play']:
                raise InvalidSensorDataError("Invalid possession data")
                
        # Add validation for future sensor types here

    def get_registered_handlers(self, sensor_type: SensorType) -> List[Callable]:
        """
        Get all handlers registered for a sensor type
        
        Args:
            sensor_type: Type of sensor data
            
        Returns:
            List of handler functions
        """
        return self.handlers[sensor_type]

    def clear_handlers(self, sensor_type: Optional[SensorType] = None) -> None:
        """
        Clear handlers for a specific sensor type or all handlers
        
        Args:
            sensor_type: Type of sensor data, or None to clear all
        """
        if sensor_type is None:
            self.handlers = {sensor_type: [] for sensor_type in SensorType}
            self.logger.info("Cleared all handlers")
        else:
            self.handlers[sensor_type] = []
            self.logger.info(f"Cleared handlers for {sensor_type.value}")
