"""
In-memory cache implementation for development/testing
"""
import time
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import asyncio
from app.cache.base import CacheInterface
from app.core.config import settings
from app.core.logging_config import get_logger


class MemoryCache(CacheInterface):
    """In-memory cache implementation with TTL support"""
    
    def __init__(self):
        self.logger = get_logger("app.cache.memory")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.logger.info("Memory cache initialized")
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if item is expired"""
        if "expires_at" not in item:
            return False
        return time.time() > item["expires_at"]
    
    def _cleanup_expired(self):
        """Remove expired items"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self._cache.items()
            if "expires_at" in item and current_time > item["expires_at"]
        ]
        for key in expired_keys:
            del self._cache[key]
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        async with self._lock:
            self._cleanup_expired()
            
            if key not in self._cache:
                return None
            
            item = self._cache[key]
            if self._is_expired(item):
                del self._cache[key]
                return None
            
            return item["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL in seconds"""
        async with self._lock:
            if ttl is None:
                ttl = settings.CACHE_TTL
            
            item = {
                "value": value,
                "created_at": time.time()
            }
            
            if ttl > 0:
                item["expires_at"] = time.time() + ttl
            
            self._cache[key] = item
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        async with self._lock:
            self._cleanup_expired()
            
            if key not in self._cache:
                return False
            
            item = self._cache[key]
            if self._is_expired(item):
                del self._cache[key]
                return False
            
            return True
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache, optionally by pattern"""
        async with self._lock:
            if pattern:
                import fnmatch
                keys_to_delete = [
                    key for key in self._cache.keys()
                    if fnmatch.fnmatch(key, pattern)
                ]
                for key in keys_to_delete:
                    del self._cache[key]
                return len(keys_to_delete)
            else:
                count = len(self._cache)
                self._cache.clear()
                return count
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        for key, value in mapping.items():
            await self.set(key, value, ttl)
        return True
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        async with self._lock:
            current_value = await self.get(key)
            if current_value is None:
                new_value = amount
            else:
                try:
                    new_value = int(current_value) + amount
                except (ValueError, TypeError):
                    new_value = amount
            
            await self.set(key, new_value)
            return new_value
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        async with self._lock:
            if key not in self._cache:
                return False
            
            item = self._cache[key]
            if self._is_expired(item):
                del self._cache[key]
                return False
            
            if ttl > 0:
                item["expires_at"] = time.time() + ttl
            elif "expires_at" in item:
                del item["expires_at"]
            
            return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check memory cache health and return status"""
        try:
            start_time = time.time()
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            await self.set(test_key, test_value, ttl=10)
            result = await self.get(test_key)
            
            if result != test_value:
                raise Exception("GET operation failed")
            
            await self.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            # Get cache stats
            async with self._lock:
                self._cleanup_expired()
                total_keys = len(self._cache)
            
            return {
                "status": "healthy",
                "backend": "memory",
                "response_time_ms": round(response_time, 2),
                "total_keys": total_keys,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Memory cache health check failed: {e}")
            return {
                "status": "unhealthy",
                "backend": "memory",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_info(self) -> Dict[str, Any]:
        """Get memory cache backend information"""
        async with self._lock:
            self._cleanup_expired()
            
            total_keys = len(self._cache)
            total_size = sum(len(str(item)) for item in self._cache.values())
            
            return {
                "backend": "memory",
                "total_keys": total_keys,
                "estimated_size_bytes": total_size,
                "implementation": "dict",
                "features": ["ttl", "cleanup", "pattern_matching"]
            }