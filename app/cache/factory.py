"""
Cache factory for creating cache instances based on configuration
"""
from typing import Optional
from app.cache.base import CacheInterface
from app.cache.redis_cache import RedisCache
from app.cache.memory_cache import MemoryCache
from app.core.config import settings
from app.core.logging_config import get_logger


class CacheFactory:
    """Factory for creating cache instances"""
    
    @staticmethod
    def create_cache(backend: Optional[str] = None) -> CacheInterface:
        """Create cache instance based on backend type"""
        logger = get_logger("app.cache.factory")
        
        if backend is None:
            backend = settings.CACHE_BACKEND.lower()
        
        logger.info(f"Creating cache backend: {backend}")
        
        if backend == "redis":
            return RedisCache()
        elif backend == "memory":
            return MemoryCache()
        elif backend == "memcache":
            # TODO: Implement memcache when needed
            logger.warning("Memcache not implemented yet, falling back to memory cache")
            return MemoryCache()
        else:
            logger.warning(f"Unknown cache backend '{backend}', falling back to memory cache")
            return MemoryCache()


# Global cache instance
_cache_instance: Optional[CacheInterface] = None


async def get_cache() -> CacheInterface:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheFactory.create_cache()
    return _cache_instance


async def close_cache():
    """Close global cache instance"""
    global _cache_instance
    if _cache_instance and hasattr(_cache_instance, 'close'):
        await _cache_instance.close()
        _cache_instance = None


async def check_cache_health() -> dict:
    """Check cache health"""
    try:
        cache = await get_cache()
        return await cache.health_check()
    except Exception as e:
        logger = get_logger("app.cache.factory")
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "unhealthy",
            "backend": settings.CACHE_BACKEND,
            "error": str(e)
        }