"""Chroma runs here so native library faults cannot terminate FastAPI."""
import traceback


def serve(connection, persist_dir: str):
    # Import native dependencies only inside this child process.
    import chromadb
    from chromadb.config import Settings

    client = None
    collections = {}
    try:
        while True:
            request = connection.recv()
            if request is None:
                return
            try:
                if client is None:
                    client = chromadb.PersistentClient(
                        path=persist_dir, settings=Settings(anonymized_telemetry=False),
                    )
                name = request["collection"]
                if name not in collections:
                    # The application supplies DashScope embeddings explicitly.
                    collections[name] = client.get_or_create_collection(
                        name=name, embedding_function=None,
                    )
                operation = request["operation"]
                if operation not in {"get", "query", "add", "count"}:
                    raise ValueError(f"Unsupported vector operation: {operation}")
                result = getattr(collections[name], operation)(**request["arguments"])
                connection.send({"ok": True, "result": result})
            except Exception:
                connection.send({"ok": False, "traceback": traceback.format_exc()})
    except EOFError:
        return
    finally:
        connection.close()
