import schedule
import time
import logging
from datetime import datetime, timedelta
from threading import Thread
import signal
import sys
from src.scrapers.scraper_manager import ScraperManager
from src.data_processing.sentiment_analyzer import SentimentAnalyzer
from src.models.model_manager import ModelManager
from config.config import Config

class NFLDataScheduler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = True
        
        # Initialize components
        self.scraper_manager = ScraperManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.model_manager = ModelManager()
        
        # Load existing models
        self.model_manager.load_all_models()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def scrape_and_update_data(self):
        """Scrape new data and update predictions"""
        try:
            self.logger.info("Starting scheduled data scrape and update")
            
            # Get current season and week
            current_season = 2025  # Update this logic as needed
            current_week = self._get_current_nfl_week()
            
            # Step 1: Scrape new data
            self.logger.info("Scraping new player statistics and news")
            self.scraper_manager.run_full_scrape(current_season, current_week)
            
            # Step 2: Process sentiment analysis on new articles
            self.logger.info("Processing sentiment analysis")
            self.sentiment_analyzer.process_news_articles(limit=100)
            
            # Step 3: Generate new predictions
            self.logger.info("Generating new predictions")
            self._generate_weekly_predictions(current_season, current_week)
            
            self.logger.info("Scheduled update completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during scheduled update: {e}")
            
    def retrain_models_daily(self):
        """Retrain models with accumulated data"""
        try:
            self.logger.info("Starting daily model retraining")
            
            current_season = 2025
            self.model_manager.update_models_with_new_data(current_season)
            
            self.logger.info("Daily model retraining completed")
            
        except Exception as e:
            self.logger.error(f"Error during model retraining: {e}")
            
    def _generate_weekly_predictions(self, season, week):
        """Generate predictions for the upcoming week"""
        try:
            # Generate predictions for next week
            next_week = week + 1 if week < 18 else 1
            
            predictions = self.model_manager.predict_weekly_top_performers(
                season, next_week, top_n=100
            )
            
            if predictions:
                # Save to database
                for model_pos in ['QB', 'RB', 'WR', 'TE']:
                    model = self.model_manager.get_model(model_pos)
                    if model:
                        pos_predictions = [p for p in predictions if p['position'] == model_pos]
                        model.save_predictions_to_db(pos_predictions)
                        
                self.logger.info(f"Generated {len(predictions)} predictions for week {next_week}")
            else:
                self.logger.warning("No predictions generated")
                
        except Exception as e:
            self.logger.error(f"Error generating predictions: {e}")
            
    def _get_current_nfl_week(self):
        """Determine current NFL week based on date"""
        # This is a simplified version - in production you'd want to use
        # actual NFL schedule data
        now = datetime.now()
        
        # NFL season typically starts in early September
        season_start = datetime(now.year, 9, 1)
        
        if now < season_start:
            return 1  # Preseason/offseason
            
        days_since_start = (now - season_start).days
        week = min(days_since_start // 7 + 1, 18)  # Regular season is 18 weeks
        
        return week
        
    def setup_schedule(self):
        """Setup the automated schedule"""
        self.logger.info("Setting up automated schedule")
        
        # Schedule data scraping every 20 minutes
        schedule.every(Config.SCRAPING_INTERVAL_MINUTES).minutes.do(
            self.scrape_and_update_data
        )
        
        # Schedule daily model retraining (at 3 AM)
        schedule.every().day.at("03:00").do(self.retrain_models_daily)
        
        # Schedule weekly comprehensive analysis (Sunday at 6 AM)
        schedule.every().sunday.at("06:00").do(self._weekly_comprehensive_update)
        
        self.logger.info("Schedule configured:")
        self.logger.info(f"- Data scraping: Every {Config.SCRAPING_INTERVAL_MINUTES} minutes")
        self.logger.info("- Model retraining: Daily at 3:00 AM")
        self.logger.info("- Comprehensive update: Sundays at 6:00 AM")
        
    def _weekly_comprehensive_update(self):
        """Comprehensive weekly update including data validation"""
        try:
            self.logger.info("Starting weekly comprehensive update")
            
            current_season = 2025
            current_week = self._get_current_nfl_week()
            
            # Run full data collection
            self.scraper_manager.run_full_scrape(current_season, current_week)
            
            # Process all unanalyzed sentiment
            self.sentiment_analyzer.process_news_articles()
            
            # Retrain models
            self.model_manager.update_models_with_new_data(current_season)
            
            # Generate predictions for next several weeks
            for week_offset in range(1, 5):  # Next 4 weeks
                future_week = current_week + week_offset
                if future_week <= 18:
                    self._generate_weekly_predictions(current_season, future_week)
                    
            self.logger.info("Weekly comprehensive update completed")
            
        except Exception as e:
            self.logger.error(f"Error during weekly update: {e}")
            
    def run(self):
        """Run the scheduler"""
        self.logger.info("Starting NFL Prediction Scheduler")
        
        # Setup schedule
        self.setup_schedule()
        
        # Run initial data collection if no recent data exists
        self.logger.info("Running initial data collection")
        self.scrape_and_update_data()
        
        # Main scheduling loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(300)  # Wait 5 minutes before continuing
                
        self.logger.info("Scheduler stopped")
        
    def run_in_background(self):
        """Run scheduler in background thread"""
        scheduler_thread = Thread(target=self.run, daemon=True)
        scheduler_thread.start()
        return scheduler_thread
        
    def get_status(self):
        """Get current status of the scheduler"""
        return {
            'running': self.running,
            'next_jobs': [str(job) for job in schedule.jobs],
            'models_loaded': len(self.model_manager.models),
            'current_week': self._get_current_nfl_week()
        }