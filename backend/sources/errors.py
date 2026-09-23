from __future__ import annotations


class SourceSearchError(RuntimeError):
    """Safe, stable error raised when a paper source cannot be queried."""

    def __init__(self, source: str, code: str, message: str) -> None:
        super().__init__(message)
        self.source = source
        self.code = code
        self.public_message = message

    def as_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "error_code": self.code,
            "message": self.public_message,
        }
