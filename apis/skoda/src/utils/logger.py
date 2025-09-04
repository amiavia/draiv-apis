"""
Structured Logger for Skoda Connect API
Advanced logging with security, performance monitoring, and structured output
"""
import logging
import json
import sys
import os
import traceback
from typing import Any, Dict, Optional, Union
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger
import hashlib
import re

# Sensitive data patterns to mask in logs
SENSITIVE_PATTERNS = [
    r'(?i)(password|passwd|pwd)[\s]*[=:][\s]*["\']?([^"\'\s,}]+)',
    r'(?i)(token|jwt|bearer)[\s]*[=:][\s]*["\']?([^"\'\s,}]+)',
    r'(?i)(api[_-]?key|apikey)[\s]*[=:][\s]*["\']?([^"\'\s,}]+)',
    r'(?i)(secret|private[_-]?key)[\s]*[=:][\s]*["\']?([^"\'\s,}]+)',
    r'(?i)(authorization)[\s]*[=:][\s]*["\']?([^"\'\s,}]+)',
    r'(?i)(spin|pin)[\s]*[=:][\s]*["\']?(\d{4,8})',
    r'(?i)(vin)[\s]*[=:][\s]*["\']?([A-HJ-NPR-Z0-9]{17})',
    r'(?i)(email)[\s]*[=:][\s]*["\']?([^"\'\s,}@]+@[^"\'\s,}]+)',
    r'(?i)(phone|mobile)[\s]*[=:][\s]*["\']?(\+?\d{10,15})',
]

class SecurityFilter(logging.Filter):
    """Filter to mask sensitive data in log records"""
    
    def __init__(self):
        super().__init__()
        self.compiled_patterns = [(re.compile(pattern), replacement) 
                                 for pattern, replacement in [
                                     (p, p.split(')')[0] + ')***MASKED***') 
                                     for p in SENSITIVE_PATTERNS
                                 ]]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log message"""
        if hasattr(record, 'msg') and record.msg:
            message = str(record.msg)
            for pattern, replacement in self.compiled_patterns:
                message = pattern.sub(replacement, message)
            record.msg = message
        
        # Also mask in args if present
        if hasattr(record, 'args') and record.args:
            masked_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.compiled_patterns:
                        arg = pattern.sub(replacement, arg)
                masked_args.append(arg)
            record.args = tuple(masked_args)
        
        return True

class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics to log records"""
    
    def __init__(self):
        super().__init__()
        self.start_time = datetime.now()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add performance metrics to record"""
        record.uptime = (datetime.now() - self.start_time).total_seconds()
        record.memory_mb = self._get_memory_usage()
        return True
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

class RequestFilter(logging.Filter):
    """Filter to add request context to log records"""
    
    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None
        self.operation = None
    
    def set_context(self, request_id: str = None, user_id: str = None, operation: str = None):
        """Set request context"""
        if request_id:
            self.request_id = request_id
        if user_id:
            self.user_id = user_id
        if operation:
            self.operation = operation
    
    def clear_context(self):
        """Clear request context"""
        self.request_id = None
        self.user_id = None
        self.operation = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to record"""
        record.request_id = self.request_id
        record.user_id = self.user_id
        record.operation = self.operation
        return True

class SkodaJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for Skoda Connect API"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record"""
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = datetime.fromtimestamp(record.created).isoformat()
        log_record['service'] = 'skoda-connect-api'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add process info
        log_record['process_id'] = os.getpid()
        log_record['thread_name'] = record.threadName
        
        # Add custom fields if present
        for field in ['request_id', 'user_id', 'operation', 'uptime', 'memory_mb']:
            if hasattr(record, field):
                log_record[field] = getattr(record, field)
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

