from __future__ import annotations

import json
import socket
import stat
import threading
import time
from pathlib import Path

from agoge.templar_server import serve_unix


class FakeRuntime:
    def __init__(self) -> None:
        self.warmed = False

    def warmup(self) -> None:
        self.warmed = True

    def evaluate(self, request: object) -> dict[str, object]:
        assert self.warmed
        assert isinstance(request, dict)
        return {"ok": True, "request_id": request["request_id"]}


class DisconnectRuntime:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.warmed = False

    def warmup(self) -> None:
        self.warmed = True

    def evaluate(self, request: object) -> dict[str, object]:
        assert self.warmed
        assert isinstance(request, dict)
        if request["request_id"] == "disconnect":
            self.started.set()
            assert self.release.wait(timeout=1.0)
        return {"ok": True, "request_id": request["request_id"]}


class FailingWarmupRuntime:
    def warmup(self) -> None:
        raise RuntimeError("warmup failed")


def test_warmup_failure_never_publishes_readiness_socket(tmp_path: Path) -> None:
    socket_path = tmp_path / "templar.sock"
    try:
        serve_unix(
            socket_path=socket_path,
            runtime=FailingWarmupRuntime(),  # type: ignore[arg-type]
        )
    except RuntimeError as exc:
        assert str(exc) == "warmup failed"
    else:  # pragma: no cover - defensive
        raise AssertionError("Templar server unexpectedly survived failed warmup")
    assert not socket_path.exists()


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


def test_client_disconnect_does_not_kill_persistent_server(tmp_path: Path) -> None:
    socket_path = tmp_path / "templar.sock"
    stop_event = threading.Event()
    runtime = DisconnectRuntime()
    thread = threading.Thread(
        target=serve_unix,
        kwargs={
            "socket_path": socket_path,
            "runtime": runtime,  # type: ignore[arg-type]
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

    first = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    first.connect(str(socket_path))
    first.sendall(b'{"request_id":"disconnect"}\n')
    assert runtime.started.wait(timeout=1.0)
    first.shutdown(socket.SHUT_RDWR)
    first.close()
    runtime.release.set()

    second = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    for _ in range(50):
        try:
            second.connect(str(socket_path))
            break
        except ConnectionRefusedError:
            time.sleep(0.01)
    else:
        raise AssertionError("Templar server did not survive disconnected client")
    second.sendall(b'{"request_id":"survivor"}\n')
    response = b""
    while b"\n" not in response:
        response += second.recv(4096)
    second.close()
    assert json.loads(response.split(b"\n", 1)[0]) == {
        "ok": True,
        "request_id": "survivor",
    }

    stop_event.set()
    thread.join(timeout=1.0)
    assert not thread.is_alive()
    assert not socket_path.exists()
