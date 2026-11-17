"""The popup's places, one module each. A view builds its widget once and
redraws it from the plugin's state in update(); shown() runs when you go
to it (load what only it needs)."""


import json


class View:
    hints = []

    def __init__(self, plugin):
        self.p = plugin
        self.seen = {}
        self.widget = self.build()

    def changed(self, part, *data):
        """Whether `part` would draw anything new. Lists are rebuilt only then:
        a rebuild would throw away the control you moved to (the card cursor)
        every time the 3 s poll comes round, and flicker."""
        key = json.dumps(data, sort_keys=True, default=str)
        if self.seen.get(part) == key:
            return False
        self.seen[part] = key
        return True

    def build(self):
        raise NotImplementedError

    def update(self):
        pass

    def shown(self, force=False):
        pass

    def editables(self):
        return []
