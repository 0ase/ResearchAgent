"""Serialized IPC to a persistent, supervised native vector-store process."""
import multiprocessing
from multiprocessing.connection import wait
from pathlib import Path
import threading

from backend.config import settings
from backend.core.errors import AppError, VectorStoreUnavailable
from backend.core.observability import logger
from backend.rag.vector_worker import serve


class VectorWorker:
    def __init__(self, persist_dir: str, timeout: float, target=serve):
        self.persist_dir = persist_dir
        self.timeout = timeout
        self.target = target
        self._lock = threading.Lock()
        self._process = None
        self._connection = None
        self._failure = None

    def _start(self):
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=self.target, args=(child, self.persist_dir), daemon=True)
        try:
            process.start()
        except Exception:
            parent.close()
            child.close()
            raise
        child.close()
        self._process, self._connection = process, parent

    def _close(self):
        if self._connection is not None:
            self._connection.close()
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=5)
            if not self._process.is_alive():
                self._process.close()
        self._process = self._connection = None

    def call(self, collection: str, operation: str, **arguments):
        with self._lock:
            if self._failure is not None:
                raise VectorStoreUnavailable() from RuntimeError(self._failure)
            worker_id = None
            try:
                if self._process is None:
                    self._start()
                worker_id = self._process.pid
                logger.debug("vector_store.operation.started", extra={"fields": {
                    "worker_id": worker_id, "operation": operation, "collection": collection,
                }})
                self._connection.send({"collection": collection, "operation": operation, "arguments": arguments})
                ready = wait([self._connection, self._process.sentinel], timeout=self.timeout)
                if not ready:
                    raise TimeoutError(f"Vector operation {operation} exceeded {self.timeout}s")
                if self._connection not in ready:
                    self._process.join(timeout=1)
                    raise RuntimeError(f"Vector worker exited with code {self._process.exitcode}")
                response = self._connection.recv()
            except (OSError, EOFError, RuntimeError, TimeoutError) as exc:
                self._failure = str(exc)
                if self._process is not None:
                    self._process.join(timeout=0.1)
                    if self._process.exitcode is not None:
                        self._failure += f"; exit_code={self._process.exitcode}"
                self._close()
                logger.error("vector_store.worker.failed", extra={"fields": {
                    "operation": operation, "collection": collection, "worker_id": worker_id,
                    "error_code": "VECTOR_STORE_UNAVAILABLE", "reason": self._failure,
                }})
                raise VectorStoreUnavailable() from RuntimeError(self._failure)
            if not response["ok"]:
                raise AppError("VECTOR_OPERATION_FAILED", "向量库操作失败，请提供追踪编号排查。", 503) from RuntimeError(response["traceback"])
            return response["result"]

    def close(self):
        with self._lock:
            if self._connection is not None and self._process.is_alive():
                try:
                    self._connection.send(None)
                    self._process.join(timeout=2)
                except (OSError, EOFError):
                    pass
            self._close()


_worker = None
_worker_lock = threading.Lock()


def get_worker() -> VectorWorker:
    global _worker
    persist_dir = Path(settings.chroma_persist_dir)
    if not persist_dir.is_absolute():
        persist_dir = Path(__file__).resolve().parents[2] / persist_dir
    with _worker_lock:
        if _worker is None or _worker.persist_dir != str(persist_dir):
            if _worker is not None:
                _worker.close()
            _worker = VectorWorker(str(persist_dir), settings.vector_store_timeout_seconds)
        return _worker


def close_vector_store():
    global _worker
    with _worker_lock:
        if _worker is not None:
            _worker.close()
            _worker = None
