"""Darpaṇa (दर्पण, "the mirror"): the phone, mirrored on this laptop, in a
Vyom popup. ekatva's window (ekatva, एकत्व, "oneness": the phone and this
laptop as one device).

The laptop's side of ekatva (github.com/Theyashsawarkar/ekatva): the phone at
a glance, jyoti (keeping the laptop awake), light and dark, the phone's clipboard, its messages,
calls and files, the action log, and pairing. It talks to ekatva's own
service (its tRPC socket) and opens at once: Vyom is already running, and
what it showed last time is on screen while fresh state loads.
"""
import time

from gi.repository import GLib, Gtk
from vyom import Plugin as Base

from . import vim
from .rpc import Client, RpcError
from .views import calls as calls_view
from .views import devices as devices_view
from .views import files as files_view
from .views import log as log_view
from .views import messages as messages_view
from .views import overview as overview_view
from .widgets import G, L, avatar, button, clear

# KEYBINDS (generated from darpana/vim.py by scripts/keybinds.py; don't edit by hand)
# keybind: Vyom/darpana leader:normal | Space j s | Set jyoti Śānta (the laptop sleeps and locks as usual)
# keybind: Vyom/darpana leader:normal | Space j a | Set jyoti Akhaṇḍa (keep the laptop awake: no lock, no sleep until the lid shuts)
# keybind: Vyom/darpana leader:normal | Space j n | Set jyoti Nandādīpa (keep the laptop awake, even with the lid closed)
# keybind: Vyom/darpana leader:normal | Space p r | Toggle phone ring (find it: full volume until pressed again)
# keybind: Vyom/darpana leader:normal | Space p l | Lock the phone
# keybind: Vyom/darpana leader:normal | Space p k | Toggle the phone's screen staying on
# keybind: Vyom/darpana leader:normal | Space p a | Answer the phone's incoming call
# keybind: Vyom/darpana leader:normal | Space p h | Hang up the phone's call (or decline it)
# keybind: Vyom/darpana leader:normal | Space p d | Dial a number from the phone (the Calls place)
# keybind: Vyom/darpana leader:normal | Space l l | Toggle the laptop's light / dark mode
# keybind: Vyom/darpana leader:normal | Space l p | Toggle the phone's light / dark mode
# keybind: Vyom/darpana leader:normal | Space l b | Switch both to light or dark (the lamp)
# keybind: Vyom/darpana leader:normal | Space g o | Go to home (the phone at a glance)
# keybind: Vyom/darpana leader:normal | Space g m | Go to the phone's messages
# keybind: Vyom/darpana leader:normal | Space g c | Go to the phone's calls
# keybind: Vyom/darpana leader:normal | Space g f | Go to the phone's files
# keybind: Vyom/darpana leader:normal | Space g l | Go to the action log
# keybind: Vyom/darpana leader:normal | Space g d | Go to the paired devices and their permissions
# keybind: Vyom/darpana leader:normal | Space y c | Copy the phone's clipboard to this laptop's
# keybind: Vyom/darpana leader:normal | Space y p | Copy this laptop's clipboard to the phone
# keybind: Vyom/darpana leader:normal | Space a p | Add a phone (shows the connect code: pairs a new phone, reconnects a paired one, any network)
# keybind: Vyom/darpana leader:normal | Space a f | Add a file to the phone (send it to Download/ekatva)
# keybind: Vyom/darpana leader:normal | Space s | Search messages or calls by name or number
# keybind: Vyom/darpana leader:normal | Space r | Reload what this place shows
# END KEYBINDS

RPC = Client()   # one connection for as long as Vyom runs

TABS = [("over", "Home"), ("msgs", "Messages"), ("calls", "Calls"),
        ("files", "Files"), ("log", "Log"), ("devices", "Devices")]
VIEWS = {"over": overview_view.Overview, "msgs": messages_view.Messages, "calls": calls_view.Calls,
         "files": files_view.Files, "log": log_view.Log, "devices": devices_view.Devices}


