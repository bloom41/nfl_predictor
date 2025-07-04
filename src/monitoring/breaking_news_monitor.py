import logging
import time
import threading
from datetime import datetime, timedelta
import re
from textblob import TextBlob
from src.database.database import db
from src.database.models import Player, Prediction, NewsArticle, TeamNews
from src.scrapers.espn_scraper import ESPNScraper
from src.scrapers.team_news_scraper import TeamNewsScraper

class BreakingNewsMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.espn_scraper = ESPNScraper()
        self.team_scraper = TeamNewsScraper()
        
        # Monitoring configuration
        self.check_interval = 300  # 5 minutes during active monitoring
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Breaking news keywords (high priority)
        self.breaking_keywords = {
            'injury_severe': {
                'keywords': ['out', 'inactive', 'ir', 'injured reserve', 'surgery', 'torn', 'fractured'],
                'impact_multiplier': -0.8,  # Severe negative impact
                'confidence_penalty': 0.3
            },
            'injury_moderate': {
                'keywords': ['questionable', 'doubtful', 'limited', 'sore', 'day-to-day'],
                'impact_multiplier': -0.3,  # Moderate negative impact
                'confidence_penalty': 0.2
            },
            'positive_news': {
                'keywords': ['cleared', 'healthy', 'full practice', 'activated', 'return'],
                'impact_multiplier': 0.2,   # Positive impact
                'confidence_bonus': 0.1
            },
            'role_change': {
                'keywords': ['starter', 'promoted', 'featured', 'increased role', 'more touches'],
                'impact_multiplier': 0.3,   # Positive role change
                'confidence_bonus': 0.15
            }
        }
        
        # Time windows for news relevance
        self.relevance_windows = {
            'breaking': timedelta(hours=2),    # Just happened
            'recent': timedelta(hours=12),     # Last 12 hours
            'current': timedelta(days=1),      # Last 24 hours
            'stale': timedelta(days=3)         # Older than 3 days
        }
        
    def start_monitoring(self, season=2024):
        """Start real-time breaking news monitoring"""
        try:
            if self.is_monitoring:
                self.logger.warning("Breaking news monitoring is already running")
                return
                
            self.is_monitoring = True
            self.season = season
            
            self.logger.info("Starting real-time breaking news monitoring...")
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(season,),
                daemon=True
            )
            self.monitor_thread.start()
            
            self.logger.info(f"Breaking news monitoring started (checking every {self.check_interval}s)")
            
        except Exception as e:
            self.logger.error(f"Error starting breaking news monitoring: {e}")
            self.is_monitoring = False
            
    def stop_monitoring(self):
        """Stop real-time breaking news monitoring"""
        try:
            self.is_monitoring = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10)
                
            self.logger.info("Breaking news monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping breaking news monitoring: {e}")
            
    def _monitoring_loop(self, season):
        """Main monitoring loop that runs in background"""
        last_check_time = datetime.utcnow() - timedelta(hours=1)
        
        while self.is_monitoring:
            try:
                current_time = datetime.utcnow()
                
                # Check for new breaking news
                breaking_news = self._fetch_recent_news(last_check_time)
                
                if breaking_news:
                    self.logger.info(f"Found {len(breaking_news)} new news items")
                    
                    # Analyze each news item
                    for news_item in breaking_news:
                        impact_analysis = self._analyze_news_impact(news_item)
                        
                        if impact_analysis['requires_action']:
                            self._handle_breaking_news(news_item, impact_analysis, season)
                            
                last_check_time = current_time
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Brief pause before retrying
                
    def _fetch_recent_news(self, since_time):
        """Fetch news articles since the last check"""
        try:
            news_items = []
            
            # Get recent ESPN news
            espn_news = self.espn_scraper.scrape_news(limit=20)
            
            # Get recent team news for all teams
            team_news = []
            for team_abbr in ['KC', 'BUF', 'SF', 'LAR', 'MIA']:  # Sample teams
                team_items = self.team_scraper.scrape_team_news(team_abbr, limit=5)
                team_news.extend(team_items)
                
            # Filter for recent news
            all_news = espn_news + team_news
            
            for news in all_news:
                news_time = news.get('published_date')
                if news_time and news_time > since_time:
                    news_items.append(news)
                    
            return news_items
            
        except Exception as e:
            self.logger.error(f"Error fetching recent news: {e}")
            return []
            
    def _analyze_news_impact(self, news_item):
        """Analyze if news item requires prediction updates"""
        try:
            title = news_item.get('title', '').lower()
            content = news_item.get('content', '').lower()
            full_text = f"{title} {content}"
            
            analysis = {
                'requires_action': False,
                'impact_type': None,
                'impact_magnitude': 0.0,
                'confidence_adjustment': 0.0,
                'affected_players': [],
                'urgency': 'low'
            }
            
            # Check for breaking news keywords
            for impact_type, config in self.breaking_keywords.items():
                keyword_matches = sum(1 for keyword in config['keywords'] if keyword in full_text)
                
                if keyword_matches > 0:
                    analysis['requires_action'] = True
                    analysis['impact_type'] = impact_type
                    analysis['impact_magnitude'] = config['impact_multiplier'] * (keyword_matches / len(config['keywords']))
                    
                    # Adjust confidence
                    if 'confidence_penalty' in config:
                        analysis['confidence_adjustment'] = -config['confidence_penalty']
                    elif 'confidence_bonus' in config:
                        analysis['confidence_adjustment'] = config['confidence_bonus']
                        
                    break
                    
            # Extract affected players
            analysis['affected_players'] = self._extract_affected_players(full_text)
            
            # Determine urgency
            if analysis['impact_magnitude'] < -0.5 or analysis['impact_magnitude'] > 0.4:
                analysis['urgency'] = 'high'
            elif abs(analysis['impact_magnitude']) > 0.2:
                analysis['urgency'] = 'medium'
                
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing news impact: {e}")
            return {'requires_action': False}
            
    def _extract_affected_players(self, text):
        """Extract player names mentioned in the news"""
        try:
            session = db.get_session()
            
            # Get all active players
            players = session.query(Player).all()
            affected_players = []
            
            for player in players:
                player_name_lower = player.name.lower()
                
                # Check for full name
                if player_name_lower in text:
                    affected_players.append({
                        'player_id': player.id,
                        'name': player.name,
                        'position': player.position,
                        'team': player.team
                    })
                else:
                    # Check for last name (if unique enough)
                    name_parts = player.name.split()
                    if len(name_parts) >= 2:
                        last_name = name_parts[-1].lower()
                        if len(last_name) > 4 and last_name in text:
                            # Verify it's actually about this player (simple heuristic)
                            if player.team.lower() in text or player.position.lower() in text:
                                affected_players.append({
                                    'player_id': player.id,
                                    'name': player.name,
                                    'position': player.position,
                                    'team': player.team
                                })
                                
            db.close_session(session)
            return affected_players
            
        except Exception as e:
            self.logger.error(f"Error extracting affected players: {e}")
            return []
            
    def _handle_breaking_news(self, news_item, impact_analysis, season):
        """Handle breaking news by updating relevant predictions"""
        try:
            affected_players = impact_analysis['affected_players']
            
            if not affected_players:
                return
                
            self.logger.info(f"Processing breaking news affecting {len(affected_players)} players: "
                           f"{impact_analysis['impact_type']} (magnitude: {impact_analysis['impact_magnitude']:.2f})")
            
            session = db.get_session()
            updates_made = 0
            
            for player_info in affected_players:
                player_id = player_info['player_id']
                
                # Find current week predictions for this player
                current_week = self._get_current_nfl_week()
                
                predictions = session.query(Prediction).filter_by(
                    player_id=player_id,
                    season=season,
                    week=current_week
                ).all()
                
                for prediction in predictions:
                    # Update prediction based on news impact
                    updated = self._update_prediction_with_news(
                        prediction, impact_analysis, news_item
                    )
                    
                    if updated:
                        updates_made += 1
                        
            if updates_made > 0:
                session.commit()
                self.logger.info(f"Updated {updates_made} predictions based on breaking news")
                
                # Send alert for high-impact news
                if impact_analysis['urgency'] == 'high':
                    self._send_breaking_news_alert(news_item, impact_analysis, updates_made)
            else:
                session.rollback()
                
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error handling breaking news: {e}")
        finally:
            db.close_session(session)
            
    def _update_prediction_with_news(self, prediction, impact_analysis, news_item):
        """Update a specific prediction based on breaking news"""
        try:
            original_fp = prediction.predicted_fantasy_points or 0
            original_confidence = prediction.confidence_score or 0.7
            
            # Apply impact to fantasy points
            impact_magnitude = impact_analysis['impact_magnitude']
            adjusted_fp = original_fp * (1 + impact_magnitude)
            
            # Ensure reasonable bounds
            adjusted_fp = max(0, min(50, adjusted_fp))  # Cap between 0-50 points
            
            # Adjust confidence
            confidence_adjustment = impact_analysis['confidence_adjustment']
            adjusted_confidence = original_confidence + confidence_adjustment
            adjusted_confidence = max(0.1, min(0.95, adjusted_confidence))  # Cap between 0.1-0.95
            
            # Only update if the change is significant
            fp_change = abs(adjusted_fp - original_fp)
            conf_change = abs(adjusted_confidence - original_confidence)
            
            if fp_change > 1.0 or conf_change > 0.05:
                prediction.predicted_fantasy_points = adjusted_fp
                prediction.confidence_score = adjusted_confidence
                
                # Update model version to indicate news adjustment
                prediction.model_version = f"{prediction.model_version or 'v2.0'}_news_adjusted"
                
                self.logger.info(f"Updated prediction for player {prediction.player_id}: "
                               f"FP: {original_fp:.1f} → {adjusted_fp:.1f}, "
                               f"Conf: {original_confidence:.2f} → {adjusted_confidence:.2f}")
                
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating prediction with news: {e}")
            return False
            
    def _get_current_nfl_week(self):
        """Get current NFL week (simplified - would need actual NFL calendar)"""
        # This is a simplified version - in production you'd check the actual NFL calendar
        current_date = datetime.utcnow()
        
        # Rough estimate: Week 1 starts in early September
        season_start = datetime(current_date.year, 9, 7)  # Approximate
        
        if current_date < season_start:
            return 1  # Preseason
        else:
            weeks_since_start = (current_date - season_start).days // 7
            return min(18, max(1, weeks_since_start + 1))
            
    def _send_breaking_news_alert(self, news_item, impact_analysis, updates_made):
        """Send alert for high-impact breaking news"""
        try:
            alert_message = f"""
🚨 HIGH-IMPACT BREAKING NEWS ALERT 🚨

News: {news_item.get('title', 'Unknown')}
Impact Type: {impact_analysis['impact_type']}
Impact Magnitude: {impact_analysis['impact_magnitude']:.2f}
Affected Players: {len(impact_analysis['affected_players'])}
Predictions Updated: {updates_made}

Source: {news_item.get('source', 'Unknown')}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """
            
            self.logger.warning(alert_message)
            
            # In production, this could send emails, SMS, or push notifications
            
        except Exception as e:
            self.logger.error(f"Error sending breaking news alert: {e}")
            
    def check_prediction_updates_needed(self, season, week=None):
        """Check which predictions might need updates based on recent news"""
        try:
            # Get recent news (last 24 hours)
            cutoff_time = datetime.utcnow() - self.relevance_windows['current']
            
            session = db.get_session()
            
            recent_news = session.query(NewsArticle).filter(
                NewsArticle.created_at >= cutoff_time
            ).all()
            
            team_news = session.query(TeamNews).filter(
                TeamNews.created_at >= cutoff_time
            ).all()
            
            all_news = list(recent_news) + list(team_news)
            
            update_recommendations = []
            
            for news in all_news:
                impact_analysis = self._analyze_news_impact({
                    'title': news.title,
                    'content': getattr(news, 'content', ''),
                    'published_date': news.created_at if hasattr(news, 'created_at') else datetime.utcnow()
                })
                
                if impact_analysis['requires_action']:
                    update_recommendations.append({
                        'news_title': news.title,
                        'impact_type': impact_analysis['impact_type'],
                        'impact_magnitude': impact_analysis['impact_magnitude'],
                        'affected_players': impact_analysis['affected_players'],
                        'urgency': impact_analysis['urgency']
                    })
                    
            db.close_session(session)
            
            return update_recommendations
            
        except Exception as e:
            self.logger.error(f"Error checking prediction updates needed: {e}")
            return []
            
    def manual_news_impact_check(self, news_text, player_name=None):
        """Manually check the impact of specific news"""
        try:
            # Create news item structure
            news_item = {
                'title': news_text,
                'content': '',
                'published_date': datetime.utcnow()
            }
            
            # Analyze impact
            impact_analysis = self._analyze_news_impact(news_item)
            
            # Filter for specific player if provided
            if player_name:
                impact_analysis['affected_players'] = [
                    p for p in impact_analysis['affected_players']
                    if player_name.lower() in p['name'].lower()
                ]
                
            return {
                'requires_action': impact_analysis['requires_action'],
                'impact_type': impact_analysis['impact_type'],
                'impact_magnitude': impact_analysis['impact_magnitude'],
                'confidence_adjustment': impact_analysis['confidence_adjustment'],
                'affected_players': impact_analysis['affected_players'],
                'urgency': impact_analysis['urgency'],
                'recommendation': self._get_impact_recommendation(impact_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Error in manual news impact check: {e}")
            return None
            
    def _get_impact_recommendation(self, impact_analysis):
        """Get recommendation based on impact analysis"""
        if not impact_analysis['requires_action']:
            return "No prediction updates needed"
            
        impact_mag = impact_analysis['impact_magnitude']
        urgency = impact_analysis['urgency']
        
        if urgency == 'high':
            if impact_mag < -0.5:
                return "URGENT: Significantly lower predictions and confidence"
            elif impact_mag > 0.4:
                return "URGENT: Significantly raise predictions and confidence"
        elif urgency == 'medium':
            if impact_mag < 0:
                return "Moderately lower predictions"
            else:
                return "Moderately raise predictions"
        else:
            return "Minor adjustment recommended"