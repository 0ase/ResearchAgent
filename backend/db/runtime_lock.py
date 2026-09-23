"""One backend owner per canonical SQLite path; the OS releases crash locks."""
import os
from pathlib import Path


class DatabaseInUseError(RuntimeError):
    pass


class DatabaseRuntimeLock:
    def __init__(self, database_path):
        from backend.db.connection import validate_database_path
        resolved = validate_database_path(database_path)
        self.path = resolved.with_suffix(resolved.suffix + ".lock")
        self._file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+b")
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise DatabaseInUseError("DATABASE_IN_USE: another backend owns this database") from exc
        self._file = handle
        return self

    def __exit__(self, *_):
        if self._file:
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file, fcntl.LOCK_UN)
            self._file.close()
            self._file = None
