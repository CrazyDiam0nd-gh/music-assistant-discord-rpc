"""Minimal Music Assistant websocket API client."""
import asyncio
import itertools
import json
from urllib.parse import urlparse

import websockets


class MAError(Exception):
    pass


def ws_url(url: str) -> str:
    """http://host:8095 -> ws://host:8095/ws (ws/wss URLs and bare host:port also accepted)."""
    url = url.strip()
    if "://" not in url:
        url = "http://" + url
    parsed = urlparse(url)
    scheme = {"http": "ws", "https": "wss"}.get(parsed.scheme, parsed.scheme)
    path = parsed.path.rstrip("/")
    if not path.endswith("/ws"):
        path += "/ws"
    return f"{scheme}://{parsed.netloc}{path}"


class MAClient:
    def __init__(self, url: str, token: str = ""):
        self.url = ws_url(url)
        self.token = token
        self._ids = itertools.count(1)
        self._ws = None
        self.server_info = {}

    async def __aenter__(self):
        try:
            self._ws = await websockets.connect(self.url, max_size=None)
            self.server_info = json.loads(await asyncio.wait_for(self._ws.recv(), 10))
        except Exception as exc:
            raise MAError(f"cannot connect to Music Assistant at {self.url}: {exc}") from exc
        if self.token:
            await self.call("auth", token=self.token)
        return self

    async def __aexit__(self, *exc):
        if self._ws:
            await self._ws.close()

    async def call(self, command: str, **args):
        mid = str(next(self._ids))
        await self._ws.send(json.dumps({"message_id": mid, "command": command, "args": args}))
        while True:
            msg = json.loads(await asyncio.wait_for(self._ws.recv(), 15))
            if msg.get("message_id") != mid:
                continue  # event or another reply
            if "error_code" in msg:
                details = msg.get("details", "")
                if "uthenticat" in details and not self.token:
                    details += " - create a long-lived token in Music Assistant " \
                               "(Settings > Profile) and run `ma-rpc setup`"
                raise MAError(details or f"error {msg['error_code']}")
            return msg.get("result")

    async def players(self) -> list:
        return await self.call("players/all")

    async def item_by_uri(self, uri: str) -> dict:
        return await self.call("music/item_by_uri", uri=uri)
