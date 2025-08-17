"""
Decorators for method-level tracing
"""
import functools
import asyncio
from typing import Any, Callable

try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(func):
        return func

from app.core.logging_config import get_logger

logger = get_logger("app.observability.decorators")


def trace_method(name: str = None, capture_args: bool = True, capture_result: bool = True):
    """Decorator to trace method calls"""
    def decorator(func: Callable) -> Callable:
        if not LANGSMITH_AVAILABLE:
            return func
        
        trace_name = name or f"{func.__module__}.{func.__qualname__}"
        
        @traceable(name=trace_name)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                inputs = {}
                if capture_args:
                    # Capture method arguments (skip 'self')
                    if args:
                        inputs['args'] = [str(arg)[:100] for arg in args[1:]]  # Skip self, truncate
                    if kwargs:
                        inputs['kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}
                
                result = func(*args, **kwargs)
                
                if capture_result:
                    outputs = {
                        "result_type": type(result).__name__,
                        "result": str(result)[:200] if result is not None else None
                    }
                
                return result
                
            except Exception as e:
                logger.error(f"Error in traced method {trace_name}: {e}")
                raise
                
        return wrapper
    return decorator


def trace_async_method(name: str = None, capture_args: bool = True, capture_result: bool = True):
    """Decorator to trace async method calls"""
    def decorator(func: Callable) -> Callable:
        if not LANGSMITH_AVAILABLE:
            return func
        
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("trace_async_method can only be used on async functions")
        
        trace_name = name or f"{func.__module__}.{func.__qualname__}"
        
        @traceable(name=trace_name)
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                inputs = {}
                if capture_args:
                    # Capture method arguments (skip 'self')
                    if args:
                        inputs['args'] = [str(arg)[:100] for arg in args[1:]]  # Skip self, truncate
                    if kwargs:
                        inputs['kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}
                
                result = await func(*args, **kwargs)
                
                if capture_result:
                    outputs = {
                        "result_type": type(result).__name__,
                        "result": str(result)[:200] if result is not None else None
                    }
                
                return result
                
            except Exception as e:
                logger.error(f"Error in traced async method {trace_name}: {e}")
                raise
                
        return wrapper
    return decorator


def trace_class_methods(cls):
    """Class decorator to trace all public methods"""
    if not LANGSMITH_AVAILABLE:
        return cls
    
    for attr_name in dir(cls):
        if attr_name.startswith('_'):
            continue
            
        attr = getattr(cls, attr_name)
        if callable(attr):
            if asyncio.iscoroutinefunction(attr):
                traced_method = trace_async_method(f"{cls.__name__}.{attr_name}")(attr)
            else:
                traced_method = trace_method(f"{cls.__name__}.{attr_name}")(attr)
            setattr(cls, attr_name, traced_method)
    
    return cls