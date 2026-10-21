import pytest
from apps.ingestion.models import ProcessingJob


@pytest.mark.parametrize("fixture_name", ["engine", "engine_with_heartbeat_check"])
def test_engine_fixture_permits_startup_database_recovery(
    request, caplog, fixture_name
):
    engine = request.getfixturevalue(fixture_name)
    assert engine.is_running()
    ProcessingJob.objects.exists()
    assert not any(
        "Failed to recover stuck database" in record.message
        for record in caplog.records
    )
