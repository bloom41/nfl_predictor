import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///nfl_predictor.db')
    
    # Scraping configuration
    SCRAPING_INTERVAL_MINUTES = 120  # Reduced from 20 to 120 minutes to prevent system overload
    REQUEST_DELAY = 1  # seconds between requests
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # Data sources
    NFL_SOURCES = {
        'espn': 'https://www.espn.com/nfl/',
        'nfl_official': 'https://www.nfl.com/',
        'pro_football_reference': 'https://www.pro-football-reference.com/',
        'fantasy_pros': 'https://www.fantasypros.com/nfl/'
    }
    
    # Model configuration
    MODEL_RETRAIN_FREQUENCY = 'daily'  # or 'weekly'
    PREDICTION_HORIZON_WEEKS = 4
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/nfl_predictor.log'
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    
    # Features for prediction
    OFFENSIVE_POSITIONS = ['QB', 'RB', 'WR', 'TE']
    
    # Prediction metrics
    PREDICTION_METRICS = [
        'passing_yards', 'passing_tds', 'rushing_yards', 'rushing_tds',
        'receiving_yards', 'receiving_tds', 'fantasy_points'
    ]