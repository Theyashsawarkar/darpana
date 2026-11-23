"""Overview: the phone at a glance and what you reach for most.

  [ ring | the phone, how it's linked | Ring Lock Awake Send Dial ]
  [ Jyoti        ][ Light and dark   ][ The phone's clipboard ]
  [ Messages (the last ones)            ][ Calls (the last ones) ]
"""
import time

from gi.repository import Gtk
from vyom import Hint

from ..lamp import JyotiLamp
from ..rpc import RpcError
from ..widgets import (
    L,
    Lamp,
    Ring,
    action,
    avatar,
    button,
    card,
    clear,
    ellipsized,
    glyph,
    heading,
)
from . import View

JYOTI = {
    "off": ("Śānta", "Sleeps and locks as usual"),
    "on": ("Akhaṇḍa", "Awake until the lid shuts"),
    "high": ("Nandādīpa", "Awake with the lid closed"),
}


class Overview(View):
    hints = [Hint("Enter", "press")]

    def build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.add_css_class("ek-page")
        root.append(self.build_hero())
        tiles = Gtk.Box(spacing=12, homogeneous=True)
        tiles.append(self.build_jyoti())
        tiles.append(self.build_lamp())
        tiles.append(self.build_clip())
        root.append(tiles)
        pair = Gtk.Box(spacing=12, homogeneous=True, vexpand=True)
        self.msgs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.calls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.msgs_card = card(heading("Messages", "chat", more=("Open all", lambda: self.p.go("msgs"))),
                              self.msgs, cls="ek-list-card")
        self.calls_card = card(heading("Calls", "call", more=("Dial", lambda: self.p.v_phone(1, "dial"))),
                               self.calls, cls="ek-list-card")
        pair.append(self.msgs_card)
        pair.append(self.calls_card)
        root.append(pair)
        return root

    # ------------------------------------------------------------ the phone
    def build_hero(self):
        hero = card(cls="ek-hero", vertical=False, spacing=20)
        over = Gtk.Overlay(valign=Gtk.Align.CENTER)
        self.ring = Ring(100, 7)
        over.set_child(self.ring)
        mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0, halign=Gtk.Align.CENTER,
                      valign=Gtk.Align.CENTER)
        self.pct = L("–", "ek-pct")
        self.bolt = glyph("bolt", "ek-bolt")
        mid.append(self.pct)
        mid.append(self.bolt)
        over.add_overlay(mid)
        hero.append(over)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True, valign=Gtk.Align.CENTER)
        line = Gtk.Box(spacing=8)
        self.dot = Gtk.Box(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        self.dot.set_size_request(8, 8)
        self.dot.add_css_class("ek-dot")
        self.link = L("", "ek-linkline", xalign=0)
        line.append(self.dot)
        line.append(self.link)
        info.append(line)
        self.name = ellipsized("", "ek-name")
        info.append(self.name)
        self.sub = L("", "ek-sub", xalign=0)
        info.append(self.sub)
        self.pills = Gtk.Box(spacing=6, margin_top=8)
        info.append(self.pills)
        hero.append(info)

        acts = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        self.ring_btn = action("bell", "Ring", self.p.ring)
        self.awake_btn = action("eye", "Awake", self.p.keep_awake)
        for b in (self.ring_btn, action("lock", "Lock", self.p.lock_phone), self.awake_btn,
                  action("send", "Send", lambda: self.p.v_send(1, "")),
                  action("call", "Dial", lambda: self.p.v_phone(1, "dial"))):
            acts.append(b)
        self.acts = acts
        hero.append(acts)
        return hero

    # ------------------------------------------------------------ jyoti
    def build_jyoti(self):
        # As on the phone: the level's flame is the focus, large at the top right
        # (the flame: at dusk, blue, bright red), the words beneath it.
        c = card(cls="ek-tile ek-jyoti", spacing=0)
        stage = Gtk.Overlay(vexpand=True)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        words.append(L("JYOTI", "ek-eyebrow", "ek-jyoti-label", xalign=0))
        words.append(Gtk.Box(vexpand=True))
        stage.set_child(words)
        self.jyoti_art = JyotiLamp(104, "ek-jyoti-art", halign=Gtk.Align.END,
                                   valign=Gtk.Align.START)
        stage.add_overlay(self.jyoti_art)
        c.append(stage)
        self.jyoti_name = L("–", "ek-big", xalign=0)
        self.jyoti_says = ellipsized("", "ek-says")
        c.append(self.jyoti_name)
        c.append(self.jyoti_says)
        self.seg = Gtk.Box(homogeneous=True, margin_top=10)
        self.seg.add_css_class("ek-seg")
        self.seg_btn = {}
        for level, text in (("off", "Śānta"), ("on", "Akhaṇḍa"), ("high", "Nandādīpa")):
            b = Gtk.Button(label=text)
            b.add_css_class("ek-seg-b")
            b.connect("clicked", lambda _b, lv=level: self.p.set_jyoti(lv))
            self.seg.append(b)
            self.seg_btn[level] = b
        c.append(self.seg)
        self.jyoti_card = c
        return c

    # ------------------------------------------------------------ light and dark
    def build_lamp(self):
        b = Gtk.Button()
        b.add_css_class("ek-tile")
        b.add_css_class("ek-card")
        b.add_css_class("ek-lamp")
        b.set_tooltip_text("Switch both to light or dark (Space l b)")
        over = Gtk.Overlay()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.append(L("LIGHT AND DARK", "ek-eyebrow", xalign=0))
        box.append(Gtk.Box(vexpand=True))
        self.lamp_name = L("–", "ek-big", xalign=0)
        box.append(self.lamp_name)
        self.lamp_says = ellipsized("This laptop and the phone", "ek-says")
        box.append(self.lamp_says)
        chips = Gtk.Box(spacing=6, margin_top=10)
        self.chip_laptop = Gtk.Box(spacing=5)
        self.chip_phone = Gtk.Box(spacing=5)
        for ch in (self.chip_laptop, self.chip_phone):
            ch.add_css_class("ek-mode-chip")
            chips.append(ch)
        box.append(chips)
        over.set_child(box)
        self.lamp = Lamp()
        self.lamp.set_halign(Gtk.Align.END)
        self.lamp.set_valign(Gtk.Align.START)
        over.add_overlay(self.lamp)
        over.set_clip_overlay(self.lamp, False)
        b.set_child(over)
        b.connect("clicked", lambda *_: self.p.flip_both())
        self.lamp_btn = b
        return b

    # ------------------------------------------------------------ the phone's clipboard
    def build_clip(self):
        c = card(cls="ek-tile ek-clip", spacing=0)
        c.append(L("THE PHONE'S CLIPBOARD", "ek-eyebrow", xalign=0))
        c.append(Gtk.Box(vexpand=True))
        self.clip_text = ellipsized("What the phone copied last", "ek-clip-q")
        c.append(self.clip_text)
        self.clip_note = L("Read only when you ask (it's in the phone's log)", "ek-says", xalign=0, margin_top=6)
        c.append(self.clip_note)
        two = Gtk.Box(spacing=6, homogeneous=True, margin_top=10)
        self.clip_get = button("Show it", lambda: self.clip("show"), "soft")
        two.append(self.clip_get)
        two.append(button("Send mine", lambda: self.clip("send"), "soft"))
        c.append(two)
        return c

    def clip(self, what):
        p = self.p
        if what == "show" and p.phone_clip is not None:
            what = "copy"
        if what in ("show", "copy"):
            def got(text):
                p.phone_clip = (text or "", time.time())
                self.update()
                if what == "copy":
                    from vyom import util
                    util.copy(text or "")
                    p.say("The phone's clipboard is on this laptop's clipboard")
            if not p.online():
                return p.say("The phone isn't connected", bad=True)
            if what == "copy" and p.phone_clip is not None:
                return got(p.phone_clip[0])
            p.run(lambda: p.rpc.phone("clipboard.get"), got)
        elif what == "send":
            def work():
                import subprocess
                text = subprocess.run(["wl-paste", "--no-newline"], capture_output=True, text=True, check=False,
                                      timeout=3).stdout
                if not text:
                    raise RpcError("This laptop's clipboard has no text")
                return p.rpc.phone("clipboard.set", {"text": text}, mutation=True)
            if not p.online():
                return p.say("The phone isn't connected", bad=True)
            p.run(work, done="Sent this laptop's clipboard to the phone")

    # ------------------------------------------------------------ drawing
    def update(self):
        p = self.p
        dev = p.online()
        st = p.phone
        # the phone
        name = p.phone_name()
        self.name.set_label(name)
        for c in ("ok", "off"):
            self.dot.remove_css_class(c)
        if dev:
            self.dot.add_css_class("ok")
            self.link.set_label("Linked directly · encrypted" if dev.get("via") == "lan"
                                else "Linked through the internet · encrypted")
        else:
            self.dot.add_css_class("off")
            self.link.set_label("ekatva is off" if p.service is False else
                                "Not connected" if p.devices else "No phone paired yet")
        bat = (st or {}).get("battery")
        if bat:
            pct = bat["percent"]
            color = "green" if bat.get("charging") or pct > 30 else "yellow" if pct > 15 else "red"
            self.ring.set(pct / 100, color)
            self.pct.set_label(f"{pct}%")
            self.bolt.set_visible(bool(bat.get("charging")))
            self.sub.set_label("Charging" if bat.get("charging") else "On battery")
        else:
            self.ring.set(0, "gray")
            self.pct.set_label("–")
            self.bolt.set_visible(False)
            self.sub.set_label("Turn ekatva on to reach it" if p.service is False else
                               "Open ekatva on the phone to link it" if p.devices else
                               "Pair one in Devices (Space a p)" if not dev else "…")
        if self.changed("pills", st and (st.get("signal"), st.get("awake"), st.get("ringing"))):
            self.draw_pills(st)
        ringing = bool((st or {}).get("ringing"))
        (self.ring_btn.add_css_class if ringing else self.ring_btn.remove_css_class)("ringing")
        self.ring_btn.text.set_label("Stop" if ringing else "Ring")
        (self.awake_btn.add_css_class if (st or {}).get("awake") else self.awake_btn.remove_css_class)("held")
        for b in self.acts:
            b.set_sensitive(bool(dev))

        # jyoti
        level = (p.jyoti or {}).get("level") or (p.laptop or {}).get("jyoti") or "off"
        n, says = JYOTI.get(level, JYOTI["off"])
        for lv in JYOTI:
            self.jyoti_card.remove_css_class(f"lv-{lv}")
            self.seg_btn[lv].remove_css_class("on")
        self.jyoti_card.add_css_class(f"lv-{level}")
        self.seg_btn[level].add_css_class("on")
        self.jyoti_name.set_label(n)
        self.jyoti_says.set_label(says)
        self.jyoti_art.set_level(level)

        # light and dark
        lm = (p.look_laptop or {}).get("mode")
        pm = (p.look_phone or {}).get("mode")
        lit = lm == "light"
        self.lamp.set_lit(lit)
        (self.lamp_btn.add_css_class if lit else self.lamp_btn.remove_css_class)("lit")
        self.lamp_name.set_label("Light" if lit else "Dark" if lm else "–")
        why = (p.look_phone or {}).get("why")
        self.lamp_says.set_label("Laptop only: the phone hasn't allowed it"
                                 if why == "not allowed" else
                                 "This laptop and the phone" if p.online() else "This laptop (the phone isn't linked)")
        self.lamp_says.set_tooltip_text(self.lamp_says.get_label())
        if self.changed("modes", lm, pm, (p.laptop or {}).get("name")):
            fill_mode(self.chip_laptop, "laptop", (p.laptop or {}).get("name") or "Laptop", lm)
            fill_mode(self.chip_phone, "phone", "Phone", pm)

        # the phone's clipboard
        if p.phone_clip is not None:
            text, at = p.phone_clip
            self.clip_text.set_label(text.strip().replace("\n", " ") or "Empty")
            mins = int((time.time() - at) // 60)
            self.clip_note.set_label("Read just now" if mins < 1 else f"Read {mins} min ago")
            self.clip_get.get_child().get_last_child().set_label("Copy here")

        # messages and calls (what was loaded last; the Messages and Calls places load them)
        if self.changed("lists", p.threads, p.call_log, p.calls_problem, p.service, bool(p.online()),
                        bool(p.devices)):
            self.draw_lists()

    def draw_lists(self):
        p = self.p
        clear(self.msgs)
        threads = p.threads or []
        for t in threads[:3]:
            self.msgs.append(thread_row(t, lambda t=t: (p.go("msgs"), p.views["msgs"].open(t["thread"]))))
        if not threads:
            self.msgs.append(L(empty(p, p.threads, "No messages yet"), "ek-empty", xalign=0, wrap=True))
        clear(self.calls)
        log = p.call_log or []
        for c in log[:3]:
            self.calls.append(call_row(c, p))
        if not log:
            self.calls.append(L(p.calls_problem or empty(p, p.call_log, "No calls yet"), "ek-empty",
                                xalign=0, wrap=True))

    def draw_pills(self, st):
        clear(self.pills)
        if not st:
            return
        sig = st.get("signal")
        if sig:
            net = {"wifi": "Wi-Fi", "mobile": "Mobile data"}.get(sig.get("network"), sig.get("network") or "")
            self.pills.append(pill("signal", net))
        self.pills.append(pill("eye", "Screen kept on" if st.get("awake") else "Screen sleeps"))
        if st.get("ringing"):
            self.pills.append(pill("bell", "Ringing", "red"))

    def shown(self, force=False):
        self.update()


def empty(p, loaded, none):
    """What an empty list means: not connected, still loading, or nothing there."""
    if p.service is False:
        return "ekatva is off"
    if not p.online():
        return "The phone isn't connected" if p.devices else "No phone paired yet"
    return "Loading…" if loaded is None else none


def pill(icon, text, color=""):
    b = Gtk.Box(spacing=6)
    b.add_css_class("ek-pill")
    if color:
        b.add_css_class(f"ek-pill-{color}")
    b.append(glyph(icon))
    b.append(L(text))
    return b


def fill_mode(box, icon, name, mode):
    clear(box)
    box.remove_css_class("dim")
    box.append(glyph(icon))
    box.append(L(name))
    if mode in ("light", "dark"):
        box.append(glyph("sun" if mode == "light" else "moon", "ek-mode-ic"))
        box.set_tooltip_text(f"{name}: {mode}")
    else:
        box.set_tooltip_text(f"{name}: unknown (not connected, or not allowed)")
        box.add_css_class("dim")


def thread_row(t, on_open):
    last = t.get("last") or {}
    who = t.get("contact") or last.get("from") or "Unknown"
    b = Gtk.Button()
    b.add_css_class("ek-row")
    box = Gtk.Box(spacing=12)
    box.append(avatar(who))
    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
    text.append(ellipsized(who, "ek-row-t"))
    text.append(ellipsized(("You: " if last.get("mine") else "") + (last.get("text") or "").replace("\n", " "),
                           "ek-row-s"))
    box.append(text)
    from ..widgets import ago
    box.append(L(ago(last.get("at")), "ek-row-time", valign=Gtk.Align.START))
    b.set_child(box)
    b.connect("clicked", lambda *_: on_open())
    return b


KIND = {"in": ("↙", "green", "Incoming"), "out": ("↗", "blue", "Outgoing"),
        "missed": ("↙", "red", "Missed"), "declined": ("↙", "red", "Declined")}


def call_row(c, plugin):
    from ..widgets import ago, duration
    arrow, color, word = KIND.get(c.get("kind"), KIND["in"])
    who = c.get("contact") or c.get("number") or "Unknown"
    b = Gtk.Button()
    b.add_css_class("ek-row")
    b.set_tooltip_text(f"Call {who} back from the phone")
    box = Gtk.Box(spacing=12)
    box.append(L(arrow, "ek-dir", f"t-{color}", valign=Gtk.Align.CENTER))
    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
    t = ellipsized(who, "ek-row-t")
    if color == "red":
        t.add_css_class("t-red")
    text.append(t)
    bits = [word] + ([duration(c["seconds"])] if c.get("seconds") else []) + [ago(c.get("at"))]
    text.append(ellipsized(" · ".join(bits), "ek-row-s"))
    box.append(text)
    box.append(glyph("call", "ek-back", valign=Gtk.Align.CENTER))
    b.set_child(box)
    number = c.get("number")
    b.connect("clicked", lambda *_: number and plugin.phone_do("calls.dial", {"number": number},
                                                               f"Calling {who} on the phone"))
    return b
