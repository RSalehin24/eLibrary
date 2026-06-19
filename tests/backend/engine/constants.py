"""Shared constants for engine tests - mirrors the engine's own constants."""

HEARTBEAT_TIMEOUT_SECONDS = 15

WORKER_KEY = "engine:worker:{hostname}"
PENDING_QUEUE = "engine:queue:pending"
ACTIVE_JOBS = "engine:active"
ENGINE_STATE = "engine:state"
ENGINE_STATE_KEY = "engine:state"

CH_WORKER_REGISTER = "engine:channel:worker:register"
CH_WORKER_HEARTBEAT = "engine:channel:worker:heartbeat"
CH_WORKER_DEREGISTER = "engine:channel:worker:deregister"
CH_WORKER_DONE = "engine:channel:worker:done"
CH_JOB_REQUEST = "engine:channel:job:request"
CH_JOB_ASSIGNED = "engine:channel:job:assigned"
CH_JOB_REASSIGNED = "engine:channel:job:reassigned"
CH_JOB_COMPLETED = "engine:channel:job:completed"
CH_WORKER_STALE = "engine:channel:worker:stale"

WORKER_STATUS_IDLE = "idle"
WORKER_STATUS_PROCESSING = "processing"
WORKER_STATUS_STALE = "stale"
WORKER_STATUS_OFFLINE = "offline"
