"""Files: the phone's folders, and sending files to it.

The phone's side is a grid of cards (a coloured tile saying what each thing
is, its name, its size and date) under a path you can click anywhere along.
Tap a folder to open it, a file to save it to ~/Downloads here.

Sending has its own picker, inside the popup (the popup holds the keyboard,
and a system dialog over it couldn't be used): this laptop's places, its
folders, files you tick, then one Send. Dropping files on the page sends them
too. They land in the phone's Download/ekatva.
"""
import base64
import os
import time

from gi.repository import Gdk, GLib, Gtk
from vyom import Hint

from ..widgets import L, button, clear, ellipsized, scroller, size
from . import View

PIECE = 512 * 1024    # the protocol's PIECE: easy on the phone's JS thread
SHOW = 400            # items drawn in one folder, at most

# What a thing is: its icon (the theme's symbolic, vector) and its colour.
KINDS = {
    "dir": ("folder-symbolic", "accent"),
    "image": ("image-x-generic-symbolic", "green"),
    "video": ("video-x-generic-symbolic", "peach"),
    "audio": ("audio-x-generic-symbolic", "mauve"),
    "archive": ("package-x-generic-symbolic", "yellow"),
    "doc": ("x-office-document-symbolic", "blue"),
    "apk": ("application-x-executable-symbolic", "teal"),
    "file": ("text-x-generic-symbolic", "overlay"),
}
EXT = {
    "image": "jpg jpeg png gif webp heic heif bmp svg avif",
    "video": "mp4 mkv webm mov avi m4v 3gp",
    "audio": "mp3 m4a flac ogg opus wav aac",
    "archive": "zip tar gz tgz xz 7z rar zst bz2",
    "doc": "pdf doc docx odt txt md rtf xls xlsx ods ppt pptx odp epub csv",
    "apk": "apk",
}
BY_EXT = {e: k for k, exts in EXT.items() for e in exts.split()}

# This laptop's places, for the picker (those that exist).
PLACES = [("Home", "~", "user-home-symbolic"), ("Downloads", "~/Downloads", "folder-download-symbolic"),
          ("Documents", "~/Documents", "folder-documents-symbolic"),
          ("Pictures", "~/Pictures", "folder-pictures-symbolic"), ("Desktop", "~/Desktop", "user-desktop-symbolic"),
          ("Videos", "~/Videos", "folder-videos-symbolic"), ("Music", "~/Music", "folder-music-symbolic")]


def kind_of(name, is_dir, mime=""):
    if is_dir:
        return "dir"
    top = (mime or "").split("/")[0]
    if top in ("image", "video", "audio"):
        return top
    return BY_EXT.get(name.rsplit(".", 1)[-1].lower() if "." in name else "", "file")


def when(ms):
    if not ms:
        return ""
    t = ms / 1000
    return time.strftime("%-d %b" if time.time() - t < 300 * 86400 else "%-d %b %Y", time.localtime(t))


def tile(name, meta, kind, on_click, picked=False):
    """One card: the kind's tile, the name, what it is."""
    icon, color = KINDS[kind]
    b = Gtk.Button()
    b.add_css_class("ek-file")
    if picked:
        b.add_css_class("picked")
    row = Gtk.Box(spacing=12)
    pv = Gtk.Box(valign=Gtk.Align.CENTER, halign=Gtk.Align.START)
    pv.set_hexpand(False)          # a 40 px square, whatever its icon asks for
    pv.set_size_request(40, 40)
    pv.add_css_class("ek-file-pv")
    pv.add_css_class(f"k-{color}")
    img = Gtk.Image(icon_name="object-select-symbolic" if picked else icon, pixel_size=20,
                    hexpand=True, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    pv.append(img)
    row.append(pv)
    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
    text.append(ellipsized(name, "ek-file-t"))
    text.append(ellipsized(meta, "ek-file-s"))
    row.append(text)
    if kind == "dir":
        row.append(Gtk.Image(icon_name="go-next-symbolic", pixel_size=14, css_classes=["ek-file-go"]))
    b.set_child(row)
    b.connect("clicked", lambda *_: on_click())
    return b


def crumbs(box, parts, go):
    """A path you can click anywhere along: parts are (label, target); the
    last is where you are."""
    clear(box)
    for i, (label, target) in enumerate(parts):
        if i:
            box.append(L("/", "ek-crumb-sep"))
        if i == len(parts) - 1:
            box.append(L(label, "ek-crumb", "here"))
        else:
            b = Gtk.Button(label=label)
            b.add_css_class("ek-crumb")
            b.connect("clicked", lambda *_, t=target: go(t))
            box.append(b)


def grid():
    return Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, min_children_per_line=2,
                       max_children_per_line=3, column_spacing=10, row_spacing=10, valign=Gtk.Align.START)


