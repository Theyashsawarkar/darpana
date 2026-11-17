"""The popup's own pieces: cards, the battery ring, the lamp, glyph buttons.

Colours come from the theme (Vyom's @green, @accent...): a drawing reads
the colour of its CSS class, so a theme change repaints it.
"""
import math
import time

from gi.repository import Gtk, Pango
from vyom import ui

L = ui.label

# Nerd Font glyphs (JetBrainsMono Nerd Font, Material Design range).
G = {
    "phone": "\U000f011c", "laptop": "\U000f0322", "bell": "\U000f009e", "lock": "\U000f033e",
    "eye": "\U000f0208", "send": "\U000f048a", "call": "\U000f03f2", "cup": "\U000f0176",
    "moon": "\U000f0594", "sun": "\U000f0599", "chat": "\U000f0361", "folder": "\U000f024b",
    "file": "\U000f0214", "image": "\U000f021f", "music": "\U000f075a", "list": "\U000f0279",
    "shield": "\U000f0483", "clip": "\U000f014c", "undo": "\U000f054c", "check": "\U000f012c",
    "plus": "\U000f0415", "up": "\U000f005d", "bolt": "\U000f0241", "signal": "\U000f08bf",
    "wifi": "\U000f05a9", "back": "\U000f004d", "hangup": "\U000f03f2", "keypad": "\U000f0b9d",
}


def clear(box):
    child = box.get_first_child()
    while child is not None:
        nxt = child.get_next_sibling()
        box.remove(child)
        child = nxt


def card(*children, cls=None, spacing=8, vertical=True):
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,
                spacing=spacing)
    b.add_css_class("ek-card")
    for c in (cls.split() if cls else []):
        b.add_css_class(c)
    for c in children:
        if c is not None:
            b.append(c)
    return b


def glyph(name, *cls, **kw):
    return L(G.get(name, name), "glyph", *cls, **kw)


def heading(text, icon, count="", count_color="accent", more=None):
    """A card's title row: an icon chip, the name, a count badge, a link on the right."""
    row = Gtk.Box(spacing=8)
    row.add_css_class("ek-head")
    row.append(glyph(icon, "ek-head-ic", valign=Gtk.Align.CENTER))
    row.append(L(text, "ek-head-t", valign=Gtk.Align.CENTER))
    if count:
        row.append(L(str(count), "ek-count", f"ek-bg-{count_color}", valign=Gtk.Align.CENTER))
    row.append(Gtk.Box(hexpand=True))
    if more:
        text_, cb = more
        b = Gtk.Button(label=text_, valign=Gtk.Align.CENTER)
        b.add_css_class("ek-link")
        b.connect("clicked", lambda *_: cb())
        row.append(b)
    return row


def action(icon, text, cb, cls=""):
    """A square button: a glyph over a word (the phone card's actions)."""
    b = Gtk.Button()
    b.add_css_class("ek-act")
    if cls:
        b.add_css_class(cls)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
    b.icon = glyph(icon, "ek-act-ic")
    b.text = L(text, "ek-act-t")
    box.append(b.icon)
    box.append(b.text)
    b.set_child(box)
    b.connect("clicked", lambda *_: cb())
    return b


def button(text, cb, cls="", icon=""):
    b = Gtk.Button()
    b.add_css_class("ek-btn")
    for c in cls.split():
        b.add_css_class(c)
    box = Gtk.Box(spacing=7, halign=Gtk.Align.CENTER)
    if icon:
        box.append(glyph(icon))
    box.append(L(text))
    b.set_child(box)
    b.connect("clicked", lambda *_: cb())
    return b


def avatar(name):
    letter = (name or "?").strip()[:1].upper() or "?"
    if not letter.isalpha():
        letter = "#"
    return L(letter, "ek-av", valign=Gtk.Align.CENTER)


def ellipsized(text, *cls, xalign=0, chars=8):
    """A one-line label that's cut with "…" and never widens the popup: its
    natural width is a few characters; it grows only into space it's given."""
    w = L(text, *cls, xalign=xalign, ellipsize=Pango.EllipsizeMode.END)
    w.set_max_width_chars(chars)
    w.set_width_chars(1)
    w.set_hexpand(True)
    return w


def scroller(child, vexpand=True):
    s = Gtk.ScrolledWindow(vexpand=vexpand, hexpand=True)
    s.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    s.set_child(child)
    return s


