#!/usr/bin/env python3
"""A stand-in for ekatva's service, with made-up data, for screenshots.

Darpaṇa talks to ekatva's service over its Unix socket (tRPC over a
WebSocket). This answers the same calls from a fictional phone and its
fictional people, messages, calls and files, so the README and the website
can show the popup without anyone's real data. Nothing here is real.

    python3 scripts/demo-service.py /tmp/demo/ekatva.sock
    EKATVA_SOCKET=/tmp/demo/ekatva.sock vyom darpana     # in a headless sway

Standard library only, like Darpaṇa.
"""
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = int(time.time() * 1000)
MIN, HOUR, DAY = 60_000, 3_600_000, 86_400_000
PHONE_KEY = "demo-phone"

DEVICES = [{
    "key": PHONE_KEY, "name": "Pixel 8", "grants": [], "pairedAt": NOW - 40 * DAY, "lastSeen": NOW,
    "online": True, "via": "lan", "info": {"model": "Pixel 8", "android": "15"},
}]
with open(os.path.join(HERE, "demo-capabilities.json")) as f:
    CAPS = json.load(f)
DEVICES[0]["grants"] = list(CAPS["presets"]["everything-but-root"])

PEOPLE = [("Asha Verma", "+91 90000 10001"), ("Dev Malhotra", "+91 90000 10002"),
          ("Meera Iyer", "+91 90000 10003"), ("Rohan", "+91 90000 10004"), ("Mom", "+91 90000 10005"),
          ("Kabir Sethi", "+91 90000 10006")]

THREADS = []
CONVO = {}
SAID = [
    [("Are we still on for dinner tonight?", False, 3), ("Yes! 8 at the usual place", True, 2),
     ("Perfect, I'll book a table", False, 1)],
    [("Sent you the slides for Monday", False, 40), ("Thanks, looks great", True, 35)],
    [("Your parcel is out for delivery", False, 95)],
    [("Football at 6?", False, 180), ("In. I'll bring the ball", True, 170)],
    [("Call me when you're free", False, 300), ("Will do, after work", True, 290)],
    [("Running 10 minutes late", False, 1500)],
]
for i, ((name, num), lines) in enumerate(zip(PEOPLE, SAID, strict=True)):
    tid = f"t{i}"
    msgs = [{"id": f"{tid}-{j}", "thread": tid, "from": num, "contact": name, "text": t, "at": NOW - ago * MIN,
             "mine": mine} for j, (t, mine, ago) in enumerate(lines)]
    CONVO[tid] = msgs
    THREADS.append({"thread": tid, "contact": name, "last": msgs[-1]})

CALLS = [
    {"id": "c1", "number": PEOPLE[0][1], "contact": PEOPLE[0][0], "kind": "in", "at": NOW - 12 * MIN, "seconds": 420},
    {"id": "c2", "number": PEOPLE[4][1], "contact": PEOPLE[4][0], "kind": "out", "at": NOW - 2 * HOUR, "seconds": 1260},
    {"id": "c3", "number": PEOPLE[1][1], "contact": PEOPLE[1][0], "kind": "missed", "at": NOW - 3 * HOUR, "seconds": 0},
    {"id": "c4", "number": PEOPLE[2][1], "contact": PEOPLE[2][0], "kind": "in", "at": NOW - 5 * HOUR, "seconds": 95},
    {"id": "c5", "number": "+91 90000 20000", "contact": None, "kind": "declined", "at": NOW - DAY, "seconds": 0},
    {"id": "c6", "number": PEOPLE[3][1], "contact": PEOPLE[3][0], "kind": "out", "at": NOW - DAY - HOUR, "seconds": 64},
    {"id": "c7", "number": PEOPLE[5][1], "contact": PEOPLE[5][0], "kind": "in", "at": NOW - 2 * DAY, "seconds": 300},
    {"id": "c8", "number": PEOPLE[0][1], "contact": PEOPLE[0][0], "kind": "missed", "at": NOW - 3 * DAY, "seconds": 0},
]

FOLDERS = ["Alarms", "DCIM", "Documents", "Download", "Movies", "Music", "Pictures", "Podcasts", "Recordings",
           "Ringtones"]
FILES = [("beach-sunset.jpg", 3_400_000, "image/jpeg"), ("boarding-pass.pdf", 210_000, "application/pdf"),
         ("road-trip.mp4", 48_000_000, "video/mp4"), ("voice-note.m4a", 820_000, "audio/mp4"),
         ("notes.txt", 4_200, "text/plain")]


def files(path):
    out = [{"name": d, "path": f"{path}/{d}", "kind": "dir", "size": 0, "mtime": NOW - 9 * DAY} for d in FOLDERS]
    out += [{"name": n, "path": f"{path}/{n}", "kind": "file", "size": s, "mtime": NOW - (i + 1) * DAY, "mime": m}
            for i, (n, s, m) in enumerate(FILES)]
    return out if path in ("~", "") else out[3:]


LOG = [("Set jyoti to Akhaṇḍa: the laptop stays awake", "jyoti.set", 3), ("Sent beach-sunset.jpg to the phone",
       "share.finish", 20), ("Dismissed a phone notification", "notifications.dismiss", 45),
       ("Switched the laptop to dark mode", "appearance.set", 120), ("Copied the phone's clipboard here",
       "clipboard.get", 300), ("Called Mom on the phone", "calls.dial", 500), ("Locked the phone", "lock.now", 900)]
