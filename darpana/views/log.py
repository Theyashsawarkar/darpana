"""Log: what was done on this laptop (or the copy of the phone's log kept
here), newest first, each entry's undo, and whether the chain checks out."""
from gi.repository import Gtk
from vyom import Hint

from ..widgets import G, L, clear, ellipsized, glyph, scroller
from . import View

# What an entry was, by its action: the glyph and the colour that means it.
# ("caffeine": entries from before it was renamed jyoti.)
LOOK = [("admin.phone", "phone", "blue"), ("root", "shield", "red"), ("jyoti", "eye", "sky"),
        ("jagaran", "eye", "sky"), ("caffeine", "eye", "sky"), ("appearance", "sun", "yellow"),
        ("files", "folder", "accent"), ("share", "send", "green"), ("sms", "chat", "accent"),
        ("calls", "call", "green"), ("lock", "lock", "blue"), ("agents", "list", "yellow"),
        ("devices", "phone", "blue"), ("clipboard", "clip", "accent"), ("journal", "undo", "accent")]


class Log(View):
    hints = [Hint("j/k", "move to an Undo"), Hint("Enter", "undo it")]

    def build(self):
        self.host = "self"
        self.entries = None
        self.checks = None
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, vexpand=True)
        root.add_css_class("ek-page")
        bar = Gtk.Box(spacing=6)
        self.filters = Gtk.Box(spacing=6)
        bar.append(self.filters)
        bar.append(Gtk.Box(hexpand=True))
        self.chain = L("", "ek-chain")
        bar.append(self.chain)
        root.append(bar)
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.list.add_css_class("ek-log")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("ek-card")
        box.add_css_class("ek-log-card")
        box.set_vexpand(True)
        box.append(scroller(self.list))
        root.append(box)
        return root

    def shown(self, force=False):
        self.load()

    def load(self):
        """The newest 400 entries: where the chain ends comes from its check."""
        p = self.p
        host = self.host

        def work():
            checks = p.rpc.query("admin.log.check")
            last = next((c.get("seq", 0) for c in checks or [] if c.get("host") == host), 0)
            entries = p.rpc.query("admin.log.list", {"host": host, "after": max(0, last - 400), "limit": 400})
            return checks, entries

        def got(r):
            self.checks = r[0]
            self.got(host, r[1])
        p.run(work, got)

    def got(self, host, entries):
        if host == self.host:
            self.entries = list(reversed(entries or []))
            self.update()

    def set_host(self, host):
        self.host = host
        self.entries = None
        self.update()
        self.load()

    def update(self):
        p = self.p
        if not self.changed("all", self.host, [(d["key"], d["name"]) for d in p.devices], self.checks,
                            [(e["seq"], e.get("undoes")) for e in self.entries or []], self.entries is None):
            return
        clear(self.filters)
        hosts = [("self", "This laptop")] + [(d["key"], short(d["name"])) for d in p.devices]
        for key, text in hosts:
            b = Gtk.Button(label=text)
            b.add_css_class("ek-filter")
            if key == self.host:
                b.add_css_class("on")
            b.connect("clicked", lambda _b, k=key: self.set_host(k))
            self.filters.append(b)
        check = next((c for c in self.checks or [] if c.get("host") == self.host), None)
        for c in ("t-green", "t-red"):
            self.chain.remove_css_class(c)
        if check:
            if check.get("problem"):
                self.chain.set_label(f"{G['shield']}  {check['problem']}")
                self.chain.add_css_class("t-red")
            else:
                self.chain.set_label(f"{G['check']}  {check['seq']:,} entries, the chain checks out")
                self.chain.add_css_class("t-green")
        else:
            self.chain.set_label("")
        clear(self.list)
        if self.entries is None:
            self.list.append(L("Loading…", "ek-empty", xalign=0))
            return
        if not self.entries:
            self.list.append(L("Nothing yet", "ek-empty", xalign=0))
        undone = {e.get("undoes") for e in self.entries if e.get("undoes") and e.get("ok")}
        for e in self.entries[:400]:
            self.list.append(self.row(e, undone))
        if self.host != "self":
            self.list.append(L("The copy of the phone's log kept here: undo its entries on the phone.",
                               "ek-empty", xalign=0, wrap=True))

    def row(self, e, undone):
        action = e.get("action", "")
        icon, color = next(((g, c) for k, g, c in LOOK if action.startswith(k)), ("list", "accent"))
        if not e.get("ok"):
            color = "red"
        box = Gtk.Box(spacing=12)
        box.add_css_class("ek-entry")
        if e["seq"] in undone:
            box.add_css_class("undone")
        box.append(L(f"#{e['seq']}", "ek-seq", valign=Gtk.Align.CENTER))
        box.append(glyph(icon, "ek-entry-ic", f"t-{color}", valign=Gtk.Align.CENTER))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        text.append(ellipsized(e.get("summary", ""), "ek-row-t"))
        bits = [e.get("actor", {}).get("name", ""), when(e.get("at", ""))]
        if not e.get("ok"):
            bits.append("refused" if e.get("error") == "not granted" else f"failed: {e.get('error', '')}")
        if e.get("undoes"):
            bits.append(f"undid #{e['undoes']}")
        if e["seq"] in undone:
            bits.append("undone")
        sub = ellipsized(" · ".join(b for b in bits if b), "ek-row-s")
        if not e.get("ok"):
            sub.add_css_class("t-red")
        text.append(sub)
        box.append(text)
        if e.get("ok") and e.get("undo") and e["seq"] not in undone and self.host == "self":
            b = Gtk.Button()
            b.add_css_class("ek-undo")
            inner = Gtk.Box(spacing=6)
            inner.append(glyph("undo"))
            inner.append(L("Undo"))
            b.set_child(inner)
            b.connect("clicked", lambda *_: self.undo(e))
            box.append(b)
        return box

    def undo(self, e):
        p = self.p

        def go():
            p.run(lambda: p.rpc.mutate("journal.undo", {"seq": e["seq"]}),
                  lambda r: (p.say(r.get("summary", "Undone") if isinstance(r, dict) else "Undone"), self.load()))
        p.confirm(f"Undo #{e['seq']}: {e.get('summary', '')}?", go)

def short(name):
    return (name or "").replace(" by Nothing", "")


def when(iso):
    import datetime
    import time
    try:
        t = datetime.datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return ""
    from ..widgets import ago
    return ago(t * 1000) if time.time() - t < 86400 * 6 else time.strftime("%-d %b, %-I:%M %p", time.localtime(t))