class _Drawn(Gtk.DrawingArea):
    def __init__(self, w, h, cls):
        super().__init__(content_width=w, content_height=h, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        for c in cls.split():
            self.add_css_class(c)
        self.set_draw_func(self.draw)

    def rgb(self):
        c = self.get_color()
        return c.red, c.green, c.blue


class Ring(_Drawn):
    """The battery ring: a faint track and an arc in the drawing's colour."""

    def __init__(self, size=100, width=7):
        super().__init__(size, size, "ek-ring")
        self.fraction, self.width = 0.0, width

    def set(self, fraction, color):
        self.fraction = max(0.0, min(1.0, fraction))
        for c in ("t-green", "t-yellow", "t-red", "t-gray"):
            self.remove_css_class(c)
        self.add_css_class(f"t-{color}")
        self.queue_draw()

    def draw(self, _a, cr, w, h):
        r, g, b = self.rgb()
        cx, cy, rad = w / 2, h / 2, min(w, h) / 2 - self.width / 2 - 2
        cr.set_line_width(self.width)
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.arc(cx, cy, rad, 0, 2 * math.pi)
        cr.stroke()
        if self.fraction > 0:
            cr.set_line_cap(1)
            # a soft glow under the arc
            cr.set_line_width(self.width + 5)
            cr.set_source_rgba(r, g, b, 0.16)
            cr.arc(cx, cy, rad, -math.pi / 2, -math.pi / 2 + 2 * math.pi * self.fraction)
            cr.stroke()
            cr.set_line_width(self.width)
            cr.set_source_rgba(r, g, b, 1)
            cr.arc(cx, cy, rad, -math.pi / 2, -math.pi / 2 + 2 * math.pi * self.fraction)
            cr.stroke()


class Lamp(_Drawn):
    """A pendant lamp: dark when the mode is dark, lit (a warm cone) when light."""

    def __init__(self):
        super().__init__(70, 78, "ek-lamp-art")
        self.lit = False

    def set_lit(self, lit):
        self.lit = lit
        (self.add_css_class if lit else self.remove_css_class)("lit")
        self.queue_draw()

    def draw(self, _a, cr, w, _h):
        r, g, b = self.rgb()
        cx = w / 2
        cr.set_source_rgba(1, 1, 1, 0.25)
        cr.set_line_width(1.4)
        cr.move_to(cx, 0)
        cr.line_to(cx, 16)
        cr.stroke()
        h = _h
        if self.lit:
            import cairo
            grad = cairo.LinearGradient(0, 40, 0, h)
            grad.add_color_stop_rgba(0, r, g, b, 0.38)
            grad.add_color_stop_rgba(1, r, g, b, 0.0)
            cr.move_to(cx - 15, 40)
            cr.line_to(cx - 30, h)
            cr.line_to(cx + 30, h)
            cr.line_to(cx + 15, 40)
            cr.close_path()
            cr.set_source(grad)
            cr.fill()
        # the shade
        cr.move_to(cx - 21, 40)
        cr.curve_to(cx - 21, 24, cx - 12, 16, cx, 16)
        cr.curve_to(cx + 12, 16, cx + 21, 24, cx + 21, 40)
        cr.close_path()
        if self.lit:
            cr.set_source_rgba(r, g, b, 1)
        else:
            cr.set_source_rgba(1, 1, 1, 0.14)
        cr.fill()
        # the bulb
        cr.save()
        cr.translate(cx, 41)
        cr.scale(8, 4.5)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        cr.set_source_rgba(1, 0.96, 0.85, 1) if self.lit else cr.set_source_rgba(1, 1, 1, 0.08)
        cr.fill()


def ago(ms):
    """'just now', '4 min', '3 h', 'Yesterday', '12 Nov'."""
    if not ms:
        return ""
    s = time.time() - ms / 1000
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)} min"
    lt, now = time.localtime(ms / 1000), time.localtime()
    if lt.tm_yday == now.tm_yday and lt.tm_year == now.tm_year:
        return time.strftime("%-I:%M %p", lt)
    if s < 2 * 86400 and (now.tm_yday - lt.tm_yday) % 366 == 1:
        return "Yesterday"
    if s < 6 * 86400:
        return time.strftime("%A", lt)
    return time.strftime("%-d %b", lt)


def duration(seconds):
    m, s = divmod(int(seconds), 60)
    if m >= 60:
        return f"{m // 60} h {m % 60} min"
    return f"{m} min" if m else f"{s} s"


def size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return ""


def search_box(placeholder, on_change):
    """A search box (Calls, Messages): one rounded box, a search icon."""
    e = Gtk.Entry(hexpand=True, placeholder_text=placeholder)
    e.add_css_class("ek-input")
    e.add_css_class("ek-search")
    e.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "system-search-symbolic")
    e.connect("changed", lambda *_: on_change())
    return e


def matches(query, name, number):
    """Does a person match the search: their name (any part), or their number
    (its digits, wherever they are: "98765" finds +91 98765 43210)?"""
    q = (query or "").strip().lower()
    if not q:
        return True
    if name and q in name.lower():
        return True
    digits = "".join(c for c in q if c.isdigit())
    return bool(digits) and len(digits) == len(q.replace(" ", "").replace("+", "")) and \
        digits in "".join(c for c in (number or "") if c.isdigit())
