import logging
import json
from datetime import datetime, timedelta
from .base_scraper import BaseScraper
from src.database.database import db
from src.database.models import ActualResults, Player

class ActualResultsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.api_base = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        
    def scrape_week_results(self, season, week):
        """Scrape actual player performance for a specific week"""
        actual_results = []
        
        try:
            # Get scoreboard for the week to find completed games
            scoreboard_url = f"{self.api_base}/scoreboard"
            params = {
                'seasontype': 2,  # Regular season
                'week': week,
                'year': season
            }
            
            response = self.get_page(scoreboard_url, params=params)
            if not response or response.status_code != 200:
                self.logger.error(f"Failed to get scoreboard for week {week}")
                return actual_results
                
            scoreboard_data = response.json()
            
            # Process each completed game
            if 'events' in scoreboard_data:
                for game in scoreboard_data['events']:
                    if game.get('status', {}).get('type', {}).get('completed', False):
                        game_results = self._scrape_game_stats(game, season, week)
                        actual_results.extend(game_results)
                        
        except Exception as e:
            self.logger.error(f"Error scraping week {week} results: {e}")
            
        return actual_results
        
    def _scrape_game_stats(self, game, season, week):
        """Scrape player stats from a specific game"""
        game_results = []
        
        try:
            game_id = game.get('id')
            if not game_id:
                return game_results
                
            # Get detailed game stats
            game_stats_url = f"{self.api_base}/summary"
            params = {'event': game_id}
            
            response = self.get_page(game_stats_url, params=params)
            if not response or response.status_code != 200:
                return game_results
                
            game_data = response.json()
            
            # Extract team information
            teams = game_data.get('header', {}).get('competitions', [{}])[0].get('competitors', [])
            game_date = self._parse_game_date(game.get('date'))
            
            # Process each team's stats
            for team in teams:
                team_abbr = team.get('team', {}).get('abbreviation', '')
                is_home = team.get('homeAway') == 'home'
                
                # Get player statistics
                team_stats = self._get_team_player_stats(game_id, team_abbr)
                
                for player_stats in team_stats:
                    result = self._create_actual_result(
                        player_stats, season, week, game_date, is_home, teams
                    )
                    if result:
                        game_results.append(result)
                        
        except Exception as e:
            self.logger.error(f"Error scraping game stats: {e}")
            
        return game_results
        
    def _get_team_player_stats(self, game_id, team_abbr):
        """Get player statistics for a team in a specific game"""
        try:
            # This would typically require the ESPN player stats API endpoint
            # For now, return sample data structure
            # In production, you'd call something like:
            # stats_url = f"{self.api_base}/boxscore"
            # params = {'event': game_id}
            
            # Simulate actual player stats (replace with real API call)
            sample_stats = [
                {
                    'player_name': 'Sample Player',
                    'team': team_abbr,
                    'position': 'QB',
                    'passing_attempts': 35,
                    'passing_completions': 25,
                    'passing_yards': 285,
                    'passing_tds': 2,
                    'interceptions': 1,
                    'rushing_attempts': 3,
                    'rushing_yards': 15,
                    'rushing_tds': 0,
                    'targets': 0,
                    'receptions': 0,
                    'receiving_yards': 0,
                    'receiving_tds': 0
                }
            ]
            
            return sample_stats
            
        except Exception as e:
            self.logger.error(f"Error getting team player stats: {e}")
            return []
            
    def _create_actual_result(self, player_stats, season, week, game_date, is_home, teams):
        """Create ActualResults object from player stats"""
        try:
            # Find player in database
            session = db.get_session()
            player = session.query(Player).filter_by(
                name=player_stats['player_name'],
                team=player_stats['team']
            ).first()
            
            if not player:
                db.close_session(session)
                return None
                
            # Calculate fantasy points
            fantasy_points = self._calculate_fantasy_points(player_stats)
            
            # Determine opponent and game result
            opponent = self._get_opponent_team(player_stats['team'], teams)
            game_result = self._determine_game_result(player_stats['team'], teams)
            
            actual_result = {
                'player_id': player.id,
                'season': season,
                'week': week,
                'actual_passing_attempts': player_stats.get('passing_attempts', 0),
                'actual_passing_completions': player_stats.get('passing_completions', 0),
                'actual_passing_yards': player_stats.get('passing_yards', 0),
                'actual_passing_tds': player_stats.get('passing_tds', 0),
                'actual_interceptions': player_stats.get('interceptions', 0),
                'actual_rushing_attempts': player_stats.get('rushing_attempts', 0),
                'actual_rushing_yards': player_stats.get('rushing_yards', 0),
                'actual_rushing_tds': player_stats.get('rushing_tds', 0),
                'actual_targets': player_stats.get('targets', 0),
                'actual_receptions': player_stats.get('receptions', 0),
                'actual_receiving_yards': player_stats.get('receiving_yards', 0),
                'actual_receiving_tds': player_stats.get('receiving_tds', 0),
                'actual_fantasy_points': fantasy_points,
                'game_date': game_date,
                'opponent_team': opponent,
                'is_home_game': is_home,
                'game_result': game_result,
                'data_source': 'ESPN'
            }
            
            db.close_session(session)
            return actual_result
            
        except Exception as e:
            self.logger.error(f"Error creating actual result: {e}")
            return None
            
    def _calculate_fantasy_points(self, stats):
        """Calculate fantasy points from actual stats"""
        points = 0
        
        # Passing: 1 point per 25 yards, 4 points per TD, -2 points per INT
        points += (stats.get('passing_yards', 0) / 25)
        points += (stats.get('passing_tds', 0) * 4)
        points -= (stats.get('interceptions', 0) * 2)
        
        # Rushing: 1 point per 10 yards, 6 points per TD
        points += (stats.get('rushing_yards', 0) / 10)
        points += (stats.get('rushing_tds', 0) * 6)
        
        # Receiving: 1 point per 10 yards, 6 points per TD, 1 point per reception
        points += (stats.get('receiving_yards', 0) / 10)
        points += (stats.get('receiving_tds', 0) * 6)
        points += stats.get('receptions', 0)
        
        return round(points, 2)
        
    def _parse_game_date(self, date_str):
        """Parse game date from ESPN format"""
        try:
            if date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        return datetime.utcnow()
        
    def _get_opponent_team(self, team, teams):
        """Get opponent team abbreviation"""
        for team_info in teams:
            team_abbr = team_info.get('team', {}).get('abbreviation', '')
            if team_abbr != team:
                return team_abbr
        return ''
        
    def _determine_game_result(self, team, teams):
        """Determine if team won, lost, or tied"""
        team_score = None
        opponent_score = None
        
        for team_info in teams:
            team_abbr = team_info.get('team', {}).get('abbreviation', '')
            score = team_info.get('score', 0)
            
            if team_abbr == team:
                team_score = score
            else:
                opponent_score = score
                
        if team_score is None or opponent_score is None:
            return 'U'  # Unknown
        elif team_score > opponent_score:
            return 'W'
        elif team_score < opponent_score:
            return 'L'
        else:
            return 'T'
            
    def store_actual_results(self, results_data):
        """Store actual results in database"""
        session = db.get_session()
        
        try:
            stored_count = 0
            
            for result in results_data:
                # Check if result already exists
                existing = session.query(ActualResults).filter_by(
                    player_id=result['player_id'],
                    season=result['season'],
                    week=result['week']
                ).first()
                
                if existing:
                    # Update existing record
                    for key, value in result.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new record
                    actual_result = ActualResults(**result)
                    session.add(actual_result)
                    
                stored_count += 1
                
            session.commit()
            self.logger.info(f"Stored {stored_count} actual results")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing actual results: {e}")
        finally:
            db.close_session(session)
            
    def scrape_season_results(self, season, start_week=1, end_week=18):
        """Scrape actual results for multiple weeks"""
        all_results = []
        
        for week in range(start_week, end_week + 1):
            self.logger.info(f"Scraping actual results for week {week}")
            week_results = self.scrape_week_results(season, week)
            
            if week_results:
                all_results.extend(week_results)
                self.store_actual_results(week_results)
                
            # Rate limiting
            import time
            time.sleep(2)
            
        return all_results