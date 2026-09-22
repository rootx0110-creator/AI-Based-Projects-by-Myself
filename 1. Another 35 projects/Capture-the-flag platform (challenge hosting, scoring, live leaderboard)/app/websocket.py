"""WebSocket event feed (live solves / joins) using simple-websocket + Flask-Sock.

Falls back gracefully: the frontend polls /api/feed when the socket is closed.
"""
import json

from flask import request
from flask_sock import Sock
from simple_websocket import ConnectionClosed

sock = Sock()


class FeedHub:
    """Tracks connected websocket clients and broadcasts events."""

    def __init__(self):
        self._clients = set()

    def register(self, ws) -> None:
        self._clients.add(ws)

    def unregister(self, ws) -> None:
        self._clients.discard(ws)

    def broadcast(self, payload: dict) -> int:
        data = json.dumps(payload)
        dead = []
        for ws in list(self._clients):
            try:
                ws.send(data)
            except ConnectionClosed:
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)
        return len(self._clients)


hub = FeedHub()


@sock.route("/ws/feed")
def feed_socket(ws):  # pragma: no cover - exercised in integration
    hub.register(ws)
    try:
        # Send a hello so the client knows the socket is live.
        ws.send(json.dumps({"kind": "hello", "at": "", "clients": len(hub._clients)}))
        while True:
            # Keep the connection open; ignore any client pings.
            msg = ws.receive(timeout=30)
            if msg is None:
                break
    except ConnectionClosed:
        pass
    finally:
        hub.unregister(ws)
