"""
Chat history management for NL2SQL agent
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from app.cache import get_cache
from app.core.config import settings
from app.core.logging_config import get_logger


class ChatHistoryManager:
    """Manages chat history for agent sessions using Redis cache"""
    
    def __init__(self, max_cnt: int = 5):
        self.logger = get_logger("app.ai.chat_history")
        self.cache = None
        self.max_cnt = max_cnt * 2
    
    async def _get_cache(self):
        """Get cache instance"""
        if self.cache is None:
            self.cache = await get_cache()
        return self.cache
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"chat_history:{session_id}"
    
    def _get_session_stats_key(self, session_id: str) -> str:
        """Generate Redis key for session stats"""
        return f"chat_stats:{session_id}"
    
    async def create_session(self) -> str:
        """Create new chat session and return session ID"""
        session_id = str(uuid.uuid4())
        
        # Initialize session stats
        stats = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message_count": 0,
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        
        cache = await self._get_cache()
        await cache.set(
            self._get_session_stats_key(session_id), 
            stats, 
            ttl=settings.CHAT_HISTORY_TTL
        )
        
        self.logger.info(f"Created new chat session: {session_id}")
        return session_id
    
    async def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add message to chat history"""
        try:
            cache = await self._get_cache()
            
            message = {
                "id": str(uuid.uuid4()),
                "role": role,  # "user", "assistant", "system"
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {}
            }
            
            # Get current history
            history_key = self._get_session_key(session_id)
            current_history = await cache.get(history_key) or []
            
            # Add new message
            current_history.append(message)
            
            # Keep only last max_cnt messages to prevent memory issues
            if len(current_history) > self.max_cnt:
                current_history = current_history[-self.max_cnt:]
            
            # Save updated history
            await cache.set(history_key, current_history)
            
            # Update session stats
            await self._update_session_stats(session_id)
            
            self.logger.debug(f"Added {role} message to session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding message to session {session_id}: {e}")
            return False
    
    async def get_history(
        self, 
        session_id: str, 
        limit: Optional[int] = None,
        include_system: bool = False
    ) -> List[Dict[str, Any]]:
        """Get chat history for session"""
        try:
            cache = await self._get_cache()
            history_key = self._get_session_key(session_id)
            history = await cache.get(history_key) or []
            
            # Filter out system messages if requested
            if not include_system:
                history = [msg for msg in history if msg.get("role") != "system"]
            
            # Apply limit
            if limit:
                history = history[-limit:]
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting history for session {session_id}: {e}")
            return []
    
    async def get_conversation_context(self, session_id: str, limit: int = 10) -> str:
        """Get formatted conversation context for the agent"""
        history = await self.get_history(session_id, limit=limit)
        
        if not history:
            return ""
        
        context_parts = []
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            context_parts.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(context_parts)
    
    async def clear_history(self, session_id: str) -> bool:
        """Clear chat history for session"""
        try:
            cache = await self._get_cache()
            
            history_key = self._get_session_key(session_id)
            stats_key = self._get_session_stats_key(session_id)
            
            await cache.delete(history_key)
            await cache.delete(stats_key)
            
            self.logger.info(f"Cleared history for session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing history for session {session_id}: {e}")
            return False
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            cache = await self._get_cache()
            stats_key = self._get_session_stats_key(session_id)
            stats = await cache.get(stats_key)
            
            if not stats:
                return {"error": "Session not found"}
            
            # Add current message count
            history = await self.get_history(session_id)
            stats["current_message_count"] = len(history)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats for session {session_id}: {e}")
            return {"error": str(e)}
    
    async def _update_session_stats(self, session_id: str):
        """Update session statistics"""
        try:
            cache = await self._get_cache()
            stats_key = self._get_session_stats_key(session_id)
            stats = await cache.get(stats_key) or {}
            
            stats["last_activity"] = datetime.now(timezone.utc).isoformat()
            stats["message_count"] = stats.get("message_count", 0) + 1
            
            await cache.set(stats_key, stats)
            
        except Exception as e:
            self.logger.error(f"Error updating stats for session {session_id}: {e}")
    
    async def list_active_sessions(self, limit: int = 100) -> List[str]:
        """List active session IDs"""
        try:
            cache = await self._get_cache()
            # This is a simplified implementation
            # In production, you might want to maintain a separate index
            
            # Get all chat_stats keys
            redis = await cache._get_redis()
            keys = await redis.keys("chat_stats:*")
            
            session_ids = [key.decode().split(":", 1)[1] for key in keys[:limit]]
            return session_ids
            
        except Exception as e:
            self.logger.error(f"Error listing active sessions: {e}")
            return []