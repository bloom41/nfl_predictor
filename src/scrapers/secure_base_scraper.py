"""
Secure base scraper with input validation, rate limiting, and SQL injection protection
"""
import re
import time
import hashlib
import logging
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse, quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.database_v2 import db_manager

logger = logging.getLogger(__name__)

class InputValidator:
    """Input validation and sanitization utility"""
    
    # Safe patterns for various inputs
    PLAYER_NAME_PATTERN = re.compile(r"^[A-Za-z\'\.\-\s]{1,50}$")
    TEAM_CODE_PATTERN = re.compile(r"^[A-Z]{2,4}$")
    URL_PATTERN = re.compile(r"^https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(/.*)?$")
    NUMERIC_PATTERN = re.compile(r"^-?[\d\.]+$")
    
    @classmethod
    def validate_player_name(cls, name: str) -> bool:
        """Validate player name format"""
        return bool(name and cls.PLAYER_NAME_PATTERN.match(name.strip()))
    
    @classmethod
    def validate_team_code(cls, team: str) -> bool:
        """Validate team code format"""
        return bool(team and cls.TEAM_CODE_PATTERN.match(team.strip().upper()))
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate URL format"""
        return bool(url and cls.URL_PATTERN.match(url.strip()))
    
    @classmethod
    def validate_numeric(cls, value: Union[str, int, float]) -> bool:
        """Validate numeric value"""
        if isinstance(value, (int, float)):
            return True
        return bool(value and cls.NUMERIC_PATTERN.match(str(value).strip()))
    
    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 500) -> str:
        """Sanitize string input"""
        if not text:
            return ""
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>"\';\\]', '', str(text))
        # Limit length
        sanitized = sanitized.strip()[:max_length]
        return sanitized
    
    @classmethod
    def sanitize_player_name(cls, name: str) -> str:
        """Sanitize player name"""
        if not name:
            return ""
        
        # Allow only letters, apostrophes, periods, hyphens, and spaces
        sanitized = re.sub(r"[^A-Za-z\'\.\-\s]", "", str(name))
        sanitized = sanitized.strip()[:50]
        return sanitized
    
    @classmethod
    def sanitize_team_code(cls, team: str) -> str:
        """Sanitize team code"""
        if not team:
            return ""
        
        # Convert to uppercase and remove non-letters
        sanitized = re.sub(r"[^A-Z]", "", str(team).upper())
        return sanitized[:4]


class SecureRateLimiter:
    """Rate limiter with exponential backoff"""
    
    def __init__(self, requests_per_minute: int = 30, burst_limit: int = 5):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.request_times = []
        self.consecutive_failures = 0
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove old requests (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we need to wait
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60 - (now - min(self.request_times))
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        # Add exponential backoff for consecutive failures
        if self.consecutive_failures > 0:
            backoff_time = min(2 ** self.consecutive_failures, 60)  # Max 60 seconds
            logger.debug(f"Applying backoff for failures: {backoff_time} seconds")
            time.sleep(backoff_time)
        
        self.request_times.append(now)
    
    def record_success(self):
        """Record successful request"""
        self.consecutive_failures = 0
    
    def record_failure(self):
        """Record failed request"""
        self.consecutive_failures += 1


class SecureBaseScraper:
    """
    Secure base scraper with proper error handling, rate limiting,
    and SQL injection protection
    """
    
    def __init__(self, source_name: str, requests_per_minute: int = 30):
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{source_name}")
        self.rate_limiter = SecureRateLimiter(requests_per_minute)
        self.validator = InputValidator()
        
        # Setup secure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set secure headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; NFL-Predictor/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def secure_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """
        Make a secure HTTP request with rate limiting and error handling
        """
        # Validate URL
        if not self.validator.validate_url(url):
            self.logger.error(f"Invalid URL format: {url}")
            return None
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            # Make request with timeout
            response = self.session.request(
                method=method,
                url=url,
                timeout=30,
                **kwargs
            )
            
            # Check response status
            response.raise_for_status()
            
            self.rate_limiter.record_success()
            self.logger.debug(f"Successful request to {url}")
            
            return response
            
        except requests.exceptions.RequestException as e:
            self.rate_limiter.record_failure()
            self.logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            self.rate_limiter.record_failure()
            self.logger.error(f"Unexpected error requesting {url}: {e}")
            return None
    
    def safe_database_query(self, query_func, *args, **kwargs):
        """
        Execute database query safely with proper session management
        """
        try:
            with db_manager.get_session() as session:
                return query_func(session, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            return None
    
    def safe_database_readonly_query(self, query_func, *args, **kwargs):
        """
        Execute read-only database query safely
        """
        try:
            with db_manager.get_readonly_session() as session:
                return query_func(session, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Database readonly query failed: {e}")
            return None
    
    def find_player_by_name(self, player_name: str, session: Session):
        """
        Safely find player by name with SQL injection protection
        """
        # Validate and sanitize input
        if not self.validator.validate_player_name(player_name):
            self.logger.warning(f"Invalid player name format: {player_name}")
            return None
        
        sanitized_name = self.validator.sanitize_player_name(player_name)
        
        try:
            from src.database.models import Player
            
            # Use parameterized query to prevent SQL injection
            result = session.query(Player).filter(
                Player.name.ilike(f"%{sanitized_name}%")
            ).first()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error finding player {sanitized_name}: {e}")
            return None
    
    def find_team_players(self, team_code: str, position: str, session: Session):
        """
        Safely find players by team and position
        """
        # Validate inputs
        if not self.validator.validate_team_code(team_code):
            self.logger.warning(f"Invalid team code: {team_code}")
            return []
        
        sanitized_team = self.validator.sanitize_team_code(team_code)
        sanitized_position = self.validator.sanitize_string(position, 10)
        
        try:
            from src.database.models import Player
            
            # Use parameterized query
            results = session.query(Player).filter(
                Player.team == sanitized_team,
                Player.position == sanitized_position
            ).all()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error finding team players {sanitized_team}/{sanitized_position}: {e}")
            return []
    
    def safe_insert_or_update(self, model_class, data: Dict[str, Any], 
                             unique_fields: List[str], session: Session):
        """
        Safely insert or update data with validation
        """
        try:
            # Validate data fields
            validated_data = self._validate_model_data(model_class, data)
            if not validated_data:
                return None
            
            # Check if record exists
            filter_criteria = {field: validated_data[field] for field in unique_fields 
                             if field in validated_data}
            
            existing = session.query(model_class).filter_by(**filter_criteria).first()
            
            if existing:
                # Update existing record
                for key, value in validated_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                session.flush()
                return existing
            else:
                # Create new record
                new_record = model_class(**validated_data)
                session.add(new_record)
                session.flush()
                return new_record
                
        except Exception as e:
            self.logger.error(f"Error inserting/updating {model_class.__name__}: {e}")
            return None
    
    def _validate_model_data(self, model_class, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate data against model schema
        """
        validated_data = {}
        
        try:
            # Get model columns
            columns = model_class.__table__.columns
            
            for column_name, column in columns.items():
                if column_name in data:
                    value = data[column_name]
                    
                    # Skip None values for non-nullable columns with defaults
                    if value is None and not column.nullable and column.default is not None:
                        continue
                    
                    # Validate based on column type
                    if hasattr(column.type, 'python_type'):
                        python_type = column.type.python_type
                        
                        if python_type == str:
                            validated_data[column_name] = self.validator.sanitize_string(
                                str(value), getattr(column.type, 'length', 500)
                            )
                        elif python_type in (int, float):
                            if self.validator.validate_numeric(value):
                                validated_data[column_name] = python_type(value)
                        else:
                            validated_data[column_name] = value
                    else:
                        validated_data[column_name] = value
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Data validation failed for {model_class.__name__}: {e}")
            return None
    
    def generate_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        key_string = f"{self.source_name}:" + ":".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def log_scraping_attempt(self, url: str, success: bool, error: str = None):
        """Log scraping attempt for monitoring"""
        log_data = {
            'source': self.source_name,
            'url': url,
            'success': success,
            'timestamp': time.time()
        }
        
        if error:
            log_data['error'] = error
        
        if success:
            self.logger.info(f"Successfully scraped {url}")
        else:
            self.logger.error(f"Failed to scrape {url}: {error}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.session.close()
            self.logger.debug(f"Cleaned up {self.source_name} scraper")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Utility functions for backward compatibility
def safe_player_lookup(player_name: str, session: Session):
    """Safe player lookup function"""
    validator = InputValidator()
    if not validator.validate_player_name(player_name):
        return None
    
    sanitized_name = validator.sanitize_player_name(player_name)
    
    try:
        from src.database.models import Player
        return session.query(Player).filter(
            Player.name.ilike(f"%{sanitized_name}%")
        ).first()
    except Exception:
        return None


def safe_team_lookup(team_code: str, session: Session):
    """Safe team lookup function"""
    validator = InputValidator()
    if not validator.validate_team_code(team_code):
        return []
    
    sanitized_team = validator.sanitize_team_code(team_code)
    
    try:
        from src.database.models import Player
        return session.query(Player).filter(
            Player.team == sanitized_team
        ).all()
    except Exception:
        return []


__all__ = ['SecureBaseScraper', 'InputValidator', 'SecureRateLimiter', 
           'safe_player_lookup', 'safe_team_lookup']