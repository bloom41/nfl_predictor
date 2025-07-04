import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from enum import Enum
from src.database.database import db
from src.database.models import (
    Player, ActualResults, Prediction, NewsArticle, TeamNews, WeatherData
)

class UnderperformanceReason(Enum):
    """Categories for why a player underperformed"""
    INJURY = "injury"
    GAME_SCRIPT = "game_script"  # Blowout, garbage time
    WEATHER = "weather"
    COACHING_DECISION = "coaching_decision"  # Benched, reduced role
    OPPONENT_DEFENSE = "opponent_defense"  # Elite defense shutdown
    GAME_FLOW = "game_flow"  # Unusual game circumstances
    RANDOM_VARIANCE = "random_variance"  # Normal statistical variation
    MODEL_ERROR = "model_error"  # Actual prediction error

class GameContextTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Performance drop thresholds
        self.performance_thresholds = {
            'severe_drop': 0.25,    # Less than 25% of predicted
            'moderate_drop': 0.50,  # Less than 50% of predicted
            'mild_drop': 0.75       # Less than 75% of predicted
        }
        
        # Context detection weights
        self.context_weights = {
            'injury_indicators': 0.8,
            'game_script_indicators': 0.7,
            'weather_indicators': 0.6,
            'coaching_indicators': 0.5,
            'opponent_indicators': 0.4
        }
        
    def analyze_underperformance_context(self, player_id, season, week, predicted_fp, actual_fp):
        """Comprehensive analysis of why a player underperformed"""
        try:
            if actual_fp >= predicted_fp * 0.8:  # Less than 20% underperformance
                return {
                    'primary_reason': UnderperformanceReason.RANDOM_VARIANCE,
                    'confidence': 0.9,
                    'should_use_for_training': True,
                    'context_scores': {},
                    'explanation': 'Performance within normal variance range'
                }
                
            # Analyze different context factors
            context_analysis = {
                'injury': self._analyze_injury_context(player_id, season, week),
                'game_script': self._analyze_game_script_context(player_id, season, week),
                'weather': self._analyze_weather_context(player_id, season, week),
                'coaching': self._analyze_coaching_context(player_id, season, week),
                'opponent': self._analyze_opponent_context(player_id, season, week),
                'game_flow': self._analyze_game_flow_context(player_id, season, week)
            }
            
            # Determine primary reason
            primary_reason, confidence = self._determine_primary_reason(
                context_analysis, predicted_fp, actual_fp
            )
            
            # Decide if this should be used for model training
            should_use_for_training = self._should_use_for_training(primary_reason, confidence)
            
            # Generate explanation
            explanation = self._generate_explanation(primary_reason, context_analysis, confidence)
            
            return {
                'primary_reason': primary_reason,
                'confidence': confidence,
                'should_use_for_training': should_use_for_training,
                'context_scores': context_analysis,
                'explanation': explanation,
                'performance_ratio': actual_fp / predicted_fp if predicted_fp > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing underperformance context: {e}")
            return {
                'primary_reason': UnderperformanceReason.MODEL_ERROR,
                'confidence': 0.5,
                'should_use_for_training': True,
                'context_scores': {},
                'explanation': 'Analysis error - default to model error'
            }
            
    def _analyze_injury_context(self, player_id, season, week):
        """Analyze injury-related context"""
        try:
            session = db.get_session()
            
            score = 0.0
            indicators = []
            
            # Check for injury news on game day
            game_day_news = self._get_game_day_news(player_id, season, week, session)
            injury_news_score = self._score_injury_news(game_day_news)
            
            if injury_news_score > 0.3:
                score += injury_news_score * 0.6
                indicators.append(f"Injury news detected (score: {injury_news_score:.2f})")
                
            # Check recent injury history
            recent_injuries = session.query(db.get_table('injury_history')).filter_by(
                player_id=player_id,
                season=season
            ).filter(
                db.get_table('injury_history').week.between(max(1, week-3), week)
            ).all() if hasattr(db, 'get_table') else []
            
            if recent_injuries:
                injury_severity_score = len(recent_injuries) * 0.2
                score += min(0.4, injury_severity_score)
                indicators.append(f"Recent injury history: {len(recent_injuries)} injuries")
                
            # Check for snap count reduction (if available)
            actual_result = session.query(ActualResults).filter_by(
                player_id=player_id, season=season, week=week
            ).first()
            
            if actual_result:
                snap_reduction_score = self._analyze_snap_reduction(actual_result)
                if snap_reduction_score > 0.2:
                    score += snap_reduction_score * 0.3
                    indicators.append(f"Reduced playing time detected")
                    
            db.close_session(session)
            
            return {
                'score': min(1.0, score),
                'indicators': indicators,
                'confidence': 0.8 if score > 0.5 else 0.4
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing injury context: {e}")
            return {'score': 0.0, 'indicators': [], 'confidence': 0.0}
            
    def _analyze_game_script_context(self, player_id, season, week):
        """Analyze game script context (blowouts, garbage time)"""
        try:
            session = db.get_session()
            
            score = 0.0
            indicators = []
            
            # Get game result
            actual_result = session.query(ActualResults).filter_by(
                player_id=player_id, season=season, week=week
            ).first()
            
            if not actual_result:
                db.close_session(session)
                return {'score': 0.0, 'indicators': [], 'confidence': 0.0}
                
            # Check for blowout indicators
            game_result = actual_result.game_result
            
            # Analyze touch distribution and game flow
            total_touches = (actual_result.actual_rushing_attempts or 0) + \
                          (actual_result.actual_receptions or 0) + \
                          (actual_result.actual_passing_attempts or 0)
                          
            # Very low touches might indicate game script issues
            player = session.query(Player).filter_by(id=player_id).first()
            expected_touches = self._get_expected_touches(player.position)
            
            if total_touches < expected_touches * 0.5:
                score += 0.4
                indicators.append(f"Low touches: {total_touches} vs expected {expected_touches}")
                
            # Check team news for game script mentions
            team_news = session.query(TeamNews).filter_by(
                team=player.team
            ).filter(
                TeamNews.created_at >= datetime.utcnow() - timedelta(days=2)
            ).all()
            
            for news in team_news:
                content = f"{news.title} {getattr(news, 'content', '')}".lower()
                if any(word in content for word in ['blowout', 'garbage time', 'rout', 'dominated']):
                    score += 0.3
                    indicators.append("Game script news mentions detected")
                    break
                    
            db.close_session(session)
            
            return {
                'score': min(1.0, score),
                'indicators': indicators,
                'confidence': 0.6 if score > 0.3 else 0.3
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing game script context: {e}")
            return {'score': 0.0, 'indicators': [], 'confidence': 0.0}
            
    def _analyze_weather_context(self, player_id, season, week):
        """Analyze weather impact context"""
        try:
            session = db.get_session()
            
            score = 0.0
            indicators = []
            
            # Get weather data if available
            weather_data = session.query(WeatherData).filter_by(
                season=season, week=week
            ).first() if hasattr(db, 'weather_data') else None
            
            if weather_data:
                # Analyze weather impact
                temp = getattr(weather_data, 'temperature', 70)
                wind = getattr(weather_data, 'wind_speed', 0)
                precip = getattr(weather_data, 'precipitation', 0)
                
                # Cold weather impact
                if temp < 32:
                    score += 0.3
                    indicators.append(f"Cold weather: {temp}°F")
                elif temp < 45:
                    score += 0.1
                    indicators.append(f"Cool weather: {temp}°F")
                    
                # Wind impact (especially for passing)
                if wind > 20:
                    score += 0.4
                    indicators.append(f"High winds: {wind} mph")
                elif wind > 15:
                    score += 0.2
                    indicators.append(f"Moderate winds: {wind} mph")
                    
                # Precipitation impact
                if precip > 0.1:
                    score += 0.3
                    indicators.append(f"Precipitation: {precip} inches")
                    
            else:
                # Check news for weather mentions
                team_news = self._get_team_news_recent(player_id, session)
                for news in team_news:
                    content = f"{news.title} {getattr(news, 'content', '')}".lower()
                    weather_words = ['rain', 'snow', 'wind', 'cold', 'weather', 'storm']
                    if any(word in content for word in weather_words):
                        score += 0.2
                        indicators.append("Weather conditions mentioned in news")
                        break
                        
            db.close_session(session)
            
            return {
                'score': min(1.0, score),
                'indicators': indicators,
                'confidence': 0.7 if score > 0.3 else 0.2
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing weather context: {e}")
            return {'score': 0.0, 'indicators': [], 'confidence': 0.0}
            
    def _analyze_coaching_context(self, player_id, season, week):
        """Analyze coaching decision context"""
        try:
            session = db.get_session()
            
            score = 0.0
            indicators = []
            
            # Check team news for coaching decisions
            team_news = self._get_team_news_recent(player_id, session)
            
            coaching_keywords = [
                'benched', 'reduced role', 'rotation', 'snap count', 'playing time',
                'coach decision', 'disciplinary', 'healthy scratch'
            ]
            
            for news in team_news:
                content = f"{news.title} {getattr(news, 'content', '')}".lower()
                
                # Check if player is mentioned with coaching keywords
                player = session.query(Player).filter_by(id=player_id).first()
                player_mentioned = player.name.lower() in content
                
                coaching_mentioned = any(keyword in content for keyword in coaching_keywords)
                
                if player_mentioned and coaching_mentioned:
                    score += 0.6
                    indicators.append("Coaching decision news detected")
                elif coaching_mentioned:
                    score += 0.2
                    indicators.append("General coaching changes mentioned")
                    
            db.close_session(session)
            
            return {
                'score': min(1.0, score),
                'indicators': indicators,
                'confidence': 0.8 if score > 0.5 else 0.3
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing coaching context: {e}")
            return {'score': 0.0, 'indicators': [], 'confidence': 0.0}
            
    def _analyze_opponent_context(self, player_id, season, week):
        """Analyze opponent defense context"""
        try:
            session = db.get_session()
            
            score = 0.0
            indicators = []
            
            # Get opponent from actual results
            actual_result = session.query(ActualResults).filter_by(
                player_id=player_id, season=season, week=week
            ).first()
            
            if actual_result and actual_result.opponent_team:
                opponent = actual_result.opponent_team
                
                # Check for elite defense mentions in news
                team_news = session.query(TeamNews).filter_by(
                    team=opponent
                ).filter(
                    TeamNews.created_at >= datetime.utcnow() - timedelta(days=7)
                ).all()
                
                defense_keywords = [
                    'elite defense', 'top defense', 'shutdown', 'dominant defense',
                    'defensive coordinator', 'blitz packages', 'coverage'
                ]
                
                for news in team_news:
                    content = f"{news.title} {getattr(news, 'content', '')}".lower()
                    if any(keyword in content for keyword in defense_keywords):
                        score += 0.3
                        indicators.append(f"Elite defense mentions for {opponent}")
                        break
                        
                # Default opponent strength score (would be enhanced with actual defensive stats)
                score += 0.1  # Base opponent factor
                indicators.append(f"Opponent factor: {opponent}")
                
            db.close_session(session)
            
            return {
                'score': min(1.0, score),
                'indicators': indicators,
                'confidence': 0.4  # Lower confidence without detailed defensive stats
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing opponent context: {e}")
            return {'score': 0.0, 'indicators': [], 'confidence': 0.0}
            
    def _analyze_game_flow_context(self, player_id, season, week):
        """Analyze unusual game flow context"""
        try:
            session = db.get_session()
            
            score = 0.0
            indicators = []
            
            # Check for unusual game circumstances
            team_news = self._get_team_news_recent(player_id, session)
            
            unusual_keywords = [
                'ejected', 'penalty', 'technical difficulties', 'delay',
                'overtime', 'special circumstances', 'unusual'
            ]
            
            for news in team_news:
                content = f"{news.title} {getattr(news, 'content', '')}".lower()
                if any(keyword in content for keyword in unusual_keywords):
                    score += 0.3
                    indicators.append("Unusual game circumstances mentioned")
                    
            db.close_session(session)
            
            return {
                'score': min(1.0, score),
                'indicators': indicators,
                'confidence': 0.5 if score > 0.2 else 0.1
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing game flow context: {e}")
            return {'score': 0.0, 'indicators': [], 'confidence': 0.0}
            
    def _determine_primary_reason(self, context_analysis, predicted_fp, actual_fp):
        """Determine the primary reason for underperformance"""
        try:
            # Calculate weighted scores
            weighted_scores = {}
            
            for context_type, analysis in context_analysis.items():
                score = analysis.get('score', 0.0)
                confidence = analysis.get('confidence', 0.0)
                weight = self.context_weights.get(f"{context_type}_indicators", 0.3)
                
                weighted_scores[context_type] = score * confidence * weight
                
            # Find the highest scoring context
            if not weighted_scores or max(weighted_scores.values()) < 0.2:
                # Low scores across all contexts - likely model error or random variance
                performance_ratio = actual_fp / predicted_fp if predicted_fp > 0 else 0
                
                if performance_ratio < 0.3:
                    return UnderperformanceReason.MODEL_ERROR, 0.6
                else:
                    return UnderperformanceReason.RANDOM_VARIANCE, 0.7
                    
            # Get the context with highest weighted score
            primary_context = max(weighted_scores, key=weighted_scores.get)
            confidence = weighted_scores[primary_context]
            
            # Map context to reason
            context_to_reason = {
                'injury': UnderperformanceReason.INJURY,
                'game_script': UnderperformanceReason.GAME_SCRIPT,
                'weather': UnderperformanceReason.WEATHER,
                'coaching': UnderperformanceReason.COACHING_DECISION,
                'opponent': UnderperformanceReason.OPPONENT_DEFENSE,
                'game_flow': UnderperformanceReason.GAME_FLOW
            }
            
            primary_reason = context_to_reason.get(primary_context, UnderperformanceReason.MODEL_ERROR)
            
            return primary_reason, min(0.95, confidence)
            
        except Exception as e:
            self.logger.error(f"Error determining primary reason: {e}")
            return UnderperformanceReason.MODEL_ERROR, 0.5
            
    def _should_use_for_training(self, primary_reason, confidence):
        """Determine if this game should be used for model training"""
        # Don't use for training if external factors caused underperformance
        external_factors = [
            UnderperformanceReason.INJURY,
            UnderperformanceReason.GAME_SCRIPT,
            UnderperformanceReason.WEATHER,
            UnderperformanceReason.COACHING_DECISION,
            UnderperformanceReason.GAME_FLOW
        ]
        
        if primary_reason in external_factors and confidence > 0.6:
            return False  # Don't use for training
            
        return True  # Use for training
        
    def _generate_explanation(self, primary_reason, context_analysis, confidence):
        """Generate human-readable explanation"""
        explanations = {
            UnderperformanceReason.INJURY: "Player likely affected by injury",
            UnderperformanceReason.GAME_SCRIPT: "Game script/blowout affected usage",
            UnderperformanceReason.WEATHER: "Weather conditions impacted performance",
            UnderperformanceReason.COACHING_DECISION: "Coaching decisions reduced role",
            UnderperformanceReason.OPPONENT_DEFENSE: "Strong opponent defense shutdown",
            UnderperformanceReason.GAME_FLOW: "Unusual game circumstances",
            UnderperformanceReason.RANDOM_VARIANCE: "Normal performance variance",
            UnderperformanceReason.MODEL_ERROR: "Prediction model error"
        }
        
        base_explanation = explanations.get(primary_reason, "Unknown reason")
        
        # Add context details
        top_indicators = []
        for context_type, analysis in context_analysis.items():
            if analysis.get('score', 0) > 0.3 and analysis.get('indicators'):
                top_indicators.extend(analysis['indicators'][:1])  # Top indicator per context
                
        if top_indicators:
            details = "; ".join(top_indicators[:2])  # Top 2 overall
            return f"{base_explanation} ({details}) - Confidence: {confidence:.2f}"
        else:
            return f"{base_explanation} - Confidence: {confidence:.2f}"
            
    # Helper methods
    def _get_game_day_news(self, player_id, season, week, session):
        """Get news from around game time"""
        try:
            # Approximate game date (would use actual schedule in production)
            game_date = datetime(2024, 9, 1) + timedelta(weeks=week-1)
            start_date = game_date - timedelta(days=1)
            end_date = game_date + timedelta(days=1)
            
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                return []
                
            news = session.query(NewsArticle).filter(
                NewsArticle.created_at.between(start_date, end_date),
                NewsArticle.players_mentioned.contains(player.name)
            ).all()
            
            return news
            
        except Exception:
            return []
            
    def _score_injury_news(self, news_articles):
        """Score injury-related news"""
        if not news_articles:
            return 0.0
            
        injury_keywords = ['injury', 'hurt', 'questionable', 'doubtful', 'out', 'inactive']
        
        total_score = 0.0
        for article in news_articles:
            content = f"{article.title} {getattr(article, 'content', '')}".lower()
            score = sum(0.2 for keyword in injury_keywords if keyword in content)
            total_score += min(1.0, score)
            
        return min(1.0, total_score / len(news_articles))
        
    def _analyze_snap_reduction(self, actual_result):
        """Analyze if snap count was reduced"""
        # Estimate snap reduction from stat production
        total_stats = (actual_result.actual_rushing_attempts or 0) + \
                     (actual_result.actual_receptions or 0) + \
                     (actual_result.actual_passing_attempts or 0)
                     
        if total_stats < 5:
            return 0.6  # Very low usage
        elif total_stats < 10:
            return 0.3  # Moderate reduction
        else:
            return 0.0  # Normal usage
            
    def _get_expected_touches(self, position):
        """Get expected touches for position"""
        return {
            'QB': 35,   # Pass attempts + rushes
            'RB': 20,   # Carries + receptions
            'WR': 10,   # Targets
            'TE': 8     # Targets
        }.get(position, 15)
        
    def _get_team_news_recent(self, player_id, session):
        """Get recent team news"""
        try:
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                return []
                
            cutoff = datetime.utcnow() - timedelta(days=3)
            return session.query(TeamNews).filter_by(
                team=player.team
            ).filter(TeamNews.created_at >= cutoff).all()
            
        except Exception:
            return []