from __future__ import annotations

import re

from backend.api.schemas.tasks import TaskStatus

ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {
        TaskStatus.RUNNING,
        TaskStatus.CANCELLING,
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
    },
    TaskStatus.RUNNING: {
        TaskStatus.CANCELLING,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.INTERRUPTED,
    },
    TaskStatus.CANCELLING: {
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
    TaskStatus.INTERRUPTED: set(),
}


def transition_task(current: TaskStatus, target: TaskStatus) -> TaskStatus:
    current = TaskStatus(current)
    target = TaskStatus(target)
    if current == target:
        return current
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"illegal task transition: {current.value} -> {target.value}")
    return target


def is_terminal(status: TaskStatus) -> bool:
    return status in {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.INTERRUPTED,
    }


def effective_locale_for_task(query: str, output_language: str | None) -> str:
    """Resolve the immutable UI/report locale for a task snapshot."""
    if output_language in {"zh-CN", "en"}:
        return output_language
    return "zh-CN" if re.search(r"[\u3400-\u9fff]", query) else "en"
