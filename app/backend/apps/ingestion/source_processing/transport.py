from urllib.parse import urlsplit

import requests

from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .authentication import load_source_authentication
from .pacing import wait_for_source_slot
from .policy import MAX_RESPONSE_BYTES, require_source_url, source_hosts


def read_bounded_response(response):
    content = bytearray()
    try:
        for part in response.iter_content(chunk_size=65536):
            content.extend(part)
            if len(content) > MAX_RESPONSE_BYTES:
                raise ExecutionFailure(
                    FailureKind.PERMANENT, "source_response_too_large"
                )
    finally:
        response.close()
    response._content = bytes(content)
    response._content_consumed = True
    return response


class ControlledSourceSession(requests.Session):
    def __init__(self, before_request, wait_for_slot=wait_for_source_slot):
        super().__init__()
        self.allowed_hosts = source_hosts()
        self.trust_env = False
        self.max_redirects = 5
        self.before_request = before_request
        self.wait_for_slot = wait_for_slot
        load_source_authentication(self)

    def send(self, request, **kwargs):
        require_source_url(request.url, self.allowed_hosts)
        self.before_request()
        self.wait_for_slot(urlsplit(request.url).hostname, self.before_request)
        kwargs["stream"] = True
        kwargs["timeout"] = (10, 60)
        kwargs["verify"] = True
        try:
            response = super().send(request, **kwargs)
            return read_bounded_response(response)
        except requests.RequestException:
            raise ExecutionFailure(
                FailureKind.TRANSIENT, "source_connection_unavailable"
            ) from None
