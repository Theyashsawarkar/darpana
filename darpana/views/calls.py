"""Calls: the phone's call history beside a dialer. The history is logged
on the phone when read, so it's loaded when you come here (at most once a
minute). The call in progress is the banner at the top of every place."""
import time

from gi.repository import Gtk
from vyom import Hint

from ..widgets import L, card, clear, glyph, matches, scroller, search_box
from . import View
from .overview import call_row

STALE = 60
PAD = [("1", ""), ("2", "ABC"), ("3", "DEF"), ("4", "GHI"), ("5", "JKL"), ("6", "MNO"),
       ("7", "PQRS"), ("8", "TUV"), ("9", "WXYZ"), ("*", ""), ("0", "+"), ("#", "")]


class Calls(View):
    hints = [Hint("Enter", "call back"), Hint("i", "type a number"), Hint("Space s", "search")]

    def build(self):
        self.filter = "all"
        root = Gtk.Box(spacing=12, vexpand=True)
        root.add_css_class("ek-page")

        left = card(cls="ek-list-card", spacing=6)
        left.set_hexpand(True)
        tabs = Gtk.Box(spacing=6)
        self.fbtn = {}
        for key, text in (("all", "Everything"), ("missed", "Missed")):
            b = Gtk.Button(label=text)
            b.add_css_class("ek-filter")
            b.connect("clicked", lambda _b, k=key: self.set_filter(k))
            tabs.append(b)
            self.fbtn[key] = b
        self.search = search_box("Search a name or number", self.update)
        tabs.append(self.search)
        left.append(tabs)
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        left.append(scroller(self.list))
        root.append(left)

        dialer = card(cls="ek-dialer", spacing=0)
        dialer.set_size_request(330, -1)
        dialer.set_hexpand(False)
        dialer.append(L("CALL FROM THE PHONE", "ek-eyebrow"))
        self.entry = Gtk.Entry(placeholder_text="Number", xalign=0.5)
        self.entry.add_css_class("ek-number")
        self.entry.connect("activate", lambda *_: self.dial())
        self.entry.connect("changed", lambda *_: self.match())
        dialer.append(self.entry)
        self.who = L("", "ek-who")
        dialer.append(self.who)
        grid = Gtk.Grid(row_spacing=10, column_spacing=14, halign=Gtk.Align.CENTER, margin_top=10,
                        margin_bottom=12)
        for i, (d, letters) in enumerate(PAD):
            b = Gtk.Button()
            b.add_css_class("ek-key")
            b.set_can_focus(False)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
            box.append(L(d, "ek-key-d"))
            box.append(L(letters or " ", "ek-key-l"))
            b.set_child(box)
            b.connect("clicked", lambda _b, d=d: self.press(d))
            grid.attach(b, i % 3, i // 3, 1, 1)
        dialer.append(grid)
        row = Gtk.Box(spacing=18, halign=Gtk.Align.CENTER)
        call = Gtk.Button()
        call.add_css_class("ek-dial")
        call.set_child(glyph("call"))
        call.set_tooltip_text("Call (Enter)")
        call.connect("clicked", lambda *_: self.dial())
        row.append(call)
        back = Gtk.Button(valign=Gtk.Align.CENTER)
        back.add_css_class("ek-icon-btn")
        back.set_child(glyph("back"))
        back.set_can_focus(False)
        back.set_tooltip_text("Delete a digit")
        back.connect("clicked", lambda *_: self.entry.set_text(self.entry.get_text()[:-1]))
        row.append(back)
        dialer.append(row)
        root.append(dialer)
        return root

    def editables(self):
        return [self.entry, self.search]

    def focus_dialer(self):
        self.p.set_vim_mode("insert")

    def set_filter(self, key):
        self.filter = key
        self.update()

    def press(self, d):
        self.entry.set_text((self.entry.get_text() + d)[:20])

    def match(self):
        n = "".join(c for c in self.entry.get_text() if c.isdigit())
        hit = None
        if len(n) > 3:
            for c in self.p.call_log or []:
                if c.get("contact") and "".join(x for x in c.get("number", "") if x.isdigit()).endswith(n[-10:]):
                    hit = c["contact"]
                    break
        self.who.set_label(hit or "")

    def dial(self):
        n = self.entry.get_text().strip()
        if not n:
            return self.p.say("Type a number first", bad=True)
        who = self.who.get_label() or n

        def done(_r):
            self.entry.set_text("")
        self.p.phone_do("calls.dial", {"number": n}, f"Calling {who} on the phone", done)

    def shown(self, force=False):
        p = self.p
        self.update()
        if not p.online():
            return
        if force or p.call_log is None or time.time() - p.calls_at > STALE:
            p.preload_calls()

    def update(self):
        for k, b in self.fbtn.items():
            (b.add_css_class if k == self.filter else b.remove_css_class)("on")
        q = self.search.get_text()
        if not self.changed("list", self.filter, q, self.p.call_log, self.p.calls_problem, bool(self.p.online())):
            return
        clear(self.list)
        log = self.p.call_log
        problem = self.p.calls_problem
        if problem:
            self.list.append(L(problem, "ek-empty", "t-yellow", xalign=0, wrap=True))
        if log is None:
            if not problem:
                self.list.append(L("Loading…" if self.p.online() else "The phone isn't connected",
                                   "ek-empty", xalign=0))
            return
        rows = [c for c in log if (self.filter == "all" or c.get("kind") in ("missed", "declined"))
                and matches(q, c.get("contact"), c.get("number"))]
        for c in rows:
            self.list.append(call_row(c, self.p))
        if not rows:
            self.list.append(L(f"No calls match “{q.strip()}”" if q.strip() else
                               "No missed calls" if self.filter == "missed" else "No calls yet", "ek-empty",
                               xalign=0))
