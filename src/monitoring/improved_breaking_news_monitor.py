"""
Improved breaking news monitor using the robust monitoring framework
"""
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.monitoring.robust_monitoring_framework import BaseMonitor
from src.scrapers.espn_scraper import ESPNScraper
from src.scrapers.team_news_scraper import TeamNewsScraper
from src.data_processing.sentiment_analyzer import SentimentAnalyzer
from src.database.database_v2 import db_session
from src.database.models import Player, Prediction, NewsArticle
from src.utils.input_validation import InputValidator, SecurityValidator

logger = logging.getLogger(__name__)

class ImprovedBreakingNewsMonitor(BaseMonitor):
    """
    Breaking news monitor with robust error handling and recovery
    """
    
    def __init__(self, check_interval: float = 300.0):  # 5 minutes
        super().__init__("BreakingNewsMonitor", check_interval)
        
        # Initialize scrapers with error handling
        try:
            self.espn_scraper = ESPNScraper()
            self.team_scraper = TeamNewsScraper()
            self.sentiment_analyzer = SentimentAnalyzer()
            self.validator = InputValidator()
        except Exception as e:
            logger.error(f"Failed to initialize scrapers: {e}")
            raise
        
        # Configuration
        self.impact_threshold = 0.7  # Threshold for triggering prediction updates
        self.max_news_items = 50     # Maximum news items to process per iteration
        self.lookback_hours = 1      # How far back to look for news
        
        # State tracking
        self.last_check_time: Optional[datetime] = None
        self.processed_urls = set()  # Track processed articles to avoid duplicates
        
        # Performance tracking
        self.news_processed = 0
        self.predictions_updated = 0
        self.impact_alerts_sent = 0
    
    def _monitor_iteration(self) -> bool:
        """
        Perform one iteration of breaking news monitoring
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            current_time = datetime.utcnow()
            
            # Determine lookback time
            if self.last_check_time:
                since_time = self.last_check_time
            else:
                since_time = current_time - timedelta(hours=self.lookback_hours)
            
            # Fetch recent news
            news_items = self._fetch_recent_news_safe(since_time)
            
            if not news_items:
                logger.debug("No new breaking news found")
                self.last_check_time = current_time
                return True
            
            logger.info(f"Processing {len(news_items)} breaking news items")
            
            # Process each news item
            high_impact_items = []
            
            for news_item in news_items:
                try:
                    # Skip if already processed
                    if news_item.get('url') in self.processed_urls:
                        continue
                    
                    # Analyze impact
                    impact_analysis = self._analyze_news_impact_safe(news_item)
                    
                    if impact_analysis and impact_analysis.get('requires_action', False):
                        high_impact_items.append((news_item, impact_analysis))
                    
                    # Track processed item
                    if news_item.get('url'):
                        self.processed_urls.add(news_item['url'])
                    
                    self.news_processed += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing news item: {e}")
                    # Continue processing other items
                    continue
            
            # Handle high impact items
            if high_impact_items:
                self._handle_breaking_news_batch(high_impact_items, current_time)
            
            # Update last check time
            self.last_check_time = current_time
            
            # Clean up old processed URLs to prevent memory growth
            self._cleanup_processed_urls()
            
            logger.info(f"Breaking news monitoring iteration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in breaking news monitoring iteration: {e}")
            return False
    
    def _fetch_recent_news_safe(self, since_time: datetime) -> List[Dict[str, Any]]:
        """
        Safely fetch recent news with error isolation
        """
        news_items = []
        
        # Fetch ESPN news with error handling
        try:
            espn_news = self.espn_scraper.scrape_news(limit=20)
            if espn_news:
                news_items.extend(self._filter_recent_news(espn_news, since_time))
                logger.debug(f"Fetched {len(espn_news)} ESPN news items")
        except Exception as e:
            logger.warning(f"Failed to fetch ESPN news: {e}")
            # Continue with other sources
        
        # Fetch team news for priority teams
        priority_teams = ['KC', 'BUF', 'SF', 'MIA', 'DAL', 'NE', 'LAR', 'PHI']
        
        for team_abbr in priority_teams:
            try:
                # Validate team code
                is_valid, validated_team = self.validator.validate_team_code(team_abbr)
                if not is_valid:
                    continue
                
                team_items = self.team_scraper.scrape_team_news(validated_team, limit=3)
                if team_items:
                    filtered_items = self._filter_recent_news(team_items, since_time)
                    news_items.extend(filtered_items)
                    
                # Rate limiting between team requests
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to fetch {team_abbr} team news: {e}")
                # Continue with other teams
                continue
        
        # Remove duplicates and limit total items
        unique_items = self._deduplicate_news(news_items)
        return unique_items[:self.max_news_items]
    
    def _filter_recent_news(self, news_items: List[Dict], since_time: datetime) -> List[Dict]:
        """Filter news items to only recent ones"""
        filtered_items = []
        
        for item in news_items:
            try:
                published_date = item.get('published_date')
                if published_date and isinstance(published_date, datetime):
                    if published_date > since_time:
                        filtered_items.append(item)
                elif not published_date:
                    # If no date, assume it's recent (but add with lower priority)
                    filtered_items.append(item)
            except Exception as e:
                logger.debug(f"Error filtering news item date: {e}")
                continue
        
        return filtered_items
    
    def _deduplicate_news(self, news_items: List[Dict]) -> List[Dict]:
        """Remove duplicate news items based on URL and title"""
        seen_urls = set()
        seen_titles = set()
        unique_items = []
        
        for item in news_items:
            url = item.get('url', '')
            title = item.get('title', '').lower().strip()
            
            # Skip if URL already seen
            if url and url in seen_urls:
                continue
            
            # Skip if very similar title already seen
            if title and title in seen_titles:
                continue
            
            unique_items.append(item)
            
            if url:
                seen_urls.add(url)
            if title:
                seen_titles.add(title)
        
        return unique_items
    
    def _analyze_news_impact_safe(self, news_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Safely analyze news impact with input validation
        """
        try:
            # Validate and sanitize inputs
            title = self.validator.sanitize_string(news_item.get('title', ''), 200)
            content = self.validator.sanitize_string(news_item.get('content', ''), 1000)
            
            if not title and not content:
                return None
            
            # Security check
            is_safe, _ = SecurityValidator.validate_safe_input(f"{title} {content}", "news_content")
            if not is_safe:
                logger.warning("Potentially unsafe news content detected, skipping")
                return None
            
            full_text = f"{title} {content}".lower()
            
            # Initialize impact analysis
            impact_analysis = {
                'impact_score': 0.0,
                'impact_type': 'unknown',
                'affected_players': [],
                'requires_action': False,
                'confidence': 0.0,
                'keywords_found': []
            }
            
            # High-impact keywords and their weights
            impact_keywords = {
                # Injury keywords (high impact)
                'injured': 0.9,
                'injury': 0.9,
                'hurt': 0.8,
                'questionable': 0.7,
                'doubtful': 0.8,
                'out': 0.9,
                'placed on ir': 1.0,
                'torn': 0.9,
                'surgery': 0.8,
                'concussion': 0.9,
                
                # Trade/roster keywords (high impact)
                'traded': 1.0,
                'signs': 0.8,
                'released': 0.9,
                'waived': 0.7,
                'suspended': 0.9,
                'cut': 0.8,
                'acquired': 0.8,
                
                # Performance keywords (medium impact)
                'benched': 0.7,
                'starting': 0.6,
                'backup': 0.5,
                'promoted': 0.6,
                'demoted': 0.6,
                
                # Team keywords (medium impact)
                'coaching change': 0.7,
                'fired': 0.8,
                'hired': 0.6,
                'scheme change': 0.6
            }
            
            # Calculate impact score
            total_impact = 0.0
            keywords_found = []
            
            for keyword, weight in impact_keywords.items():
                if keyword in full_text:
                    total_impact += weight
                    keywords_found.append(keyword)
                    
                    # Determine impact type
                    if keyword in ['injured', 'injury', 'hurt', 'questionable', 'doubtful', 'out', 'concussion']:
                        impact_analysis['impact_type'] = 'injury'
                    elif keyword in ['traded', 'signs', 'released', 'waived', 'acquired']:
                        impact_analysis['impact_type'] = 'roster_change'
                    elif keyword in ['benched', 'starting', 'backup', 'promoted', 'demoted']:
                        impact_analysis['impact_type'] = 'role_change'
            
            impact_analysis['impact_score'] = min(total_impact, 1.0)  # Cap at 1.0
            impact_analysis['keywords_found'] = keywords_found
            
            # Extract mentioned players
            affected_players = self._extract_mentioned_players(full_text)
            impact_analysis['affected_players'] = affected_players
            
            # Boost impact score if star players are mentioned
            star_players = ['mahomes', 'allen', 'jackson', 'herbert', 'mccaffrey', 'henry', 'kupp', 'adams', 'kelce']
            for player in affected_players:
                if any(star in player.lower() for star in star_players):
                    impact_analysis['impact_score'] += 0.2
                    break
            
            # Final impact score (capped at 1.0)
            impact_analysis['impact_score'] = min(impact_analysis['impact_score'], 1.0)
            
            # Determine if action is required
            impact_analysis['requires_action'] = impact_analysis['impact_score'] >= self.impact_threshold
            
            # Calculate confidence based on number of keywords and content quality
            confidence = min(0.5 + (len(keywords_found) * 0.1) + (len(content) / 1000 * 0.1), 0.95)
            impact_analysis['confidence'] = confidence
            
            return impact_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing news impact: {e}")
            return None
    
    def _extract_mentioned_players(self, text: str) -> List[str]:
        """Extract player names mentioned in text"""
        try:
            # Get known players from database
            def get_player_names(session):
                players = session.query(Player.name).filter(
                    Player.position.in_(['QB', 'RB', 'WR', 'TE'])
                ).all()
                return [player.name for player in players]
            
            player_names = db_session.execute_readonly_query(get_player_names)
            
            if not player_names:
                return []
            
            mentioned_players = []
            text_lower = text.lower()
            
            for name in player_names:
                # Check for full name or last name
                name_lower = name.lower()
                last_name = name_lower.split()[-1] if ' ' in name_lower else name_lower
                
                if name_lower in text_lower or (len(last_name) > 3 and last_name in text_lower):
                    mentioned_players.append(name)
            
            return mentioned_players[:10]  # Limit to top 10 mentions
            
        except Exception as e:
            logger.warning(f"Error extracting player mentions: {e}")
            return []
    
    def _handle_breaking_news_batch(self, high_impact_items: List[tuple], current_time: datetime):
        """
        Handle a batch of high-impact news items
        """
        try:
            for news_item, impact_analysis in high_impact_items:
                try:
                    self._handle_single_breaking_news(news_item, impact_analysis, current_time)
                    self.impact_alerts_sent += 1
                except Exception as e:
                    logger.error(f"Error handling single breaking news item: {e}")
                    continue
            
            logger.info(f"Processed {len(high_impact_items)} high-impact news items")
            
        except Exception as e:
            logger.error(f"Error in batch news handling: {e}")
    
    def _handle_single_breaking_news(self, news_item: Dict, impact_analysis: Dict, current_time: datetime):
        """Handle a single high-impact breaking news item"""
        try:
            # Store news article in database
            def store_news_article(session):
                # Check if already exists
                existing = session.query(NewsArticle).filter_by(
                    url=news_item.get('url')
                ).first()
                
                if existing:
                    return existing.id
                
                # Create new article
                article = NewsArticle(
                    title=news_item.get('title', ''),
                    content=news_item.get('content', ''),
                    url=news_item.get('url', ''),
                    source=news_item.get('source', 'unknown'),
                    published_date=news_item.get('published_date', current_time),
                    sentiment_score=impact_analysis.get('impact_score', 0.0),
                    players_mentioned=','.join(impact_analysis.get('affected_players', [])),
                    teams_mentioned=''  # Could be enhanced to extract teams
                )
                
                session.add(article)
                session.flush()
                return article.id
            
            article_id = db_session.execute_query(store_news_article)
            
            # Log the high-impact news
            logger.info(
                f"High-impact breaking news detected: "
                f"'{news_item.get('title', 'No title')}' "
                f"(Impact: {impact_analysis['impact_score']:.2f}, "
                f"Type: {impact_analysis['impact_type']}, "
                f"Players: {', '.join(impact_analysis['affected_players'][:3])})"
            )
            
            # TODO: Trigger prediction updates for affected players
            # This would integrate with the prediction system
            
            # TODO: Send notifications if configured
            # This could integrate with alerting systems
            
        except Exception as e:
            logger.error(f"Error handling breaking news item: {e}")
    
    def _cleanup_processed_urls(self):
        """Clean up old processed URLs to prevent memory growth"""
        if len(self.processed_urls) > 1000:  # Keep last 1000 URLs
            # Convert to list, sort, and keep recent ones
            url_list = list(self.processed_urls)
            # Keep the most recent 500 URLs (simple cleanup)
            self.processed_urls = set(url_list[-500:])
            logger.debug("Cleaned up old processed URLs")
    
    def get_monitor_metrics(self) -> Dict[str, Any]:
        """Get monitor-specific metrics"""
        base_metrics = self.get_metrics()
        
        base_metrics.update({
            'news_processed': self.news_processed,
            'predictions_updated': self.predictions_updated,
            'impact_alerts_sent': self.impact_alerts_sent,
            'processed_urls_count': len(self.processed_urls),
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'impact_threshold': self.impact_threshold
        })
        
        return base_metrics


__all__ = ['ImprovedBreakingNewsMonitor']