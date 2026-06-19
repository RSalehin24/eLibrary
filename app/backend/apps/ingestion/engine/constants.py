"""Constants and configuration for the Central Job Engine."""

HEARTBEAT_TIMEOUT_SECONDS = 15
HEARTBEAT_CHECK_INTERVAL = 2.0
DEFAULT_REDIS_URL = "redis://redis:6379/0"

ENGINE_POLL_INTERVAL = 0.01

REDIS_SOCKET_TIMEOUT = 5
REDIS_SOCKET_CONNECT_TIMEOUT = 5

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

ALL_CHANNELS = [
    CH_WORKER_REGISTER,
    CH_WORKER_HEARTBEAT,
    CH_WORKER_DEREGISTER,
    CH_WORKER_DONE,
    CH_JOB_REQUEST,
]

WORKER_STATUS_IDLE = "idle"
WORKER_STATUS_PROCESSING = "processing"
WORKER_STATUS_STALE = "stale"
WORKER_STATUS_OFFLINE = "offline"

WORKER_STATUS_CHOICES = [
    WORKER_STATUS_IDLE,
    WORKER_STATUS_PROCESSING,
    WORKER_STATUS_STALE,
    WORKER_STATUS_OFFLINE,
]
