#!/usr/bin/env python3
"""
PostgreSQL Database Configuration for NFL Assistant
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

Base = declarative_base()

class PostgreSQLPlayer(Base):
    """PostgreSQL Player model"""
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    team = Column(String(10), nullable=False)
    position = Column(String(10), nullable=False)
    season = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PostgreSQLPrediction(Base):
    """PostgreSQL Prediction model"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String(100), nullable=False)
    team = Column(String(10), nullable=False)
    position = Column(String(10), nullable=False)
    week = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    predicted_points = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    scoring_format = Column(String(20), default='half_ppr')
    model_version = Column(String(50), default='v1.0')
    created_at = Column(DateTime, default=datetime.utcnow)

class PostgreSQLGameResult(Base):
    """PostgreSQL Game Results model"""
    __tablename__ = 'game_results'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String(100), nullable=False)
    team = Column(String(10), nullable=False)
    position = Column(String(10), nullable=False)
    week = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    actual_points = Column(Float, nullable=False)
    fantasy_points_ppr = Column(Float)
    fantasy_points_half_ppr = Column(Float)
    fantasy_points_standard = Column(Float)
    
    # Individual stats
    passing_yards = Column(Integer, default=0)
    passing_tds = Column(Integer, default=0)
    passing_attempts = Column(Integer, default=0)
    passing_completions = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    
    rushing_yards = Column(Integer, default=0)
    rushing_tds = Column(Integer, default=0)
    rushing_attempts = Column(Integer, default=0)
    
    receiving_yards = Column(Integer, default=0)
    receiving_tds = Column(Integer, default=0)
    receptions = Column(Integer, default=0)
    targets = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class PostgreSQLInjuryReport(Base):
    """PostgreSQL Injury Report model"""
    __tablename__ = 'injury_reports'
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String(100), nullable=False)
    team = Column(String(10), nullable=False)
    position = Column(String(10), nullable=False)
    week = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    injury_status = Column(String(20))  # healthy, questionable, doubtful, out, ir
    injury_description = Column(Text)
    date_reported = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))
    
class DatabaseManager:
    """PostgreSQL Database Manager"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.setup_database()
    
    def setup_database(self):
        """Setup PostgreSQL database connection"""
        try:
            # Database configuration from environment variables
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'nfl_assistant'),
                'username': os.getenv('POSTGRES_USER', 'hsuh'),
                'password': os.getenv('POSTGRES_PASSWORD', '')
            }
            
            # Create connection string with proper authentication
            if db_config['password']:
                connection_string = (
                    f"postgresql://{db_config['username']}:{db_config['password']}"
                    f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                )
            else:
                # Use peer authentication for local connections without password
                connection_string = (
                    f"postgresql://{db_config['username']}"
                    f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                )
            
            # Create engine
            self.engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False  # Set to True for SQL debugging
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("✅ PostgreSQL database connection established")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            # Fallback to SQLite for development
            self.setup_sqlite_fallback()
    
    def setup_sqlite_fallback(self):
        """Fallback to SQLite if PostgreSQL is not available"""
        try:
            sqlite_path = os.path.join(os.path.dirname(__file__), 'nfl_assistant_fallback.db')
            connection_string = f"sqlite:///{sqlite_path}"
            
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                echo=False
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.warning("⚠️  Using SQLite fallback database")
            
        except Exception as e:
            logger.error(f"❌ SQLite fallback failed: {e}")
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
    
    def get_session(self):
        """Get database session"""
        if self.SessionLocal:
            return self.SessionLocal()
        return None
    
    def test_connection(self):
        """Test database connection"""
        try:
            session = self.get_session()
            if session:
                # Simple test query
                session.execute(text("SELECT 1"))
                session.close()
                return True
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
        return False
    
    def store_prediction(self, player_data, prediction, week, season=2024):
        """Store prediction in database"""
        try:
            session = self.get_session()
            if not session:
                return False
            
            prediction_record = PostgreSQLPrediction(
                player_id=player_data.get('id', 0),
                player_name=player_data['name'],
                team=player_data['team'],
                position=player_data['position'],
                week=week,
                season=season,
                predicted_points=prediction['points'],
                confidence=prediction['confidence'],
                scoring_format=prediction.get('scoring', 'half_ppr')
            )
            
            session.add(prediction_record)
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store prediction: {e}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def get_recent_predictions(self, position=None, week=None, limit=100):
        """Get recent predictions from database"""
        try:
            session = self.get_session()
            if not session:
                return []
            
            query = session.query(PostgreSQLPrediction)
            
            if position:
                query = query.filter(PostgreSQLPrediction.position == position)
            
            if week:
                query = query.filter(PostgreSQLPrediction.week == week)
            
            predictions = query.order_by(
                PostgreSQLPrediction.created_at.desc()
            ).limit(limit).all()
            
            session.close()
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Failed to get predictions: {e}")
            if session:
                session.close()
            return []

# Global database instance
db_manager = DatabaseManager()

def initialize_database():
    """Initialize database and create tables"""
    db_manager.create_tables()
    return db_manager.test_connection()

def get_db_session():
    """Get database session for use in Flask app"""
    return db_manager.get_session()