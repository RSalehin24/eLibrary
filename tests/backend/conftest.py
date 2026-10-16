import ipaddress
import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_service_settings(settings):
    settings.SOURCE_SITE_HOST = "www.example.com"
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_RESULT_BACKEND = "cache+memory://"
    settings.PROCESSING_CHECKPOINT_REDIS_URL = ""


@pytest.fixture(autouse=True)
def isolate_test_network(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return
    connect = socket.socket.connect
    resolve = socket.getaddrinfo

    def local_address(host):
        if host in {None, "localhost"}:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def resolve_locally(host, *arguments, **keywords):
        if not local_address(host):
            raise AssertionError("Non-live tests must mock external DNS lookups.")
        return resolve(host, *arguments, **keywords)

    def connect_locally(connection, address):
        if connection.family in {socket.AF_INET, socket.AF_INET6} and not local_address(
            address[0]
        ):
            raise AssertionError(
                "Non-live tests must mock external network connections."
            )
        return connect(connection, address)

    monkeypatch.setattr(socket.socket, "connect", connect_locally)
    monkeypatch.setattr(socket, "getaddrinfo", resolve_locally)
