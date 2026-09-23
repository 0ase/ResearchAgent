"""Launcher-owned shutdown file; no public HTTP shutdown endpoint."""
import argparse
import asyncio
import ctypes
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn


async def serve(port, stop_file, parent_pid):
    server = uvicorn.Server(uvicorn.Config("backend.main:app", host="127.0.0.1", port=port))
    parent_handle = None
    if os.name == "nt" and parent_pid:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        parent_handle = kernel.OpenProcess(0x00100000, False, parent_pid)

    async def watch():
        while not server.should_exit:
            parent_gone = parent_handle and kernel.WaitForSingleObject(parent_handle, 0) == 0
            if parent_gone or await asyncio.to_thread(stop_file.exists):
                server.should_exit = True
                return
            await asyncio.sleep(0.2)

    monitor = asyncio.create_task(watch())
    try:
        await server.serve()
        if not server.started:
            raise SystemExit(1)
    finally:
        monitor.cancel()
        await asyncio.gather(monitor, return_exceptions=True)
        if parent_handle:
            kernel.CloseHandle(parent_handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--stop-file", type=Path, required=True)
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(serve(args.port, args.stop_file, args.parent_pid))
