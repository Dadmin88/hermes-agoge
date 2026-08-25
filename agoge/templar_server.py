from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from threading import Event

from .templar_runtime import TemplarRuntime

_MAX_REQUEST_BYTES = 768 * 1024


def _handle_connection(conn: socket.socket, runtime: TemplarRuntime) -> None:
    """Handle one bounded client without allowing peer I/O failure to kill the daemon."""

    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_REQUEST_BYTES:
                chunks = []
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        if not chunks:
            return
        payload = b"".join(chunks).split(b"\n", 1)[0]
        try:
            request = json.loads(payload.decode("utf-8"))
            response = runtime.evaluate(request)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            return
        encoded = (
            json.dumps(response, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        conn.sendall(encoded)
    except OSError:
        # A caller may time out or disconnect after the request was accepted but
        # before inference completes. That client-local failure must never stop
        # the persistent evaluator from serving subsequent Fleet requests.
        return


def serve_unix(
    *,
    socket_path: Path,
    runtime: TemplarRuntime,
    backlog: int = 16,
    stop_event: Event | None = None,
) -> None:
    runtime.warmup()
    if socket_path.exists():
        socket_path.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(socket_path))
        os.chmod(socket_path, 0o600)
        server.listen(backlog)
        server.settimeout(0.25)
        while stop_event is None or not stop_event.is_set():
            try:
                conn, _ = server.accept()
            except TimeoutError:
                continue
            with conn:
                _handle_connection(conn, runtime)
    finally:
        server.close()
        if socket_path.exists():
            socket_path.unlink()
