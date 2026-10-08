from fastapi.responses import StreamingResponse


class ManagedStreamingResponse(StreamingResponse):
    """Close generators in the streaming task, including send/disconnect errors."""

    async def stream_response(self, send):
        try:
            await super().stream_response(send)
        finally:
            close = getattr(self.body_iterator, "aclose", None)
            if close is not None:
                await close()
