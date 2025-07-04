"""
Comprehensive input validation and sanitization utilities
"""
import re
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class InputValidator:
    """
    Comprehensive input validation and sanitization for NFL prediction system
    """
    
    # Regular expressions for validation
    PATTERNS = {
        'player_name': re.compile(r"^[A-Za-z\'\.\-\s]{1,50}$"),
        'team_code': re.compile(r"^[A-Z]{2,4}$"),
        'position': re.compile(r"^(QB|RB|WR|TE|K|DEF)$"),
        'url': re.compile(r"^https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(/.*)?$"),
        'email': re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
        'numeric': re.compile(r"^-?[\d\.]+$"),
        'alphanumeric': re.compile(r"^[a-zA-Z0-9]+$"),
        'safe_string': re.compile(r"^[a-zA-Z0-9\s\-_\.]{1,100}$"),
    }
    
    # Valid team codes
    VALID_TEAMS = {
        'BUF', 'MIA', 'NE', 'NYJ',  # AFC East
        'BAL', 'CIN', 'CLE', 'PIT',  # AFC North
        'HOU', 'IND', 'JAX', 'TEN',  # AFC South
        'DEN', 'KC', 'LV', 'LAC',    # AFC West
        'DAL', 'NYG', 'PHI', 'WAS',  # NFC East
        'CHI', 'DET', 'GB', 'MIN',   # NFC North
        'ATL', 'CAR', 'NO', 'TB',    # NFC South
        'ARI', 'LAR', 'SF', 'SEA'    # NFC West
    }
    
    # Valid positions
    VALID_POSITIONS = {'QB', 'RB', 'WR', 'TE', 'K', 'DEF'}
    
    # Data type limits
    LIMITS = {
        'week': (1, 18),
        'season': (2020, 2030),
        'age': (18, 50),
        'experience': (0, 25),
        'fantasy_points': (0, 100),
        'passing_yards': (0, 600),
        'rushing_yards': (0, 400),
        'receiving_yards': (0, 300),
        'touchdowns': (0, 10),
        'interceptions': (0, 10),
        'receptions': (0, 20),
    }
    
    @classmethod
    def validate_player_name(cls, name: Any) -> Tuple[bool, str]:
        """
        Validate player name
        
        Returns:
            Tuple[bool, str]: (is_valid, sanitized_name_or_error)
        """
        try:
            if not name:
                return False, "Player name cannot be empty"
            
            name_str = str(name).strip()
            
            if len(name_str) < 2:
                return False, "Player name too short"
            
            if len(name_str) > 50:
                return False, "Player name too long"
            
            if not cls.PATTERNS['player_name'].match(name_str):
                return False, "Player name contains invalid characters"
            
            # Additional checks
            if name_str.count(' ') > 3:  # Max 4 names
                return False, "Too many name parts"
            
            return True, cls.sanitize_player_name(name_str)
            
        except Exception as e:
            logger.error(f"Error validating player name: {e}")
            return False, "Validation error"
    
    @classmethod
    def validate_team_code(cls, team: Any) -> Tuple[bool, str]:
        """Validate team code"""
        try:
            if not team:
                return False, "Team code cannot be empty"
            
            team_str = str(team).strip().upper()
            
            if team_str not in cls.VALID_TEAMS:
                return False, f"Invalid team code: {team_str}"
            
            return True, team_str
            
        except Exception as e:
            logger.error(f"Error validating team code: {e}")
            return False, "Validation error"
    
    @classmethod
    def validate_position(cls, position: Any) -> Tuple[bool, str]:
        """Validate player position"""
        try:
            if not position:
                return False, "Position cannot be empty"
            
            pos_str = str(position).strip().upper()
            
            if pos_str not in cls.VALID_POSITIONS:
                return False, f"Invalid position: {pos_str}"
            
            return True, pos_str
            
        except Exception as e:
            logger.error(f"Error validating position: {e}")
            return False, "Validation error"
    
    @classmethod
    def validate_numeric(cls, value: Any, field_name: str = None, allow_negative: bool = True) -> Tuple[bool, Union[float, str]]:
        """
        Validate numeric value with optional field-specific limits
        
        Args:
            value: Value to validate
            field_name: Optional field name for applying specific limits
            allow_negative: Whether negative values are allowed
            
        Returns:
            Tuple[bool, Union[float, str]]: (is_valid, numeric_value_or_error)
        """
        try:
            if value is None:
                return False, "Numeric value cannot be None"
            
            # Convert to float
            try:
                if isinstance(value, str):
                    # Remove commas and strip whitespace
                    clean_value = value.replace(',', '').strip()
                    numeric_value = float(clean_value)
                else:
                    numeric_value = float(value)
            except (ValueError, TypeError):
                return False, f"Cannot convert to numeric: {value}"
            
            # Check for infinity or NaN
            if not (numeric_value == numeric_value):  # NaN check
                return False, "Value is NaN"
            
            if abs(numeric_value) == float('inf'):
                return False, "Value is infinite"
            
            # Check negative values
            if not allow_negative and numeric_value < 0:
                return False, "Negative values not allowed"
            
            # Apply field-specific limits
            if field_name and field_name in cls.LIMITS:
                min_val, max_val = cls.LIMITS[field_name]
                if numeric_value < min_val or numeric_value > max_val:
                    return False, f"Value {numeric_value} outside valid range [{min_val}, {max_val}]"
            
            return True, numeric_value
            
        except Exception as e:
            logger.error(f"Error validating numeric value: {e}")
            return False, "Validation error"
    
    @classmethod
    def validate_date_range(cls, season: Any, week: Any) -> Tuple[bool, Union[Tuple[int, int], str]]:
        """Validate season and week combination"""
        try:
            # Validate season
            season_valid, season_result = cls.validate_numeric(season, 'season', allow_negative=False)
            if not season_valid:
                return False, f"Invalid season: {season_result}"
            
            # Validate week
            week_valid, week_result = cls.validate_numeric(week, 'week', allow_negative=False)
            if not week_valid:
                return False, f"Invalid week: {week_result}"
            
            season_int = int(season_result)
            week_int = int(week_result)
            
            # Additional business logic checks
            if season_int < 2020:
                return False, "Season too old for predictions"
            
            if season_int > datetime.now().year + 1:
                return False, "Season too far in future"
            
            return True, (season_int, week_int)
            
        except Exception as e:
            logger.error(f"Error validating date range: {e}")
            return False, "Validation error"
    
    @classmethod
    def validate_url(cls, url: Any) -> Tuple[bool, str]:
        """Validate URL format"""
        try:
            if not url:
                return False, "URL cannot be empty"
            
            url_str = str(url).strip()
            
            if not cls.PATTERNS['url'].match(url_str):
                return False, "Invalid URL format"
            
            # Additional security checks
            if any(dangerous in url_str.lower() for dangerous in ['javascript:', 'data:', 'vbscript:']):
                return False, "Potentially dangerous URL scheme"
            
            return True, url_str
            
        except Exception as e:
            logger.error(f"Error validating URL: {e}")
            return False, "Validation error"
    
    @classmethod
    def validate_stats_data(cls, stats: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Validate player statistics data
        
        Args:
            stats: Dictionary of statistical data
            
        Returns:
            Tuple[bool, Union[Dict[str, Any], str]]: (is_valid, validated_stats_or_error)
        """
        try:
            if not isinstance(stats, dict):
                return False, "Stats must be a dictionary"
            
            validated_stats = {}
            
            # Define expected stats with validation rules
            stat_validations = {
                'passing_yards': ('passing_yards', False),
                'passing_tds': ('touchdowns', False),
                'interceptions': ('interceptions', False),
                'rushing_yards': ('rushing_yards', False),
                'rushing_tds': ('touchdowns', False),
                'receiving_yards': ('receiving_yards', False),
                'receiving_tds': ('touchdowns', False),
                'receptions': ('receptions', False),
                'fantasy_points': ('fantasy_points', False),
            }
            
            for stat_name, (limit_key, allow_negative) in stat_validations.items():
                if stat_name in stats:
                    is_valid, result = cls.validate_numeric(
                        stats[stat_name], 
                        limit_key, 
                        allow_negative
                    )
                    
                    if not is_valid:
                        return False, f"Invalid {stat_name}: {result}"
                    
                    validated_stats[stat_name] = result
                else:
                    validated_stats[stat_name] = 0  # Default to 0 for missing stats
            
            return True, validated_stats
            
        except Exception as e:
            logger.error(f"Error validating stats data: {e}")
            return False, "Validation error"
    
    @classmethod
    def sanitize_string(cls, text: Any, max_length: int = 500, allow_html: bool = False) -> str:
        """
        Sanitize string input
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags
            
        Returns:
            str: Sanitized string
        """
        try:
            if not text:
                return ""
            
            text_str = str(text)
            
            # Remove null bytes
            text_str = text_str.replace('\x00', '')
            
            # Remove or escape dangerous characters
            if not allow_html:
                # Remove HTML tags and potentially dangerous characters
                text_str = re.sub(r'<[^>]*>', '', text_str)
                text_str = re.sub(r'[<>"\';\\]', '', text_str)
            
            # Control character removal (except tabs, newlines, carriage returns)
            text_str = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text_str)
            
            # Normalize whitespace
            text_str = re.sub(r'\s+', ' ', text_str)
            
            # Trim and limit length
            text_str = text_str.strip()[:max_length]
            
            return text_str
            
        except Exception as e:
            logger.error(f"Error sanitizing string: {e}")
            return ""
    
    @classmethod
    def sanitize_player_name(cls, name: str) -> str:
        """Sanitize player name specifically"""
        if not name:
            return ""
        
        # Allow only letters, apostrophes, periods, hyphens, and spaces
        sanitized = re.sub(r"[^A-Za-z\'\.\-\s]", "", str(name))
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Capitalize properly
        sanitized = ' '.join(word.capitalize() for word in sanitized.split())
        
        return sanitized.strip()[:50]
    
    @classmethod
    def sanitize_team_code(cls, team: str) -> str:
        """Sanitize team code"""
        if not team:
            return ""
        
        # Convert to uppercase and remove non-letters
        sanitized = re.sub(r"[^A-Z]", "", str(team).upper())
        return sanitized[:4]
    
    @classmethod
    def validate_batch_data(cls, data_list: List[Dict[str, Any]], 
                           required_fields: List[str],
                           max_batch_size: int = 1000) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        Validate batch data for bulk operations
        
        Args:
            data_list: List of data dictionaries to validate
            required_fields: List of required field names
            max_batch_size: Maximum allowed batch size
            
        Returns:
            Tuple[bool, Union[List[Dict[str, Any]], str]]: (is_valid, validated_data_or_error)
        """
        try:
            if not isinstance(data_list, list):
                return False, "Data must be a list"
            
            if len(data_list) > max_batch_size:
                return False, f"Batch size {len(data_list)} exceeds maximum {max_batch_size}"
            
            if not data_list:
                return False, "Batch cannot be empty"
            
            validated_batch = []
            
            for i, item in enumerate(data_list):
                if not isinstance(item, dict):
                    return False, f"Item {i} is not a dictionary"
                
                # Check required fields
                for field in required_fields:
                    if field not in item:
                        return False, f"Item {i} missing required field: {field}"
                
                # Sanitize string fields
                validated_item = {}
                for key, value in item.items():
                    if isinstance(value, str):
                        validated_item[key] = cls.sanitize_string(value)
                    else:
                        validated_item[key] = value
                
                validated_batch.append(validated_item)
            
            return True, validated_batch
            
        except Exception as e:
            logger.error(f"Error validating batch data: {e}")
            return False, "Validation error"


class SecurityValidator:
    """Additional security-focused validation"""
    
    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"'.*OR.*'.*=.*'",
        r"';.*DROP.*TABLE.*",
        r"';.*DELETE.*FROM.*",
        r"';.*INSERT.*INTO.*",
        r"';.*UPDATE.*SET.*",
        r"UNION.*SELECT",
        r"<script.*>",
        r"javascript:",
        r"onload=",
        r"onerror=",
    ]
    
    @classmethod
    def check_sql_injection(cls, text: str) -> bool:
        """
        Check for SQL injection patterns
        
        Returns:
            bool: True if suspicious patterns found
        """
        if not text:
            return False
        
        text_upper = text.upper()
        
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                return True
        
        return False
    
    @classmethod
    def validate_safe_input(cls, text: str, field_name: str = "") -> Tuple[bool, str]:
        """
        Validate input for security issues
        
        Returns:
            Tuple[bool, str]: (is_safe, sanitized_text_or_error)
        """
        try:
            if cls.check_sql_injection(text):
                return False, f"Security violation in {field_name}"
            
            # Additional XSS checks
            if any(pattern in text.lower() for pattern in ['<script', 'javascript:', 'onload=', 'onerror=']):
                return False, f"XSS attempt detected in {field_name}"
            
            return True, InputValidator.sanitize_string(text)
            
        except Exception as e:
            logger.error(f"Error in security validation: {e}")
            return False, "Security validation error"


# Decorator for input validation
def validate_inputs(**validations):
    """
    Decorator for automatic input validation
    
    Usage:
        @validate_inputs(player_name='player_name', team='team_code')
        def some_function(player_name, team):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get function signature to map args to kwargs
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each specified parameter
            for param_name, validation_type in validations.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    
                    if validation_type == 'player_name':
                        is_valid, result = InputValidator.validate_player_name(value)
                    elif validation_type == 'team_code':
                        is_valid, result = InputValidator.validate_team_code(value)
                    elif validation_type == 'position':
                        is_valid, result = InputValidator.validate_position(value)
                    elif validation_type == 'numeric':
                        is_valid, result = InputValidator.validate_numeric(value)
                    elif validation_type == 'url':
                        is_valid, result = InputValidator.validate_url(value)
                    else:
                        continue  # Skip unknown validation types
                    
                    if not is_valid:
                        raise ValidationError(f"Invalid {param_name}: {result}")
                    
                    # Update with validated/sanitized value
                    bound_args.arguments[param_name] = result
            
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator


__all__ = ['InputValidator', 'SecurityValidator', 'ValidationError', 'validate_inputs']