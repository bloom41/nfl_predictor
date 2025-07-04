import logging
from datetime import datetime
from .espn_scraper import ESPNScraper
from .team_news_scraper import TeamNewsScraper
from src.database.database import db
from src.database.models import Player, PlayerStats, NewsArticle
from src.data_processing.workload_analyzer import WorkloadAnalyzer

class ScraperManager:
    def __init__(self):
        self.scrapers = {
            'espn': ESPNScraper(),
        }
        self.team_news_scraper = TeamNewsScraper()
        self.workload_analyzer = WorkloadAnalyzer()
        self.logger = logging.getLogger(__name__)
        
    def scrape_all_player_stats(self, season, week=None):
        """Scrape player statistics from all sources"""
        all_stats = []
        
        for source_name, scraper in self.scrapers.items():
            try:
                self.logger.info(f"Scraping player stats from {source_name}")
                stats = scraper.scrape_player_stats(season, week)
                all_stats.extend(stats)
                self.logger.info(f"Scraped {len(stats)} player records from {source_name}")
            except Exception as e:
                self.logger.error(f"Error scraping from {source_name}: {e}")
                
        return all_stats
        
    def scrape_all_news(self, limit=50):
        """Scrape news articles from all sources"""
        all_articles = []
        
        for source_name, scraper in self.scrapers.items():
            try:
                self.logger.info(f"Scraping news from {source_name}")
                articles = scraper.scrape_news(limit)
                all_articles.extend(articles)
                self.logger.info(f"Scraped {len(articles)} articles from {source_name}")
            except Exception as e:
                self.logger.error(f"Error scraping news from {source_name}: {e}")
                
        return all_articles
        
    def store_player_stats(self, stats_data, season, week):
        """Store scraped player statistics in database"""
        session = db.get_session()
        
        try:
            for stat in stats_data:
                # Find or create player
                player = session.query(Player).filter_by(
                    name=stat['player_name'],
                    team=stat['team']
                ).first()
                
                if not player:
                    player = Player(
                        name=stat['player_name'],
                        position=stat['position'],
                        team=stat['team']
                    )
                    session.add(player)
                    session.flush()  # Get the player ID
                
                # Check if stats already exist
                existing_stats = session.query(PlayerStats).filter_by(
                    player_id=player.id,
                    season=season,
                    week=week or 0
                ).first()
                
                if existing_stats:
                    # Update existing stats
                    for key, value in stat.items():
                        if hasattr(existing_stats, key) and key not in ['player_name', 'team', 'position']:
                            setattr(existing_stats, key, value)
                else:
                    # Create new stats record
                    player_stats = PlayerStats(
                        player_id=player.id,
                        season=season,
                        week=week or 0,
                        passing_attempts=stat.get('passing_attempts', 0),
                        passing_completions=stat.get('passing_completions', 0),
                        passing_yards=stat.get('passing_yards', 0),
                        passing_tds=stat.get('passing_tds', 0),
                        interceptions=stat.get('interceptions', 0),
                        rushing_attempts=stat.get('rushing_attempts', 0),
                        rushing_yards=stat.get('rushing_yards', 0),
                        rushing_tds=stat.get('rushing_tds', 0),
                        targets=stat.get('targets', 0),
                        receptions=stat.get('receptions', 0),
                        receiving_yards=stat.get('receiving_yards', 0),
                        receiving_tds=stat.get('receiving_tds', 0)
                    )
                    session.add(player_stats)
                    
            session.commit()
            self.logger.info(f"Stored {len(stats_data)} player stats records")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing player stats: {e}")
        finally:
            db.close_session(session)
            
    def store_news_articles(self, articles_data):
        """Store scraped news articles in database"""
        session = db.get_session()
        
        try:
            for article in articles_data:
                # Check if article already exists
                existing_article = session.query(NewsArticle).filter_by(
                    url=article['url']
                ).first()
                
                if not existing_article and article['url']:
                    news_article = NewsArticle(
                        title=article['title'],
                        content=article.get('content', ''),
                        source=article['source'],
                        url=article['url'],
                        published_date=article.get('published_date')
                    )
                    session.add(news_article)
                    
            session.commit()
            self.logger.info(f"Stored {len(articles_data)} news articles")
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing news articles: {e}")
        finally:
            db.close_session(session)
            
    def run_full_scrape(self, season, week=None):
        """Run complete scraping process for stats, news, and team data"""
        self.logger.info("Starting full scraping process")
        
        # Scrape player statistics
        stats_data = self.scrape_all_player_stats(season, week)
        if stats_data:
            self.store_player_stats(stats_data, season, week)
            
        # Scrape general news articles
        news_data = self.scrape_all_news()
        if news_data:
            self.store_news_articles(news_data)
            
        # Scrape team-specific news
        self.logger.info("Scraping team news")
        team_news_data = self.team_news_scraper.scrape_all_team_news(limit_per_team=5)
        if team_news_data:
            self.team_news_scraper.store_team_news(team_news_data)
            self.logger.info(f"Scraped {len(team_news_data)} team news articles")
            
        # Analyze workload for all players if we have stats
        if week and stats_data:
            self.logger.info("Analyzing player workloads")
            workload_data = self.workload_analyzer.analyze_all_players_workload(season, week)
            self.logger.info(f"Analyzed workload for {len(workload_data)} players")
            
        self.logger.info("Full scraping process completed")