"""Atomic JSON snapshots and single-writer locks for local pipeline scripts."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile


@contextmanager
def file_lock(path):
    """Lock a stable sidecar file; the OS releases the lock on process exit."""
    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"Another process is using {path}; retry after it finishes") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path, text):
    """Replace text after a full write; read-modify-write callers also need a lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_json(path, data):
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_json_object(path):
    """Missing state is empty; unreadable or corrupt state must not be reset."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data