class Plugin(Base):
    name, title, icon, color = "darpana", "Darpaṇa", G["phone"], "blue"
    layout = "card"
    width, height = 832, 560          # x Vyom's scale (1.25): 1040 x 700
    modal = True
    start_mode = "normal"
    tabs = TABS
    tab = "over"
    key_groups = vim.GROUPS
    hints = []   # Vyom's footer already has H/L tabs, Space leader, ? keys

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        self.rpc = RPC
        self.root = None
        self.views = {}
        self.stops = []
        self.poll_id = None     # the 3 s poll while open
        self.call_id = None     # the call timer
        self.service = None     # True / False: does ekatva's service answer
        self.syncing = False
        # What it showed last: on screen at once on the next opening.
        self.devices, self.laptop, self.phone, self.jyoti = [], None, None, None
        self.look_laptop, self.look_phone, self.call = None, None, None
        self.threads, self.call_log, self.caps = None, None, None
        self.route = None   # the tunnel and LAN addresses (admin.link.watch)
        self.phone_clip = None
        self.threads_at = self.calls_at = 0
        self.calls_problem = None

    # ------------------------------------------------------------ lifecycle
    def available(self):
        return True, ""

    def opened(self, args):
        super().opened(args)
        if args and args[0] in VIEWS:
            self.tab = args[0]
        elif args and args[0] == "pair":
            self.tab = "devices"
        self.want_pair = bool(args and args[0] == "pair")

    def build_card(self):
        if self.root is None:
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            inner.add_css_class("ek")
            w, h = self.panel.sizes()[:2] if self.panel else (1040, 700)
            # The popup's size is fixed: nothing inside (a long message, a long
            # file name) may widen it past the screen. Content is cut, never the frame.
            self.root = Gtk.ScrolledWindow(propagate_natural_width=False, propagate_natural_height=False)
            self.root.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.EXTERNAL)
            self.root.set_size_request(w - 2, max(420, h - 110))
            self.root.set_child(inner)
            self.banner = Gtk.Box()
            self.banner.add_css_class("ek-banner-holder")
            inner.append(self.banner)
            self.holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
            inner.append(self.holder)
        self.show_tab()
        self.start()
        return self.root

    def unfocus(self):
        """Nothing chosen when a place shows: a stray Enter does nothing (GTK
        would pick the first control, say jyoti's Off), and j starts at the top."""
        if self.panel is not None:
            self.panel.set_focus(None)
        return False

    def closed(self):
        for stop in self.stops:
            stop()
        self.stops = []
        for name in ("poll_id", "call_id"):
            t = getattr(self, name)
            if t is not None:
                GLib.source_remove(t)
                setattr(self, name, None)

    def tab_changed(self, key):
        self.show_tab()

    def show_tab(self):
        # The top bar's tab follows (a `vyom darpana calls` opening, Space g c).
        btn = getattr(self.panel, "tab_buttons", {}).get(self.tab) if self.panel else None
        if btn is not None and not btn.get_active() and not self.syncing:
            self.syncing = True
            btn.set_active(True)    # its handler comes back here through tab_changed
            self.syncing = False
        view = self.views.get(self.tab)
        if view is None:
            view = self.views[self.tab] = VIEWS[self.tab](self)
        clear(self.holder)
        self.holder.append(view.widget)
        view.update()
        view.shown()
        GLib.idle_add(self.unfocus)
        if self.tab == "devices" and getattr(self, "want_pair", False):
            self.want_pair = False
            view.pair(True)
        if self.panel is not None:
            self.panel.refresh_hints() if hasattr(self.panel, "refresh_hints") else None

    def view(self, key):
        return self.views.get(key)

    def go(self, key):
        self.select_tab(key)

    # ------------------------------------------------------------ live state
    def start(self):
        """Subscriptions while the popup is open; polls for what has none."""
        self.closed()
        self.follow()
        self.poll()
        self.poll_id = GLib.timeout_add_seconds(3, self.poll_tick)
        self.draw_banner()
        self.preload()
        if self.caps is None:
            self.run(lambda: self.rpc.query("admin.capabilities"), self.on_caps, quiet=True)

    def poll_tick(self):
        self.poll()
        return True

    def poll(self):
        def status():
            try:
                return self.rpc.query("status", timeout=5)
            except RpcError as e:
                return Failure(str(e))
        self.run(status, self.on_laptop, quiet=True)
        if self.online():
            self.run(lambda: self.rpc.phone("status"), self.on_phone, quiet=True)
        else:
            self.on_phone(None)
        if self.tab == "over":
            self.run(self.load_looks, self.on_looks, quiet=True)

    def load_looks(self):
        laptop = self.rpc.query("appearance.get")
        try:
            phone = self.rpc.phone("appearance.get") if self.online() else None
        except RpcError as e:
            # Not allowed on the phone (its Settings), or it went away: the lamp says which.
            phone = {"mode": None, "why": "not allowed" if "may not" in str(e) else str(e)}
        return laptop, phone

    def on_looks(self, r):
        self.look_laptop, self.look_phone = r
        self.refresh_views()

    def on_devices(self, devices):
        was = self.online()
        self.devices = devices or []
        if self.online() and not was:
            self.poll()
            self.preload()
        self.refresh_views()

    PRELOAD = 300   # seconds: how stale the overview's messages and calls may get

    def preload(self, force=False):
        """The last messages and calls for the overview. Each read is logged
        on the phone, so not more often than every 5 minutes."""
        if not self.online():
            return
        now = time.time()
        if force or now - self.threads_at > self.PRELOAD:
            self.threads_at = now
            self.run(lambda: self.rpc.phone("sms.threads"), self.got_threads, quiet=True)
        if force or now - self.calls_at > self.PRELOAD:
            self.preload_calls()

    def preload_calls(self):
        self.calls_at = time.time()

        def calls():
            try:
                return self.rpc.phone("calls.log", {"limit": 60})
            except RpcError as e:
                return Failure(str(e))
        self.run(calls, self.got_calls, quiet=True)

    def got_threads(self, threads):
        self.threads = threads or []
        self.threads_at = time.time()
        for key in ("over", "msgs"):
            v = self.views.get(key)
            if v is not None:
                v.update()

    def got_calls(self, r):
        if isinstance(r, Failure):
            self.calls_problem = ("Update ekatva on the phone to see the call history here"
                                  if "calls.log" in r else str(r))
        else:
            self.calls_problem = None
            self.call_log = r or []
            self.calls_at = time.time()
        for key in ("over", "calls"):
            v = self.views.get(key)
            if v is not None:
                v.update()

    def on_jyoti(self, j):
        self.jyoti = j
        self.refresh_views()

    def on_laptop(self, st):
        ok = not isinstance(st, Failure)
        if ok:
            self.laptop = st
        if ok != self.service:
            self.service = ok
            self.draw_banner()
            if ok:     # back: follow it again
                self.follow()
        self.refresh_views()

    def follow(self):
        for stop in self.stops:
            stop()
        self.stops = [
            self.rpc.subscribe("admin.devices.watch", self.on_devices),
            self.rpc.subscribe("jyoti.watch", self.on_jyoti),
            self.rpc.subscribe("admin.calls.watch", self.on_call),
            self.rpc.subscribe("admin.link.watch", self.on_route),
        ]

    def on_route(self, route):
        self.route = route
        self.refresh_views()

    def on_phone(self, st):
        self.phone = st
        self.refresh_views()

    def on_caps(self, caps):
        self.caps = caps
        self.refresh_views()

    def on_call(self, call):
        self.call = call
        self.draw_banner()
        v = self.views.get("over")
        if v:
            v.update()

    def refresh_views(self):
        v = self.views.get(self.tab)
        if v is not None:
            v.update()

    def online(self):
        return next((d for d in self.devices if d.get("online")), None)

    def phone_name(self):
        d = self.online() or (self.devices[0] if self.devices else None)
        return short_name(d["name"]) if d else "Your phone"

    # ------------------------------------------------------------ the call banner
    def draw_banner(self):
        if getattr(self, "banner", None) is None:
            return
        clear(self.banner)
        if self.call_id is not None:
            GLib.source_remove(self.call_id)
            self.call_id = None
        c = self.call if self.service is not False else None
        if self.service is False:
            self.banner.set_visible(True)
            box = Gtk.Box(spacing=14, hexpand=True)
            box.add_css_class("ek-banner")
            box.add_css_class("off")
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
            text.append(L("ekatva is off on this laptop", "ek-banner-t", xalign=0))
            text.append(L("Nothing reaches the phone until it's on. Its switch is in quick settings.",
                          "ek-banner-s", xalign=0))
            box.append(text)
            box.append(button("Turn it on", self.turn_on, "accent", "check"))
            self.banner.append(box)
            return
        if not c:
            self.banner.set_visible(False)
            return
        self.banner.set_visible(True)
        who = c.get("contact") or c.get("number") or "Unknown number"
        box = Gtk.Box(spacing=14, hexpand=True)
        box.add_css_class("ek-banner")
        av = avatar(who)
        av.add_css_class("ek-av-call")
        box.append(av)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        text.append(L(who, "ek-banner-t", xalign=0))
        if c["state"] == "ringing":
            box.add_css_class("ringing")
            kind = "video call" if c.get("video") else "call"
            sub = (f"{c['app']} {kind} on {short_name(c['name'])}" if c.get("app") else
                   f"Calling {short_name(c['name'])}" + (f" · {c['number']}" if c.get("contact") and c.get("number") else ""))
            text.append(L(sub, "ek-banner-s", xalign=0))
            box.append(text)
            box.append(button("Decline", lambda: self.phone_do("calls.hangUp", None, "Declined"), "danger soft"))
            box.append(button("Answer", lambda: self.phone_do("calls.answer", None, "Answered: talk on the phone"),
                              "ok", "call"))
        else:
            self.call_time = L("", "ek-banner-s", xalign=0)
            text.append(self.call_time)
            box.append(text)
            box.append(button("Hang up", lambda: self.phone_do("calls.hangUp", None, "Hung up"), "danger", "call"))
            self.tick_call()
            self.call_id = GLib.timeout_add_seconds(1, self.tick_call)
        self.banner.append(box)

    def tick_call(self):
        c = self.call
        if not c or c["state"] != "active" or not getattr(self, "call_time", None):
            self.call_id = None
            return False
        s = max(0, int(time.time() - c["since"] / 1000))
        kind = "video call" if c.get("video") else "call"
        on = f"On a {c['app']} {kind}" if c.get("app") else f"On a {kind}"
        self.call_time.set_label(f"{on} on {short_name(c['name'])} · {s // 60}:{s % 60:02d}")
        return True

    # ------------------------------------------------------------ doing things
    def run(self, work, then=None, quiet=False, done=None):
        """work() in a worker thread; then(result) on the main loop. What ekatva
        or the phone refused shows in the footer (unless quiet) in its own
        words; only a real bug reaches Vyom's log."""
        def guarded():
            try:
                return work()
            except RpcError as e:
                return _Raised(str(e))

        def after(r):
            # A Failure that work() returned on purpose goes to then(); one it raised doesn't.
            if isinstance(r, (Exception, _Raised)):
                if not quiet:
                    self.say(str(r) if isinstance(r, (RpcError, _Raised)) else f"Something went wrong: {r}",
                             bad=True)
                return
            if done:
                self.say(done)
            if then:
                then(r)
        if self.panel is not None:
            self.panel.background(guarded, after)

    def say(self, text, bad=False):
        if self.panel is not None and self.panel.get_visible():
            self.set_status(text, "bad" if bad else "ok", clear_after=4)
        else:   # finished after the popup closed (a file sent): tell the desktop
            from vyom import util
            util.notify("ekatva", text, icon="phone", app="ekatva")

    def turn_on(self):
        """ekatva's service switch ([plugin.darpana] turn_on; Vayu's is ekatva-toggle.sh)."""
        import subprocess
        cmd = self.conf.get("turn_on", "systemctl --user start ekatva.service")

        def work():
            r = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True, timeout=20, check=False)
            if r.returncode != 0:
                raise RpcError((r.stderr or r.stdout).strip() or "couldn't turn ekatva on")
            return True
        self.run(work, lambda _r: GLib.timeout_add(1200, lambda: (self.poll(), False)[1]),
                 done="Turning ekatva on…")

    def phone_do(self, path, inp=None, done=None, then=None):
        """A mutation on the phone; `done` says what happened."""
        if not self.online():
            self.say("The phone isn't connected", bad=True)
            return
        self.run(lambda: self.rpc.phone(path, inp, mutation=True), then, done=done)

    def set_jyoti(self, level):
        self.run(lambda: self.rpc.mutate("jyoti.set", {"level": level, "minutes": None}),
                 done={"off": "Jyoti: Śānta", "on": "Jyoti: Akhaṇḍa", "high": "Jyoti: Nandādīpa"}[level])

    def flip_laptop(self):
        def work():
            a = self.rpc.query("appearance.get")
            return self.rpc.mutate("appearance.set", {"mode": "light" if a["mode"] == "dark" else "dark"})
        self.run(work, lambda _r: self.run(self.load_looks, self.on_looks, quiet=True), done="Switched this laptop")

    def flip_phone(self):
        def work():
            a = self.rpc.phone("appearance.get")
            return self.rpc.phone("appearance.set", {"mode": "light" if a["mode"] == "dark" else "dark"},
                                  mutation=True)
        if not self.online():
            return self.say("The phone isn't connected", bad=True)
        self.run(work, lambda _r: self.run(self.load_looks, self.on_looks, quiet=True), done="Switched the phone")

    def flip_both(self):
        """The lamp: both to the opposite of the laptop's mode."""
        to = "dark" if (self.look_laptop or {}).get("mode") == "light" else "light"

        def work():
            self.rpc.mutate("appearance.set", {"mode": to})
            if self.online():
                try:
                    self.rpc.phone("appearance.set", {"mode": to}, mutation=True)
                except RpcError:
                    pass
            return self.load_looks()
        self.run(work, self.on_looks, done=f"Both {to}")

    def ring(self):
        ringing = bool((self.phone or {}).get("ringing"))
        self.phone_do("stopRinging" if ringing else "ring", None,
                      "Stopped ringing" if ringing else "Ringing the phone until you stop it",
                      lambda _r: self.poll())

    def keep_awake(self):
        on = not (self.phone or {}).get("awake")
        self.phone_do("keepAwake", {"on": on}, "Its screen stays on" if on else "It may sleep again",
                      lambda _r: self.poll())

    def lock_phone(self):
        self.phone_do("lock", None, "Locked the phone")

    # ------------------------------------------------------------ vim keys
    def keys(self, tab):
        return vim.keys(tab)

    def editables(self):
        v = self.views.get(self.tab)
        return v.editables() if v is not None else []

    def insert_target(self):
        # Space s asks for the search box, not the place's first box.
        want, self.want_insert = getattr(self, "want_insert", None), None
        return want or super().insert_target()

    def tab_hints(self):
        v = self.views.get(self.tab)
        return (v.hints if v is not None and v.hints else []) + self.hints

    def v_jyoti(self, _n, level):
        self.set_jyoti(level)

    def v_phone(self, _n, what):
        {"ring": self.ring, "lock": self.lock_phone, "awake": self.keep_awake,
         "answer": lambda: self.phone_do("calls.answer", None, "Answered"),
         "hangup": lambda: self.phone_do("calls.hangUp", None, "Hung up"),
         "dial": lambda: (self.go("calls"), self.views["calls"].focus_dialer())}[what]()

    def v_look(self, _n, which):
        {"laptop": self.flip_laptop, "phone": self.flip_phone, "both": self.flip_both}[which]()

    def v_go(self, _n, key):
        self.go(key)

    def v_pair(self, _n, _a):
        self.go("devices")
        self.views["devices"].pair(True)

    def v_clip(self, _n, what):
        self.go("over")
        self.views["over"].clip(what)

    def v_send(self, _n, _a):
        self.go("files")
        self.views["files"].pick()

    def v_search(self, _n, _a):
        v = self.views.get(self.tab)
        box = getattr(v, "search", None)
        if box is None:
            self.say("Search is in Messages and Calls", bad=True)
            return
        self.want_insert = box
        self.set_vim_mode("insert")
        box.grab_focus()

    def v_refresh(self, _n, _a):
        self.poll()
        v = self.views.get(self.tab)
        if v is not None:
            v.shown(force=True)

    def v_view(self, n, arg):
        """A key that belongs to the tab you're on (undo in the log...)."""
        v = self.views.get(self.tab)
        if v is not None and hasattr(v, "key"):
            v.key(arg, n)

    def escape(self):
        v = self.views.get(self.tab)
        return bool(v is not None and hasattr(v, "escape") and v.escape())


class Failure(str):
    """An expected failure (the phone went away, a permission is off), as text."""


class _Raised(str):
    """What run()'s work raised, in ekatva's words."""


def short_name(name):
    """'CMF by Nothing Phone 2 Pro' -> 'CMF Phone 2 Pro'."""
    return (name or "the phone").replace(" by Nothing", "")
