"""Rate limiting setup using slowapi (Redis-backed for distributed rate limiting)"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory by default; for production use Redis as storage
# For distributed setup: storage_uri="redis://redis:6379/1"
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE", REDIS_URL.replace("/0", "/1"))


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=RATE_LIMIT_STORAGE,
    default_limits=["200/minute"],  # global default
)
