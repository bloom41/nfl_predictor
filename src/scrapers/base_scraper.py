import requests
import time
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
import logging
from config.config import Config

class BaseScraper(ABC):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': Config.USER_AGENT})
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def get_page(self, url, delay=None, params=None):
        """Fetch a web page with rate limiting"""
        if delay is None:
            delay = Config.REQUEST_DELAY
            
        try:
            time.sleep(delay)
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None
            
    def parse_html(self, html_content):
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')
        
    @abstractmethod
    def scrape_player_stats(self, season, week=None):
        """Scrape player statistics"""
        pass
        
    @abstractmethod
    def scrape_news(self, limit=50):
        """Scrape news articles"""
        pass