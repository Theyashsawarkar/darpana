"""A small tRPC client for ekatva's daemon, over its local socket.

The daemon serves tRPC (JSON, no transformer) as a WebSocket on
$XDG_RUNTIME_DIR/ekatva.sock. This speaks just enough RFC 6455 for that:
no dependencies beyond the standard library, so the panel opens without
loading anything new.

One connection, kept open while Vyom runs (it's cheap: a Unix socket). A
reader thread answers calls and feeds subscriptions; calls block the
calling thread (always a worker: panel.background), subscription data is
handed to the GTK main loop.
"""
import base64
import itertools
import json
import os
import socket
import struct
import threading

from gi.repository import GLib

SOCK = os.environ.get("EKATVA_SOCKET") or os.path.join(
    os.environ.get("XDG_RUNTIME_DIR") or os.path.expanduser("~/.local/state"), "ekatva.sock")


class RpcError(Exception):
    """What the daemon (or the phone) said went wrong, in its own words."""


class Down(RpcError):
    """ekatva's service isn't running or stopped answering."""


class Client:
    def __init__(self, path=SOCK):
        self.path = path
        self.sock = None
        self.lock = threading.Lock()        # one writer at a time, one connect at a time
        self.ids = itertools.count(1)
        self.waiting = {}                   # id -> [Event, result, error]
        self.subs = {}                      # id -> (path, input, on_data)

    # ------------------------------------------------------------ the socket
    def _connect(self):
        if self.sock is not None:
            return
        if not os.path.exists(self.path):
            raise Down("the ekatva service isn't running")
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            s.connect(self.path)
            key = base64.b64encode(os.urandom(16)).decode()
            s.sendall((
                "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
                f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode())
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = s.recv(1024)
                if not chunk:
                    raise Down("the ekatva service closed the connection")
                head += chunk
            if b" 101 " not in head.split(b"\r\n", 1)[0]:
                raise Down("the ekatva service refused the connection")
            rest = head.split(b"\r\n\r\n", 1)[1]
        except OSError as e:
            s.close()
            raise Down(f"can't reach the ekatva service ({e.strerror or e})") from e
        s.settimeout(None)
        self.sock = s
        threading.Thread(target=self._read, args=(s, rest), daemon=True, name="ekatva-rpc").start()
        # Subscriptions made before a drop come back with the connection.
        for sid, (path, inp, _cb) in list(self.subs.items()):
            self._send({"id": sid, "method": "subscription", "params": {"path": path, "input": inp}})

    def _send(self, obj):
        data = json.dumps(obj).encode()
        mask = os.urandom(4)
        n = len(data)
        head = bytes([0x81])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(head + mask + body)

    def _read(self, s, buf):
        def need(k):
            nonlocal buf
            while len(buf) < k:
                chunk = s.recv(65536)
                if not chunk:
                    raise ConnectionError("closed")
                buf += chunk
            out, buf = buf[:k], buf[k:]
            return out

        message = b""
        try:
            while True:
                b0, b1 = need(2)
                op, n = b0 & 0x0F, b1 & 0x7F
                if n == 126:
                    n = struct.unpack(">H", need(2))[0]
                elif n == 127:
                    n = struct.unpack(">Q", need(8))[0]
                mask = need(4) if b1 & 0x80 else None
                payload = need(n)
                if mask:
                    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                if op == 0x8:                       # close
                    break
                if op == 0x9:                       # ping: answer it
                    with self.lock:
                        self.sock.sendall(bytes([0x8A, 0x80 | len(payload)]) + b"\0\0\0\0" + payload)
                    continue
                if op in (0x1, 0x2, 0x0):
                    message += payload
                    if b0 & 0x80:                   # the last fragment
                        self._dispatch(message)
                        message = b""
        except (OSError, ConnectionError, ValueError):
            pass
        self._dropped(s)

    def _drop_locked(self):
        s, self.sock = self.sock, None
        if s is not None:
            try:
                s.close()
            except OSError:
                pass

    def _dropped(self, s):
        with self.lock:
            if self.sock is s:
                self.sock = None
        try:
            s.close()
        except OSError:
            pass
        for slot in list(self.waiting.values()):
            if not slot[0].is_set():
                slot[2] = Down("the ekatva service went away")
                slot[0].set()

    def _dispatch(self, raw):
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        mid = msg.get("id")
        if mid in self.subs:
            res = msg.get("result") or {}
            if res.get("type") == "data":
                cb = self.subs[mid][2]
                data = res.get("data")
                GLib.idle_add(lambda: (cb(data), False)[1])
            return
        slot = self.waiting.get(mid)
        if slot is None:
            return
        if "error" in msg:
            slot[2] = RpcError(readable(msg["error"]))
        else:
            slot[1] = (msg.get("result") or {}).get("data")
        slot[0].set()

    # ------------------------------------------------------------ the calls
    def call(self, method, path, inp=None, timeout=20):
        """A query or a mutation; blocks (call it from a worker thread)."""
        mid = next(self.ids)
        slot = [threading.Event(), None, None]
        self.waiting[mid] = slot
        params = {"path": path}
        if inp is not None:
            params["input"] = inp
        try:
            for attempt in (1, 2):
                with self.lock:
                    self._connect()
                    try:
                        self._send({"id": mid, "method": method, "params": params})
                        break
                    except OSError as e:
                        # The service restarted under us: a fresh connection, once.
                        self._drop_locked()
                        if attempt == 2:
                            raise Down(f"lost the ekatva service ({e.strerror or e})") from e
            if not slot[0].wait(timeout):
                raise Down("the ekatva service didn't answer")
            if slot[2]:
                raise slot[2]
            return slot[1]
        finally:
            self.waiting.pop(mid, None)

    def query(self, path, inp=None, timeout=20):
        return self.call("query", path, inp, timeout)

    def mutate(self, path, inp=None, timeout=60):
        return self.call("mutation", path, inp, timeout)

    def phone(self, path, inp=None, mutation=False, key=None):
        """A call on the connected phone, relayed by the daemon."""
        body = {"key": key, "path": path, "input": inp}
        return self.call("mutation" if mutation else "query",
                         "admin.phone.mutate" if mutation else "admin.phone.query", body)

    def subscribe(self, path, on_data, inp=None):
        """Follows a subscription; on_data runs on the main loop. Returns a stop()."""
        mid = next(self.ids)
        self.subs[mid] = (path, inp, on_data)

        def start():
            try:
                with self.lock:
                    self._connect()
                    self._send({"id": mid, "method": "subscription", "params": {"path": path, "input": inp}})
            except (RpcError, OSError):
                with self.lock:
                    self._drop_locked()   # comes back with the next call's connection

        threading.Thread(target=start, daemon=True).start()

        def stop():
            if self.subs.pop(mid, None) is None:
                return
            try:
                with self.lock:
                    if self.sock is not None:
                        self._send({"id": mid, "method": "subscription.stop"})
            except OSError:
                pass
        return stop


def readable(err):
    """A tRPC error as one clean sentence (zod's issue lists included)."""
    message = (err or {}).get("message") or "something went wrong"
    if message.lstrip().startswith("["):
        try:
            issues = json.loads(message)
            message = "; ".join(i.get("message", "") for i in issues if i.get("message")) or message
        except ValueError:
            pass
    return message[:1].upper() + message[1:]
