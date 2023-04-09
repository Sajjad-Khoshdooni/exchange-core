from uuid import uuid4

from django.utils import timezone


class SocketClient:

    def __init__(self, socket, subscribe_request):
        self.id = socket.id
        self.last_ping = timezone.now()
        self.socket = socket
        self.subscribe_request = subscribe_request

    def __eq__(self, other):
        if isinstance(other, SocketClient):
            return self.id == other.id
        return NotImplemented

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.id

    def update_ping(self):
        self.last_ping = timezone.now()
