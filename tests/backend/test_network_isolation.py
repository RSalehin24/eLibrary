import socket

import pytest


def test_non_live_tests_cannot_open_an_external_network_connection():
    with (
        socket.socket() as connection,
        pytest.raises(AssertionError, match="must mock external"),
    ):
        connection.connect(("192.0.2.1", 443))


def test_non_live_tests_cannot_resolve_external_hosts():
    with pytest.raises(AssertionError, match="must mock external DNS"):
        socket.getaddrinfo("external.example.test", 443)