class Files(View):
    hints = [Hint("Enter", "open"), Hint("Space a f", "send files")]

    def build(self):
        self.path = "~"
        self.items = None
        self.sending = None
        self.picking = False
        self.here = os.path.expanduser("~")
        self.picked = {}
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, vexpand=True)
        root.add_css_class("ek-page")

        # ---- the phone's files
        self.phone_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, vexpand=True)
        bar = Gtk.Box(spacing=8)
        self.trail = Gtk.Box(spacing=2, hexpand=True, valign=Gtk.Align.CENTER)
        bar.append(self.trail)
        self.send_btn = button("Send files", self.pick, "accent", "send")
        bar.append(self.send_btn)
        self.phone_page.append(bar)
        self.grid = grid()
        self.phone_page.append(scroller(self.grid))
        self.drop = L("", "ek-drop")
        self.phone_page.append(self.drop)
        root.append(self.phone_page)

        # ---- the picker: this laptop's files
        self.pick_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, vexpand=True)
        head = Gtk.Box(spacing=10)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        titles.append(L("Send to the phone", "ek-pick-title", xalign=0))
        titles.append(L("Pick files on this laptop; they land in the phone's Download/ekatva",
                        "ek-pick-sub", xalign=0))
        head.append(titles)
        head.append(button("Cancel", self.cancel_pick, "soft"))
        self.go_btn = button("Send", self.send_picked, "accent", "send")
        head.append(self.go_btn)
        self.pick_page.append(head)
        self.places = Gtk.Box(spacing=6)
        for label, path, icon in PLACES:
            full = os.path.expanduser(path)
            if not os.path.isdir(full):
                continue
            b = Gtk.Button()
            b.add_css_class("ek-place")
            inner = Gtk.Box(spacing=6)
            inner.append(Gtk.Image(icon_name=icon, pixel_size=14))
            inner.append(L(label))
            b.set_child(inner)
            b.connect("clicked", lambda *_, p=full: self.local(p))
            self.places.append(b)
        self.pick_page.append(self.places)
        self.local_trail = Gtk.Box(spacing=2)
        self.pick_page.append(self.local_trail)
        self.local_grid = grid()
        self.pick_page.append(scroller(self.local_grid))
        self.pick_page.set_visible(False)
        root.append(self.pick_page)

        target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        target.connect("drop", self.dropped)
        target.connect("enter", lambda *_: (self.drop.add_css_class("over"), Gdk.DragAction.COPY)[1])
        target.connect("leave", lambda *_: self.drop.remove_css_class("over"))
        root.add_controller(target)
        return root

    def shown(self, force=False):
        if not self.picking:
            self.load()

    # ------------------------------------------------------------ the phone's
    def load(self):
        p = self.p
        self.update()
        if not p.online():
            return
        path = self.path
        p.run(lambda: p.rpc.phone("files.list", {"path": path}), lambda r: self.got(path, r))

    def got(self, path, items):
        if path != self.path:
            return
        self.items = sorted(items or [], key=lambda f: (f.get("kind") != "dir", f.get("name", "").lower()))
        self.update()

    def go_to(self, path):
        self.path = path or "~"
        self.items = None
        self.load()

    def open(self, f):
        if f.get("kind") == "dir":
            self.go_to(f["path"])
        elif f.get("kind") == "file":
            self.save(f)

    def go_up(self):
        if self.path not in ("~", "/", ""):
            self.go_to(self.path.rsplit("/", 1)[0] or "~")

    def escape(self):
        if self.picking:
            here, home = self.here.rstrip("/"), os.path.expanduser("~")
            if here != home and here.startswith(home):
                self.local(os.path.dirname(here))
            else:
                self.cancel_pick()
            return True
        if self.path not in ("~", "/", ""):
            self.go_up()
            return True
        return False

    def update(self):
        p = self.p
        parts = [x for x in self.path.strip("~/").split("/") if x] if self.path not in ("~", "") else []
        trail = [("The phone", "~")] + [(x, "~/" + "/".join(parts[:i + 1])) for i, x in enumerate(parts)]
        crumbs(self.trail, trail, self.go_to)
        self.send_btn.set_sensitive(bool(p.online()) and self.sending is None)
        self.drop.set_label(self.sending or "Drop files here to send them to the phone (Download/ekatva)")
        if not self.changed("grid", self.path, self.items, bool(p.online())):
            return
        clear(self.grid)
        if not p.online():
            self.grid.append(L("The phone isn't connected", "ek-empty"))
            return
        if self.items is None:
            self.grid.append(L("Loading…", "ek-empty"))
            return
        if not self.items:
            self.grid.append(L("This folder is empty", "ek-empty"))
        for f in self.items[:SHOW]:
            is_dir = f.get("kind") == "dir"
            meta = "Folder" if is_dir else " · ".join(x for x in (size(f.get("size", 0)), when(f.get("mtime"))) if x)
            self.grid.append(tile(f.get("name", ""), meta, kind_of(f.get("name", ""), is_dir, f.get("mime")),
                                  lambda f=f: self.open(f)))

    def save(self, f):
        """A file from the phone into ~/Downloads (a new name if one is there)."""
        p = self.p
        name = f.get("name") or "file"
        dest_dir = os.path.expanduser("~/Downloads")
        if self.sending:
            return p.say("Wait for the file on its way first", bad=True)

        def work():
            os.makedirs(dest_dir, exist_ok=True)
            stem, ext = os.path.splitext(name)
            path, n = os.path.join(dest_dir, name), 1
            while os.path.exists(path):
                path = os.path.join(dest_dir, f"{stem} ({n}){ext}")
                n += 1
            part, off, total = path + ".part", 0, f.get("size", 0)
            try:
                with open(part, "wb") as out:
                    while True:
                        r = p.rpc.phone("files.read", {"path": f["path"], "offset": off, "length": PIECE})
                        chunk = base64.b64decode(r.get("data") or "")
                        out.write(chunk)
                        off += len(chunk)
                        self.progress_later(f"Saving {name}: {off * 100 // max(1, total)}%")
                        if r.get("eof") or not chunk:
                            break
                os.replace(part, path)
                return ("ok", path)
            except Exception as e:  # noqa: BLE001  (the phone went away, no space: say so, nothing half-written)
                if os.path.exists(part):
                    os.remove(part)
                return ("bad", f"Couldn't save {name}: {e}")

        def after(r):
            self.sending = None
            self.update()
            kind, text = r
            p.say(f"Saved to {text.replace(os.path.expanduser('~'), '~')}" if kind == "ok" else text,
                  bad=kind != "ok")

        self.sending = f"Saving {name}…"
        self.update()
        p.run(work, after)

    def progress_later(self, text):
        def show():
            if self.sending:
                self.sending = text
                self.update()
            return False
        GLib.idle_add(show)

    # ------------------------------------------------------------ the picker
    def pick(self):
        if not self.p.online():
            return self.p.say("The phone isn't connected", bad=True)
        self.picking = True
        self.picked = {}
        self.phone_page.set_visible(False)
        self.pick_page.set_visible(True)
        self.local(self.here if os.path.isdir(self.here) else os.path.expanduser("~"))
        return None

    def cancel_pick(self):
        self.picking = False
        self.pick_page.set_visible(False)
        self.phone_page.set_visible(True)
        self.update()

    def local(self, path):
        """Show a folder on this laptop in the picker."""
        self.here = path
        home = os.path.expanduser("~")
        rel = os.path.relpath(path, home) if path.startswith(home) else path
        parts = [] if rel == "." else [x for x in rel.split("/") if x]
        trail = [("Home", home)] + [(x, os.path.join(home, *parts[:i + 1])) for i, x in enumerate(parts)]
        crumbs(self.local_trail, trail, self.local)
        try:
            with os.scandir(path) as it:
                entries = [e for e in it if not e.name.startswith(".")]
        except OSError as e:
            entries = []
            self.p.say(f"Can't open {rel}: {e.strerror}", bad=True)
        entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=True), e.name.lower()))
        clear(self.local_grid)
        if not entries:
            self.local_grid.append(L("Nothing here", "ek-empty"))
        for e in entries[:SHOW]:
            is_dir = e.is_dir(follow_symlinks=True)
            try:
                st = e.stat()
            except OSError:
                continue
            meta = "Folder" if is_dir else f"{size(st.st_size)} · {when(st.st_mtime * 1000)}"
            full = e.path
            if is_dir:
                self.local_grid.append(tile(e.name, meta, "dir", lambda f=full: self.local(f)))
            else:
                self.local_grid.append(tile(e.name, meta, kind_of(e.name, False), lambda f=full: self.toggle(f),
                                            picked=full in self.picked))
        self.count()

    def toggle(self, path):
        if path in self.picked:
            del self.picked[path]
        else:
            try:
                self.picked[path] = os.path.getsize(path)
            except OSError:
                return
        self.local(self.here)

    def count(self):
        n, total = len(self.picked), sum(self.picked.values())
        self.go_btn.set_sensitive(n > 0 and self.sending is None)
        label = f"Send {n} file{'s' if n != 1 else ''} · {size(total)}" if n else "Send"
        box = self.go_btn.get_child()
        last = box.get_last_child() if isinstance(box, Gtk.Box) else None
        if isinstance(last, Gtk.Label):
            last.set_label(label)
        else:
            self.go_btn.set_label(label)

    def send_picked(self):
        paths = list(self.picked)
        self.cancel_pick()
        self.send(paths)

    # ------------------------------------------------------------ sending
    def dropped(self, _t, value, _x, _y):
        self.drop.remove_css_class("over")
        paths = [f.get_path() for f in value.get_files() if f.get_path()]
        self.send(paths)
        return True

    def send(self, paths):
        paths = [x for x in paths if x and os.path.isfile(x)]
        if not paths:
            return self.p.say("Only files can be sent (not folders)", bad=True)
        if self.sending:
            return self.p.say("Wait for the file on its way first", bad=True)
        p = self.p

        def work():
            sent = []
            for path in paths:
                name, total = os.path.basename(path), os.path.getsize(path)
                try:
                    r = p.rpc.phone("share.begin", {"name": name, "size": total}, mutation=True)
                    with open(path, "rb") as fh:
                        off = 0
                        while chunk := fh.read(PIECE):
                            p.rpc.phone("share.put", {"id": r["id"], "data": base64.b64encode(chunk).decode()},
                                        mutation=True)
                            off += len(chunk)
                            self.progress_later(f"Sending {name}: {off * 100 // max(1, total)}%")
                    p.rpc.phone("share.finish", {"id": r["id"]}, mutation=True)
                    sent.append(name)
                except Exception as e:  # noqa: BLE001  (the phone went away, a file vanished: say which)
                    return ("bad", f"Couldn't send {name}: {e}" + (f" ({len(sent)} sent before it)" if sent else ""))
            return ("ok", f"Sent {len(sent)} file{'s' if len(sent) != 1 else ''} to the phone (Download/ekatva)")

        def after(r):
            self.sending = None
            self.update()
            kind, text = r
            p.say(text, bad=kind != "ok")
            if kind == "ok":
                self.load()

        self.sending = "Sending…"
        self.update()
        p.run(work, after)
