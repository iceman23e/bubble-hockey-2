# game_analytics/exceptions.py

class AnalyticsError(Exception):
    """Base exception for analytics errors"""
    pass

class InsufficientDataError(AnalyticsError):
    """Raised when not enough data exists for meaningful analysis"""
    pass

class InvalidGameStateError(AnalyticsError):
    """Raised when game state is invalid or inconsistent"""
    pass

class InvalidSensorDataError(AnalyticsError):
    """Raised when sensor data is invalid or in unexpected format"""
    pass

class DatabaseError(AnalyticsError):
    """Raised when database operations fail"""
    pass

class ConfigurationError(AnalyticsError):
    """Raised when system configuration is invalid"""
    pass
