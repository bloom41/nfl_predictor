"""
NFL News and Updates Monitoring System
Monitors real-time news, trades, injuries, and team updates
"""
import os
import sys
import json
import time
import logging
import requests
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from .models import Player, InjuryReport
from .data_collector import NFLDataCollector

logger = logging.getLogger(__name__)

class NFLNewsMonitor:
    """Real-time NFL news and updates monitoring system"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # News and update sources
        self.news_sources = {
            'espn_news': 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/news',
            'nfl_news': 'https://www.nfl.com/news/',
            'fantasy_pros': 'https://www.fantasypros.com/nfl/news/',
            'rotoworld': 'https://www.nbcsports.com/fantasy/football',
            'sleeper_api': 'https://api.sleeper.app/v1/league',  # For transaction data
        }
        
        # Update tracking
        self.last_update_times = {}
        self.rate_limit_delay = 2.0  # More conservative for news APIs
        
        # Keywords for important updates
        self.important_keywords = [
            'injury', 'injured', 'questionable', 'doubtful', 'out', 'IR',
            'trade', 'traded', 'signed', 'released', 'waived',
            'suspended', 'activated', 'practice squad',
            'starting', 'benched', 'depth chart',
            'covid', 'protocol', 'illness',
            'surgery', 'rehab', 'return'
        ]
        
        # Initialize data collector for updates
        self.data_collector = NFLDataCollector()

    def monitor_espn_news(self) -> List[Dict[str, Any]]:
        """Monitor ESPN NFL news API"""
        try:
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(self.news_sources['espn_news'], timeout=15)
            if response.status_code != 200:
                logger.warning(f"ESPN News API returned {response.status_code}")
                return []
            
            news_data = response.json()
            articles = news_data.get('articles', [])
            
            important_news = []
            for article in articles[:20]:  # Process latest 20 articles
                headline = article.get('headline', '').lower()
                description = article.get('description', '').lower()
                
                # Check if article contains important keywords
                if any(keyword in headline or keyword in description for keyword in self.important_keywords):
                    news_item = {
                        'source': 'espn',
                        'headline': article.get('headline'),
                        'description': article.get('description'),
                        'url': article.get('links', {}).get('web', {}).get('href'),
                        'published': article.get('published'),
                        'categories': article.get('categories', []),
                        'importance': self._calculate_news_importance(headline, description),
                        'processed_at': datetime.now().isoformat()
                    }
                    important_news.append(news_item)
            
            logger.info(f"Found {len(important_news)} important news items from ESPN")
            return important_news
            
        except Exception as e:
            logger.error(f"Error monitoring ESPN news: {e}")
            return []

    def _calculate_news_importance(self, headline: str, description: str) -> str:
        """Calculate importance level of news item"""
        text = (headline + ' ' + description).lower()
        
        # High importance keywords
        high_keywords = ['trade', 'traded', 'surgery', 'ir', 'suspended', 'starting', 'benched']
        medium_keywords = ['injury', 'injured', 'questionable', 'doubtful', 'signed', 'released']
        
        if any(keyword in text for keyword in high_keywords):
            return 'high'
        elif any(keyword in text for keyword in medium_keywords):
            return 'medium'
        else:
            return 'low'

    def process_injury_updates(self, news_items: List[Dict[str, Any]]):
        """Process injury-related news and update database"""
        injury_updates = []
        
        for item in news_items:
            if item['importance'] in ['high', 'medium']:
                text = (item['headline'] + ' ' + item['description']).lower()
                
                # Extract player names and injury status
                injury_info = self._extract_injury_info(text, item)
                if injury_info:
                    injury_updates.append(injury_info)
        
        # Save injury reports to database
        for injury in injury_updates:
            try:
                InjuryReport.objects.create(
                    player_id=injury.get('player_id', 0),
                    player_name=injury['player_name'],
                    team=injury.get('team', 'UNK'),
                    position=injury.get('position', 'UNK'),
                    week=self._get_current_nfl_week(),
                    season=timezone.now().year,
                    injury_status=injury['status'],
                    injury_description=injury['description'],
                    source=injury['source'],
                    date_reported=timezone.now()
                )
                logger.info(f"Created injury report for {injury['player_name']}: {injury['status']}")
            except Exception as e:
                logger.error(f"Error saving injury report: {e}")

    def _extract_injury_info(self, text: str, news_item: Dict) -> Optional[Dict[str, Any]]:
        """Extract injury information from news text"""
        # This is a simplified extraction - in production, you'd use NLP
        injury_statuses = {
            'questionable': 'questionable',
            'doubtful': 'doubtful',
            'out': 'out',
            'ir': 'ir',
            'injured reserve': 'ir',
            'healthy': 'healthy'
        }
        
        for status_text, status_code in injury_statuses.items():
            if status_text in text:
                # Try to extract player name (simplified - would need better NLP)
                words = text.split()
                potential_names = []
                
                for i, word in enumerate(words):
                    if word.istitle() and i < len(words) - 1 and words[i + 1].istitle():
                        potential_names.append(f"{word} {words[i + 1]}")
                
                if potential_names:
                    return {
                        'player_name': potential_names[0],  # Take first potential name
                        'status': status_code,
                        'description': news_item['headline'][:200],
                        'source': news_item['source'],
                        'team': 'UNK',  # Would need better extraction
                        'position': 'UNK'
                    }
        
        return None

    def _get_current_nfl_week(self) -> int:
        """Calculate current NFL week based on date"""
        # NFL season typically starts first Thursday after Labor Day
        current_date = timezone.now().date()
        year = current_date.year
        
        # Approximate NFL season start (adjust as needed)
        if current_date.month >= 9:  # September or later
            season_start = datetime(year, 9, 7).date()  # Approximate start
        else:  # Before September, previous season
            season_start = datetime(year - 1, 9, 7).date()
        
        days_since_start = (current_date - season_start).days
        week = max(1, min(18, (days_since_start // 7) + 1))
        
        return week

    def monitor_team_transactions(self) -> List[Dict[str, Any]]:
        """Monitor team transactions (trades, signings, releases)"""
        transactions = []
        
        try:
            # This would integrate with APIs that provide transaction data
            # For now, we'll create a framework that can be extended
            
            # ESPN transactions endpoint (if available)
            time.sleep(self.rate_limit_delay)
            
            # Placeholder for transaction monitoring
            logger.info("Monitoring team transactions...")
            
            # In production, this would:
            # 1. Monitor waiver wire claims
            # 2. Track free agent signings
            # 3. Monitor trades
            # 4. Update player team affiliations
            
        except Exception as e:
            logger.error(f"Error monitoring transactions: {e}")
        
        return transactions

    def update_player_data_from_news(self, news_items: List[Dict[str, Any]]):
        """Update player data based on news items"""
        for item in news_items:
            if item['importance'] == 'high':
                # Extract relevant updates and apply to player records
                self._process_player_update(item)

    def _process_player_update(self, news_item: Dict[str, Any]):
        """Process individual player update from news"""
        try:
            # This would include logic to:
            # 1. Extract player name from news
            # 2. Determine type of update (injury, trade, etc.)
            # 3. Update relevant database records
            # 4. Trigger prediction model updates if needed
            
            logger.debug(f"Processing player update: {news_item['headline']}")
            
        except Exception as e:
            logger.error(f"Error processing player update: {e}")

    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        logger.info("Starting NFL news monitoring cycle...")
        
        try:
            # 1. Monitor ESPN news
            espn_news = self.monitor_espn_news()
            
            # 2. Process injury updates
            if espn_news:
                self.process_injury_updates(espn_news)
            
            # 3. Monitor transactions
            transactions = self.monitor_team_transactions()
            
            # 4. Update player data
            self.update_player_data_from_news(espn_news)
            
            logger.info(f"Monitoring cycle complete: {len(espn_news)} news items processed")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")

    def setup_scheduled_monitoring(self):
        """Set up scheduled monitoring for ongoing updates"""
        logger.info("Setting up scheduled NFL monitoring...")
        
        # Schedule monitoring every 30 minutes during season
        schedule.every(30).minutes.do(self.run_monitoring_cycle)
        
        # More frequent monitoring during game days (Sundays, Mondays, Thursdays)
        schedule.every().sunday.at("09:00").do(self.run_monitoring_cycle)
        schedule.every().sunday.at("11:00").do(self.run_monitoring_cycle)
        schedule.every().sunday.at("13:00").do(self.run_monitoring_cycle)
        schedule.every().sunday.at("16:00").do(self.run_monitoring_cycle)
        schedule.every().sunday.at("20:00").do(self.run_monitoring_cycle)
        
        # Monday and Thursday night games
        schedule.every().monday.at("19:00").do(self.run_monitoring_cycle)
        schedule.every().thursday.at("19:00").do(self.run_monitoring_cycle)
        
        logger.info("Scheduled monitoring configured")

    def start_continuous_monitoring(self):
        """Start continuous monitoring in background"""
        self.setup_scheduled_monitoring()
        
        logger.info("Starting continuous NFL monitoring...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

# Utility functions for Django integration
def start_news_monitoring():
    """Start the news monitoring system"""
    monitor = NFLNewsMonitor()
    monitor.start_continuous_monitoring()

def run_single_monitoring_cycle():
    """Run a single monitoring cycle"""
    monitor = NFLNewsMonitor()
    monitor.run_monitoring_cycle()