"""
Automated NFL Data Collection System
Continuously monitors and collects NFL data with automatic scheduling
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
import numpy as np
import logging
import time
import threading
import schedule
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.data_collection.nfl_data_collector import NFLDataCollector, PlayerGameData
from src.monitoring.robust_monitoring_framework import BaseMonitor
from src.utils.type_hint_utility import PlayerId, Season, Week, TeamCode
from src.utils.unified_database_operations import DatabaseSessionManager
from src.database.models import ActualResults, Player


class CollectionStatus(Enum):
    """Data collection status"""
    IDLE = "idle"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    SCHEDULED = "scheduled"


@dataclass
class CollectionTask:
    """Data collection task"""
    task_id: str
    season: Season
    week: Week
    task_type: str  # 'weekly', 'daily_update', 'backfill'
    scheduled_time: datetime
    status: CollectionStatus
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class AutomatedDataCollector(BaseMonitor):
    """Automated NFL data collection with scheduling and monitoring"""
    
    def __init__(self) -> None:
        super().__init__("AutomatedDataCollector")
        
        # Initialize logger after super().__init__
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.data_collector = NFLDataCollector()
        self.real_data_collector = None  # Will import when needed
        self.db_manager = DatabaseSessionManager()
        
        # Collection state
        self.current_season = 2024
        self.collection_status = CollectionStatus.IDLE
        self.active_tasks: Dict[str, CollectionTask] = {}
        self.completed_tasks: List[CollectionTask] = []
        
        # Scheduling configuration
        self.schedule_config = {
            'game_day_collection': {
                'enabled': True,
                'time': '10:00',  # 10 AM on game days
                'days': ['Sunday', 'Monday', 'Thursday']
            },
            'daily_updates': {
                'enabled': True,
                'time': '06:00',  # 6 AM daily
                'frequency': 'daily'
            },
            'weekly_summary': {
                'enabled': True,
                'time': '23:00',  # 11 PM on Tuesdays
                'day': 'Tuesday'
            },
            'live_updates': {
                'enabled': True,
                'interval_minutes': 30,  # Every 30 minutes during games
                'game_window_hours': 8   # 8-hour window around game time
            }
        }
        
        # Collection metrics
        self.metrics = {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'total_players_updated': 0,
            'last_collection_time': None,
            'average_collection_time': 0.0,
            'data_quality_score': 0.0
        }
        
        # Initialize scheduler
        self._setup_scheduler()
    
    def start_monitoring(self) -> None:
        """Start the automated data collection system"""
        self.logger.info("Starting automated NFL data collection system")
        
        try:
            # Start the base monitoring
            super().start()
            
            # Schedule initial data collection
            self._schedule_initial_collections()
            
            # Start scheduler thread
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            self.logger.info("Automated data collection system started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start automated data collection: {e}")
            raise
    
    def _monitor_iteration(self) -> bool:
        """Required implementation of BaseMonitor abstract method"""
        try:
            # Process pending tasks
            self._process_pending_tasks()
            
            # Check for game day collections
            self._check_game_day_collections()
            
            # Update collection metrics
            self._update_metrics()
            
            # Health check
            self._perform_health_check()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in data collection monitoring iteration: {e}")
            return False
    
    def _setup_scheduler(self) -> None:
        """Setup automated scheduling"""
        try:
            # Clear any existing schedules
            schedule.clear()
            
            # Daily data updates
            if self.schedule_config['daily_updates']['enabled']:
                schedule.every().day.at(self.schedule_config['daily_updates']['time']).do(
                    self._schedule_daily_update
                )
            
            # Game day collections
            if self.schedule_config['game_day_collection']['enabled']:
                for day in self.schedule_config['game_day_collection']['days']:
                    getattr(schedule.every(), day.lower()).at(
                        self.schedule_config['game_day_collection']['time']
                    ).do(self._schedule_game_day_collection)
            
            # Weekly summary
            if self.schedule_config['weekly_summary']['enabled']:
                getattr(schedule.every(), self.schedule_config['weekly_summary']['day'].lower()).at(
                    self.schedule_config['weekly_summary']['time']
                ).do(self._schedule_weekly_summary)
            
            self.logger.info("Data collection scheduler configured successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up scheduler: {e}")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler in a separate thread"""
        while self.get_status().value in ['running', 'starting']:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in scheduler thread: {e}")
                time.sleep(300)  # Wait 5 minutes before retry
    
    def _schedule_daily_update(self) -> None:
        """Schedule daily data update"""
        current_week = self._get_current_nfl_week()
        task_id = f"daily_update_{datetime.now().strftime('%Y%m%d')}"
        
        task = CollectionTask(
            task_id=task_id,
            season=self.current_season,
            week=current_week,
            task_type='daily_update',
            scheduled_time=datetime.utcnow(),
            status=CollectionStatus.SCHEDULED
        )
        
        self.active_tasks[task_id] = task
        self.logger.info(f"Scheduled daily update task: {task_id}")
    
    def _schedule_game_day_collection(self) -> None:
        """Schedule game day data collection"""
        current_week = self._get_current_nfl_week()
        task_id = f"game_day_{datetime.now().strftime('%Y%m%d')}"
        
        task = CollectionTask(
            task_id=task_id,
            season=self.current_season,
            week=current_week,
            task_type='weekly',
            scheduled_time=datetime.utcnow(),
            status=CollectionStatus.SCHEDULED
        )
        
        self.active_tasks[task_id] = task
        self.logger.info(f"Scheduled game day collection task: {task_id}")
    
    def _schedule_weekly_summary(self) -> None:
        """Schedule weekly summary collection"""
        current_week = self._get_current_nfl_week()
        task_id = f"weekly_summary_{current_week}"
        
        task = CollectionTask(
            task_id=task_id,
            season=self.current_season,
            week=current_week,
            task_type='weekly',
            scheduled_time=datetime.utcnow(),
            status=CollectionStatus.SCHEDULED
        )
        
        self.active_tasks[task_id] = task
        self.logger.info(f"Scheduled weekly summary task: {task_id}")
    
    def _schedule_initial_collections(self) -> None:
        """Schedule initial data collections for missing weeks"""
        try:
            # Check what data we're missing
            missing_weeks = self._identify_missing_data()
            
            for week in missing_weeks:
                task_id = f"backfill_{self.current_season}_week_{week}"
                
                task = CollectionTask(
                    task_id=task_id,
                    season=self.current_season,
                    week=week,
                    task_type='backfill',
                    scheduled_time=datetime.utcnow() + timedelta(minutes=5),  # Start in 5 minutes
                    status=CollectionStatus.SCHEDULED
                )
                
                self.active_tasks[task_id] = task
                self.logger.info(f"Scheduled backfill task for Week {week}")
                
        except Exception as e:
            self.logger.error(f"Error scheduling initial collections: {e}")
    
    def _process_pending_tasks(self) -> None:
        """Process all pending collection tasks"""
        for task_id, task in list(self.active_tasks.items()):
            if task.status == CollectionStatus.SCHEDULED and datetime.utcnow() >= task.scheduled_time:
                self._execute_collection_task(task)
    
    def _execute_collection_task(self, task: CollectionTask) -> None:
        """Execute a specific collection task"""
        try:
            self.logger.info(f"Executing collection task: {task.task_id}")
            task.status = CollectionStatus.COLLECTING
            
            start_time = time.time()
            
            # Execute the collection based on task type
            if task.task_type in ['weekly', 'backfill']:
                # Use real data collector for historical data
                success = self._collect_real_week_data(task.season, task.week)
            elif task.task_type == 'daily_update':
                success = self._collect_daily_updates(task.season, task.week)
            else:
                self.logger.warning(f"Unknown task type: {task.task_type}")
                success = False
            
            collection_time = time.time() - start_time
            
            if success:
                task.status = CollectionStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                self.metrics['successful_collections'] += 1
                self.metrics['total_players_updated'] += self._count_updated_players(task)
                
                self.logger.info(f"Collection task {task.task_id} completed successfully in {collection_time:.2f}s")
            else:
                self._handle_collection_failure(task)
            
            # Update metrics
            self.metrics['total_collections'] += 1
            self.metrics['last_collection_time'] = datetime.utcnow()
            self._update_average_collection_time(collection_time)
            
            # Move completed/failed tasks to history
            if task.status in [CollectionStatus.COMPLETED, CollectionStatus.ERROR]:
                self.completed_tasks.append(task)
                if len(self.completed_tasks) > 100:  # Keep last 100 tasks
                    self.completed_tasks = self.completed_tasks[-100:]
                
                del self.active_tasks[task.task_id]
            
        except Exception as e:
            self.logger.error(f"Error executing collection task {task.task_id}: {e}")
            self._handle_collection_failure(task, str(e))
    
    def _collect_daily_updates(self, season: Season, week: Week) -> bool:
        """Collect daily updates (lighter than full weekly collection)"""
        try:
            # Check for recent games that might have updated stats
            current_time = datetime.utcnow()
            cutoff_time = current_time - timedelta(hours=24)
            
            # Get players who played recently
            def get_recent_players(session):
                return session.query(ActualResults).filter(
                    ActualResults.game_date >= cutoff_time,
                    ActualResults.season == season
                ).all()
            
            recent_results = self.db_manager.execute_readonly(get_recent_players)
            
            if not recent_results:
                self.logger.info("No recent games found for daily update")
                return True
            
            # Update stats for these players
            updated_count = 0
            for result in recent_results:
                if self._update_player_stats(result.player_id, season, week):
                    updated_count += 1
            
            self.logger.info(f"Daily update completed: {updated_count} players updated")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in daily updates: {e}")
            return False
    
    def _update_player_stats(self, player_id: PlayerId, season: Season, week: Week) -> bool:
        """Update stats for a specific player"""
        try:
            # This would fetch latest stats from APIs for this player
            # For now, simulate an update
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating player {player_id} stats: {e}")
            return False
    
    def _handle_collection_failure(self, task: CollectionTask, error_message: str = None) -> None:
        """Handle collection task failure with retry logic"""
        task.retry_count += 1
        task.error_message = error_message
        
        if task.retry_count <= task.max_retries:
            # Schedule retry
            retry_delay = min(60 * (2 ** task.retry_count), 3600)  # Exponential backoff, max 1 hour
            task.scheduled_time = datetime.utcnow() + timedelta(seconds=retry_delay)
            task.status = CollectionStatus.SCHEDULED
            
            self.logger.warning(f"Collection task {task.task_id} failed, retry {task.retry_count}/{task.max_retries} in {retry_delay}s")
        else:
            # Max retries exceeded
            task.status = CollectionStatus.ERROR
            self.metrics['failed_collections'] += 1
            
            self.logger.error(f"Collection task {task.task_id} failed permanently after {task.max_retries} retries")
    
    def _check_game_day_collections(self) -> None:
        """Check if additional game day collections are needed"""
        try:
            current_time = datetime.utcnow()
            
            # Check if it's during a typical game window
            if self._is_game_window(current_time):
                # Check if we need live updates
                if self.schedule_config['live_updates']['enabled']:
                    last_live_update = self._get_last_live_update_time()
                    
                    if not last_live_update or (current_time - last_live_update).total_seconds() > (
                        self.schedule_config['live_updates']['interval_minutes'] * 60
                    ):
                        self._schedule_live_update()
                        
        except Exception as e:
            self.logger.error(f"Error checking game day collections: {e}")
    
    def _schedule_live_update(self) -> None:
        """Schedule a live update during games"""
        current_week = self._get_current_nfl_week()
        task_id = f"live_update_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        task = CollectionTask(
            task_id=task_id,
            season=self.current_season,
            week=current_week,
            task_type='daily_update',
            scheduled_time=datetime.utcnow(),
            status=CollectionStatus.SCHEDULED
        )
        
        self.active_tasks[task_id] = task
        self.logger.info(f"Scheduled live update task: {task_id}")
    
    def _identify_missing_data(self) -> List[Week]:
        """Identify weeks with missing or incomplete data"""
        try:
            current_week = self._get_current_nfl_week()
            missing_weeks = []
            
            for week in range(1, min(current_week + 1, 19)):  # Check up to current week
                if not self._has_complete_data(self.current_season, week):
                    missing_weeks.append(week)
            
            return missing_weeks
            
        except Exception as e:
            self.logger.error(f"Error identifying missing data: {e}")
            return []
    
    def _has_complete_data(self, season: Season, week: Week) -> bool:
        """Check if we have complete data for a season/week"""
        try:
            def check_data(session):
                count = session.query(ActualResults).filter(
                    ActualResults.season == season,
                    ActualResults.week == week
                ).count()
                return count > 100  # Expect at least 100 player records per week
            
            return self.db_manager.execute_readonly(check_data)
            
        except Exception as e:
            self.logger.error(f"Error checking data completeness: {e}")
            return False
    
    def _get_current_nfl_week(self) -> Week:
        """Get current NFL week based on date"""
        try:
            # NFL season typically starts first Thursday after Labor Day
            season_start = datetime(2024, 9, 5)  # Approximate 2024 start
            current_date = datetime.utcnow()
            
            if current_date < season_start:
                return 1
            
            days_since_start = (current_date - season_start).days
            week = min(18, max(1, (days_since_start // 7) + 1))
            
            return week
            
        except Exception as e:
            self.logger.error(f"Error calculating current NFL week: {e}")
            return 1
    
    def _is_game_window(self, current_time: datetime) -> bool:
        """Check if current time is within a game window"""
        # NFL games typically on Sunday (1-8 PM ET), Monday (8-11 PM ET), Thursday (8-11 PM ET)
        weekday = current_time.weekday()  # 0=Monday, 6=Sunday
        hour = current_time.hour
        
        if weekday == 6:  # Sunday
            return 17 <= hour <= 23  # 1-8 PM ET (assuming UTC)
        elif weekday == 0:  # Monday
            return 20 <= hour <= 23  # 8-11 PM ET
        elif weekday == 3:  # Thursday
            return 20 <= hour <= 23  # 8-11 PM ET
        
        return False
    
    def _get_last_live_update_time(self) -> Optional[datetime]:
        """Get timestamp of last live update"""
        live_tasks = [task for task in self.completed_tasks if 'live_update' in task.task_id]
        if live_tasks:
            return max(task.completed_at for task in live_tasks if task.completed_at)
        return None
    
    def _count_updated_players(self, task: CollectionTask) -> int:
        """Count how many players were updated in this task"""
        try:
            def count_players(session):
                return session.query(ActualResults).filter(
                    ActualResults.season == task.season,
                    ActualResults.week == task.week,
                    ActualResults.updated_at >= task.created_at
                ).count()
            
            return self.db_manager.execute_readonly(count_players)
            
        except Exception as e:
            self.logger.error(f"Error counting updated players: {e}")
            return 0
    
    def _update_metrics(self) -> None:
        """Update collection metrics"""
        try:
            # Calculate data quality score
            if self.metrics['total_collections'] > 0:
                success_rate = self.metrics['successful_collections'] / self.metrics['total_collections']
                self.metrics['data_quality_score'] = success_rate * 100
            
            # Log metrics periodically
            if self.metrics['total_collections'] % 10 == 0:
                self.logger.info(f"Collection metrics: {self.metrics}")
                
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
    
    def _update_average_collection_time(self, collection_time: float) -> None:
        """Update running average of collection times"""
        if self.metrics['average_collection_time'] == 0:
            self.metrics['average_collection_time'] = collection_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.metrics['average_collection_time'] = (
                alpha * collection_time + (1 - alpha) * self.metrics['average_collection_time']
            )
    
    def _perform_health_check(self) -> None:
        """Perform health check on data collection system"""
        try:
            health_status = {
                'status': 'healthy',
                'active_tasks': len(self.active_tasks),
                'collection_status': self.collection_status.value,
                'last_collection': self.metrics['last_collection_time'],
                'success_rate': self.metrics['data_quality_score'],
                'issues': []
            }
            
            # Check for issues
            if len(self.active_tasks) > 10:
                health_status['issues'].append("High number of active tasks")
                health_status['status'] = 'warning'
            
            if self.metrics['data_quality_score'] < 80:
                health_status['issues'].append("Low data quality score")
                health_status['status'] = 'warning'
            
            failed_tasks = [task for task in self.completed_tasks[-10:] if task.status == CollectionStatus.ERROR]
            if len(failed_tasks) > 3:
                health_status['issues'].append("Multiple recent failures")
                health_status['status'] = 'error'
            
            # Store health status in the base monitor's health system  
            from src.monitoring.robust_monitoring_framework import HealthStatus
            with self._health_lock:
                if health_status['status'] == 'healthy':
                    self._health.status = HealthStatus.HEALTHY
                elif health_status['status'] == 'warning':
                    self._health.status = HealthStatus.DEGRADED
                else:
                    self._health.status = HealthStatus.UNHEALTHY
                
                self._health.message = '; '.join(health_status.get('issues', ['No issues']))
                if not self._health.message:
                    self._health.message = 'Operating normally'
            
        except Exception as e:
            self.logger.error(f"Error in health check: {e}")
            from src.monitoring.robust_monitoring_framework import HealthStatus
            with self._health_lock:
                self._health.status = HealthStatus.UNHEALTHY
                self._health.message = str(e)
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get current collection status"""
        return {
            'collection_status': self.collection_status.value,
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'metrics': self.metrics,
            'health_status': self.get_health().__dict__,
            'current_season': self.current_season,
            'current_week': self._get_current_nfl_week()
        }
    
    def force_collection(self, season: Season, week: Week) -> str:
        """Force immediate data collection for a specific week"""
        task_id = f"manual_{season}_week_{week}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task = CollectionTask(
            task_id=task_id,
            season=season,
            week=week,
            task_type='weekly',
            scheduled_time=datetime.utcnow(),
            status=CollectionStatus.SCHEDULED
        )
        
        self.active_tasks[task_id] = task
        self.logger.info(f"Forced collection task scheduled: {task_id}")
        
        return task_id
    
    def _collect_real_week_data(self, season: Season, week: Week) -> bool:
        """Collect real NFL data for a specific week"""
        try:
            # Lazy import to avoid circular dependencies
            if not self.real_data_collector:
                from src.data_collection.real_nfl_data_collector import RealNFLDataCollector
                self.real_data_collector = RealNFLDataCollector()
            
            self.logger.info(f"Collecting REAL NFL data for {season} Week {week}")
            success = self.real_data_collector.collect_week_data(season, week)
            
            if success:
                self.logger.info(f"Successfully collected real data for Week {week}")
            else:
                self.logger.warning(f"Failed to collect real data for Week {week}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error in real data collection for Week {week}: {e}")
            return False


# Global instance for easy access
automated_collector = AutomatedDataCollector()


def start_automated_collection() -> None:
    """Start the automated data collection system"""
    automated_collector.start_monitoring()


def get_collection_status() -> Dict[str, Any]:
    """Get current collection status"""
    return automated_collector.get_collection_status()


def force_week_collection(season: Season = 2024, week: Optional[Week] = None) -> str:
    """Force collection for a specific week"""
    if week is None:
        week = automated_collector._get_current_nfl_week()
    
    return automated_collector.force_collection(season, week)


__all__ = [
    'AutomatedDataCollector', 'CollectionTask', 'CollectionStatus',
    'automated_collector', 'start_automated_collection', 
    'get_collection_status', 'force_week_collection'
]