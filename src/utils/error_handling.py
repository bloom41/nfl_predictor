"""
Standardized error handling and logging utilities for NFL prediction system
"""
import logging
import traceback
import functools
import time
from typing import Any, Callable, Dict, Optional, Type, Union
from datetime import datetime
from enum import Enum

class ErrorCode(Enum):
    """Standardized error codes"""
    # Database errors (1000-1999)
    DB_CONNECTION_ERROR = 1001
    DB_QUERY_ERROR = 1002
    DB_TRANSACTION_ERROR = 1003
    DB_VALIDATION_ERROR = 1004
    
    # API/Network errors (2000-2999)
    NETWORK_ERROR = 2001
    API_RATE_LIMIT = 2002
    API_TIMEOUT = 2003
    API_UNAUTHORIZED = 2004
    API_NOT_FOUND = 2005
    
    # Data processing errors (3000-3999)
    DATA_VALIDATION_ERROR = 3001
    DATA_PARSING_ERROR = 3002
    DATA_MISSING_ERROR = 3003
    DATA_FORMAT_ERROR = 3004
    
    # Model errors (4000-4999)
    MODEL_TRAINING_ERROR = 4001
    MODEL_PREDICTION_ERROR = 4002
    MODEL_LOADING_ERROR = 4003
    MODEL_VALIDATION_ERROR = 4004
    
    # System errors (5000-5999)
    SYSTEM_CONFIG_ERROR = 5001
    SYSTEM_MEMORY_ERROR = 5002
    SYSTEM_IO_ERROR = 5003
    SYSTEM_PERMISSION_ERROR = 5004
    
    # Business logic errors (6000-6999)
    BUSINESS_RULE_ERROR = 6001
    BUSINESS_VALIDATION_ERROR = 6002
    BUSINESS_STATE_ERROR = 6003
    
    # Unknown/Generic errors (9000-9999)
    UNKNOWN_ERROR = 9001
    EXTERNAL_SERVICE_ERROR = 9002


class NFLPredictorError(Exception):
    """Base exception class for NFL predictor system"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR, 
                 details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()
    
    def __str__(self):
        return f"[{self.error_code.name}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            'error_code': self.error_code.value,
            'error_name': self.error_code.name,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'cause': str(self.cause) if self.cause else None
        }


class DatabaseError(NFLPredictorError):
    """Database-related errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.DB_CONNECTION_ERROR, **kwargs):
        super().__init__(message, error_code, **kwargs)


class NetworkError(NFLPredictorError):
    """Network/API-related errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.NETWORK_ERROR, **kwargs):
        super().__init__(message, error_code, **kwargs)


class DataError(NFLPredictorError):
    """Data processing/validation errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.DATA_VALIDATION_ERROR, **kwargs):
        super().__init__(message, error_code, **kwargs)


