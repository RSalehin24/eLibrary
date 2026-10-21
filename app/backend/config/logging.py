def logging_settings(level: str) -> dict[str, object]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
            }
        },
        "root": {"handlers": ["console"], "level": level},
    }
