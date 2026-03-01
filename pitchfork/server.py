"""
Pitchfork HTTP + WebSocket server.

Uses websockets to sync and asyncio to serve HTTP
HTTP runs on `port`, WebSocket on `port + 1`.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class PitchforkServer:
    def __init__(
        self,
        deck_path: Path,
        css_path: Path,
        host: str = "localhost",
        port: int = 1312
    ):
        self.deck_path = deck_path
        self.css_path = css_path
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.slides_json: str = "[]"
        self.default_layout: str = "body"
        self._css_dir = Path(__file__).parent

    # MARK: Public API

    def set_slides_json(self, slides_json: str) -> None:
        self.slides_json = slides_json

    async def broadcast(self, message: dict) -> None:
        if not self.clients:
            return
        data = json.dumps(message)
        await asyncio.gather(
            *[c.send(data) for c in list(self.clients)],
            return_exceptions=True,
        )

    # MARK: WebSocket handler

    async def _ws_handler(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "navigate":
                    relay = json.dumps(msg)
                    await asyncio.gather(
                        *[c.send(relay) for c in list(self.clients) if c is not ws],
                        return_exceptions=True,
                    )
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)

    # MARK: HTTP handler

    def _inject(self, html: str) -> bytes:
        """Inject runtime values into an HTML template."""
        return (
            html.replace("__SLIDES_JSON__", self.slides_json)
               .replace("__WS_PORT__", str(self.port + 1))
               .encode("utf-8")
        )

    def _serve_static(self, path: str) -> Optional[Tuple[bytes, str]]:
        """Return (body, content_type) for static assets, or None if not found."""
        if path == "/styles.css":
            body = self.css_path.read_bytes() if self.css_path.exists() else b""
            return body, "text/css"
        if path == "/pitchfork.css":
            return (self._css_dir / "pitchfork.css").read_bytes(), "text/css"

        # Serve arbitrary files relative to the deck directory
        MIME_TYPES = {
            ".html": "text/html", ".htm": "text/html",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif",
            ".webp": "image/webp", ".svg": "image/svg+xml",
            ".mp4": "video/mp4", ".webm": "video/webm",
            ".pdf": "application/pdf",
            ".js": "text/javascript", ".woff2": "font/woff2",
        }
        # Sanitise: prevent directory traversal
        try:
            rel = Path(path.lstrip("/"))
            if ".." in rel.parts:
                return None
            candidate = (self.deck_path.parent / rel).resolve()
            candidate.relative_to(self.deck_path.parent.resolve())  # must stay inside deck dir
        except Exception:
            return None

        if not candidate.is_file():
            return None

        ct = MIME_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
        return candidate.read_bytes(), ct

    async def _http_handler(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        from pitchfork.templates import SLIDES_PAGE, NOTES_PAGE, PRESENTER_PAGE, TIMER_PAGE

        try:
            raw = await asyncio.wait_for(reader.read(8192), timeout=10.0)
        except asyncio.TimeoutError:
            writer.close()
            await writer.wait_closed()
            return

        try:
            request_line = raw.decode("utf-8", errors="replace").split("\r\n")[0]
            parts = request_line.split()
            path = parts[1].split("?")[0] if len(parts) >= 2 else "/"
        except Exception:
            writer.close()
            await writer.wait_closed()
            return

        page_routes: Dict[str, str] = {
            "/": SLIDES_PAGE,
            "/slides": SLIDES_PAGE,
            "/notes": NOTES_PAGE,
            "/presenter": PRESENTER_PAGE,
            "/timer": TIMER_PAGE,
        }

        if path in page_routes:
            body = self._inject(page_routes[path])
            ct = "text/html"
        else:
            result = self._serve_static(path)
            if result is None:
                writer.write(
                    b"HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n\r\nNot found"
                )
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
            body, ct = result

        header = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: {ct}; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(header + body)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    # MARK: Entry point

    async def start(self) -> None:
        http_server = await asyncio.start_server(
            self._http_handler, self.host, self.port
        )
        ws_server = await websockets.serve(
            self._ws_handler, self.host, self.port + 1
        )
        print(f"\n   Endpoints:")
        print(f"     Slides:    http://{self.host}:{self.port}/slides")
        print(f"     Notes:     http://{self.host}:{self.port}/notes        Press 'n' in Slides view")
        print(f"     Presenter: http://{self.host}:{self.port}/presenter    Press 'p' in Slides view")
        print(f"     Timer:     http://{self.host}:{self.port}/timer        Press 't' in Slides view")
        print(f"     (Ctrl+C to stop)\n")
        async with http_server, ws_server:
            await asyncio.Future()  # run until cancelled
