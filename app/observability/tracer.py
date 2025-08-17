"""
LangSmith tracing utilities for agent observability
"""
import os
import functools
from typing import Dict, Any, Optional
from contextlib import contextmanager

try:
    from langsmith import Client, traceable
    from langsmith.run_helpers import tracing_context
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Mock decorators for when LangSmith is not available
    def traceable(func):
        return func

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("app.observability")


def setup_langsmith():
    """Initialize LangSmith tracing"""
    if not LANGSMITH_AVAILABLE:
        logger.warning("LangSmith not available - install 'langsmith' package for observability")
        return False
    
    if not settings.LANGCHAIN_TRACING_V2:
        logger.info("LangSmith tracing disabled in config")
        return False
    
    if not settings.LANGCHAIN_API_KEY:
        logger.warning("LANGCHAIN_API_KEY not set - LangSmith tracing disabled")
        return False
    
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
    
    try:
        # Test connection
        client = Client()
        logger.info(f"✅ LangSmith tracing enabled for project: {settings.LANGCHAIN_PROJECT}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith: {e}")
        return False


@contextmanager
def trace_agent_call(operation_name: str, inputs: Dict[str, Any]):
    """Context manager for tracing agent operations"""
    if not LANGSMITH_AVAILABLE or not settings.LANGCHAIN_TRACING_V2:
        yield {}
        return
    
    try:
        with tracing_context(operation_name) as context:
            # Log inputs
            context.update(inputs)
            
            outputs = {}
            yield outputs
            
            # Log outputs will be added by the caller
            
    except Exception as e:
        logger.error(f"Error in trace_agent_call: {e}")
        yield {}


def trace_classification(classifier_type: str):
    """Decorator for tracing intent classification"""
    def decorator(func):
        if not LANGSMITH_AVAILABLE:
            return func
            
        @traceable(name=f"classify_intent_{classifier_type}")
        @functools.wraps(func)
        def wrapper(self, text: str, *args, **kwargs):
            # Add metadata to trace
            inputs = {
                "text": text,
                "classifier_type": classifier_type,
                "confidence_threshold": getattr(self, 'confidence_threshold', 0.0),
                "fallback_intent": getattr(self, 'fallback_intent', None)
            }
            
            try:
                result = func(self, text, *args, **kwargs)
                
                # Add result metadata
                outputs = {
                    "intent": result.intent.value if hasattr(result, 'intent') else str(result),
                    "confidence": getattr(result, 'confidence', 0.0),
                    "metadata": getattr(result, 'metadata', {})
                }
                
                return result
                
            except Exception as e:
                logger.error(f"Error in classification: {e}")
                raise
                
        return wrapper
    return decorator


def trace_nl2sql_operation(operation_name: str):
    """Decorator for tracing NL2SQL operations"""
    def decorator(func):
        if not LANGSMITH_AVAILABLE:
            return func
            
        @traceable(name=f"nl2sql_{operation_name}")
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            try:
                # Capture inputs
                inputs = {
                    "operation": operation_name,
                    "args": str(args)[:200],  # Truncate for readability
                }
                
                result = await func(self, *args, **kwargs)
                
                # Capture outputs
                outputs = {
                    "success": getattr(result, 'success', True),
                    "result_type": type(result).__name__
                }
                
                return result
                
            except Exception as e:
                logger.error(f"Error in NL2SQL operation {operation_name}: {e}")
                raise
                
        @traceable(name=f"nl2sql_{operation_name}")
        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            try:
                inputs = {
                    "operation": operation_name,
                    "args": str(args)[:200],
                }
                
                result = func(self, *args, **kwargs)
                
                outputs = {
                    "success": getattr(result, 'success', True),
                    "result_type": type(result).__name__
                }
                
                return result
                
            except Exception as e:
                logger.error(f"Error in NL2SQL operation {operation_name}: {e}")
                raise
        
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def get_trace_url() -> Optional[str]:
    """Get the current trace URL if available"""
    if not LANGSMITH_AVAILABLE or not settings.LANGCHAIN_TRACING_V2:
        return None
    
    try:
        # This would need to be implemented based on the current trace context
        # For now, return the project URL
        return f"{settings.LANGCHAIN_ENDPOINT}/projects/{settings.LANGCHAIN_PROJECT}"
    except Exception:
        return None


def add_trace_metadata(metadata: Dict[str, Any]):
    """Add metadata to current trace"""
    if not LANGSMITH_AVAILABLE or not settings.LANGCHAIN_TRACING_V2:
        return
    
    try:
        # Add metadata to current trace context
        # This would be implemented with proper LangSmith context management
        logger.debug(f"Adding trace metadata: {metadata}")
    except Exception as e:
        logger.error(f"Error adding trace metadata: {e}")