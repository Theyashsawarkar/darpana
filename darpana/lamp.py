"""Jyoti's flame (ज्योति: keeping the laptop awake): the flame at dusk for
Śānta (at rest, its colour drained to lilacs), blue for Akhaṇḍa (the unbroken
flame), bright red for Nandādīpa (the flame kept burning day and night).

The drawings are ekatva's (apps/mobile/src/ui/jyoti-art.ts, written out by
apps/mobile/scripts/jyoti-art.mjs), copied to assets/jyoti/: the same flame as
the phone's. Vectors, always drawn at exactly the size shown times the
screen's scale: sharp, never a scaled picture.
"""
import os

from gi.repository import Gdk, GLib, Gtk

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = {"off": "flame-shanta.svg", "on": "flame-akhanda.svg", "high": "flame-nandadipa.svg"}
DRAWING = {}
for level, name in FILE.items():
    with open(os.path.join(HERE, "assets", "jyoti", name), encoding="utf-8") as f:
        DRAWING[level] = f.read()


def svg(level, px):
    """The drawing with its size set, so librsvg draws it at `px`, not at 200 and scaled."""
    return DRAWING[level].replace("<svg ", f'<svg width="{px}" height="{px}" ', 1)


class JyotiLamp(Gtk.Image):
    """The level's flame at `size` px."""

    def __init__(self, size, *cls, **kw):
        kw.pop("stroke", None)   # line drawings had a stroke width; these don't
        super().__init__(pixel_size=size, **kw)
        self.size, self.level = size, None
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
        data = svg(level, px).encode()
        self.set_from_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(data)))
