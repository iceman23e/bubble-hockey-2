# database.py

import sqlite3
import logging
import json
from datetime import datetime
import os

class Database:
    def __init__(self):
        # Ensure database directory exists
        os.makedirs('database', exist_ok=True)
        self.conn = sqlite3.connect('database/bubble_hockey.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
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

        # Create state_history table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS state_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                state TEXT,
                timestamp TEXT,
                state_data TEXT,
                FOREIGN KEY(game_id) REFERENCES game_history(id)
            )
        ''')

        # Create diagnostics_log table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnostics_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                sensor_name TEXT,
                event_type TEXT,
                data TEXT
            )
        ''')

        self.conn.commit()

    def start_new_game(self, mode):
        """Start a new game and return the game ID."""
        try:
            date_time = datetime.now().isoformat()
            self.cursor.execute('''
                INSERT INTO game_history (date_time, mode)
                VALUES (?, ?)
            ''', (date_time, mode))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logging.error(f"Error starting new game: {e}")
            return None

    def end_game(self, game_id, score):
        """End a game with final scores."""
        try:
            duration = self._calculate_game_duration(game_id)
            winner_id = self._determine_winner(score)
            
            self.cursor.execute('''
                UPDATE game_history
                SET score_red = ?, score_blue = ?, duration = ?, winner_id = ?
                WHERE id = ?
            ''', (score['red'], score['blue'], duration, winner_id, game_id))
            self.conn.commit()
            
            logging.info(f"Game {game_id} ended with scores: Red {score['red']}, Blue {score['blue']}")
        except sqlite3.Error as e:
            logging.error(f"Error ending game: {e}")

    def record_goal(self, game_id, team):
        """Record a goal event."""
        try:
            self.cursor.execute('''
                INSERT INTO goal_events (game_id, team, time)
                VALUES (?, ?, ?)
            ''', (game_id, team, datetime.now().isoformat()))
            self.conn.commit()
            logging.info(f"Goal recorded for {team} team in game {game_id}")
        except sqlite3.Error as e:
            logging.error(f"Error recording goal: {e}")

    def save_game_state(self, game_id, state_data):
        """Save current game state."""
        try:
            self.cursor.execute('''
                INSERT INTO state_history (game_id, state, timestamp, state_data)
                VALUES (?, ?, ?, ?)
            ''', (game_id, state_data['state'], datetime.now().isoformat(), 
                  json.dumps(state_data)))
            self.conn.commit()
            logging.debug(f"Game state saved for game {game_id}")
        except sqlite3.Error as e:
            logging.error(f"Error saving game state: {e}")

    def get_last_game_state(self, game_id):
        """Retrieve the last saved state for a game."""
        try:
            self.cursor.execute('''
                SELECT state_data FROM state_history 
                WHERE game_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            ''', (game_id,))
            result = self.cursor.fetchone()
            return json.loads(result[0]) if result else None
        except sqlite3.Error as e:
            logging.error(f"Error retrieving game state: {e}")
            return None

    def log_diagnostic_event(self, sensor_name, event_type, data):
        """Log a diagnostic event."""
        try:
            self.cursor.execute('''
                INSERT INTO diagnostics_log (timestamp, sensor_name, event_type, data)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), sensor_name, event_type, 
                  json.dumps(data) if isinstance(data, dict) else str(data)))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error logging diagnostic event: {e}")

    def get_goal_trends(self):
        """Get goal scoring trends."""
        try:
            self.cursor.execute('''
                SELECT strftime('%H:%M', time) AS minute, team, COUNT(*) AS goals
                FROM goal_events
                GROUP BY minute, team
                ORDER BY minute
            ''')
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error retrieving goal trends: {e}")
            return []

    def get_game_stats(self, game_id):
        """Get comprehensive stats for a game."""
        try:
            self.cursor.execute('''
                SELECT gh.*, 
                       COUNT(ge.id) as total_goals,
                       AVG(CASE WHEN gh.duration > 0 
                           THEN CAST(COUNT(ge.id) AS FLOAT) / gh.duration 
                           ELSE 0 END) as goals_per_minute
                FROM game_history gh
                LEFT JOIN goal_events ge ON gh.id = ge.game_id
                WHERE gh.id = ?
                GROUP BY gh.id
            ''', (game_id,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Error retrieving game stats: {e}")
            return None

    def _calculate_game_duration(self, game_id):
        """Calculate the duration of a game."""
        try:
            self.cursor.execute('''
                SELECT date_time FROM game_history WHERE id = ?
            ''', (game_id,))
            start_time = datetime.fromisoformat(self.cursor.fetchone()[0])
            return int((datetime.now() - start_time).total_seconds())
        except (sqlite3.Error, TypeError) as e:
            logging.error(f"Error calculating game duration: {e}")
            return 0

    def _determine_winner(self, score):
        """Determine the winner based on scores."""
        if score['red'] > score['blue']:
            return 'red'
        elif score['blue'] > score['red']:
            return 'blue'
        return None

    def vacuum_old_records(self, days_to_keep=30):
        """Clean up old records to prevent database bloat."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            self.cursor.execute('''
                DELETE FROM goal_events 
                WHERE game_id IN (
                    SELECT id FROM game_history 
                    WHERE date_time < ?
                )
            ''', (cutoff_date,))
            self.cursor.execute('VACUUM')
            self.conn.commit()
            logging.info(f"Cleaned up records older than {days_to_keep} days")
        except sqlite3.Error as e:
            logging.error(f"Error cleaning up old records: {e}")

    def close(self):
        """Close the database connection."""
        self.conn.close()
        logging.info('Database connection closed')
