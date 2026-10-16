from apps.processing.jobs.failures import AttemptFailure, FailureKind


class ExecutionFailure(RuntimeError):
    def __init__(self, kind: FailureKind, code: str):
        self.failure = AttemptFailure(kind, code)
        super().__init__(code)
