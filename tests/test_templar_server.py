from __future__ import annotations

import json
import socket
import stat
import threading
import time
from pathlib import Path

from agoge.templar_server import serve_unix


class FakeRuntime:
    def evaluate(self, request: object) -> dict[str, object]:
        assert isinstance(request, dict)
        return {"ok": True, "request_id": request["request_id"]}


def test_unix_server_is_private_responds_and_cleans_up(tmp_path: Path) -> None:
    socket_path = tmp_path / "templar.sock"
    stop_event = threading.Event()
    thread = threading.Thread(
        target=serve_unix,
        kwargs={
            "socket_path": socket_path,
            "runtime": FakeRuntime(),  # type: ignore[arg-type]
            "stop_event": stop_event,
        },
        daemon=True,
    )
    thread.start()
    for _ in range(50):
        if socket_path.exists():
            break
        time.sleep(0.01)
    assert socket_path.exists()
    assert stat.S_IMODE(socket_path.stat().st_mode) == 0o600

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(str(socket_path))
    client.sendall(b'{"request_id":"r1"}\n')
    response = b""
    while b"\n" not in response:
        response += client.recv(4096)
    client.close()
    assert json.loads(response.split(b"\n", 1)[0]) == {
        "ok": True,
        "request_id": "r1",
    }

    stop_event.set()
    thread.join(timeout=1.0)
    assert not thread.is_alive()
    assert not socket_path.exists()
