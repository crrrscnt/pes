import bcrypt
import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .config import settings

# Redis client
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'),
                          hashed_password.encode('utf-8'))


def create_session(user_id: str, role: str) -> str:
    """Create a new session and return session ID"""
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": user_id,
        "role": role,
        "created_at": datetime.utcnow().isoformat()
    }

    # Store session in Redis with TTL
    redis_client.setex(
        f"session:{session_id}",
        settings.session_ttl_seconds,
        json.dumps(session_data)
    )

    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data from Redis"""
    session_data = redis_client.get(f"session:{session_id}")
    if session_data:
        return json.loads(session_data)
    return None


def delete_session(session_id: str) -> bool:
    """Delete a session from Redis"""
    return redis_client.delete(f"session:{session_id}") > 0


def cleanup_expired_sessions():
    """Clean up expired sessions (Redis TTL handles this automatically)"""
    # This is handled by Redis TTL, but we could add manual cleanup if needed
    pass
