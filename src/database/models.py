from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import our type aliases
from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode, Position, FantasyPoints, PlayerName

Base = declarative_base()

class Player(Base):
    __tablename__ = 'players'
    
    id: PlayerId = Column(Integer, primary_key=True)
    name: PlayerName = Column(String(100), nullable=False)
    position: Position = Column(String(10), nullable=False)
    team: TeamCode = Column(String(50), nullable=False)
    age: Optional[int] = Column(Integer)
    height: Optional[str] = Column(String(10))
    weight: Optional[int] = Column(Integer)
    experience_years: Optional[int] = Column(Integer)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name='{self.name}', position='{self.position}', team='{self.team}')>"

class PlayerStats(Base):
    __tablename__ = 'player_stats'
    
    id: int = Column(Integer, primary_key=True)
    player_id: PlayerId = Column(Integer, nullable=False)
    season: Season = Column(Integer, nullable=False)
    week: Week = Column(Integer, nullable=False)
    
    # Passing stats
    passing_attempts: int = Column(Integer, default=0)
    passing_completions: int = Column(Integer, default=0)
    passing_yards: int = Column(Integer, default=0)
    passing_tds: int = Column(Integer, default=0)
    interceptions: int = Column(Integer, default=0)
    
    # Rushing stats
    rushing_attempts: int = Column(Integer, default=0)
    rushing_yards: int = Column(Integer, default=0)
    rushing_tds: int = Column(Integer, default=0)
    
    # Receiving stats
    targets: int = Column(Integer, default=0)
    receptions: int = Column(Integer, default=0)
    receiving_yards: int = Column(Integer, default=0)
    receiving_tds: int = Column(Integer, default=0)
    
    # Fantasy points
    fantasy_points: FantasyPoints = Column(Float, default=0.0)
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<PlayerStats(player_id={self.player_id}, season={self.season}, week={self.week}, fantasy_points={self.fantasy_points})>"