ENTRIES = [{"seq": 1200 + i, "at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime((NOW - m * MIN) / 1000)),
            "actor": {"key": "local", "name": "you"}, "action": a, "summary": s, "input": None, "ok": True}
           for i, (s, a, m) in enumerate(reversed(LOG))]
ENTRIES[-1]["undo"] = {"kind": "jyoti.set", "data": {}}

STATE = {
    "status": {"name": "vayu", "battery": {"percent": 82, "charging": True, "plugged": True}, "cpu": 14,
               "temperature": 46, "uptime": 18_000, "jyoti": "on", "waiting": 0, "locked": False, "firewall": None},
    "jyoti": {"level": "on", "since": NOW - 40 * MIN, "until": None, "lidHold": True},
    "appearance": {"mode": "dark", "settable": True, "why": None},
}
PHONE = {
    "status": {"name": "Pixel 8", "battery": {"percent": 76, "charging": False}, "signal": {"bars": 4, "network": "5G"},
               "locked": False, "awake": False, "ringing": False},
    "appearance.get": {"mode": "dark", "settable": True, "why": None},
    "clipboard.get": "Table for two at 8, Indigo Deli",
}


def answer(path, inp):
    """The data for one call: a query or mutation."""
    if path == "status":
        return STATE["status"]
    if path == "jyoti.get":
        return STATE["jyoti"]
    if path == "appearance.get":
        return STATE["appearance"]
    if path == "admin.capabilities":
        return CAPS
    if path == "admin.pair.start":   # a made-up code: no real key or token
        return {"uri": "ekatva://pair?v=1&k=demo-laptop-key&t=demo-token&n=vayu&lan=192.168.1.7:47100&url="
                + TUNNEL, "expires": int(time.time() * 1000) + 2 * MIN, "lan": ROUTE["lan"], "url": TUNNEL}
    if path == "admin.log.check":
        return [{"host": "self", "name": "vayu", "seq": ENTRIES[-1]["seq"], "problem": None},
                {"host": PHONE_KEY, "name": "Pixel 8", "seq": 640, "problem": None}]
    if path == "admin.log.list":
        return ENTRIES if (inp or {}).get("host", "self") == "self" else []
    if path in ("admin.phone.query", "admin.phone.mutate"):
        p, i = inp.get("path"), inp.get("input") or {}
        if p == "sms.threads":
            return THREADS
        if p == "sms.read":
            return CONVO.get(i.get("thread"), [])
        if p == "calls.log":
            return CALLS
        if p == "files.list":
            return files(i.get("path", "~"))
        if p in PHONE:
            return PHONE[p]
        return {"value": None, "summary": "Done (demo)"}
    return {"value": None, "summary": "Done (demo)"}


TUNNEL = "wss://quiet-river-28.trycloudflare.com"   # made up
ROUTE = {"url": TUNNEL, "lan": ["192.168.1.7:47100"],
         "tunnel": {"kind": "cloudflared", "state": "up", "url": TUNNEL, "always": True,
                    "since": NOW - 3 * HOUR, "problem": None}}


def subscription(path):
    """The first (and, in the demo, only) value a watch sends."""
    return {"admin.devices.watch": DEVICES, "jyoti.watch": STATE["jyoti"], "admin.calls.watch": None,
            "admin.pair.pending": None, "admin.link.watch": ROUTE}.get(path)


# ---------------------------------------------------------------- WebSocket
def frame(text):
    data = text.encode()
    n = len(data)
    head = bytes([0x81]) + (bytes([n]) if n < 126 else bytes([126]) + struct.pack(">H", n) if n < 65536
                            else bytes([127]) + struct.pack(">Q", n))
    return head + data


def read_frame(conn):
    def exact(n):
        b = b""
        while len(b) < n:
            chunk = conn.recv(n - len(b))
            if not chunk:
                raise ConnectionError
            b += chunk
        return b
    b1, b2 = exact(2)
    op, n = b1 & 0x0F, b2 & 0x7F
    if n == 126:
        n = struct.unpack(">H", exact(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", exact(8))[0]
    mask = exact(4) if b2 & 0x80 else b"\0\0\0\0"
    data = bytes(c ^ mask[i % 4] for i, c in enumerate(exact(n)))
    return op, data


def serve(conn):
    req = b""
    while b"\r\n\r\n" not in req:
        req += conn.recv(4096)
    key = next(line.split(b":", 1)[1].strip() for line in req.split(b"\r\n") if line.lower().startswith(b"sec-websocket-key"))
    accept = base64.b64encode(hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()).decode()
    conn.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                  f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode())
    lock = threading.Lock()

    def send(obj):
        with lock:
            conn.sendall(frame(json.dumps(obj)))
    try:
        while True:
            op, data = read_frame(conn)
            if op == 8:
                return
            if op == 9:
                with lock:
                    conn.sendall(bytes([0x8A, 0]))
                continue
            if op != 1:
                continue
            msg = json.loads(data)
            mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
            if method == "subscription":
                send({"id": mid, "result": {"type": "started"}})
                send({"id": mid, "result": {"type": "data", "data": subscription(params.get("path"))}})
            elif method in ("query", "mutation"):
                send({"id": mid, "result": {"type": "data", "data": answer(params.get("path"), params.get("input"))}})
    except (ConnectionError, OSError):
        return


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ekatva-demo.sock"
    if os.path.exists(path):
        os.remove(path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(8)
    print(f"demo ekatva service on {path}", flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=serve, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
