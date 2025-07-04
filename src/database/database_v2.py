"""
Improved database layer with proper session management and connection pooling
"""
import logging
import contextlib
from typing import Optional, Generator
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from .models import Base
from config.config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Enhanced database manager with proper session lifecycle management,
    connection pooling, and error handling
    """
    
    def __init__(self):
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._initialized = False
        
    def initialize(self):
        """Initialize database connection with proper configuration"""
        if self._initialized:
            return
            
        try:
            # Enhanced engine configuration with connection pooling
            if Config.DATABASE_URL.startswith('sqlite'):
                # SQLite-specific configuration
                engine_config = {
                    'poolclass': pool.StaticPool,
                    'connect_args': {
                        'check_same_thread': False,
                        'timeout': 20
                    },
                    'echo': Config.DEBUG_MODE,  # Log SQL queries in debug mode
                }
            else:
                # Configuration for other databases (PostgreSQL, MySQL, etc.)
                engine_config = {
                    'pool_pre_ping': True,  # Verify connections before use
                    'pool_recycle': 300,    # Recycle connections every 5 minutes
                    'pool_size': 10,        # Connection pool size
                    'max_overflow': 20,     # Max overflow connections
                    'echo': Config.DEBUG_MODE,  # Log SQL queries in debug mode
                }
            
            self._engine = create_engine(Config.DATABASE_URL, **engine_config)
            
            # Add connection event listeners for better error handling
            self._setup_event_listeners()
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False  # Keep objects accessible after commit
            )
            
            self._initialized = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring and debugging"""
        
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance"""
            if Config.DATABASE_URL.startswith('sqlite'):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.close()
        
        @event.listens_for(self._engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout events"""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self._engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin events"""
            logger.debug("Connection returned to pool")
    
    @contextlib.contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with proper cleanup
        
        Usage:
            with db.get_session() as session:
                # Use session here
                session.add(obj)
                session.commit()
        """
        if not self._initialized:
            self.initialize()
            
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @contextlib.contextmanager
    def get_readonly_session(self) -> Generator[Session, None, None]:
        """
        Context manager for read-only database sessions
        Automatically rolls back any changes
        """
        if not self._initialized:
            self.initialize()
            
        session = self._session_factory()
        try:
            yield session
        except Exception as e:
            logger.error(f"Database readonly session error: {e}")
            raise
        finally:
            session.rollback()  # Always rollback for readonly
            session.close()
    
    def create_tables(self):
        """Create all database tables"""
        if not self._initialized:
            self.initialize()
            
        try:
            Base.metadata.create_all(bind=self._engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution)"""
        if not self._initialized:
            self.initialize()
            
        try:
            Base.metadata.drop_all(bind=self._engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def get_engine(self) -> Engine:
        """Get the SQLAlchemy engine"""
        if not self._initialized:
            self.initialize()
        return self._engine
    
    def check_connection(self) -> bool:
        """Check if database connection is healthy"""
        try:
            if not self._initialized:
                self.initialize()
                
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """Get database connection information"""
        if not self._initialized:
            return {"status": "not_initialized"}
            
        try:
            pool = self._engine.pool
            return {
                "status": "connected",
                "url": str(self._engine.url).replace(self._engine.url.password or "", "***"),
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close database connections and cleanup"""
        try:
            if self._engine:
                self._engine.dispose()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        finally:
            self._initialized = False


class DatabaseSession:
    """
    Utility class for database operations with automatic session management
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def execute_query(self, query_func, *args, **kwargs):
        """
        Execute a query function with automatic session management
        
        Args:
            query_func: Function that takes session as first argument
            *args: Additional arguments for query_func
            **kwargs: Keyword arguments for query_func
        """
        with self.db_manager.get_session() as session:
            return query_func(session, *args, **kwargs)
    
    def execute_readonly_query(self, query_func, *args, **kwargs):
        """
        Execute a read-only query function
        """
        with self.db_manager.get_readonly_session() as session:
            return query_func(session, *args, **kwargs)
    
    def bulk_insert(self, model_class, data_list: list, batch_size: int = 1000):
        """
        Efficiently insert large amounts of data in batches
        
        Args:
            model_class: SQLAlchemy model class
            data_list: List of dictionaries containing data
            batch_size: Number of records per batch
        """
        total_inserted = 0
        
        try:
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                
                with self.db_manager.get_session() as session:
                    objects = [model_class(**data) for data in batch]
                    session.bulk_save_objects(objects)
                    total_inserted += len(batch)
                    
                logger.debug(f"Inserted batch {i//batch_size + 1}, total: {total_inserted}")
                
            logger.info(f"Bulk insert completed: {total_inserted} records")
            return total_inserted
            
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise
    
    def safe_get_or_create(self, model_class, defaults=None, **kwargs):
        """
        Safely get or create a model instance
        
        Args:
            model_class: SQLAlchemy model class
            defaults: Default values for creation
            **kwargs: Filter criteria
            
        Returns:
            tuple: (instance, created_flag)
        """
        with self.db_manager.get_session() as session:
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


# Singleton database manager instance
db_manager = DatabaseManager()

# Utility session handler
db_session = DatabaseSession(db_manager)

# Legacy compatibility - provides same interface as old db object
class LegacyDatabaseInterface:
    """Provides backward compatibility with existing code"""
    
    def __init__(self):
        self._db_manager = db_manager
    
    def get_session(self):
        """Legacy method - returns session (caller must close)"""
        logger.warning("Using legacy get_session() - consider upgrading to context manager")
        if not self._db_manager._initialized:
            self._db_manager.initialize()
        return self._db_manager._session_factory()
    
    def close_session(self, session):
        """Legacy method - closes session"""
        session.close()
    
    def create_tables(self):
        """Legacy method - creates tables"""
        self._db_manager.create_tables()

# Legacy compatibility instance
db = LegacyDatabaseInterface()

# Export main interfaces
__all__ = ['db_manager', 'db_session', 'db', 'DatabaseSession']