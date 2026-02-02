import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import colorlog
from config import settings


class AgentLogger:
    """
    Custom logger for agents with colored console output and file logging
    """
    
    def __init__(self, name: str = "agentmesh"):
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Set level from config
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Prevent duplicate handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        
        # Add handlers
        self._add_console_handler()
        self._add_file_handler()
    
    def _add_console_handler(self):
        """Add colored console handler"""
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        
        # Colored formatter
        console_format = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s '
            '%(cyan)s[%(name)s]%(reset)s '
            '%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'blue',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self):
        """Add file handler for detailed logging"""
        # Ensure log directory exists
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with date
        log_file = log_dir / f"agentmesh_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed formatter for file
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(self._format_message(message, kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(self._format_message(message, kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(self._format_message(message, kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(self._format_message(message, kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(self._format_message(message, kwargs))
    
    def _format_message(self, message: str, context: dict) -> str:
        """Format message with optional context"""
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            return f"{message} | {context_str}"
        return message
    
    def agent_action(self, agent_name: str, action: str, details: Optional[dict] = None):
        """Log agent action"""
        msg = f"🤖 {agent_name} → {action}"
        if details:
            self.info(msg, **details)
        else:
            self.info(msg)
    
    def tool_call(self, tool_name: str, params: dict):
        """Log tool call"""
        self.info(f"🔧 Tool call: {tool_name}", **params)
    
    def tool_result(self, tool_name: str, success: bool, details: Optional[dict] = None):
        """Log tool result"""
        status = "✅ Success" if success else "❌ Failed"
        msg = f"{status}: {tool_name}"
        if details:
            self.info(msg, **details)
        else:
            self.info(msg)
    
    def query_start(self, query: str, query_id: str):
        """Log query start"""
        self.info("📝 New query started", query=query, query_id=query_id)
    
    def query_complete(self, query_id: str, confidence: float, duration: float):
        """Log query completion"""
        self.info(
            "✅ Query completed",
            query_id=query_id,
            confidence=confidence,
            duration_seconds=f"{duration:.2f}"
        )
    
    def query_failed(self, query_id: str, error: str):
        """Log query failure"""
        self.error("❌ Query failed", query_id=query_id, error=error)


class AgentLoggerFactory:
    """
    Factory to create loggers for different components
    """
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str) -> AgentLogger:
        """
        Get or create a logger for a component
        
        Args:
            name: Logger name (e.g., 'planner', 'research', 'orchestrator')
            
        Returns:
            AgentLogger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = AgentLogger(name)
        return cls._loggers[name]


# Create default logger
logger = AgentLoggerFactory.get_logger("agentmesh")


# Convenience functions for common operations
def log_agent_action(agent_name: str, action: str, **details):
    """Quick log for agent actions"""
    logger.agent_action(agent_name, action, details if details else None)


def log_tool_call(tool_name: str, **params):
    """Quick log for tool calls"""
    logger.tool_call(tool_name, params)


def log_tool_result(tool_name: str, success: bool, **details):
    """Quick log for tool results"""
    logger.tool_result(tool_name, success, details if details else None)


def get_agent_logger(agent_name: str) -> AgentLogger:
    """
    Get a logger for a specific agent
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        AgentLogger configured for that agent
    """
    return AgentLoggerFactory.get_logger(agent_name)


# Context manager for timing operations
class LogTimer:
    """Context manager for timing operations"""
    
    def __init__(self, logger: AgentLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"⏱️  Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"✅ Completed: {self.operation}", duration=f"{duration:.2f}s")
        else:
            self.logger.error(f"❌ Failed: {self.operation}", duration=f"{duration:.2f}s", error=str(exc_val))
        
        return False  # Don't suppress exceptions


# Example usage decorator
def log_execution(operation_name: str):
    """
    Decorator to log function execution
    
    Usage:
        @log_execution("search_web")
        def search_web(query):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_logger = AgentLoggerFactory.get_logger(func.__module__)
            
            with LogTimer(func_logger, f"{operation_name}"):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator