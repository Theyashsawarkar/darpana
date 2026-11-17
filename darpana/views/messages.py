"""Messages: the phone's conversations, one open beside them, a box to text
from the phone. Reading them is logged on the phone, so they're loaded
when you come here (and again only after a minute or with Space r), not
on every opening of the popup."""
import time

from gi.repository import GLib, Gtk
from vyom import Hint

from ..widgets import (
    L,
    avatar,
    card,
    clear,
    ellipsized,
    glyph,
    matches,
    scroller,
    search_box,
)
from . import View
from .overview import thread_row

STALE = 60


class Messages(View):
    hints = [Hint("i", "write"), Hint("Enter", "open"), Hint("Space s", "search")]

    def build(self):
        self.current = None
        self.convo = []
        root = Gtk.Box(spacing=12, vexpand=True)
        root.add_css_class("ek-page")
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.search = search_box("Search a name or number", self.update)
        self.search.set_margin_bottom(6)
        left = card(self.search, scroller(self.list), cls="ek-list-card ek-threads")
        left.set_size_request(290, -1)
        left.set_hexpand(False)
        root.append(left)

        chat = card(cls="ek-chat", spacing=0)
        chat.set_hexpand(True)
        head = Gtk.Box(spacing=12)
        head.add_css_class("ek-chathead")
        self.head_av = Gtk.Box()
        head.append(self.head_av)
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.head_name = ellipsized("Pick a conversation", "ek-chat-name")
        self.head_num = ellipsized("", "ek-chat-num")
        names.append(self.head_name)
        names.append(self.head_num)
        head.append(names)
        self.call_btn = Gtk.Button()
        self.call_btn.add_css_class("ek-icon-btn")
        self.call_btn.add_css_class("call")
        self.call_btn.set_child(glyph("call"))
        self.call_btn.set_tooltip_text("Call from the phone")
        self.call_btn.connect("clicked", lambda *_: self.call())
        head.append(self.call_btn)
        chat.append(head)

        self.bubbles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.bubbles.add_css_class("ek-bubbles")
        self.scroll = scroller(self.bubbles)
        chat.append(self.scroll)

        comp = Gtk.Box(spacing=8)
        comp.add_css_class("ek-composer")
        self.entry = Gtk.Entry(hexpand=True, placeholder_text="Text from the phone…")
        self.entry.add_css_class("ek-input")
        self.entry.connect("activate", lambda *_: self.send())
        comp.append(self.entry)
        send = Gtk.Button()
        send.add_css_class("ek-send")
        send.set_child(glyph("up"))
        send.set_tooltip_text("Send (Enter)")
        send.connect("clicked", lambda *_: self.send())
        comp.append(send)
        chat.append(comp)
        root.append(chat)
        return root

    def editables(self):
        return [self.entry, self.search]

    def shown(self, force=False):
        p = self.p
        self.update()
        if not p.online():
            return
        if force or p.threads is None or time.time() - p.threads_at > STALE:
            p.threads_at = time.time()
            p.run(lambda: p.rpc.phone("sms.threads"), p.got_threads)
        elif self.current is not None and not self.convo:
            self.open(self.current)

    def thread(self):
        return next((t for t in (self.p.threads or []) if t["thread"] == self.current), None)

    def open(self, thread_id):
        self.current = thread_id
        self.convo = []
        self.update()
        p = self.p
        p.run(lambda: p.rpc.phone("sms.read", {"thread": thread_id, "limit": 60}), self.got_convo)

    def got_convo(self, msgs):
        self.convo = sorted(msgs or [], key=lambda m: m.get("at", 0))
        self.draw_convo()

    def update(self):
        p = self.p
        threads = p.threads or []
        # On Messages with none open: the newest one (reading it is logged on the phone).
        if p.tab == "msgs" and self.current is None and threads and p.online():
            self.current = threads[0]["thread"]
            p.run(lambda t=self.current: p.rpc.phone("sms.read", {"thread": t, "limit": 60}), self.got_convo)
        q = self.search.get_text()
        if not self.changed("list", p.threads, q, self.current, bool(p.online())):
            return
        clear(self.list)
        if not p.online() and not threads:
            self.list.append(L("The phone isn't connected", "ek-empty", xalign=0))
        elif p.threads is None:
            self.list.append(L("Loading…", "ek-empty", xalign=0))
        shown = [t for t in threads if matches(q, t.get("contact"), (t.get("last") or {}).get("from"))]
        if threads and not shown:
            self.list.append(L(f"No conversation matches “{q.strip()}”", "ek-empty", xalign=0, wrap=True))
        for t in shown:
            row = thread_row(t, lambda t=t: self.open(t["thread"]))
            if t["thread"] == self.current:
                row.add_css_class("on")
            self.list.append(row)
        t = self.thread()
        clear(self.head_av)
        if t:
            who = t.get("contact") or t["last"].get("from")
            self.head_av.append(avatar(who))
            self.head_name.set_label(who)
            self.head_num.set_label(t["last"].get("from") if t.get("contact") else "")
        self.call_btn.set_sensitive(bool(t))
        self.draw_convo()

    def draw_convo(self):
        if not self.changed("convo", self.current, self.convo):
            return
        clear(self.bubbles)
        day = None
        for m in self.convo:
            d = time.strftime("%A, %-d %B", time.localtime(m["at"] / 1000))
            if d != day:
                day = d
                today = time.strftime("%A, %-d %B")
                self.bubbles.append(L("Today" if d == today else d, "ek-day"))
            b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            b.add_css_class("ek-bubble")
            b.add_css_class("me" if m.get("mine") else "them")
            b.set_halign(Gtk.Align.END if m.get("mine") else Gtk.Align.START)
            text = L(m.get("text", ""), "ek-bubble-t", xalign=0, wrap=True, max_width_chars=48)
            text.set_selectable(True)
            b.append(text)
            b.append(L(time.strftime("%-I:%M %p", time.localtime(m["at"] / 1000)), "ek-bubble-time", xalign=1))
            self.bubbles.append(b)
        GLib.idle_add(self.to_bottom)

    def to_bottom(self):
        adj = self.scroll.get_vadjustment()
        adj.set_value(adj.get_upper())
        return False

    def send(self):
        t = self.thread()
        text = self.entry.get_text().strip()
        if not t or not text:
            return
        to = t["last"].get("from")
        p = self.p

        def sent(_r):
            self.entry.set_text("")
            self.convo.append({"text": text, "mine": True, "at": time.time() * 1000})
            self.draw_convo()
        p.phone_do("sms.send", {"to": to, "text": text}, f"Sent to {t.get('contact') or to}", sent)

    def call(self):
        t = self.thread()
        if t:
            n = t["last"].get("from")
            self.p.phone_do("calls.dial", {"number": n}, f"Calling {t.get('contact') or n} on the phone")