class ModelError(NFLPredictorError):
    """Model training/prediction errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.MODEL_PREDICTION_ERROR, **kwargs):
        super().__init__(message, error_code, **kwargs)


class ErrorHandler:
    """Centralized error handling and logging"""
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.error_counts = {}
        self.last_errors = {}
    
    def handle_error(self, error: Exception, context: str = "", 
                    suppress: bool = False, notify: bool = False) -> Optional[NFLPredictorError]:
        """
        Handle an error with standardized logging and optional re-raising
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            suppress: Whether to suppress the error (don't re-raise)
            notify: Whether to send notifications for this error
            
        Returns:
            NFLPredictorError: Wrapped error if suppressed, None if re-raised
        """
        try:
            # Convert to standardized error if needed
            if isinstance(error, NFLPredictorError):
                std_error = error
            else:
                std_error = self._convert_to_standard_error(error, context)
            
            # Log the error
            self._log_error(std_error, context)
            
            # Update error tracking
            self._track_error(std_error)
            
            # Send notifications if requested
            if notify:
                self._send_notification(std_error, context)
            
            # Re-raise or return based on suppress flag
            if suppress:
                return std_error
            else:
                raise std_error
                
        except Exception as e:
            # Fallback error handling
            self.logger.critical(f"Error in error handler: {e}")
            if not suppress:
                raise error  # Re-raise original error
            return NFLPredictorError("Error handling failed", ErrorCode.SYSTEM_CONFIG_ERROR)
    
    def _convert_to_standard_error(self, error: Exception, context: str) -> NFLPredictorError:
        """Convert generic exception to standardized error"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Map common exceptions to error codes
        error_mapping = {
            'ConnectionError': ErrorCode.DB_CONNECTION_ERROR,
            'TimeoutError': ErrorCode.API_TIMEOUT,
            'PermissionError': ErrorCode.SYSTEM_PERMISSION_ERROR,
            'MemoryError': ErrorCode.SYSTEM_MEMORY_ERROR,
            'ValueError': ErrorCode.DATA_VALIDATION_ERROR,
            'KeyError': ErrorCode.DATA_MISSING_ERROR,
            'TypeError': ErrorCode.DATA_FORMAT_ERROR,
            'FileNotFoundError': ErrorCode.SYSTEM_IO_ERROR,
            'ImportError': ErrorCode.SYSTEM_CONFIG_ERROR,
        }
        
        # Check for SQL-related errors
        if any(keyword in error_message.lower() for keyword in ['sql', 'database', 'connection']):
            error_code = ErrorCode.DB_CONNECTION_ERROR
            error_class = DatabaseError
        # Check for network-related errors
        elif any(keyword in error_message.lower() for keyword in ['request', 'http', 'network', 'timeout']):
            error_code = ErrorCode.NETWORK_ERROR
            error_class = NetworkError
        # Check for data-related errors
        elif any(keyword in error_message.lower() for keyword in ['validation', 'parse', 'format']):
            error_code = ErrorCode.DATA_VALIDATION_ERROR
            error_class = DataError
        # Use mapped error code
        elif error_type in error_mapping:
            error_code = error_mapping[error_type]
            error_class = NFLPredictorError
        else:
            error_code = ErrorCode.UNKNOWN_ERROR
            error_class = NFLPredictorError
        
        details = {
            'original_type': error_type,
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        return error_class(
            message=f"{context}: {error_message}" if context else error_message,
            error_code=error_code,
            details=details,
            cause=error
        )
    
    def _log_error(self, error: NFLPredictorError, context: str):
        """Log error with appropriate level and formatting"""
        error_dict = error.to_dict()
        
        # Determine log level based on error code
        if error.error_code.value < 3000:  # Critical system errors
            log_level = logging.ERROR
        elif error.error_code.value < 5000:  # Data/model errors
            log_level = logging.WARNING
        else:  # Business logic errors
            log_level = logging.INFO
        
        # Format log message
        log_message = f"[{error.error_code.name}] {error.message}"
        if context:
            log_message = f"{context} - {log_message}"
        
        # Log with details
        self.logger.log(log_level, log_message, extra={'error_details': error_dict})
        
        # Log stack trace for critical errors
        if log_level == logging.ERROR and error.cause:
            self.logger.error(f"Stack trace: {error.details.get('traceback', 'Not available')}")
    
    def _track_error(self, error: NFLPredictorError):
        """Track error frequency and patterns"""
        error_key = error.error_code.name
        
        # Update error counts
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Store last occurrence
        self.last_errors[error_key] = {
            'timestamp': error.timestamp,
            'message': error.message,
            'count': self.error_counts[error_key]
        }
        
        # Log warning if error is frequent
        if self.error_counts[error_key] % 10 == 0:
            self.logger.warning(f"Error {error_key} has occurred {self.error_counts[error_key]} times")
    
    def _send_notification(self, error: NFLPredictorError, context: str):
        """Send error notification (placeholder for actual implementation)"""
        # This could integrate with:
        # - Email alerts
        # - Slack notifications
        # - PagerDuty
        # - Custom webhook
        
        self.logger.info(f"Notification would be sent for error: {error.error_code.name}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors"""
        return {
            'error_counts': self.error_counts.copy(),
            'last_errors': self.last_errors.copy(),
            'total_errors': sum(self.error_counts.values())
        }
    
    def reset_error_tracking(self):
        """Reset error tracking counters"""
        self.error_counts.clear()
        self.last_errors.clear()
        self.logger.info("Error tracking counters reset")


# Global error handler instance
global_error_handler = ErrorHandler()


def handle_errors(error_handler: Optional[ErrorHandler] = None, 
                 suppress: bool = False, 
                 notify: bool = False,
                 context: str = ""):
    """
    Decorator for automatic error handling
    
    Args:
        error_handler: Custom error handler instance
        suppress: Whether to suppress errors
        notify: Whether to send notifications
        context: Context string for error messages
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = error_handler or global_error_handler
            func_context = context or f"{func.__module__}.{func.__name__}"
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return handler.handle_error(
                    e, 
                    context=func_context, 
                    suppress=suppress, 
                    notify=notify
                )
        
        return wrapper
    return decorator


def retry_on_error(max_retries: int = 3, 
                  retry_delay: float = 1.0, 
                  backoff_factor: float = 2.0,
                  retry_on: tuple = (Exception,)):
    """
    Decorator for retrying functions on error
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (seconds)
        backoff_factor: Factor to multiply delay by after each retry
        retry_on: Tuple of exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = retry_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logging.getLogger(__name__).warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f} seconds..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logging.getLogger(__name__).error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}"
                        )
                        raise
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    raise
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default_return=None, 
                error_handler: Optional[ErrorHandler] = None, **kwargs):
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        *args: Function arguments
        default_return: Value to return if function fails
        error_handler: Custom error handler
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or default_return if error occurs
    """
    handler = error_handler or global_error_handler
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handler.handle_error(e, context=f"safe_execute({func.__name__})", suppress=True)
        return default_return


class CircuitBreaker:
    """Circuit breaker pattern for handling repeated failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise NFLPredictorError(
                    "Circuit breaker is OPEN - service unavailable",
                    ErrorCode.EXTERNAL_SERVICE_ERROR
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


__all__ = [
    'ErrorCode', 'NFLPredictorError', 'DatabaseError', 'NetworkError', 
    'DataError', 'ModelError', 'ErrorHandler', 'global_error_handler',
    'handle_errors', 'retry_on_error', 'safe_execute', 'CircuitBreaker'
]