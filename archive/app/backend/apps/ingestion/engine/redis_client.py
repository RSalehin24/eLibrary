"""Redis client factory for the Central Job Engine."""

import os
from redis import Redis

from .constants import DEFAULT_REDIS_URL


def get_redis_url():
    """Return the Redis URL from environment or default."""
    return os.environ.get("REDIS_URL", os.environ.get("CELERY_BROKER_URL", DEFAULT_REDIS_URL))


def create_redis_client(decode_responses=True, **kwargs):
    """
    Create and return a Redis client configured for the Engine.
    """
    url = get_redis_url()
    return Redis.from_url(
        url,
        decode_responses=decode_responses,
        socket_connect_timeout=kwargs.pop("socket_connect_timeout", 5),
        socket_timeout=kwargs.pop("socket_timeout", 5),
        **kwargs,
    )
