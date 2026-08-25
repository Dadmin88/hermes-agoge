from __future__ import annotations

import json
import os
import socket
from pathlib import Path

from .templar_runtime import TemplarRuntime

_MAX_REQUEST_BYTES = 768 * 1024


def serve_unix(
    *,
    socket_path: Path,
    runtime: TemplarRuntime,
    backlog: int = 16,
) -> None:
    if socket_path.exists():
        socket_path.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(socket_path))
        os.chmod(socket_path, 0o600)
        server.listen(backlog)
        while True:
            conn, _ = server.accept()
            with conn:
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
                    continue
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
                    continue
                encoded = (
                    json.dumps(response, sort_keys=True, separators=(",", ":"))
                    + "\n"
                ).encode("utf-8")
                conn.sendall(encoded)
    finally:
        server.close()
        if socket_path.exists():
            socket_path.unlink()
