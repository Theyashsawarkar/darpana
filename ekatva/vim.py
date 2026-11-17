"""ekatva's keys, as data (Vayu's Space-leader grammar).

A card: NORMAL mode, and Vyom's card cursor moves through the controls
(j / k, gg / G, h / l) and presses one (Enter); i types in the place's box
(a message, a number). Ctrl+1..6 (and Tab) switch places. Space is the
leader: j jyoti (keeping the laptop awake), p the phone, l light and dark (this tool's nouns), and
the shared groups: g go to, y copy, a add, r refresh.

An action "verb:arg" runs Plugin.v_<verb>(count, arg) in ekatva/__init__.py.
"""
from vyom.keys import Bind

B = Bind
CARD = True
GROUPS = {" j": "jyoti (keep awake)", " p": "the phone", " l": "light and dark", " g": "go to", " y": "copy",
          " a": "add"}

LEADER = [
    B(" js", "jyoti:off", "Set jyoti Śānta (the laptop sleeps and locks as usual)"),
    B(" ja", "jyoti:on", "Set jyoti Akhaṇḍa (keep the laptop awake: no lock, no sleep until the lid shuts)"),
    B(" jn", "jyoti:high", "Set jyoti Nandādīpa (keep the laptop awake, even with the lid closed)"),
    B(" pr", "phone:ring", "Toggle phone ring (find it: full volume until pressed again)"),
    B(" pl", "phone:lock", "Lock the phone"),
    B(" pk", "phone:awake", "Toggle the phone's screen staying on"),
    B(" pa", "phone:answer", "Answer the phone's incoming call"),
    B(" ph", "phone:hangup", "Hang up the phone's call (or decline it)"),
    B(" pd", "phone:dial", "Dial a number from the phone (the Calls place)"),
    B(" ll", "look:laptop", "Toggle the laptop's light / dark mode"),
    B(" lp", "look:phone", "Toggle the phone's light / dark mode"),
    B(" lb", "look:both", "Switch both to light or dark (the lamp)"),
    B(" go", "go:over", "Go to home (the phone at a glance)"),
    B(" gm", "go:msgs", "Go to the phone's messages"),
    B(" gc", "go:calls", "Go to the phone's calls"),
    B(" gf", "go:files", "Go to the phone's files"),
    B(" gl", "go:log", "Go to the action log"),
    B(" gd", "go:devices", "Go to the paired devices and their permissions"),
    B(" yc", "clip:copy", "Copy the phone's clipboard to this laptop's"),
    B(" yp", "clip:send", "Copy this laptop's clipboard to the phone"),
    B(" ap", "pair", "Add a phone (shows the pairing code; works from any network)"),
    B(" af", "send", "Add a file to the phone (send it to Download/ekatva)"),
    B(" s", "search", "Search messages or calls by name or number"),
    B(" r", "refresh", "Reload what this place shows"),
]

SECTIONS = [("ekatva leader", "normal", "Leader (Space)", LEADER)]


def keys(_tab):
    return list(LEADER)
