"""
Robust monitoring framework with proper threading, error handling, and recovery
"""
import logging
import threading
import time
import queue
import signal
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from src.utils.error_handling import ErrorHandler, NFLPredictorError, ErrorCode, CircuitBreaker

logger = logging.getLogger(__name__)

class MonitorStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    PAUSED = "paused"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class MonitorHealth:
    status: HealthStatus
    last_success: Optional[datetime]
    consecutive_failures: int
    total_failures: int
    error_rate: float
    message: str

class BackoffStrategy:
    """Exponential backoff with jitter for error recovery"""
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 300.0, 
                 multiplier: float = 2.0, jitter: bool = True):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.current_delay = initial_delay
        
    def get_delay(self) -> float:
        """Get next delay duration"""
        delay = min(self.current_delay, self.max_delay)
        
        if self.jitter:
            # Add jitter to prevent thundering herd
            import random
            delay *= (0.5 + random.random() * 0.5)
            
        return delay
    
    def increase_delay(self):
        """Increase delay for next failure"""
        self.current_delay = min(self.current_delay * self.multiplier, self.max_delay)
    
    def reset(self):
        """Reset delay to initial value"""
        self.current_delay = self.initial_delay

class BaseMonitor(ABC):
    """
    Base class for all monitoring components with robust error handling
    """
    
    def __init__(self, name: str, check_interval: float = 60.0, max_failures: int = 5):
        self.name = name
        self.check_interval = check_interval
        self.max_failures = max_failures
        
        # Threading and control
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._status = MonitorStatus.STOPPED
        self._status_lock = threading.RLock()
        
        # Error handling and recovery
        self.error_handler = ErrorHandler(f"{__name__}.{name}")
        self.backoff = BackoffStrategy()
        self.circuit_breaker = CircuitBreaker(failure_threshold=max_failures)
        
        # Health tracking
        self._health = MonitorHealth(
            status=HealthStatus.UNKNOWN,
            last_success=None,
            consecutive_failures=0,
            total_failures=0,
            error_rate=0.0,
            message="Not started"
        )
        self._health_lock = threading.RLock()
        
        # Performance metrics
        self._start_time: Optional[datetime] = None
        self._last_check_time: Optional[datetime] = None
        self._check_count = 0
        self._success_count = 0
        
        # Shutdown handling
        self._shutdown_handlers: List[Callable] = []
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    @abstractmethod
    def _monitor_iteration(self) -> bool:
        """
        Perform one monitoring iteration
        
        Returns:
            bool: True if successful, False if failed
        """
        pass
    
    def start(self) -> bool:
        """Start the monitor"""
        try:
            with self._status_lock:
                if self._status != MonitorStatus.STOPPED:
                    logger.warning(f"Monitor {self.name} is already running")
                    return False
                
                self._status = MonitorStatus.STARTING
                self._stop_event.clear()
                self._pause_event.clear()
                
                # Create and start monitoring thread
                self._thread = threading.Thread(
                    target=self._monitoring_loop,
                    name=f"Monitor-{self.name}",
                    daemon=True
                )
                self._thread.start()
                
                self._status = MonitorStatus.RUNNING
                self._start_time = datetime.utcnow()
                
                logger.info(f"Monitor {self.name} started successfully")
                return True
                
        except Exception as e:
            self._status = MonitorStatus.ERROR
            self.error_handler.handle_error(e, f"Failed to start monitor {self.name}")
            return False
    
    def stop(self, timeout: float = 30.0) -> bool:
        """Stop the monitor gracefully"""
        try:
            with self._status_lock:
                if self._status == MonitorStatus.STOPPED:
                    return True
                    
                self._status = MonitorStatus.STOPPING
                self._stop_event.set()
                
                # Wait for thread to finish
                if self._thread and self._thread.is_alive():
                    self._thread.join(timeout=timeout)
                    
                    if self._thread.is_alive():
                        logger.error(f"Monitor {self.name} failed to stop within {timeout}s")
                        return False
                
                self._status = MonitorStatus.STOPPED
                
                # Run shutdown handlers
                for handler in self._shutdown_handlers:
                    try:
                        handler()
                    except Exception as e:
                        logger.error(f"Error in shutdown handler: {e}")
                
                logger.info(f"Monitor {self.name} stopped successfully")
                return True
                
        except Exception as e:
            self.error_handler.handle_error(e, f"Failed to stop monitor {self.name}")
            return False
    
    def pause(self):
        """Pause the monitor"""
        with self._status_lock:
            if self._status == MonitorStatus.RUNNING:
                self._status = MonitorStatus.PAUSED
                self._pause_event.set()
                logger.info(f"Monitor {self.name} paused")
    
    def resume(self):
        """Resume the monitor"""
        with self._status_lock:
            if self._status == MonitorStatus.PAUSED:
                self._status = MonitorStatus.RUNNING
                self._pause_event.clear()
                logger.info(f"Monitor {self.name} resumed")
    
    def _monitoring_loop(self):
        """Main monitoring loop with robust error handling"""
        logger.info(f"Starting monitoring loop for {self.name}")
        
        while not self._stop_event.is_set():
            try:
                # Check if paused
                if self._pause_event.is_set():
                    time.sleep(1.0)
                    continue
                
                # Perform monitoring iteration with circuit breaker
                success = self.circuit_breaker.call(self._safe_monitor_iteration)
                
                if success:
                    self._handle_success()
                else:
                    self._handle_failure(None)
                
                # Wait for next iteration
                self._wait_for_next_iteration()
                
            except NFLPredictorError as e:
                self._handle_failure(e)
                
            except Exception as e:
                # Wrap unexpected errors
                wrapped_error = NFLPredictorError(
                    f"Unexpected error in {self.name} monitoring loop",
                    ErrorCode.SYSTEM_CONFIG_ERROR,
                    cause=e
                )
                self._handle_failure(wrapped_error)
        
        logger.info(f"Monitoring loop for {self.name} stopped")
    
    def _safe_monitor_iteration(self) -> bool:
        """Safely execute one monitoring iteration with error isolation"""
        try:
            self._last_check_time = datetime.utcnow()
            self._check_count += 1
            
            # Execute the actual monitoring logic
            result = self._monitor_iteration()
            
            if result:
                self._success_count += 1
                return True
            else:
                raise NFLPredictorError(
                    "Monitor iteration returned False",
                    ErrorCode.BUSINESS_STATE_ERROR
                )
                
        except Exception as e:
            if isinstance(e, NFLPredictorError):
                raise
            else:
                raise NFLPredictorError(
                    f"Error in monitor iteration: {str(e)}",
                    ErrorCode.SYSTEM_CONFIG_ERROR,
                    cause=e
                )
    
    def _handle_success(self):
        """Handle successful monitoring iteration"""
        with self._health_lock:
            self._health.last_success = datetime.utcnow()
            self._health.consecutive_failures = 0
            self._health.status = HealthStatus.HEALTHY
            self._health.message = "Operating normally"
            
            # Update error rate
            if self._check_count > 0:
                self._health.error_rate = (self._check_count - self._success_count) / self._check_count
        
        # Reset backoff
        self.backoff.reset()
        
        logger.debug(f"Monitor {self.name} iteration successful")
    
    def _handle_failure(self, error: Optional[NFLPredictorError]):
        """Handle failed monitoring iteration"""
        with self._health_lock:
            self._health.consecutive_failures += 1
            self._health.total_failures += 1
            
            # Update error rate
            if self._check_count > 0:
                self._health.error_rate = (self._check_count - self._success_count) / self._check_count
            
            # Determine health status
            if self._health.consecutive_failures >= self.max_failures:
                self._health.status = HealthStatus.UNHEALTHY
                self._health.message = f"Failed {self._health.consecutive_failures} times consecutively"
            elif self._health.error_rate > 0.5:
                self._health.status = HealthStatus.DEGRADED
                self._health.message = f"High error rate: {self._health.error_rate:.1%}"
            else:
                self._health.status = HealthStatus.DEGRADED
                self._health.message = f"Recent failure: {str(error) if error else 'Unknown'}"
        
        # Log the error
        if error:
            self.error_handler.handle_error(error, f"Monitor {self.name} iteration failed", suppress=True)
        
        # Increase backoff delay
        self.backoff.increase_delay()
        
        # Sleep with backoff before next attempt
        backoff_delay = self.backoff.get_delay()
        logger.warning(f"Monitor {self.name} failed, backing off for {backoff_delay:.1f}s")
        self._stop_event.wait(backoff_delay)
    
    def _wait_for_next_iteration(self):
        """Wait for the next monitoring iteration"""
        self._stop_event.wait(self.check_interval)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Monitor {self.name} received signal {signum}, shutting down...")
        self.stop()
    
    def add_shutdown_handler(self, handler: Callable):
        """Add a function to be called on shutdown"""
        self._shutdown_handlers.append(handler)
    
    def get_status(self) -> MonitorStatus:
        """Get current monitor status"""
        with self._status_lock:
            return self._status
    
    def get_health(self) -> MonitorHealth:
        """Get current monitor health"""
        with self._health_lock:
            return MonitorHealth(
                status=self._health.status,
                last_success=self._health.last_success,
                consecutive_failures=self._health.consecutive_failures,
                total_failures=self._health.total_failures,
                error_rate=self._health.error_rate,
                message=self._health.message
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        uptime = (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0
        
        return {
            'name': self.name,
            'status': self._status.value,
            'uptime_seconds': uptime,
            'check_count': self._check_count,
            'success_count': self._success_count,
            'success_rate': self._success_count / max(self._check_count, 1),
            'last_check': self._last_check_time.isoformat() if self._last_check_time else None,
            'health': self.get_health().__dict__,
            'circuit_breaker_state': self.circuit_breaker.state
        }


class MonitorManager:
    """
    Manager for multiple monitoring components
    Provides centralized control and health checking
    """
    
    def __init__(self):
        self.monitors: Dict[str, BaseMonitor] = {}
        self.logger = logging.getLogger(f"{__name__}.MonitorManager")
        self._shutdown_requested = False
    
    def register_monitor(self, monitor: BaseMonitor):
        """Register a monitor with the manager"""
        self.monitors[monitor.name] = monitor
        self.logger.info(f"Registered monitor: {monitor.name}")
    
    def start_all(self) -> Dict[str, bool]:
        """Start all registered monitors"""
        results = {}
        
        for name, monitor in self.monitors.items():
            try:
                success = monitor.start()
                results[name] = success
                
                if success:
                    self.logger.info(f"Started monitor: {name}")
                else:
                    self.logger.error(f"Failed to start monitor: {name}")
                    
            except Exception as e:
                self.logger.error(f"Exception starting monitor {name}: {e}")
                results[name] = False
        
        return results
    
    def stop_all(self, timeout: float = 30.0) -> Dict[str, bool]:
        """Stop all registered monitors"""
        results = {}
        self._shutdown_requested = True
        
        for name, monitor in self.monitors.items():
            try:
                success = monitor.stop(timeout)
                results[name] = success
                
                if success:
                    self.logger.info(f"Stopped monitor: {name}")
                else:
                    self.logger.error(f"Failed to stop monitor: {name}")
                    
            except Exception as e:
                self.logger.error(f"Exception stopping monitor {name}: {e}")
                results[name] = False
        
        return results
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status of all monitors"""
        if not self.monitors:
            return {
                'status': 'no_monitors',
                'healthy_count': 0,
                'total_count': 0,
                'monitors': {}
            }
        
        monitor_health = {}
        healthy_count = 0
        
        for name, monitor in self.monitors.items():
            health = monitor.get_health()
            monitor_health[name] = {
                'status': health.status.value,
                'message': health.message,
                'consecutive_failures': health.consecutive_failures,
                'error_rate': health.error_rate
            }
            
            if health.status == HealthStatus.HEALTHY:
                healthy_count += 1
        
        # Determine overall status
        if healthy_count == len(self.monitors):
            overall_status = 'healthy'
        elif healthy_count > 0:
            overall_status = 'degraded'
        else:
            overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'healthy_count': healthy_count,
            'total_count': len(self.monitors),
            'monitors': monitor_health
        }
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics for all monitors"""
        return {
            name: monitor.get_metrics()
            for name, monitor in self.monitors.items()
        }


# Global monitor manager instance
monitor_manager = MonitorManager()

__all__ = [
    'BaseMonitor', 'MonitorManager', 'MonitorStatus', 'HealthStatus', 
    'MonitorHealth', 'BackoffStrategy', 'monitor_manager'
]