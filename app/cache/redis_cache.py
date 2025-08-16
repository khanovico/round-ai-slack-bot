"""
Redis cache implementation with scalability features
"""
import json
import pickle
from typing import Any, Optional, Dict, List, Union
import redis.asyncio as redis
from app.cache.base import CacheInterface
from app.core.config import settings
from app.core.logging_config import get_logger


class RedisCache(CacheInterface):
    """Redis-based cache implementation with connection pooling and failover"""
    
    def __init__(self):
        self.logger = get_logger("app.cache.redis")
        self._redis: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection with lazy initialization"""
        if self._redis is None:
            try:
                # Create connection pool for scalability
                self._pool = redis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                )
                self._redis = redis.Redis(connection_pool=self._pool)
                
                # Test connection
                await self._redis.ping()
                self.logger.info("Redis connection established successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._redis
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first for better interoperability
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            redis = await self._get_redis()
            data = await redis.get(key)
            
            if data is None:
                return None
            
            return self._deserialize(data)
            
        except Exception as e:
            self.logger.error(f"Error getting key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL in seconds"""
        try:
            redis = await self._get_redis()
            data = self._serialize(value)
            
            if ttl is None:
                ttl = settings.CACHE_TTL
            
            await redis.setex(key, ttl, data)
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        try:
            redis = await self._get_redis()
            result = await redis.delete(key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Error deleting key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            redis = await self._get_redis()
            result = await redis.exists(key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Error checking existence of key '{key}': {e}")
            return False
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache, optionally by pattern"""
        try:
            redis = await self._get_redis()
            
            if pattern:
                keys = await redis.keys(pattern)
                if keys:
                    return await redis.delete(*keys)
                return 0
            else:
                await redis.flushdb()
                return 1
                
        except Exception as e:
            self.logger.error(f"Error clearing cache with pattern '{pattern}': {e}")
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        try:
            redis = await self._get_redis()
            
            if not keys:
                return {}
            
            values = await redis.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting multiple keys: {e}")
            return {}
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        try:
            redis = await self._get_redis()
            
            if not mapping:
                return True
            
            if ttl is None:
                ttl = settings.CACHE_TTL
            
            # Use pipeline for better performance
            pipe = redis.pipeline()
            
            for key, value in mapping.items():
                data = self._serialize(value)
                pipe.setex(key, ttl, data)
            
            await pipe.execute()
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting multiple keys: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            redis = await self._get_redis()
            return await redis.incr(key, amount)
            
        except Exception as e:
            self.logger.error(f"Error incrementing key '{key}': {e}")
            return 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        try:
            redis = await self._get_redis()
            result = await redis.expire(key, ttl)
            return result
            
        except Exception as e:
            self.logger.error(f"Error setting TTL for key '{key}': {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health and return status"""
        try:
            import time
            start_time = time.time()
            
            redis = await self._get_redis()
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            # Test SET
            await redis.set(test_key, test_value, ex=10)
            
            # Test GET
            result = await redis.get(test_key)
            if result.decode() != test_value:
                raise Exception("GET operation failed")
            
            # Test DELETE
            await redis.delete(test_key)
            
            # Get Redis info
            info = await redis.info()
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy",
                "backend": "redis",
                "response_time_ms": round(response_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "redis_version": info.get("redis_version", "unknown"),
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "backend": "redis",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis backend information"""
        try:
            redis = await self._get_redis()
            info = await redis.info()
            
            return {
                "backend": "redis",
                "version": info.get("redis_version", "unknown"),
                "mode": info.get("redis_mode", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_system_memory": info.get("total_system_memory_human", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "keyspace": {k: v for k, v in info.items() if k.startswith("db")},
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Redis info: {e}")
            return {
                "backend": "redis",
                "error": str(e)
            }
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.aclose()
        if self._pool:
            await self._pool.aclose()
        self.logger.info("Redis connection closed")


