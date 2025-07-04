"""
Unified database session handling patterns
Consolidates duplicate session management across modules
"""
import logging
from contextlib import contextmanager
from typing import Callable, Any, Optional, List, Dict
from src.database.database_v2 import db_session
from src.utils.error_handling import handle_errors, DatabaseError, ErrorCode

logger = logging.getLogger(__name__)

class DatabaseSessionManager:
    """Centralized database session management with error handling"""
    
    @staticmethod
    @handle_errors(suppress=False)
    def execute_with_session(query_func: Callable, *args, **kwargs) -> Any:
        """Execute a function with proper session management"""
        return db_session.execute_query(query_func, *args, **kwargs)
    
    @staticmethod
    @handle_errors(suppress=False)
    def execute_readonly(query_func: Callable, *args, **kwargs) -> Any:
        """Execute a read-only function with proper session management"""
        return db_session.execute_readonly_query(query_func, *args, **kwargs)
    
    @staticmethod
    @contextmanager
    def managed_session():
        """Context manager for manual session management"""
        with db_session.db_manager.get_session() as session:
            yield session
    
    @staticmethod
    def bulk_insert_with_validation(model_class, data_list: List[Dict], 
                                  validation_func: Optional[Callable] = None):
        """Bulk insert with optional validation"""
        try:
            # Validate data if function provided
            if validation_func:
                validated_data = []
                for item in data_list:
                    if validation_func(item):
                        validated_data.append(item)
                data_list = validated_data
            
            # Use bulk insert
            return db_session.bulk_insert(model_class, data_list)
            
        except Exception as e:
            raise DatabaseError(f"Bulk insert failed: {e}", ErrorCode.DB_TRANSACTION_ERROR)
    
    @staticmethod
    def safe_find_player(player_name: str, session_func: Optional[Callable] = None):
        """Safely find a player by name with proper validation"""
        from src.utils.input_validation import InputValidator
        from src.database.models import Player
        
        validator = InputValidator()
        
        # Validate player name
        is_valid, validated_name = validator.validate_player_name(player_name)
        if not is_valid:
            logger.warning(f"Invalid player name format: {player_name}")
            return None
        
        def find_player_query(session):
            return session.query(Player).filter(
                Player.name.ilike(f"%{validated_name}%")
            ).first()
        
        if session_func:
            return session_func(find_player_query)
        else:
            return DatabaseSessionManager.execute_readonly(find_player_query)
    
    @staticmethod
    def safe_find_team_players(team_code: str, position: Optional[str] = None):
        """Safely find players by team and optionally position"""
        from src.utils.input_validation import InputValidator
        from src.database.models import Player
        
        validator = InputValidator()
        
        # Validate team code
        is_valid, validated_team = validator.validate_team_code(team_code)
        if not is_valid:
            logger.warning(f"Invalid team code: {team_code}")
            return []
        
        def find_team_players_query(session):
            query = session.query(Player).filter(Player.team == validated_team)
            
            if position:
                is_pos_valid, validated_pos = validator.validate_position(position)
                if is_pos_valid:
                    query = query.filter(Player.position == validated_pos)
            
            return query.all()
        
        return DatabaseSessionManager.execute_readonly(find_team_players_query)
    
    @staticmethod
    def safe_get_or_create(model_class, defaults: Optional[Dict] = None, **kwargs):
        """Safely get or create a model instance"""
        def get_or_create_query(session):
            instance = session.query(model_class).filter_by(**kwargs).first()
            
            if instance:
                return instance, False
            else:
                params = dict(kwargs)
                if defaults:
                    params.update(defaults)
                
                instance = model_class(**params)
                session.add(instance)
                session.flush()  # Get ID without committing
                return instance, True
        
        return DatabaseSessionManager.execute_with_session(get_or_create_query)

# Global instance
db_manager = DatabaseSessionManager()

# Convenience functions for backward compatibility
def safe_query(query_func: Callable, *args, **kwargs) -> Any:
    """Safely execute a database query"""
    return db_manager.execute_with_session(query_func, *args, **kwargs)

def safe_readonly_query(query_func: Callable, *args, **kwargs) -> Any:
    """Safely execute a read-only database query"""
    return db_manager.execute_readonly(query_func, *args, **kwargs)

def find_player_by_name(player_name: str):
    """Find player by name with validation - convenience function"""
    return db_manager.safe_find_player(player_name)

def find_team_players(team_code: str, position: Optional[str] = None):
    """Find team players with validation - convenience function"""
    return db_manager.safe_find_team_players(team_code, position)

# Common query patterns
class CommonQueries:
    """Common database query patterns"""
    
    @staticmethod
    def get_player_stats(player_id: int, season: int, week: Optional[int] = None):
        """Get player statistics for a season/week"""
        from src.database.models import PlayerStats
        
        def stats_query(session):
            query = session.query(PlayerStats).filter(
                PlayerStats.player_id == player_id,
                PlayerStats.season == season
            )
            
            if week is not None:
                query = query.filter(PlayerStats.week == week)
            
            return query.all()
        
        return safe_readonly_query(stats_query)
    
    @staticmethod
    def get_recent_player_stats(player_id: int, limit: int = 5):
        """Get most recent player statistics"""
        from src.database.models import PlayerStats
        
        def recent_stats_query(session):
            return session.query(PlayerStats).filter(
                PlayerStats.player_id == player_id
            ).order_by(
                PlayerStats.season.desc(),
                PlayerStats.week.desc()
            ).limit(limit).all()
        
        return safe_readonly_query(recent_stats_query)
    
    @staticmethod
    def get_position_players(position: str, active_only: bool = True):
        """Get all players for a position"""
        from src.database.models import Player
        from src.utils.input_validation import InputValidator
        
        validator = InputValidator()
        is_valid, validated_pos = validator.validate_position(position)
        
        if not is_valid:
            return []
        
        def position_query(session):
            query = session.query(Player).filter(Player.position == validated_pos)
            # Could add active_only filter here if we had that field
            return query.all()
        
        return safe_readonly_query(position_query)

# Global queries instance
queries = CommonQueries()

__all__ = [
    'DatabaseSessionManager', 'db_manager', 'safe_query', 'safe_readonly_query',
    'find_player_by_name', 'find_team_players', 'CommonQueries', 'queries'
]