class NewsArticle(Base):
    __tablename__ = 'news_articles'
    
    id: int = Column(Integer, primary_key=True)
    title: str = Column(String(500), nullable=False)
    content: Optional[str] = Column(Text)
    source: str = Column(String(100), nullable=False)
    url: Optional[str] = Column(String(1000))
    published_date: Optional[datetime] = Column(DateTime)
    sentiment_score: Optional[float] = Column(Float)  # -1 to 1, negative to positive
    players_mentioned: Optional[str] = Column(Text)  # JSON string of player names
    teams_mentioned: Optional[str] = Column(Text)   # JSON string of team names
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<NewsArticle(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"

class Prediction(Base):
    __tablename__ = 'predictions'
    
    id: int = Column(Integer, primary_key=True)
    player_id: PlayerId = Column(Integer, nullable=False)
    season: Season = Column(Integer, nullable=False)
    week: Week = Column(Integer, nullable=False)
    
    predicted_passing_yards: Optional[float] = Column(Float)
    predicted_passing_tds: Optional[float] = Column(Float)
    predicted_rushing_yards: Optional[float] = Column(Float)
    predicted_rushing_tds: Optional[float] = Column(Float)
    predicted_receiving_yards: Optional[float] = Column(Float)
    predicted_receiving_tds: Optional[float] = Column(Float)
    predicted_fantasy_points: Optional[FantasyPoints] = Column(Float)
    
    confidence_score: Optional[float] = Column(Float)  # 0 to 1
    model_version: Optional[str] = Column(String(50))
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Prediction(player_id={self.player_id}, season={self.season}, week={self.week}, fantasy_points={self.predicted_fantasy_points})>"
    
class InjuryHistory(Base):
    __tablename__ = 'injury_history'
    
    id: int = Column(Integer, primary_key=True)
    player_id: PlayerId = Column(Integer, nullable=False)
    season: Season = Column(Integer, nullable=False)
    week: Week = Column(Integer, nullable=False)
    injury_type: Optional[str] = Column(String(100))  # e.g., "hamstring", "knee", "ankle"
    body_part: Optional[str] = Column(String(50))     # e.g., "leg", "arm", "back"
    severity: Optional[str] = Column(String(20))      # e.g., "minor", "moderate", "major"
    games_missed: int = Column(Integer, default=0)
    is_active: bool = Column(Boolean, default=True)  # Currently injured
    return_date: Optional[datetime] = Column(DateTime)
    description: Optional[str] = Column(Text)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<InjuryHistory(player_id={self.player_id}, injury_type='{self.injury_type}', severity='{self.severity}')>"

class WorkloadTracking(Base):
    __tablename__ = 'workload_tracking'
    
    id: int = Column(Integer, primary_key=True)
    player_id: PlayerId = Column(Integer, nullable=False)
    season: Season = Column(Integer, nullable=False)
    week: Week = Column(Integer, nullable=False)
    
    # Snap counts and usage
    offensive_snaps: int = Column(Integer, default=0)
    total_snaps: int = Column(Integer, default=0)
    snap_percentage: float = Column(Float, default=0.0)
    
    # Touch/target data for skill positions
    total_touches: int = Column(Integer, default=0)  # rushes + receptions
    targets: int = Column(Integer, default=0)
    red_zone_touches: int = Column(Integer, default=0)
    
    # Workload metrics
    yards_after_contact: float = Column(Float, default=0.0)
    air_yards_share: float = Column(Float, default=0.0)  # For receivers
    
    # Risk indicators
    consecutive_games_high_usage: int = Column(Integer, default=0)  # Games with >80% snaps
    touches_vs_season_avg: float = Column(Float, default=0.0)  # Percentage above/below average
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<WorkloadTracking(player_id={self.player_id}, season={self.season}, week={self.week}, snap_percentage={self.snap_percentage})>"

class TeamNews(Base):
    __tablename__ = 'team_news'
    
    id: int = Column(Integer, primary_key=True)
    team: TeamCode = Column(String(50), nullable=False)
    title: str = Column(String(500), nullable=False)
    content: Optional[str] = Column(Text)
    source: str = Column(String(100), nullable=False)
    url: Optional[str] = Column(String(1000))
    published_date: Optional[datetime] = Column(DateTime)
    
    # Team news categories
    category: Optional[str] = Column(String(50))  # "coaching", "roster", "strategy", "injury_report"
    impact_level: Optional[str] = Column(String(20))  # "high", "medium", "low"
    
    # Affected players/positions
    affected_players: Optional[str] = Column(Text)  # JSON string of player names
    affected_positions: Optional[str] = Column(Text)  # JSON string of positions
    
    sentiment_score: Optional[float] = Column(Float)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<TeamNews(team='{self.team}', title='{self.title[:50]}...', impact_level='{self.impact_level}')>"

class WeatherData(Base):
    __tablename__ = 'weather_data'
    
    id: int = Column(Integer, primary_key=True)
    game_date: datetime = Column(DateTime, nullable=False)
    venue: str = Column(String(100), nullable=False)
    temperature: Optional[float] = Column(Float)  # Fahrenheit
    wind_speed: Optional[float] = Column(Float)   # mph
    wind_direction: Optional[str] = Column(String(10))
    precipitation: Optional[float] = Column(Float)  # inches
    humidity: Optional[float] = Column(Float)     # percentage
    weather_condition: Optional[str] = Column(String(50))  # "clear", "rain", "snow", etc.
    is_dome: bool = Column(Boolean, default=False)
    
    # Impact factors
    kicking_difficulty: Optional[float] = Column(Float)  # 0-1 scale
    passing_difficulty: Optional[float] = Column(Float)  # 0-1 scale
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<WeatherData(venue='{self.venue}', date='{self.game_date}', condition='{self.weather_condition}')>"

class ActualResults(Base):
    __tablename__ = 'actual_results'
    
    id: int = Column(Integer, primary_key=True)
    player_id: PlayerId = Column(Integer, nullable=False)
    season: Season = Column(Integer, nullable=False)
    week: Week = Column(Integer, nullable=False)
    
    # Actual game statistics
    actual_passing_attempts: int = Column(Integer, default=0)
    actual_passing_completions: int = Column(Integer, default=0)
    actual_passing_yards: int = Column(Integer, default=0)
    actual_passing_tds: int = Column(Integer, default=0)
    actual_interceptions: int = Column(Integer, default=0)
    
    actual_rushing_attempts: int = Column(Integer, default=0)
    actual_rushing_yards: int = Column(Integer, default=0)
    actual_rushing_tds: int = Column(Integer, default=0)
    
    actual_targets: int = Column(Integer, default=0)
    actual_receptions: int = Column(Integer, default=0)
    actual_receiving_yards: int = Column(Integer, default=0)
    actual_receiving_tds: int = Column(Integer, default=0)
    
    # Calculated actual fantasy points
    actual_fantasy_points: FantasyPoints = Column(Float, default=0.0)
    
    # Game context
    game_date: Optional[datetime] = Column(DateTime)
    opponent_team: Optional[TeamCode] = Column(String(10))
    is_home_game: bool = Column(Boolean, default=True)
    game_result: Optional[str] = Column(String(10))  # "W", "L", "T"
    
    # Data source tracking
    data_source: str = Column(String(100), default='ESPN')
    verified: bool = Column(Boolean, default=False)  # Manual verification flag
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ActualResults(player_id={self.player_id}, season={self.season}, week={self.week}, fantasy_points={self.actual_fantasy_points})>"

class PredictionAccuracy(Base):
    __tablename__ = 'prediction_accuracy'
    
    id: int = Column(Integer, primary_key=True)
    prediction_id: int = Column(Integer, nullable=False)  # Links to Prediction table
    player_id: PlayerId = Column(Integer, nullable=False)
    season: Season = Column(Integer, nullable=False)
    week: Week = Column(Integer, nullable=False)
    
    # Predicted vs Actual differences
    fantasy_points_error: Optional[float] = Column(Float)  # predicted - actual
    fantasy_points_abs_error: Optional[float] = Column(Float)  # abs(predicted - actual)
    fantasy_points_percent_error: Optional[float] = Column(Float)  # (predicted - actual) / actual
    
    passing_yards_error: Optional[float] = Column(Float)
    rushing_yards_error: Optional[float] = Column(Float)
    receiving_yards_error: Optional[float] = Column(Float)
    
    # Accuracy metrics
    was_within_5_points: bool = Column(Boolean, default=False)
    was_within_10_points: bool = Column(Boolean, default=False)
    was_within_20_percent: bool = Column(Boolean, default=False)
    
    # Model performance
    model_version: Optional[str] = Column(String(50))
    confidence_score: Optional[float] = Column(Float)  # Original prediction confidence
    accuracy_grade: Optional[str] = Column(String(10))  # A, B, C, D, F
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<PredictionAccuracy(player_id={self.player_id}, season={self.season}, week={self.week}, grade='{self.accuracy_grade}')>"

class ModelMetadata(Base):
    __tablename__ = 'model_metadata'
    
    id: int = Column(Integer, primary_key=True)
    model_name: str = Column(String(100), nullable=False)
    version: str = Column(String(50), nullable=False)
    training_date: datetime = Column(DateTime, nullable=False)
    accuracy_score: Optional[float] = Column(Float)
    feature_importance: Optional[str] = Column(Text)  # JSON string
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ModelMetadata(name='{self.model_name}', version='{self.version}', active={self.is_active})>"

class TransactionLog(Base):
    __tablename__ = 'transaction_log'
    
    id: int = Column(Integer, primary_key=True)
    player_id: PlayerId = Column(Integer, nullable=False)  # Links to Player table
    transaction_type: str = Column(String(50), nullable=False)  # 'trade', 'signing', 'release', 'waiver'
    old_team: Optional[TeamCode] = Column(String(10))  # Team before transaction
    new_team: Optional[TeamCode] = Column(String(10))  # Team after transaction
    source: str = Column(String(100), nullable=False)  # Data source (nfl_com, espn, etc.)
    raw_text: Optional[str] = Column(Text)  # Original transaction text
    timestamp: datetime = Column(DateTime, nullable=False)
    impact_level: str = Column(String(20), default='medium')  # 'high', 'medium', 'low'
    processed: bool = Column(Boolean, default=False)  # Whether prediction updates were made
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<TransactionLog(player_id={self.player_id}, type='{self.transaction_type}', old_team='{self.old_team}', new_team='{self.new_team}')>"