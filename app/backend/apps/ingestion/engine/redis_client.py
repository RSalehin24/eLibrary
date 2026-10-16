"""Redis client factory for the Central Job Engine."""

import os
from urllib.parse import urlsplit

from redis import Redis

from .constants import DEFAULT_REDIS_URL


def get_redis_url():
    """Keep Redis engine state separate from an AMQP task broker."""
    if explicit := os.environ.get("REDIS_URL"):
        return explicit
    for name in (
        "PROCESSING_CHECKPOINT_REDIS_URL",
        "CELERY_RESULT_BACKEND",
        "CELERY_BROKER_URL",
    ):
        value = os.environ.get(name, "")
        if urlsplit(value).scheme in {"redis", "rediss", "unix"}:
            return value
    return DEFAULT_REDIS_URL


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
