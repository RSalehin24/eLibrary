from unittest.mock import patch

import pytest
from apps.ingestion.engine.engine import JobEngine


@pytest.mark.parametrize(
    ("entry", "work"),
    [("_event_loop", "_process_events"), ("_stale_check_loop", "_check_stale_workers")],
)
def test_engine_threads_close_database_connections_even_on_failure(entry, work):
    engine = JobEngine(redis=object())
    with (
        patch.object(engine, work, side_effect=RuntimeError("thread failed")),
        patch("django.db.connections.close_all") as close,
        pytest.raises(RuntimeError, match="thread failed"),
    ):
        getattr(engine, entry)()
    close.assert_called_once_with()
