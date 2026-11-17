"""Jyoti's lamps (ज्योति: keeping the laptop awake), plain line drawings in
one colour, like a glyph: the diya unlit for Śānta (at rest, lilac-grey),
the diya for Akhaṇḍa (the unbroken flame, blue) and the samai for
Nandādīpa (the lamp kept burning day and night, ember). Always drawn at
exactly the size shown times the screen's scale: sharp, never scaled.

The same drawings as the phone's (ekatva: apps/mobile/src/ui/icon.tsx,
"akhanda" and "nandadipa") and the bar's (dotfiles), on a 24 grid.
"""
from gi.repository import Gdk, GLib, Gtk

# ekatva's own two colours (style.css: @jyoti-akhanda, @jyoti-nanda).
COLOR = {"off": "#cbbfd8", "on": "#86aee0", "high": "#e58b52"}

DRAWING = {
    "off": '<path d="M4 14.5h16a8 6 0 0 1-16 0z"/><path d="M9.5 22h5"/><path d="M12 14.4v-1.6"/>'
           '<path d="M12 10.9c-1.2-1 .9-2.1-.2-3.4s.9-2.2.1-3.5" opacity=".75"/>',
    "on": '<path d="M4 14.5h16a8 6 0 0 1-16 0z"/><path d="M9.5 22h5"/>'
          '<path d="M12 4.6c1.9 2.3 2.7 4 2.7 5.3a2.7 2.7 0 0 1-5.4 0c0-1.3.8-3 2.7-5.3z"/><path d="M12 9.2v1.2"/>',
    "high": '<path d="M5 11.2h14c-.6 1.7-3.4 2.6-7 2.6s-6.4-.9-7-2.6z"/><path d="M12 13.8v5"/>'
            '<circle cx="12" cy="16" r="1.1"/><path d="M8.5 21.5h7l-1.2-2.7h-4.6z"/>'
            '<path d="M12 4.04c1.52 1.84 2.16 3.2 2.16 4.24a2.16 2.16 0 0 1-4.32 0c0-1.04.64-2.4 2.16-4.24z"/>'
            '<path d="M6.6 7.58c.8.97 1.13 1.68 1.13 2.23a1.13 1.13 0 0 1-2.27 0c0-.55.34-1.26 1.13-2.23z"/>'
            '<path d="M17.4 7.58c.8.97 1.13 1.68 1.13 2.23a1.13 1.13 0 0 1-2.27 0c0-.55.34-1.26 1.13-2.23z"/>',
}


def svg(level, px, stroke):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 24 24" '
            f'fill="none" stroke="{COLOR[level]}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">{DRAWING[level]}</svg>')


class JyotiLamp(Gtk.Image):
    """The level's lamp at `size` px."""

    def __init__(self, size, *cls, stroke=1.7, **kw):
        super().__init__(pixel_size=size, **kw)
        self.size, self.stroke, self.level = size, stroke, None
        self.set_can_target(False)
        for c in cls:
            self.add_css_class(c)
        self.set_visible(False)
        self.drawn = None
        self.connect("notify::scale-factor", lambda *_: self.paint())

    def set_level(self, level):
        self.level = level
        self.paint()

    def paint(self):
        level = self.level
        self.set_visible(level in DRAWING)
        if level not in DRAWING:
            return
        px = self.size * max(1, self.get_scale_factor())
        if self.drawn == (level, px):
            return
        self.drawn = (level, px)
        data = svg(level, px, self.stroke).encode()
        self.set_from_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(data)))
