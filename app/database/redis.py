"""
Redis service for session state and caching
"""
import redis.asyncio as redis
import json
from typing import Optional, Any
from app.config import settings
from app.schemas import UserProfile


class RedisService:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        self.client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self):
        if self.client:
            await self.client.close()
    
    async def set_session(self, user_id: str, data: dict, expire: int = 86400):
        if self.client:
            await self.client.setex(
                f"session:{user_id}",
                expire,
                json.dumps(data, default=str)
            )
    
    async def get_session(self, user_id: str) -> Optional[dict]:
        if self.client:
            data = await self.client.get(f"session:{user_id}")
            if data:
                return json.loads(data)
        return None
    
    async def delete_session(self, user_id: str):
        if self.client:
            await self.client.delete(f"session:{user_id}")
    
    async def set_user_profile(self, user_id: str, profile: UserProfile, expire: int = 604800):
        if self.client:
            profile_dict = profile.model_dump(mode="json")
            await self.client.setex(
                f"profile:{user_id}",
                expire,
                json.dumps(profile_dict, default=str)
            )
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        if self.client:
            data = await self.client.get(f"profile:{user_id}")
            if data:
                profile_dict = json.loads(data)
                return UserProfile(**profile_dict)
        return None
    
    async def cache_task(self, task_id: str, data: dict, expire: int = 3600):
        if self.client:
            await self.client.setex(
                f"task:{task_id}",
                expire,
                json.dumps(data, default=str)
            )
    
    async def get_cached_task(self, task_id: str) -> Optional[dict]:
        if self.client:
            data = await self.client.get(f"task:{task_id}")
            if data:
                return json.loads(data)
        return None
    
    async def increment_streak(self, user_id: str) -> int:
        if self.client:
            key = f"streak:{user_id}"
            streak = await self.client.incr(key)
            await self.client.expire(key, 86400)
            return streak
        return 0
    
    async def get_streak(self, user_id: str) -> int:
        if self.client:
            streak = await self.client.get(f"streak:{user_id}")
            return int(streak) if streak else 0
        return 0
    
    async def set_daily_boost(self, user_id: str, multiplier: float, expire: int = 86400):
        if self.client:
            await self.client.setex(
                f"boost:{user_id}",
                expire,
                str(multiplier)
            )
    
    async def get_daily_boost(self, user_id: str) -> Optional[float]:
        if self.client:
            boost = await self.client.get(f"boost:{user_id}")
            return float(boost) if boost else None
        return None


redis_service = RedisService()
