

CATALOG_AUTOMATION_MATRIX_CASES = [
    pytest.param(
        {
            "initial": {
                "sync_status": "not_started",
                "request_creation_status": "not_started",
                "top_status": ProcessingSyncStatus.IDLE,
                "sync_owner": "catalog_automation",
            },
            "action": {"path": "/api/processing/automation/catalog/run/"},
            "expected": {
                "status": "syncing",
                "phase": "sync",
                "run_mode": "catalog_automation",
                "sync_status": "running",
                "request_creation_status": "not_started",
                "sync_owner": "catalog_automation",
                "request_creation": None,
            },
        },
        id="automation-not_started-not_started",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "running",
                "request_creation_status": "not_started",
                "top_status": ProcessingSyncStatus.SYNCING,
                "sync_owner": "catalog_automation",
            },
            "action": {"path": "/api/processing/sync/catalog/pause/"},
            "expected": {
                "status": "pausing",
                "phase": "sync",
                "run_mode": "catalog_automation",
                "sync_status": "pausing",
                "request_creation_status": "not_started",
                "sync_owner": "catalog_automation",
                "request_creation": None,
            },
        },
        id="automation-running-not_started",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "pausing",
                "request_creation_status": "not_started",
                "top_status": ProcessingSyncStatus.PAUSING,
                "sync_owner": "catalog_automation",
            },
            "action": {"path": "/api/processing/automation/catalog/run/"},
            "expected": {
                "status": "pausing",
                "phase": "sync",
                "run_mode": "catalog_automation",
                "sync_status": "pausing",
                "request_creation_status": "not_started",
                "sync_owner": "catalog_automation",
                "request_creation": None,
            },
        },
        id="automation-pausing-not_started",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "paused",
                "request_creation_status": "not_started",
                "top_status": ProcessingSyncStatus.PAUSED,
                "sync_owner": "catalog_automation",
            },
            "action": {
                "path": "/api/processing/sync/catalog/resume/",
                "body": {"runMode": "catalog_automation"},
            },
            "expected": {
                "status": "syncing",
                "phase": "sync",
                "run_mode": "catalog_automation",
                "sync_status": "running",
                "request_creation_status": "not_started",
                "sync_owner": "catalog_automation",
                "request_creation": None,
            },
        },
        id="automation-paused-not_started",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "completed",
                "request_creation_status": "not_started",
                "top_status": ProcessingSyncStatus.IDLE,
                "sync_owner": "manual",
            },
            "action": {"path": "/api/processing/automation/catalog/run/"},
            "expected": {
                "status": "syncing",
                "phase": "request_creation",
                "run_mode": "catalog_automation",
                "sync_status": "completed",
                "request_creation_status": "running",
                "sync_owner": "manual",
                "request_creation_owner": "catalog_automation",
                "request_creation": {
                    **catalog_matrix_request_creation_payload(),
                    "lastRecordId": "",
                    "processedCount": 0,
                    "createdCount": 0,
                },
            },
        },
        id="automation-completed-not_started",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "completed",
                "request_creation_status": "running",
                "top_status": ProcessingSyncStatus.SYNCING,
                "sync_owner": "manual",
            },
            "action": {"path": "/api/processing/sync/catalog/pause/"},
            "expected": {
                "status": "pausing",
                "phase": "request_creation",
                "run_mode": "catalog_automation",
                "sync_status": "completed",
                "request_creation_status": "pausing",
                "sync_owner": "manual",
                "request_creation_owner": "catalog_automation",
                "request_creation": catalog_matrix_request_creation_payload(),
            },
        },
        id="automation-completed-running",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "completed",
                "request_creation_status": "pausing",
                "top_status": ProcessingSyncStatus.PAUSING,
                "sync_owner": "manual",
            },
            "action": {"path": "/api/processing/automation/catalog/run/"},
            "expected": {
                "status": "pausing",
                "phase": "request_creation",
                "run_mode": "catalog_automation",
                "sync_status": "completed",
                "request_creation_status": "pausing",
                "sync_owner": "manual",
                "request_creation_owner": "catalog_automation",
                "request_creation": catalog_matrix_request_creation_payload(),
            },
        },
        id="automation-completed-pausing",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "completed",
                "request_creation_status": "paused",
                "top_status": ProcessingSyncStatus.PAUSED,
                "sync_owner": "manual",
            },
            "action": {
                "path": "/api/processing/sync/catalog/resume/",
                "body": {"runMode": "catalog_automation"},
            },
            "expected": {
                "status": "syncing",
                "phase": "request_creation",
                "run_mode": "catalog_automation",
                "sync_status": "completed",
                "request_creation_status": "running",
                "sync_owner": "manual",
                "request_creation_owner": "catalog_automation",
                "request_creation": catalog_matrix_request_creation_payload(),
            },
        },
        id="automation-completed-paused",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "completed",
                "request_creation_status": "completed",
                "top_status": ProcessingSyncStatus.IDLE,
                "sync_owner": "manual",
                "request_creation": {},
            },
            "action": {"path": "/api/processing/automation/catalog/run/"},
            "expected": {
                "status": "syncing",
                "phase": "sync",
                "run_mode": "catalog_automation",
                "sync_status": "running",
                "request_creation_status": "not_started",
                "sync_owner": "catalog_automation",
                "request_creation": None,
            },
        },
        id="automation-completed-completed",
    ),
    pytest.param(
        {
            "initial": {
                "sync_status": "paused",
                "request_creation_status": "paused",
                "top_status": ProcessingSyncStatus.PAUSED,
                "sync_owner": "manual",
            },
            "action": {
                "path": "/api/processing/sync/catalog/resume/",
                "body": {"runMode": "catalog_automation"},
            },
            "expected": {
                "status": "syncing",
                "phase": "request_creation",
                "run_mode": "catalog_automation",
                "sync_status": "paused",
                "request_creation_status": "running",
                "sync_owner": "manual",
                "request_creation_owner": "catalog_automation",
                "request_creation": catalog_matrix_request_creation_payload(),
            },
        },
        id="automation-paused-paused",
    ),
]
