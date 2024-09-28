# database.py

import sqlite3
import logging
from datetime import datetime

class Database:
    def __init__(self):
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
        self.conn.commit()

    def start_new_game(self, mode):
        date_time = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO game_history (date_time, mode)
            VALUES (?, ?)
        ''', (date_time, mode))
        self.conn.commit()
        return self.cursor.lastrowid  # Return the game ID

    def end_game(self, game_id, score):
        # Update the game history with the final score
        self.cursor.execute('''
            UPDATE game_history
            SET score_red = ?, score_blue = ?, duration = ?, winner_id = ?
            WHERE id = ?
        ''', (score['red'], score['blue'], 0, 0, game_id))  # Adjust duration and winner_id as needed
        self.conn.commit()

    def get_goal_trends(self):
        self.cursor.execute('''
            SELECT strftime('%H:%M', time) AS minute, team, COUNT(*) AS goals
            FROM goal_events
            GROUP BY minute, team
            ORDER BY minute
        ''')
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
        logging.info('Database connection closed')
