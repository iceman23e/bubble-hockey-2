# database.py

import sqlite3
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

class Database:
    def __init__(self):
        # Ensure database directory exists
        os.makedirs('database', exist_ok=True)
        
        self.conn = sqlite3.connect('database/bubble_hockey.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Create all necessary database tables"""
        # Create users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                avatar TEXT
            )
        ''')

        # Create game_stats table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                goals_scored INTEGER DEFAULT 0,
                goals_allowed INTEGER DEFAULT 0,
                power_ups_used INTEGER DEFAULT 0,
                taunts_used INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Create game_history table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time TEXT,
                mode TEXT,
                player_red_id INTEGER,
                player_blue_id INTEGER,
                score_red INTEGER,
                score_blue INTEGER,
                duration INTEGER,
                winner_id INTEGER,
                FOREIGN KEY(player_red_id) REFERENCES users(id),
                FOREIGN KEY(player_blue_id) REFERENCES users(id),
                FOREIGN KEY(winner_id) REFERENCES users(id)
            )
        ''')

        # Create goal_events table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                team TEXT,
                time TIMESTAMP,
                FOREIGN KEY(game_id) REFERENCES game_history(id)
            )
        ''')

        # Create analytics_history table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                timestamp TEXT,
                win_probability_red REAL,
                win_probability_blue REAL,
                momentum_team TEXT,
                momentum_score REAL,
                momentum_intensity TEXT,
                is_critical_moment BOOLEAN,
                period INTEGER,
                time_remaining REAL,
                score_red INTEGER,
                score_blue INTEGER,
                FOREIGN KEY(game_id) REFERENCES game_history(id)
            )
        ''')

        # Create scoring_patterns table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS scoring_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                pattern_type TEXT,
                team TEXT,
                start_time REAL,
                end_time REAL,
                goals_count INTEGER,
                pattern_data TEXT,
                FOREIGN KEY(game_id) REFERENCES game_history(id)
            )
        ''')

        self.conn.commit()

    def start_new_game(self, mode: str) -> int:
        """Start a new game and return the game ID"""
        date_time = datetime.now().isoformat()
        try:
            self.cursor.execute('''
                INSERT INTO game_history (date_time, mode)
                VALUES (?, ?)
            ''', (date_time, mode))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logging.error(f"Error starting new game: {e}")
            return -1

    def end_game(self, game_id: int, score: Dict[str, int]):
        """Update the game history with the final score"""
        try:
            self.cursor.execute('''
                UPDATE game_history
                SET score_red = ?, score_blue = ?
                WHERE id = ?
            ''', (score['red'], score['blue'], game_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error ending game: {e}")

    def record_goal(self, game_id: int, team: str, time: float):
        """Record a goal event"""
        try:
            self.cursor.execute('''
                INSERT INTO goal_events (game_id, team, time)
                VALUES (?, ?, ?)
            ''', (game_id, team, time))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error recording goal: {e}")

    def save_game_state(self, game_id: int, analysis_data: Dict[str, Any]):
        """Save analytics data for the current game state"""
        try:
            analytics = analysis_data['analysis']
            self.cursor.execute('''
                INSERT INTO analytics_history (
                    game_id, timestamp, win_probability_red, win_probability_blue,
                    momentum_team, momentum_score, momentum_intensity,
                    is_critical_moment, period, time_remaining, score_red, score_blue
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_id,
                analysis_data['timestamp'],
                analytics['win_probability']['red'],
                analytics['win_probability']['blue'],
                analytics['momentum']['current_state']['team'],
                analytics['momentum']['current_state']['score'],
                analytics['momentum']['current_state']['intensity'],
                analytics['is_critical_moment'],
                analytics.get('period', 1),
                analytics.get('time_remaining', 0),
                analytics.get('score', {}).get('red', 0),
                analytics.get('score', {}).get('blue', 0)
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error saving game state: {e}")

    def save_scoring_pattern(self, game_id: int, pattern_data: Dict[str, Any]):
        """Save a scoring pattern"""
        try:
            self.cursor.execute('''
                INSERT INTO scoring_patterns (
                    game_id, pattern_type, team, start_time, end_time,
                    goals_count, pattern_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_id,
                pattern_data['type'],
                pattern_data['team'],
                pattern_data['start_time'],
                pattern_data['end_time'],
                pattern_data['goals_count'],
                str(pattern_data['details'])
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error saving scoring pattern: {e}")

    def get_game_stats(self, game_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get game statistics"""
        try:
            if game_id:
                self.cursor.execute('''
                    SELECT * FROM game_history WHERE id = ?
                ''', (game_id,))
            else:
                self.cursor.execute('SELECT * FROM game_history')
            
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting game stats: {e}")
            return []

    def get_winners_by_differential(self, diff: int) -> Dict[str, float]:
        """Get historical win rates for a given score differential"""
        try:
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN (score_red - score_blue) >= ? 
                        AND winner_id = player_red_id THEN 1 ELSE 0 END) as red_wins,
                    SUM(CASE WHEN (score_blue - score_red) >= ? 
                        AND winner_id = player_blue_id THEN 1 ELSE 0 END) as blue_wins
                FROM game_history
                WHERE ABS(score_red - score_blue) >= ?
            ''', (diff, diff, abs(diff)))
            
            result = self.cursor.fetchone()
            if result and result[0] > 0:
                total = result[0]
                return {
                    'total_games': total,
                    'win_rate': (result[1] + result[2]) / total if total > 0 else 0.5
                }
            return {'total_games': 0, 'win_rate': 0.5}
        except sqlite3.Error as e:
            logging.error(f"Error getting winners by differential: {e}")
            return {'total_games': 0, 'win_rate': 0.5}

    def get_period_stats(self, period: int) -> Dict[str, Any]:
        """Get statistics for a specific period"""
        try:
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_goals,
                    SUM(CASE WHEN team = 'red' THEN 1 ELSE 0 END) as red_goals,
                    SUM(CASE WHEN team = 'blue' THEN 1 ELSE 0 END) as blue_goals
                FROM goal_events
                WHERE time >= ? AND time < ?
            ''', (period * 180, (period + 1) * 180))
            
            result = self.cursor.fetchone()
            if result:
                return {
                    'total_goals': result[0],
                    'red_goals': result[1],
                    'blue_goals': result[2]
                }
            return {'total_goals': 0, 'red_goals': 0, 'blue_goals': 0}
        except sqlite3.Error as e:
            logging.error(f"Error getting period stats: {e}")
            return {'total_goals': 0, 'red_goals': 0, 'blue_goals': 0}

    def get_recent_goals(self, game_id: int, window: int = 60) -> List[Dict[str, Any]]:
        """Get goals within recent time window"""
        try:
            self.cursor.execute('''
                SELECT * FROM goal_events
                WHERE game_id = ?
                AND time >= (
                    SELECT MAX(time) FROM goal_events 
                    WHERE game_id = ?
                ) - ?
                ORDER BY time DESC
            ''', (game_id, game_id, window))
            
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting recent goals: {e}")
            return []

    def get_analytics_history(self, game_id: int) -> List[Dict[str, Any]]:
        """Get analytics history for a game"""
        try:
            self.cursor.execute('''
                SELECT * FROM analytics_history
                WHERE game_id = ?
                ORDER BY timestamp
            ''', (game_id,))
            
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting analytics history: {e}")
            return []

    def get_scoring_patterns(self, game_id: int) -> List[Dict[str, Any]]:
        """Get scoring patterns for a game"""
        try:
            self.cursor.execute('''
                SELECT * FROM scoring_patterns
                WHERE game_id = ?
                ORDER BY start_time
            ''', (game_id,))
            
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting scoring patterns: {e}")
            return []

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logging.info('Database connection closed')
