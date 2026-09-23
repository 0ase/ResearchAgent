"""Own a launcher child tree without WMI or enumerating unrelated processes.

The wrapper joins its Windows job BEFORE creating children. Its non-inherited
job handle closes on every exit, including forced launcher termination.
https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
"""
import argparse
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import time


def own_windows_job():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class BasicLimits(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                    ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t),
                    ("max_ws", ctypes.c_size_t), ("active", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD)]

    class Limits(ctypes.Structure):
        _fields_ = [("basic", BasicLimits), ("io", ctypes.c_uint64 * 6),
                    ("memory", ctypes.c_size_t * 4)]

    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    job = kernel.CreateJobObjectW(None, None)
    limits = Limits()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    return kernel, job


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--stop-file", type=Path, required=True)
    parser.add_argument("--graceful", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    kernel, job = own_windows_job()
    parent = kernel.OpenProcess(0x00100000, False, args.parent_pid)
    if not parent:
        raise ctypes.WinError(ctypes.get_last_error())
    command = args.command[1:] if args.command[0] == "--" else args.command
    child = subprocess.Popen(command)
    stopping = None
    while child.poll() is None:
        if kernel.WaitForSingleObject(parent, 0) == 0 or args.stop_file.exists():
            if not args.graceful:
                os._exit(0)
            if stopping is None:
                args.stop_file.touch()
                stopping = time.monotonic()
            if time.monotonic() - stopping >= 15:
                os._exit(1)
        time.sleep(0.1)
    # os._exit closes the job and any lingering grandchildren, preserving status.
    os._exit(child.returncode)


if __name__ == "__main__":
    main()
