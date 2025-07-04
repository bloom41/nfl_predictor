import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from src.database.database import db
from src.database.models import Player, PlayerStats, NewsArticle, InjuryHistory, WorkloadTracking, TeamNews
from .injury_tracker import InjuryTracker
from .workload_analyzer import WorkloadAnalyzer

class FeatureEngineer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.injury_tracker = InjuryTracker()
        self.workload_analyzer = WorkloadAnalyzer()
        
    def create_player_features(self, player_id, season, target_week):
        """Create features for a specific player up to target week"""
        session = db.get_session()
        
        try:
            # Get player basic info
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                return None
                
            # Get historical stats
            stats = session.query(PlayerStats).filter_by(
                player_id=player_id,
                season=season
            ).filter(PlayerStats.week < target_week).all()
            
            if not stats:
                return None
                
            # Convert to DataFrame
            stats_df = pd.DataFrame([{
                'week': s.week,
                'passing_yards': s.passing_yards,
                'passing_tds': s.passing_tds,
                'rushing_yards': s.rushing_yards,
                'rushing_tds': s.rushing_tds,
                'receiving_yards': s.receiving_yards,
                'receiving_tds': s.receiving_tds,
                'fantasy_points': s.fantasy_points or self._calculate_fantasy_points(s)
            } for s in stats])
            
            # Create features
            features = {
                'player_id': player_id,
                'position': player.position,
                'team': player.team,
                'age': player.age or 25,  # Default if unknown
                'experience_years': player.experience_years or 1,
            }
            
            # Recent performance features (last 3 games)
            recent_stats = stats_df.tail(3)
            features.update({
                'avg_passing_yards_3games': recent_stats['passing_yards'].mean(),
                'avg_passing_tds_3games': recent_stats['passing_tds'].mean(),
                'avg_rushing_yards_3games': recent_stats['rushing_yards'].mean(),
                'avg_rushing_tds_3games': recent_stats['rushing_tds'].mean(),
                'avg_receiving_yards_3games': recent_stats['receiving_yards'].mean(),
                'avg_receiving_tds_3games': recent_stats['receiving_tds'].mean(),
                'avg_fantasy_points_3games': recent_stats['fantasy_points'].mean(),
            })
            
            # Season-long averages
            features.update({
                'season_avg_passing_yards': stats_df['passing_yards'].mean(),
                'season_avg_passing_tds': stats_df['passing_tds'].mean(),
                'season_avg_rushing_yards': stats_df['rushing_yards'].mean(),
                'season_avg_rushing_tds': stats_df['rushing_tds'].mean(),
                'season_avg_receiving_yards': stats_df['receiving_yards'].mean(),
                'season_avg_receiving_tds': stats_df['receiving_tds'].mean(),
                'season_avg_fantasy_points': stats_df['fantasy_points'].mean(),
            })
            
            # Trend features (last 5 games)
            if len(stats_df) >= 5:
                last_5 = stats_df.tail(5)
                features.update({
                    'fantasy_points_trend': self._calculate_trend(last_5['fantasy_points']),
                    'passing_yards_trend': self._calculate_trend(last_5['passing_yards']),
                    'consistency_score': self._calculate_consistency(last_5['fantasy_points'])
                })
            else:
                features.update({
                    'fantasy_points_trend': 0,
                    'passing_yards_trend': 0,
                    'consistency_score': 0
                })
            
            # Games played
            features['games_played'] = len(stats_df)
            
            # Add injury risk features
            injury_features = self.create_injury_risk_features(player_id, season, target_week)
            features.update(injury_features)
            
            # Add workload risk features
            workload_features = self.create_workload_risk_features(player_id, season, target_week)
            features.update(workload_features)
            
            # Add team context features
            team_features = self.create_team_context_features(player.team, target_week)
            features.update(team_features)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error creating features for player {player_id}: {e}")
            return None
        finally:
            db.close_session(session)
            
    def create_sentiment_features(self, player_id, days_back=7):
        """Create sentiment features from recent news mentions"""
        session = db.get_session()
        
        try:
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                return {}
                
            # Get recent news mentioning the player
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            news_articles = session.query(NewsArticle).filter(
                NewsArticle.created_at >= cutoff_date,
                NewsArticle.players_mentioned.contains(player.name)
            ).all()
            
            if not news_articles:
                return {
                    'sentiment_score': 0,
                    'news_mentions': 0,
                    'positive_mentions': 0,
                    'negative_mentions': 0
                }
                
            # Analyze sentiment
            sentiment_scores = [a.sentiment_score for a in news_articles if a.sentiment_score is not None]
            
            return {
                'sentiment_score': np.mean(sentiment_scores) if sentiment_scores else 0,
                'news_mentions': len(news_articles),
                'positive_mentions': sum(1 for s in sentiment_scores if s > 0.1),
                'negative_mentions': sum(1 for s in sentiment_scores if s < -0.1)
            }
            
        except Exception as e:
            self.logger.error(f"Error creating sentiment features for player {player_id}: {e}")
            return {}
        finally:
            db.close_session(session)
            
    def create_matchup_features(self, player_team, opponent_team, week):
        """Create matchup-specific features"""
        # This would require additional data about team defenses, weather, etc.
        # For now, return basic features
        return {
            'is_home_game': True,  # Would need schedule data
            'opponent_pass_defense_rank': 15,  # Would need defensive rankings
            'opponent_run_defense_rank': 15,
            'weather_factor': 1.0,  # Would need weather data
        }
        
    def prepare_training_data(self, season, position=None):
        """Prepare training dataset for model"""
        session = db.get_session()
        
        try:
            # Get all players for the position
            query = session.query(Player)
            if position:
                query = query.filter(Player.position == position)
            players = query.all()
            
            training_data = []
            
            for player in players:
                # Get all weeks where we have data
                stats = session.query(PlayerStats).filter_by(
                    player_id=player.id,
                    season=season
                ).order_by(PlayerStats.week).all()
                
                # Create features for each week (predicting next week's performance)
                for i, stat in enumerate(stats[:-1]):  # Exclude last week (no target)
                    target_week = stats[i + 1]
                    
                    # Create features up to current week
                    features = self.create_player_features(player.id, season, stat.week + 1)
                    if not features:
                        continue
                        
                    # Add sentiment features
                    sentiment_features = self.create_sentiment_features(player.id)
                    features.update(sentiment_features)
                    
                    # Add matchup features
                    matchup_features = self.create_matchup_features(player.team, '', target_week.week)
                    features.update(matchup_features)
                    
                    # Add target variables
                    features.update({
                        'target_passing_yards': target_week.passing_yards,
                        'target_passing_tds': target_week.passing_tds,
                        'target_rushing_yards': target_week.rushing_yards,
                        'target_rushing_tds': target_week.rushing_tds,
                        'target_receiving_yards': target_week.receiving_yards,
                        'target_receiving_tds': target_week.receiving_tds,
                        'target_fantasy_points': target_week.fantasy_points or self._calculate_fantasy_points(target_week)
                    })
                    
                    training_data.append(features)
                    
            return pd.DataFrame(training_data)
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            return pd.DataFrame()
        finally:
            db.close_session(session)
            
    def _calculate_fantasy_points(self, stats):
        """Calculate fantasy points from stats"""
        points = 0
        
        # Passing: 1 point per 25 yards, 4 points per TD
        points += (stats.passing_yards or 0) / 25
        points += (stats.passing_tds or 0) * 4
        points -= (stats.interceptions or 0) * 2
        
        # Rushing: 1 point per 10 yards, 6 points per TD
        points += (stats.rushing_yards or 0) / 10
        points += (stats.rushing_tds or 0) * 6
        
        # Receiving: 1 point per 10 yards, 6 points per TD, 1 point per reception
        points += (stats.receiving_yards or 0) / 10
        points += (stats.receiving_tds or 0) * 6
        points += (stats.receptions or 0)
        
        return round(points, 2)
        
    def _calculate_trend(self, values):
        """Calculate trend (slope) of recent performance"""
        if len(values) < 2:
            return 0
        x = np.arange(len(values))
        return np.polyfit(x, values, 1)[0]
        
    def _calculate_consistency(self, values):
        """Calculate consistency score (inverse of coefficient of variation)"""
        if len(values) < 2 or np.mean(values) == 0:
            return 0
        cv = np.std(values) / np.mean(values)
        return 1 / (1 + cv)  # Higher score = more consistent
        
    def create_injury_risk_features(self, player_id, season, week):
        """Create injury risk-based features"""
        try:
            # Get comprehensive injury risk assessment
            risk_analysis = self.injury_tracker.calculate_combined_risk_score(player_id, season, week)
            
            return {
                'injury_risk_score': risk_analysis.get('total_risk_score', 0.1),
                'historical_injury_risk': risk_analysis.get('injury_risk', 0.1),
                'workload_injury_risk': risk_analysis.get('workload_risk', 0.1),
                'injury_risk_factors_count': len(risk_analysis.get('risk_factors', [])),
                'has_injury_prone_areas': 1 if risk_analysis.get('injury_prone_areas') else 0,
                'usage_trend_increasing': 1 if risk_analysis.get('usage_trend') == 'increasing' else 0
            }
        except Exception as e:
            self.logger.error(f"Error creating injury risk features: {e}")
            return {
                'injury_risk_score': 0.1,
                'historical_injury_risk': 0.1,
                'workload_injury_risk': 0.1,
                'injury_risk_factors_count': 0,
                'has_injury_prone_areas': 0,
                'usage_trend_increasing': 0
            }
            
    def create_workload_risk_features(self, player_id, season, week):
        """Create workload and overuse risk features"""
        session = db.get_session()
        
        try:
            # Get recent workload data
            recent_workloads = session.query(WorkloadTracking).filter_by(
                player_id=player_id,
                season=season
            ).filter(WorkloadTracking.week < week).order_by(WorkloadTracking.week.desc()).limit(4).all()
            
            if not recent_workloads:
                return {
                    'avg_snap_percentage': 50.0,
                    'avg_touches_per_game': 10.0,
                    'high_usage_games_count': 0,
                    'workload_trend': 0.0,
                    'touches_above_season_avg': 0.0,
                    'consecutive_high_usage': 0
                }
                
            # Calculate workload metrics
            snap_percentages = [w.snap_percentage for w in recent_workloads]
            touches = [w.total_touches for w in recent_workloads]
            # Calculate high usage based on snap percentage instead
            high_usage_games = sum(1 for w in recent_workloads if w.snap_percentage > 80.0)
            
            # Calculate trends
            workload_trend = 0
            if len(snap_percentages) >= 2:
                workload_trend = snap_percentages[0] - snap_percentages[-1]  # Recent - oldest
                
            return {
                'avg_snap_percentage': np.mean(snap_percentages),
                'avg_touches_per_game': np.mean(touches),
                'high_usage_games_count': high_usage_games,
                'workload_trend': workload_trend,
                'touches_above_season_avg': recent_workloads[0].touches_vs_season_avg if recent_workloads else 0,
                'consecutive_high_usage': recent_workloads[0].consecutive_games_high_usage if recent_workloads else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error creating workload features: {e}")
            return {
                'avg_snap_percentage': 50.0,
                'avg_touches_per_game': 10.0,
                'high_usage_games_count': 0,
                'workload_trend': 0.0,
                'touches_above_season_avg': 0.0,
                'consecutive_high_usage': 0
            }
        finally:
            db.close_session(session)
            
    def create_team_context_features(self, team, week):
        """Create team-specific context features"""
        session = db.get_session()
        
        try:
            # Get recent team news
            cutoff_date = datetime.utcnow() - timedelta(days=14)  # Last 2 weeks
            team_news = session.query(TeamNews).filter(
                TeamNews.team == team,
                TeamNews.created_at >= cutoff_date
            ).all()
            
            if not team_news:
                return {
                    'team_news_sentiment': 0.0,
                    'coaching_changes_recent': 0,
                    'injury_report_mentions': 0,
                    'roster_changes_recent': 0,
                    'team_news_impact_high': 0
                }
                
            # Analyze team news
            sentiments = [news.sentiment_score for news in team_news if news.sentiment_score is not None]
            coaching_changes = sum(1 for news in team_news if news.category == 'coaching')
            injury_mentions = sum(1 for news in team_news if news.category == 'injury_report')
            roster_changes = sum(1 for news in team_news if news.category == 'roster')
            high_impact_news = sum(1 for news in team_news if news.impact_level == 'high')
            
            return {
                'team_news_sentiment': np.mean(sentiments) if sentiments else 0.0,
                'coaching_changes_recent': min(coaching_changes, 3),  # Cap at 3
                'injury_report_mentions': min(injury_mentions, 5),    # Cap at 5
                'roster_changes_recent': min(roster_changes, 5),      # Cap at 5
                'team_news_impact_high': min(high_impact_news, 3)     # Cap at 3
            }
            
        except Exception as e:
            self.logger.error(f"Error creating team context features: {e}")
            return {
                'team_news_sentiment': 0.0,
                'coaching_changes_recent': 0,
                'injury_report_mentions': 0,
                'roster_changes_recent': 0,
                'team_news_impact_high': 0
            }
        finally:
            db.close_session(session)