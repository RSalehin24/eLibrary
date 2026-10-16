import requests
from requests.adapters import BaseAdapter


def fixture_request_slot(host, boundary):
    # Fixture pages do not consume production source bandwidth; pacing has independent tests.
    return None


class FixtureAdapter(BaseAdapter):
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def send(self, request, **options):
        self.calls.append((request, options))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        status, headers, body = reply
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers)
        response._content, response._content_consumed = body, True
        response.url, response.request, response.encoding = (
            request.url,
            request,
            "utf-8",
        )
        return response

    def close(self):
        pass
