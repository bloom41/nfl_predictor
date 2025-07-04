import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from textblob import TextBlob
import re
from src.database.database import db
from src.database.models import (
    Player, ActualResults, Prediction, PredictionAccuracy, 
    NewsArticle, TeamNews, InjuryHistory
)

class InjuryAwareFilter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Injury detection keywords
        self.injury_keywords = {
            'severe': ['concussion', 'torn', 'surgery', 'ir', 'injured reserve', 'season-ending', 'fractured'],
            'moderate': ['sprained', 'strained', 'pulled', 'bruised', 'sore', 'questionable', 'doubtful'],
            'minor': ['rest', 'maintenance', 'precautionary', 'probable', 'limited']
        }
        
        # Performance drop indicators
        self.drop_thresholds = {
            'severe_drop': 0.25,    # Less than 25% of predicted points
            'moderate_drop': 0.50,  # Less than 50% of predicted points
            'minor_drop': 0.75      # Less than 75% of predicted points
        }
        
        # Game context indicators
        self.game_context_keywords = {
            'blowout': ['blowout', 'rout', 'dominated', 'shutout'],
            'garbage_time': ['garbage time', 'backups', 'reserves'],
            'weather': ['rain', 'snow', 'wind', 'storm', 'weather'],
            'ejection': ['ejected', 'flagrant', 'unsportsmanlike']
        }
        
    def detect_injury_affected_games(self, season, position=None, min_drop_threshold=0.5):
        """Detect games where poor performance was likely due to injury"""
        session = db.get_session()
        
        try:
            # Get prediction vs actual data
            query = session.query(Prediction, ActualResults, Player).join(
                ActualResults,
                (Prediction.player_id == ActualResults.player_id) &
                (Prediction.season == ActualResults.season) &
                (Prediction.week == ActualResults.week)
            ).join(
                Player, Prediction.player_id == Player.id
            ).filter(Prediction.season == season)
            
            if position:
                query = query.filter(Player.position == position)
                
            results = query.all()
            
            injury_affected_games = []
            
            for prediction, actual, player in results:
                # Calculate performance drop
                predicted_fp = prediction.predicted_fantasy_points or 0
                actual_fp = actual.actual_fantasy_points or 0
                
                if predicted_fp == 0:
                    continue
                    
                performance_ratio = actual_fp / predicted_fp
                
                # Check if significant underperformance occurred
                if performance_ratio < min_drop_threshold:
                    injury_analysis = self._analyze_potential_injury(
                        player, actual, prediction, performance_ratio
                    )
                    
                    if injury_analysis['is_likely_injury']:
                        injury_affected_games.append({
                            'player_id': player.id,
                            'player_name': player.name,
                            'position': player.position,
                            'season': actual.season,
                            'week': actual.week,
                            'predicted_fp': predicted_fp,
                            'actual_fp': actual_fp,
                            'performance_ratio': performance_ratio,
                            'injury_indicators': injury_analysis['indicators'],
                            'confidence_score': injury_analysis['confidence'],
                            'recommended_action': injury_analysis['action']
                        })
                        
            self.logger.info(f"Detected {len(injury_affected_games)} potentially injury-affected games")
            return injury_affected_games
            
        except Exception as e:
            self.logger.error(f"Error detecting injury-affected games: {e}")
            return []
        finally:
            db.close_session(session)
            
    def _analyze_potential_injury(self, player, actual_result, prediction, performance_ratio):
        """Analyze if poor performance was likely due to injury"""
        indicators = []
        confidence_score = 0.0
        
        # 1. Check game day news for injury reports
        game_day_news = self._get_game_day_news(player.id, actual_result.game_date)
        news_injury_score = self._analyze_news_for_injury(game_day_news)
        
        if news_injury_score > 0.3:
            indicators.append(f"Game day injury news (score: {news_injury_score:.2f})")
            confidence_score += news_injury_score * 0.4
            
        # 2. Check for historical injury patterns
        injury_history_score = self._check_injury_history_context(
            player.id, actual_result.season, actual_result.week
        )
        
        if injury_history_score > 0.2:
            indicators.append(f"Recent injury history (score: {injury_history_score:.2f})")
            confidence_score += injury_history_score * 0.3
            
        # 3. Analyze performance drop pattern
        drop_analysis = self._analyze_performance_drop_pattern(
            player.id, actual_result, prediction
        )
        
        if drop_analysis['suspicious']:
            indicators.append(f"Unusual performance drop: {drop_analysis['description']}")
            confidence_score += drop_analysis['score'] * 0.2
            
        # 4. Check snap count / playing time indicators
        playing_time_analysis = self._analyze_playing_time(actual_result)
        
        if playing_time_analysis['reduced']:
            indicators.append(f"Reduced playing time: {playing_time_analysis['description']}")
            confidence_score += 0.1
            
        # 5. Check for other game context factors
        game_context = self._analyze_game_context(actual_result)
        
        for context_type, score in game_context.items():
            if score > 0.2:
                indicators.append(f"Game context - {context_type}: {score:.2f}")
                confidence_score += score * 0.1
                
        # Determine if likely injury
        is_likely_injury = confidence_score > 0.4 or news_injury_score > 0.6
        
        # Recommend action
        if confidence_score > 0.7:
            action = 'exclude_from_training'
        elif confidence_score > 0.4:
            action = 'flag_for_review'
        else:
            action = 'include_with_context'
            
        return {
            'is_likely_injury': is_likely_injury,
            'confidence': confidence_score,
            'indicators': indicators,
            'action': action
        }
        
    def _get_game_day_news(self, player_id, game_date):
        """Get news from game day and surrounding days"""
        session = db.get_session()
        
        try:
            # Get player info
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                return []
                
            # Search for news within 2 days of game
            start_date = game_date - timedelta(days=2)
            end_date = game_date + timedelta(days=1)
            
            # Check general news
            general_news = session.query(NewsArticle).filter(
                NewsArticle.created_at >= start_date,
                NewsArticle.created_at <= end_date,
                NewsArticle.players_mentioned.contains(player.name)
            ).all()
            
            # Check team news
            team_news = session.query(TeamNews).filter(
                TeamNews.team == player.team,
                TeamNews.created_at >= start_date,
                TeamNews.created_at <= end_date
            ).all()
            
            return list(general_news) + list(team_news)
            
        except Exception as e:
            self.logger.error(f"Error getting game day news: {e}")
            return []
        finally:
            db.close_session(session)
            
    def _analyze_news_for_injury(self, news_articles):
        """Analyze news articles for injury indicators"""
        if not news_articles:
            return 0.0
            
        injury_score = 0.0
        total_articles = len(news_articles)
        
        for article in news_articles:
            content = f"{article.title} {getattr(article, 'content', '')}"
            content_lower = content.lower()
            
            # Check for injury keywords
            article_score = 0.0
            
            for severity, keywords in self.injury_keywords.items():
                for keyword in keywords:
                    if keyword in content_lower:
                        if severity == 'severe':
                            article_score += 0.8
                        elif severity == 'moderate':
                            article_score += 0.5
                        elif severity == 'minor':
                            article_score += 0.2
                            
            # Check for status keywords
            status_keywords = ['out', 'inactive', 'dnp', 'did not practice']
            for keyword in status_keywords:
                if keyword in content_lower:
                    article_score += 0.6
                    
            # Normalize article score
            article_score = min(1.0, article_score)
            injury_score += article_score
            
        # Return average injury score
        return min(1.0, injury_score / total_articles)
        
    def _check_injury_history_context(self, player_id, season, week):
        """Check if player had recent injuries that might affect performance"""
        session = db.get_session()
        
        try:
            # Look for injuries in the last 4 weeks
            recent_injuries = session.query(InjuryHistory).filter(
                InjuryHistory.player_id == player_id,
                InjuryHistory.season == season,
                InjuryHistory.week >= (week - 4),
                InjuryHistory.week < week
            ).all()
            
            if not recent_injuries:
                return 0.0
                
            injury_score = 0.0
            
            for injury in recent_injuries:
                weeks_ago = week - injury.week
                severity_multiplier = {
                    'minor': 0.2,
                    'moderate': 0.5,
                    'major': 0.8
                }.get(injury.severity, 0.3)
                
                # More recent injuries have higher impact
                recency_multiplier = max(0.2, 1.0 - (weeks_ago * 0.2))
                
                injury_score += severity_multiplier * recency_multiplier
                
            return min(1.0, injury_score)
            
        except Exception as e:
            self.logger.error(f"Error checking injury history: {e}")
            return 0.0
        finally:
            db.close_session(session)
            
    def _analyze_performance_drop_pattern(self, player_id, actual_result, prediction):
        """Analyze if the performance drop follows injury patterns"""
        try:
            # Get recent performance for comparison
            session = db.get_session()
            
            recent_actuals = session.query(ActualResults).filter(
                ActualResults.player_id == player_id,
                ActualResults.season == actual_result.season,
                ActualResults.week < actual_result.week,
                ActualResults.week >= (actual_result.week - 4)
            ).order_by(ActualResults.week.desc()).limit(3).all()
            
            if len(recent_actuals) < 2:
                return {'suspicious': False, 'score': 0.0, 'description': 'Insufficient data'}
                
            # Calculate recent average
            recent_avg = np.mean([r.actual_fantasy_points for r in recent_actuals])
            current_actual = actual_result.actual_fantasy_points
            
            # Check for sudden drop vs gradual decline
            if recent_avg > 0:
                sudden_drop_ratio = current_actual / recent_avg
                
                if sudden_drop_ratio < 0.3:  # Less than 30% of recent average
                    return {
                        'suspicious': True,
                        'score': 0.7,
                        'description': f'Sudden drop to {sudden_drop_ratio:.1%} of recent average'
                    }
                elif sudden_drop_ratio < 0.5:  # Less than 50% of recent average
                    return {
                        'suspicious': True,
                        'score': 0.4,
                        'description': f'Significant drop to {sudden_drop_ratio:.1%} of recent average'
                    }
                    
            return {'suspicious': False, 'score': 0.0, 'description': 'Normal performance variation'}
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance drop: {e}")
            return {'suspicious': False, 'score': 0.0, 'description': 'Analysis error'}
        finally:
            db.close_session(session)
            
    def _analyze_playing_time(self, actual_result):
        """Analyze if reduced playing time indicates injury"""
        try:
            # Estimate playing time from stats
            total_touches = (actual_result.actual_rushing_attempts or 0) + \
                          (actual_result.actual_receptions or 0) + \
                          (actual_result.actual_passing_attempts or 0)
                          
            # Very low touch count might indicate injury
            if total_touches < 5:
                return {
                    'reduced': True,
                    'description': f'Very low touches ({total_touches}), possible injury'
                }
            elif total_touches < 10:
                return {
                    'reduced': True,
                    'description': f'Low touches ({total_touches}), possible limited role'
                }
                
            return {'reduced': False, 'description': 'Normal playing time'}
            
        except Exception as e:
            self.logger.error(f"Error analyzing playing time: {e}")
            return {'reduced': False, 'description': 'Analysis error'}
            
    def _analyze_game_context(self, actual_result):
        """Analyze game context that might explain poor performance"""
        context_scores = {}
        
        try:
            # Check game result for blowout
            if actual_result.game_result:
                # This would require score data - simplified for now
                context_scores['blowout'] = 0.0
                
            # Check for weather (would need weather data)
            context_scores['weather'] = 0.0
            
            # Check for other factors
            context_scores['other'] = 0.0
            
            return context_scores
            
        except Exception as e:
            self.logger.error(f"Error analyzing game context: {e}")
            return {}
            
    def create_filtered_training_dataset(self, season, position=None, exclude_injury_games=True):
        """Create training dataset with injury-affected games filtered out"""
        try:
            # Get all prediction/actual pairs
            session = db.get_session()
            
            query = session.query(Prediction, ActualResults, Player).join(
                ActualResults,
                (Prediction.player_id == ActualResults.player_id) &
                (Prediction.season == ActualResults.season) &
                (Prediction.week == ActualResults.week)
            ).join(
                Player, Prediction.player_id == Player.id
            ).filter(Prediction.season == season)
            
            if position:
                query = query.filter(Player.position == position)
                
            all_results = query.all()
            
            if not exclude_injury_games:
                return all_results
                
            # Detect injury-affected games
            injury_games = self.detect_injury_affected_games(season, position)
            injury_game_keys = {(ig['player_id'], ig['season'], ig['week']) for ig in injury_games}
            
            # Filter out injury-affected games
            filtered_results = []
            excluded_count = 0
            
            for prediction, actual, player in all_results:
                game_key = (player.id, actual.season, actual.week)
                
                if game_key in injury_game_keys:
                    excluded_count += 1
                    self.logger.debug(f"Excluding injury-affected game: {player.name} Week {actual.week}")
                else:
                    filtered_results.append((prediction, actual, player))
                    
            self.logger.info(f"Filtered training dataset: {len(filtered_results)} games included, "
                           f"{excluded_count} injury-affected games excluded")
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Error creating filtered training dataset: {e}")
            return []
        finally:
            db.close_session(session)
            
    def update_prediction_accuracy_with_context(self, season):
        """Update prediction accuracy records with injury context"""
        session = db.get_session()
        
        try:
            # Get injury-affected games
            injury_games = self.detect_injury_affected_games(season)
            
            updated_count = 0
            
            for injury_game in injury_games:
                # Find corresponding accuracy record
                accuracy_record = session.query(PredictionAccuracy).filter_by(
                    player_id=injury_game['player_id'],
                    season=injury_game['season'],
                    week=injury_game['week']
                ).first()
                
                if accuracy_record:
                    # Add context flag (would need to add this field to model)
                    # For now, we can use the accuracy_grade field to mark these
                    accuracy_record.accuracy_grade = f"INJ_{accuracy_record.accuracy_grade}"
                    updated_count += 1
                    
            session.commit()
            self.logger.info(f"Updated {updated_count} accuracy records with injury context")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating accuracy records with context: {e}")
        finally:
            db.close_session(session)
            
    def generate_injury_filter_report(self, season, position=None):
        """Generate comprehensive report on injury filtering"""
        try:
            injury_games = self.detect_injury_affected_games(season, position)
            
            if not injury_games:
                return "No injury-affected games detected for the specified criteria."
                
            # Analyze patterns
            df = pd.DataFrame(injury_games)
            
            report = []
            report.append("=== INJURY-AWARE FILTERING REPORT ===")
            report.append(f"Season: {season}" + (f", Position: {position}" if position else ""))
            report.append(f"Total Injury-Affected Games Detected: {len(injury_games)}")
            report.append("")
            
            # Position breakdown
            if 'position' in df.columns:
                pos_breakdown = df['position'].value_counts()
                report.append("POSITION BREAKDOWN:")
                for pos, count in pos_breakdown.items():
                    avg_ratio = df[df['position'] == pos]['performance_ratio'].mean()
                    report.append(f"  {pos}: {count} games (avg performance: {avg_ratio:.1%})")
                report.append("")
                
            # Severity analysis
            severe_injuries = df[df['performance_ratio'] < 0.25]
            moderate_injuries = df[(df['performance_ratio'] >= 0.25) & (df['performance_ratio'] < 0.5)]
            
            report.append("SEVERITY ANALYSIS:")
            report.append(f"  Severe Performance Drops (<25%): {len(severe_injuries)}")
            report.append(f"  Moderate Performance Drops (25-50%): {len(moderate_injuries)}")
            report.append("")
            
            # Top injury-affected games
            top_affected = df.nlargest(5, 'confidence_score')
            report.append("TOP INJURY-AFFECTED GAMES:")
            for _, game in top_affected.iterrows():
                report.append(f"  {game['player_name']} Week {game['week']}: "
                            f"{game['performance_ratio']:.1%} performance "
                            f"(confidence: {game['confidence_score']:.2f})")
                for indicator in game['injury_indicators'][:2]:  # Top 2 indicators
                    report.append(f"    - {indicator}")
                    
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating injury filter report: {e}")
            return "Error generating injury filter report"