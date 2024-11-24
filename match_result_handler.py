# match_result_handler.py

from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
from player import Player

class MatchResult:
    """Stores data about a completed match."""
    def __init__(self,
                 match_id: str,
                 red_player: Player,
                 blue_player: Player,
                 winner: str,
                 red_score: int,
                 blue_score: int,
                 match_date: datetime,
                 game_mode: str,
                 analytics_data: Optional[Dict] = None):
        self.match_id = match_id
        self.red_player = red_player
        self.blue_player = blue_player
        self.winner = winner
        self.red_score = red_score
        self.blue_score = blue_score
        self.match_date = match_date
        self.game_mode = game_mode
        self.analytics_data = analytics_data or {}
        self.rating_changes: Dict[str, Tuple[float, float]] = {}  # {player_id: (old_rating, new_rating)}

    def to_dict(self) -> Dict:
        """Convert match result to dictionary for storage."""
        return {
            'match_id': self.match_id,
            'red_player_id': self.red_player.id,
            'blue_player_id': self.blue_player.id,
            'winner': self.winner,
            'red_score': self.red_score,
            'blue_score': self.blue_score,
            'match_date': self.match_date.isoformat(),
            'game_mode': self.game_mode,
            'analytics_data': self.analytics_data,
            'rating_changes': self.rating_changes
        }

    @classmethod
    def from_dict(cls, data: Dict, player_db) -> 'MatchResult':
        """Create MatchResult instance from dictionary."""
        return cls(
            match_id=data['match_id'],
            red_player=player_db.get_player(data['red_player_id']),
            blue_player=player_db.get_player(data['blue_player_id']),
            winner=data['winner'],
            red_score=data['red_score'],
            blue_score=data['blue_score'],
            match_date=datetime.fromisoformat(data['match_date']),
            game_mode=data['game_mode'],
            analytics_data=data.get('analytics_data', {})
        )

