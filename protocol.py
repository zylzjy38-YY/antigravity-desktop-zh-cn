"""Attach only to a selected application's loopback debugging endpoint."""
import json
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

import websocket

LOOPBACK = {'127.0.0.1', 'localhost', '::1'}


def local_page(target: dict) -> bool:
    try:
        url = urlsplit(target['url'])
        return target.get('type') == 'page' and url.scheme in {'http', 'https'} and url.hostname in LOOPBACK
    except (KeyError, ValueError, TypeError):
        return False


def list_targets(port: int) -> list:
    # Local inspection must not go through environment/system HTTP proxies.
    opener = build_opener(ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{port}/json/list', timeout=2) as response:
        payload = response.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError('Target response too large')
    targets = json.loads(payload)
    if not isinstance(targets, list):
        raise ValueError('Invalid target response')
    return targets


class Cdp:
    def __init__(self, url: str, port: int):
        address = urlsplit(url)
        if (address.scheme != 'ws' or address.hostname not in LOOPBACK
                or address.port != port or address.username or address.password):
            raise ValueError('Refusing non-local or mismatched debugger endpoint')
        self.socket = websocket.create_connection(url, timeout=5, suppress_origin=True,
                                                 http_no_proxy=['127.0.0.1', 'localhost', '::1'])
        self.sequence = 0
        self.script_id = None

    def call(self, method: str, params: dict | None = None) -> dict:
        import time
        self.sequence += 1
        self.socket.send(json.dumps({'id': self.sequence, 'method': method, 'params': params or {}}))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            self.socket.settimeout(max(0.01, deadline - time.monotonic()))
            payload = self.socket.recv()
            if len(payload) > 2 * 1024 * 1024:
                raise ValueError('Debugger response too large')
            reply = json.loads(payload)
            if reply.get('id') == self.sequence:
                if reply.get('error'):
                    raise RuntimeError('Debugger rejected method: ' + method)
                return reply.get('result', {})
        raise TimeoutError('Debugger command timed out')

    def close(self):
        self.socket.close()
