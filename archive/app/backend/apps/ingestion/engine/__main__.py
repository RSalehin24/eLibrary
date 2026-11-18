"""
Entry point for running the Central Job Engine standalone.

Usage:
    python -m apps.ingestion.engine
"""

import logging
import signal
import sys

from .engine import JobEngine
from .redis_client import create_redis_client


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("engine")

    redis = create_redis_client()
    engine = JobEngine(redis)

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        engine.stop()
        redis.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("Starting Central Job Engine...")
    engine.start()

    signal.pause()


if __name__ == "__main__":
    main()
