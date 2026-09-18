"""Limit request bodies before multipart parsing or JSON allocation."""
from starlette.responses import JSONResponse

from opencmo.rag.parsing import MAX_BYTES


class KnowledgeBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST" or scope.get("path") != "/api/v1/knowledge/documents":
            return await self.app(scope, receive, send)
        limit = MAX_BYTES + 256 * 1024  # bounded multipart metadata overhead
        headers = dict(scope.get("headers", []))
        try:
            too_large = int(headers.get(b"content-length", b"0")) > limit
        except ValueError:
            too_large = True
        if too_large:
            return await JSONResponse({"error": "file_too_large"}, status_code=413)(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                return await JSONResponse({"error": "file_too_large"}, status_code=413)(scope, receive, send)
            if not message.get("more_body"):
                break
        consumed = False
        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        await self.app(scope, replay, send)
