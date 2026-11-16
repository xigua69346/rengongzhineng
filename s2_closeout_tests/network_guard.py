"""Forbid paid/external socket connections during the unchanged 84-test regression."""
import socket
import pytest
@pytest.fixture(autouse=True)
def local_only(monkeypatch):
    original=socket.socket.connect
    def connect(sock,address):
        if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','::1','localhost'):
            raise AssertionError('CLOSEOUT_EXTERNAL_NETWORK_FORBIDDEN')
        return original(sock,address)
    monkeypatch.setattr(socket.socket,'connect',connect)
