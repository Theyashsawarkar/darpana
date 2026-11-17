"""Devices: the paired phones, what each may do on this laptop (switches
grouped by risk), unpairing, and pairing a new one (a QR code, then four
emoji to compare)."""
import os
import subprocess
import time

from gi.repository import GLib, Gtk
from vyom import Hint

from ..widgets import L, button, card, clear, ellipsized, glyph, scroller
from . import View

RISK = [("low", "Low risk", "green"), ("medium", "Medium", "yellow"), ("high", "High", "red")]
VERSE = ("यस्मिन्सर्वाणि भूतान्यात्मैवाभूद्विजानतः ।\nतत्र को मोहः कः शोक एकत्वमनुपश्यतः ॥")


class Devices(View):
    hints = [Hint("Enter", "toggle"), Hint("Space a p", "pair a phone")]

    def build(self):
        self.sel = None
        self.pairing = False
        self.offer = None
        self.pending = []
        self.preset = "everything-but-root"
        self.stop_pending = None
        root = Gtk.Box(spacing=12, vexpand=True)
        root.add_css_class("ek-page")
        left = card(cls="ek-devcard", spacing=8)
        left.set_size_request(300, -1)
        left.set_hexpand(False)
        self.devs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.append(self.devs)
        self.detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.append(self.detail)
        left.append(Gtk.Box(vexpand=True))
        left.append(button("Pair a phone", lambda: self.pair(True), "soft", "plus"))
        verse = L(VERSE, "ek-verse", justify=Gtk.Justification.CENTER, wrap=True)
        left.append(verse)
        left.append(L("Īśa Upaniṣad 7", "ek-verse-src"))
        root.append(left)
        self.right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        root.append(self.right)
        return root

    def device(self):
        devs = self.p.devices
        return next((d for d in devs if d["key"] == self.sel), devs[0] if devs else None)

    def shown(self, force=False):
        self.update()

    # ------------------------------------------------------------ drawing
    def update(self):
        p = self.p
        if not self.changed("all", p.devices, p.caps, self.sel, self.pairing, self.pending, self.offer,
                            getattr(self, "qr", None), self.preset):
            return
        clear(self.devs)
        for d in p.devices:
            b = Gtk.Button()
            b.add_css_class("ek-row")
            if self.device() is d:
                b.add_css_class("on")
            box = Gtk.Box(spacing=12)
            ph = glyph("phone", "ek-dev-ic")
            box.append(ph)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
            text.append(ellipsized(d["name"].replace(" by Nothing", ""), "ek-row-t"))
            sub = ("Connected · " + ("direct" if d.get("via") == "lan" else "through the internet")
                   if d.get("online") else f"Last seen {seen(d.get('lastSeen'))}")
            s = ellipsized(sub, "ek-row-s")
            if d.get("online"):
                s.add_css_class("t-green")
            text.append(s)
            box.append(text)
            b.set_child(box)
            b.connect("clicked", lambda _b, k=d["key"]: self.pick(k))
            self.devs.append(b)
        if not p.devices:
            self.devs.append(L("No phone yet. Pair one: it takes a QR code and four emoji.", "ek-empty",
                               xalign=0, wrap=True))
        clear(self.detail)
        d = self.device()
        if d:
            info = d.get("info") or {}
            for k, v in (("Paired", time.strftime("%-d %B %Y", time.localtime(d["pairedAt"] / 1000))),
                         ("Phone", " ".join(x for x in (info.get("model"), info.get("os")) if x) or "–"),
                         ("Key", f"{d['key'][:4]} {d['key'][4:8]} {d['key'][8:12]}")):
                row = Gtk.Box(spacing=10)
                row.append(L(k, "ek-kv-k", xalign=0))
                row.append(ellipsized(v, "ek-kv-v", "ek-mono" if k == "Key" else "ek-kv-v"))
                self.detail.append(row)
            self.detail.append(button("Unpair this phone", lambda: self.unpair(d), "danger soft"))
        clear(self.right)
        if self.pairing:
            self.right.append(self.pair_card())
        elif d:
            self.right.append(self.perms_card(d))
        else:
            self.right.append(card(L("Pair a phone to choose what it may do here.", "ek-empty"),
                                   cls="ek-list-card"))

    def pick(self, key):
        self.sel = key
        self.pairing = False
        self.update()

    # ------------------------------------------------------------ permissions
    def perms_card(self, d):
        p = self.p
        caps = (p.caps or {}).get("capabilities") or {}
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.append(L(f"What {d['name'].replace(' by Nothing', '')} may do here", "ek-section", xalign=0))
        if not caps:
            box.append(L("Loading…", "ek-empty", xalign=0))
        mine = [(k, c) for k, c in caps.items() if (c.get("side") == "laptop" and k != "admin")
                or k == "phone.notifications"]
        for risk, title, color in RISK:
            rows = [(k, c) for k, c in mine if c.get("risk") == risk]
            if not rows:
                continue
            head = Gtk.Box(spacing=8, margin_top=10)
            head.append(L("", "ek-risk-dot", f"ek-bg-{color}", valign=Gtk.Align.CENTER))
            head.append(L(title, "ek-group", xalign=0))
            box.append(head)
            for key, c in rows:
                row = Gtk.Box(spacing=12)
                row.add_css_class("ek-perm")
                text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
                title, detail = c.get("title", key), c.get("detail", "")
                if key == "phone.notifications":   # the phone's own, sent here (not this laptop's)
                    title, detail = "Send its notifications here", "the phone's notifications, on this laptop"
                text.append(ellipsized(title, "ek-row-t"))
                text.append(ellipsized(detail, "ek-row-s"))
                row.append(text)
                sw = switch(key in d.get("grants", []))
                sw.connect("state-set", lambda _s, on, k=key: self.grant(d, k, on))
                row.append(sw)
                box.append(row)
        box.append(L("What this laptop may do on the phone is chosen on the phone, in its Settings.",
                     "ek-empty", xalign=0, wrap=True, margin_top=10))
        return card(scroller(box), cls="ek-list-card")

    def grant(self, d, key, on):
        grants = set(d.get("grants", []))
        (grants.add if on else grants.discard)(key)
        p = self.p
        title = ((p.caps or {}).get("capabilities") or {}).get(key, {}).get("title", key)
        p.run(lambda: p.rpc.mutate("admin.devices.grant", {"key": d["key"], "grants": sorted(grants)}),
              done=("Allowed: " if on else "Not allowed any more: ") + title)
        return False

    def unpair(self, d):
        p = self.p
        name = d["name"].replace(" by Nothing", "")

        def go():
            p.run(lambda: p.rpc.mutate("admin.devices.unpair", {"key": d["key"]}),
                  done=f"Unpaired {name} (undo it in the log)")
        p.confirm(f"Unpair {name}? It can't connect until you pair it again.", go)

    # ------------------------------------------------------------ pairing
    def pair(self, on):
        p = self.p
        self.pairing = on
        if self.stop_pending:
            self.stop_pending()
            self.stop_pending = None
        if on:
            self.offer, self.qr, self.pending = None, None, []
            self.stop_pending = p.rpc.subscribe("admin.pair.pending", self.got_pending)
            p.run(lambda: p.rpc.mutate("admin.pair.start", {"away": True}), self.got_offer)
            GLib.timeout_add_seconds(1, self.tick)
        self.update()

    def escape(self):
        if self.pairing:
            self.pair(False)
            return True
        return False

    def got_offer(self, offer):
        self.offer = offer
        path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "ekatva-pair.png")
        try:
            subprocess.run(["qrencode", "-o", path, "-s", "8", "-m", "2", offer["uri"]], check=True, timeout=5)
            self.qr = path
        except (OSError, subprocess.SubprocessError):
            self.qr = None
        self.update()

    def got_pending(self, pending):
        self.pending = pending or []
        if self.pairing:
            self.update()

    def tick(self):
        if not self.pairing:
            return False
        if self.offer and hasattr(self, "left_lbl"):
            left = max(0, int(self.offer["expires"] / 1000 - time.time()))
            self.left_lbl.set_label(f"Works once, for {left // 60}:{left % 60:02d} more" if left
                                    else "Expired: press New code")
        return True

    def pair_card(self):
        c = card(cls="ek-pair", spacing=10)
        head = Gtk.Box(spacing=8)
        head.append(L("Pair a phone", "ek-pair-t", xalign=0, hexpand=True))
        head.append(button("Close", lambda: self.pair(False), "soft"))
        c.append(head)
        req = self.pending[0] if self.pending else None
        if req:
            addr = (req.get("info") or {}).get("address")
            c.append(L(f"{req['name']} wants to pair{f' (from {addr})' if addr else ''}. "
                       "Does it show exactly these?", "ek-says", xalign=0, wrap=True))
            c.append(L("  ".join(req.get("sas", [])), "ek-sas"))
            presets = list(((self.p.caps or {}).get("presets") or {}).keys()) or ["everything-but-root"]
            seg = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)
            for name in presets:
                b = Gtk.Button(label=name.replace("-", " ").capitalize())
                b.add_css_class("ek-filter")
                if name == self.preset:
                    b.add_css_class("on")
                b.connect("clicked", lambda _b, n=name: (setattr(self, "preset", n), self.update()))
                seg.append(b)
            c.append(L("It may do:", "ek-says"))
            c.append(seg)
            two = Gtk.Box(spacing=8, homogeneous=True, margin_top=8)
            two.append(button("They match: pair", lambda: self.decide(req, True), "ok", "check"))
            two.append(button("Refuse", lambda: self.decide(req, False), "danger soft"))
            c.append(two)
            c.append(L("If they differ, refuse: someone else may have used the code.", "ek-empty", wrap=True))
            return c
        row = Gtk.Box(spacing=18)
        if self.qr:
            pic = Gtk.Picture.new_for_filename(self.qr)
            pic.set_size_request(220, 220)
            pic.set_can_shrink(True)
            frame = Gtk.Box()
            frame.add_css_class("ek-qr")
            frame.append(pic)
            row.append(frame)
        else:
            row.append(L("Opening a tunnel…" if not self.offer else "Couldn't draw the code (qrencode)",
                         "ek-empty"))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.CENTER, hexpand=True)
        text.append(L("Scan this with ekatva on the phone.", "ek-row-t", xalign=0, wrap=True))
        self.left_lbl = L("", "ek-row-s", xalign=0)
        text.append(self.left_lbl)
        self.tick()
        if self.offer:
            text.append(L("Works from any network (mobile data too)" if self.offer.get("url")
                          else "Same Wi-Fi only", "ek-row-s", xalign=0))
            text.append(button("New code", lambda: self.pair(True), "soft"))
        text.append(L("Then check the phone shows the same four emoji as here.", "ek-row-s", xalign=0, wrap=True))
        row.append(text)
        c.append(row)
        return c

    def decide(self, req, accept):
        p = self.p
        grants = ((p.caps or {}).get("presets") or {}).get(self.preset, [])

        def after(_r):
            if accept:
                self.pair(False)
            else:
                self.pair(True)
        p.run(lambda: p.rpc.mutate("admin.pair.confirm", {"id": req["id"], "accept": accept, "grants": grants}),
              after, done="Paired" if accept else "Refused")


def switch(active):
    """A switch the card cursor reaches (j / k, Enter flips it), without GTK's
    two tiny on/off images (they warn about their baselines)."""
    s = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
    c = s.get_first_child()
    while c is not None:
        if isinstance(c, Gtk.Image):
            c.set_visible(False)
        c = c.get_next_sibling()
    return s


def seen(ms):
    from ..widgets import ago
    return ago(ms) or "never"