class MatchResultHandler:
    """Handles processing of match results and rating updates."""
    
    def __init__(self, rating_system):
        self.rating_system = rating_system
        self.matches: Dict[str, MatchResult] = {}
        self.match_history: Dict[str, list] = {}  # player_id: [match_ids]

    def process_result(self,
                      winner: Player,
                      loser: Player,
                      match_result: MatchResult) -> None:
        """
        Process a match result and update player ratings/stats.
        
        Args:
            winner: Winning player
            loser: Losing player
            match_result: Complete match result data
        """
        try:
            # Store match result
            self.matches[match_result.match_id] = match_result
            
            # Update match history for both players
            for player_id in [winner.id, loser.id]:
                if player_id not in self.match_history:
                    self.match_history[player_id] = []
                self.match_history[player_id].append(match_result.match_id)

            # Calculate rating changes
            old_winner_rating = winner.elo
            old_loser_rating = loser.elo

            # Get analytics factors
            analytics = self._process_analytics(match_result.analytics_data)
            
            # Calculate new ratings
            new_winner_rating, new_loser_rating = self.rating_system.calculate_new_ratings(
                winner_rating=old_winner_rating,
                loser_rating=old_loser_rating,
                score_diff=abs(match_result.red_score - match_result.blue_score),
                analytics_factors=analytics
            )

            # Store rating changes in match result
            match_result.rating_changes = {
                winner.id: (old_winner_rating, new_winner_rating),
                loser.id: (old_loser_rating, new_loser_rating)
            }

            # Update player ratings
            winner.elo = new_winner_rating
            loser.elo = new_loser_rating

            # Update player stats
            self._update_player_stats(winner, loser, match_result)
            
            logging.info(
                f"Processed match result: {winner.name} ({new_winner_rating:.1f}) "
                f"vs {loser.name} ({new_loser_rating:.1f})"
            )

        except Exception as e:
            logging.error(f"Error processing match result: {e}")
            raise

    def _process_analytics(self, analytics_data: Dict) -> Dict:
        """Process analytics data for rating adjustments."""
        try:
            return {
                'momentum_factor': min(1.2, analytics_data.get('momentum', {})
                    .get('dominance_ratio', 1.0)),
                'comeback_factor': 1.2 if analytics_data.get('patterns', {})
                    .get('comeback_completed', False) else 1.0,
                'skill_factor': self._calculate_skill_factor(analytics_data)
            }
        except Exception as e:
            logging.warning(f"Error processing analytics data: {e}")
            return {'momentum_factor': 1.0, 'comeback_factor': 1.0, 'skill_factor': 1.0}

    def _calculate_skill_factor(self, analytics_data: Dict) -> float:
        """Calculate skill factor based on analytics data."""
        try:
            skill_indicators = analytics_data.get('skill_indicators', {})
            
            # Normalize each indicator to 0-1 range
            quick_reactions = skill_indicators.get('quick_response_rate', 0) / 100
            combo_efficiency = skill_indicators.get('combo_success_rate', 0) / 100
            power_up_usage = skill_indicators.get('power_up_efficiency', 0)
            
            # Weight and combine factors
            weights = {'quick': 0.4, 'combo': 0.3, 'power_up': 0.3}
            skill_score = (
                quick_reactions * weights['quick'] +
                combo_efficiency * weights['combo'] +
                power_up_usage * weights['power_up']
            )
            
            # Convert to factor (0.8 - 1.2 range)
            return 0.8 + (skill_score * 0.4)
            
        except Exception as e:
            logging.warning(f"Error calculating skill factor: {e}")
            return 1.0

    def _update_player_stats(self,
                           winner: Player,
                           loser: Player,
                           match_result: MatchResult) -> None:
        """Update player statistics based on match result."""
        try:
            # Update basic stats for both players
            for player in [winner, loser]:
                player.stats.total_matches += 1
                if player == winner:
                    player.stats.wins += 1
                    player.stats.current_win_streak += 1
                    player.stats.best_win_streak = max(
                        player.stats.best_win_streak,
                        player.stats.current_win_streak
                    )
                else:
                    player.stats.losses += 1
                    player.stats.current_win_streak = 0

                # Update game mode stats
                if match_result.game_mode not in player.stats.mode_stats:
                    player.stats.mode_stats[match_result.game_mode] = {
                        'matches': 0,
                        'wins': 0,
                        'losses': 0
                    }
                mode_stats = player.stats.mode_stats[match_result.game_mode]
                mode_stats['matches'] += 1
                if player == winner:
                    mode_stats['wins'] += 1
                else:
                    mode_stats['losses'] += 1

            # Update analytics-based stats
            winner.update_stats_from_analytics(match_result.analytics_data)
            loser.update_stats_from_analytics(match_result.analytics_data)

        except Exception as e:
            logging.error(f"Error updating player stats: {e}")

    def get_player_match_history(self,
                               player_id: str,
                               limit: Optional[int] = None) -> list:
        """Get match history for a player."""
        try:
            match_ids = self.match_history.get(player_id, [])
            if limit:
                match_ids = match_ids[-limit:]
            return [self.matches[mid] for mid in match_ids
                    if mid in self.matches]
        except Exception as e:
            logging.error(f"Error getting match history: {e}")
            return []

    def get_head_to_head_stats(self,
                              player1_id: str,
                              player2_id: str) -> Dict:
        """Get head-to-head statistics for two players."""
        try:
            # Find common matches
            player1_matches = set(self.match_history.get(player1_id, []))
            player2_matches = set(self.match_history.get(player2_id, []))
            common_matches = player1_matches.intersection(player2_matches)

            stats = {
                'total_matches': 0,
                'player1_wins': 0,
                'player2_wins': 0,
                'avg_score_diff': 0,
                'last_match': None
            }

            score_diffs = []
            for match_id in common_matches:
                match = self.matches[match_id]
                stats['total_matches'] += 1
                if match.winner == player1_id:
                    stats['player1_wins'] += 1
                else:
                    stats['player2_wins'] += 1
                
                score_diff = abs(match.red_score - match.blue_score)
                score_diffs.append(score_diff)

                if not stats['last_match'] or \
                   match.match_date > stats['last_match'].match_date:
                    stats['last_match'] = match

            if score_diffs:
                stats['avg_score_diff'] = sum(score_diffs) / len(score_diffs)

            return stats

        except Exception as e:
            logging.error(f"Error getting head-to-head stats: {e}")
            return {}
