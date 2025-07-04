import logging
import logging.handlers
import os
from datetime import datetime
from config.config import Config

def setup_logging():
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(Config.LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Create separate handler for errors
    error_log_file = Config.LOG_FILE.replace('.log', '_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    
    logging.info("Logging configured successfully")

class PerformanceMonitor:
    """Monitor system performance and key metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            'scraping_runs': 0,
            'scraping_errors': 0,
            'predictions_generated': 0,
            'model_training_runs': 0,
            'last_successful_scrape': None,
            'last_model_update': None
        }
        
    def log_scraping_run(self, success=True, records_scraped=0):
        """Log a scraping run"""
        self.metrics['scraping_runs'] += 1
        
        if success:
            self.metrics['last_successful_scrape'] = datetime.utcnow()
            self.logger.info(f"Scraping run completed successfully - {records_scraped} records")
        else:
            self.metrics['scraping_errors'] += 1
            self.logger.error("Scraping run failed")
            
    def log_prediction_generation(self, count):
        """Log prediction generation"""
        self.metrics['predictions_generated'] += count
        self.logger.info(f"Generated {count} predictions")
        
    def log_model_training(self, success=True):
        """Log model training"""
        self.metrics['model_training_runs'] += 1
        
        if success:
            self.metrics['last_model_update'] = datetime.utcnow()
            self.logger.info("Model training completed successfully")
        else:
            self.logger.error("Model training failed")
            
    def get_metrics(self):
        """Get current metrics"""
        return self.metrics.copy()
        
    def log_system_health(self):
        """Log system health metrics"""
        self.logger.info("System Health Check:")
        self.logger.info(f"  Total scraping runs: {self.metrics['scraping_runs']}")
        self.logger.info(f"  Scraping errors: {self.metrics['scraping_errors']}")
        self.logger.info(f"  Predictions generated: {self.metrics['predictions_generated']}")
        self.logger.info(f"  Model training runs: {self.metrics['model_training_runs']}")
        self.logger.info(f"  Last successful scrape: {self.metrics['last_successful_scrape']}")
        self.logger.info(f"  Last model update: {self.metrics['last_model_update']}")
        
        # Calculate success rates
        if self.metrics['scraping_runs'] > 0:
            success_rate = (1 - self.metrics['scraping_errors'] / self.metrics['scraping_runs']) * 100
            self.logger.info(f"  Scraping success rate: {success_rate:.1f}%")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()