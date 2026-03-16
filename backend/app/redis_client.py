import logging
import redis
from .config import settings

logger = logging.getLogger(__name__)

# Redis client instance. Wrap creation to log failures early instead of crashing later.
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    logger.exception("Failed to create Redis client from URL: %s",
                     settings.redis_url)
    redis_client = None


def get_redis():
    """Dependency to get Redis client"""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client