class SkodaLoggerManager:
    """
    Advanced logger manager for Skoda Connect API
    
    Features:
    - Structured JSON logging
    - Security filtering (mask sensitive data)
    - Performance monitoring
    - Request tracing
    - Multiple output formats
    - Log rotation and archival
    """
    
    def __init__(
        self,
        name: str = "skoda-connect-api",
        level: str = "INFO",
        log_dir: Optional[str] = None,
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        backup_count: int = 5,
        console_output: bool = True,
        json_format: bool = True
    ):
        """
        Initialize logger manager
        
        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            max_file_size: Maximum file size before rotation
            backup_count: Number of backup files to keep
            console_output: Whether to output to console
            json_format: Whether to use JSON formatting
        """
        self.name = name
        self.level = getattr(logging, level.upper())
        self.log_dir = log_dir
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.console_output = console_output
        self.json_format = json_format
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create filters
        self.security_filter = SecurityFilter()
        self.performance_filter = PerformanceFilter()
        self.request_filter = RequestFilter()
        
        # Setup handlers
        self._setup_handlers()
        
        # Setup formatters
        self._setup_formatters()
    
    def _setup_handlers(self):
        """Setup log handlers"""
        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            console_handler.addFilter(self.security_filter)
            console_handler.addFilter(self.performance_filter)
            console_handler.addFilter(self.request_filter)
            self.logger.addHandler(console_handler)
        
        # File handlers
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Main log file (rotating by size)
            main_log_file = os.path.join(self.log_dir, f"{self.name}.log")
            file_handler = RotatingFileHandler(
                main_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.level)
            file_handler.addFilter(self.security_filter)
            file_handler.addFilter(self.performance_filter)
            file_handler.addFilter(self.request_filter)
            self.logger.addHandler(file_handler)
            
            # Error log file (errors and critical only)
            error_log_file = os.path.join(self.log_dir, f"{self.name}-error.log")
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.addFilter(self.security_filter)
            error_handler.addFilter(self.performance_filter)
            error_handler.addFilter(self.request_filter)
            self.logger.addHandler(error_handler)
            
            # Daily log file (time-based rotation)
            daily_log_file = os.path.join(self.log_dir, f"{self.name}-daily.log")
            daily_handler = TimedRotatingFileHandler(
                daily_log_file,
                when='midnight',
                interval=1,
                backupCount=30  # Keep 30 days
            )
            daily_handler.setLevel(self.level)
            daily_handler.addFilter(self.security_filter)
            daily_handler.addFilter(self.performance_filter)
            daily_handler.addFilter(self.request_filter)
            self.logger.addHandler(daily_handler)
    
    def _setup_formatters(self):
        """Setup log formatters"""
        if self.json_format:
            # JSON formatter for structured logging
            json_formatter = SkodaJSONFormatter(
                '%(timestamp)s %(service)s %(level)s %(logger)s %(module)s %(function)s %(line)d'
            )
            for handler in self.logger.handlers:
                handler.setFormatter(json_formatter)
        else:
            # Standard text formatter
            text_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            for handler in self.logger.handlers:
                handler.setFormatter(text_formatter)
    
    def set_request_context(self, request_id: str = None, user_id: str = None, operation: str = None):
        """Set context for current request"""
        self.request_filter.set_context(request_id, user_id, operation)
    
    def clear_request_context(self):
        """Clear current request context"""
        self.request_filter.clear_context()
    
    def log_api_request(
        self,
        method: str,
        endpoint: str,
        user_id: str,
        request_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        status_code: Optional[int] = None,
        response_size: Optional[int] = None
    ):
        """Log API request with structured data"""
        self.logger.info(
            "API request processed",
            extra={
                "event_type": "api_request",
                "method": method,
                "endpoint": endpoint,
                "user_id": self._hash_pii(user_id),
                "request_size": len(json.dumps(request_data)) if request_data else 0,
                "response_size": response_size,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "success": status_code < 400 if status_code else None
            }
        )
    
    def log_external_api_call(
        self,
        service: str,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        retry_count: int = 0,
        error: Optional[str] = None
    ):
        """Log external API call"""
        self.logger.info(
            f"External API call to {service}",
            extra={
                "event_type": "external_api_call",
                "service": service,
                "endpoint": endpoint,
                "method": method,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "retry_count": retry_count,
                "success": status_code < 400,
                "error": error
            }
        )
    
    def log_cache_operation(
        self,
        operation: str,
        key: str,
        hit: Optional[bool] = None,
        ttl: Optional[int] = None,
        size: Optional[int] = None
    ):
        """Log cache operation"""
        self.logger.debug(
            f"Cache {operation}",
            extra={
                "event_type": "cache_operation",
                "operation": operation,
                "key_hash": self._hash_key(key),
                "hit": hit,
                "ttl": ttl,
                "size": size
            }
        )
    
    def log_rate_limit_event(
        self,
        user_id: str,
        operation: str,
        allowed: bool,
        requests_made: int,
        limit: int,
        reset_time: Optional[str] = None
    ):
        """Log rate limiting event"""
        level = logging.WARNING if not allowed else logging.DEBUG
        self.logger.log(
            level,
            f"Rate limit {'exceeded' if not allowed else 'check'} for {operation}",
            extra={
                "event_type": "rate_limit",
                "user_id": self._hash_pii(user_id),
                "operation": operation,
                "allowed": allowed,
                "requests_made": requests_made,
                "limit": limit,
                "reset_time": reset_time
            }
        )
    
    def log_circuit_breaker_event(
        self,
        name: str,
        state: str,
        failure_count: int,
        success_rate: float,
        action: Optional[str] = None
    ):
        """Log circuit breaker state change"""
        self.logger.warning(
            f"Circuit breaker {name} {action or 'status'}",
            extra={
                "event_type": "circuit_breaker",
                "name": name,
                "state": state,
                "failure_count": failure_count,
                "success_rate": success_rate,
                "action": action
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        user_id: str,
        details: Dict[str, Any],
        severity: str = "warning"
    ):
        """Log security-related event"""
        level = getattr(logging, severity.upper())
        self.logger.log(
            level,
            f"Security event: {event_type}",
            extra={
                "event_type": "security",
                "security_event_type": event_type,
                "user_id": self._hash_pii(user_id),
                "details": details,
                "severity": severity
            }
        )
    
    def _hash_pii(self, data: str) -> str:
        """Hash PII data for logging"""
        if not data:
            return ""
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    
    def _hash_key(self, key: str) -> str:
        """Hash cache key for logging"""
        return hashlib.md5(key.encode()).hexdigest()[:8]
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics"""
        return {
            "name": self.name,
            "level": logging.getLevelName(self.level),
            "handlers": len(self.logger.handlers),
            "log_dir": self.log_dir,
            "json_format": self.json_format,
            "console_output": self.console_output,
            "uptime": self.performance_filter._get_memory_usage()
        }

# Global logger instance
_global_logger_manager: Optional[SkodaLoggerManager] = None

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get configured logger instance
    
    Args:
        name: Optional logger name (uses global if not provided)
        
    Returns:
        Configured logger instance
    """
    global _global_logger_manager
    
    if _global_logger_manager is None:
        # Initialize with environment variables or defaults
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_dir = os.getenv("LOG_DIR", "./logs")
        json_logging = os.getenv("JSON_LOGGING", "true").lower() == "true"
        
        _global_logger_manager = SkodaLoggerManager(
            name=name or "skoda-connect-api",
            level=log_level,
            log_dir=log_dir if os.path.exists(os.path.dirname(log_dir) or ".") else None,
            json_format=json_logging
        )
    
    return _global_logger_manager.get_logger()

def set_request_context(request_id: str = None, user_id: str = None, operation: str = None):
    """Set global request context for logging"""
    if _global_logger_manager:
        _global_logger_manager.set_request_context(request_id, user_id, operation)

def clear_request_context():
    """Clear global request context"""
    if _global_logger_manager:
        _global_logger_manager.clear_request_context()

# Context manager for request logging
class LoggingContext:
    """Context manager for request-scoped logging"""
    
    def __init__(self, request_id: str = None, user_id: str = None, operation: str = None):
        self.request_id = request_id
        self.user_id = user_id
        self.operation = operation
    
    def __enter__(self):
        set_request_context(self.request_id, self.user_id, self.operation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        clear_request_context()

# Example usage and testing
if __name__ == "__main__":
    # Test the logger
    logger_manager = SkodaLoggerManager(
        name="test-skoda-api",
        level="DEBUG",
        log_dir="./test_logs"
    )
    
    logger = logger_manager.get_logger()
    
    # Test different log types
    with LoggingContext(request_id="req-123", user_id="user@example.com", operation="get_status"):
        logger.info("Test info message")
        logger.warning("Test warning with sensitive data: password=secret123")
        logger.error("Test error message")
        
        # Test structured logging methods
        logger_manager.log_api_request(
            method="GET",
            endpoint="/api/vehicles/status",
            user_id="user@example.com",
            duration_ms=150.5,
            status_code=200
        )
        
        logger_manager.log_external_api_call(
            service="skoda-connect",
            endpoint="/auth/token",
            method="POST",
            duration_ms=500.2,
            status_code=200
        )