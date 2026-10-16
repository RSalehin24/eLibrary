import signal
from contextlib import contextmanager
from threading import Event


@contextmanager
def termination_event():
    stopped = Event()
    previous = {
        number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)
    }
    for number in previous:
        signal.signal(number, lambda *_: stopped.set())
    try:
        yield stopped
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
