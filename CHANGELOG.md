# Changelog

## Unreleased

- **Files, redone.** Cards with a coloured tile for each kind (folders, images, video, audio, documents, archives, apps), the name, size and date; the path at the top is clickable anywhere along it (the Up button is gone; Esc still goes up).
- **Sending files has its own picker, inside the popup** (no system dialog): this laptop's places (Home, Downloads, Documents, Pictures…), its folders, tick the files, one Send with their count and size. Dropping files on the page still sends them.
- **Search in Messages and Calls**, by name or number (any part of it, e.g. the last digits): a box above each list, or `Space s`.
- **One box, not two, in every text box**: focus lights the box's own border (with Vyom's matching fix).
- A call row says it calls back wherever you click it (a green call badge on every row). Overview is now **Home**.
- **Caffeine is now Jyoti** (ज्योति, the flame), as everywhere in ekatva: its levels are **Śānta** (शान्त, at rest), **Akhaṇḍa** (अखण्ड, the unbroken flame) and **Nandādīpa** (नन्दादीप, the lamp kept burning day and night). The Overview tile shows each lit level's lamp, a plain line drawing in its colour: the diya unlit (lilac-grey) for Śānta, the diya (blue) for Akhaṇḍa, the samai (ember) for Nandādīpa, drawn at exactly its size times the screen's scale. As on the phone, the lamp is the tile's focus (120 px at the top right), with the name and a one-line description beneath it. Keys: `Space j s` / `j a` / `j n` (were `Space c …`); colours `@jyoti-akhanda` / `@jyoti-nanda`. Old log entries still show with its icon.
- **Fixed: the popup could grow wider than the screen** (a long message or file name widened it, and everything slid off). Its size is fixed now; long text is cut with "…".
- **Fixed: the cursor jumped back every 3 seconds** (each poll rebuilt the lists, and the control you'd moved to with j / k with them). Lists are redrawn only when what they show changed: no flicker either.
- **Fixed: "ekatva is off" never showed.** With the service off, a banner says so, with a Turn it on button (`[plugin.ekatva] turn_on`, default `systemctl --user start ekatva.service`).
- Opens with nothing selected: a stray Enter does nothing (it used to land on caffeine's Off), and j starts at Ring. The cursor ring shows on every control; buttons that can't work right now (the phone isn't linked) look it.
- The phone gone, a permission off, the service restarting mid-call: said in the footer in plain words, never a traceback; the client reconnects by itself.
- The overview loads the last messages and calls by itself (at most every 5 minutes: each read is in the phone's log), and says why a list is empty (loading, not connected, ekatva off, nothing yet).
- The lamp says when the phone hasn't allowed light and dark ("Laptop only").
- Files: tap a file to save it to ~/Downloads; "Send a file" steps aside for the file picker (the popup holds the keyboard) and comes back; failed sends and saves say which file and why, and leave nothing half-written.
- Opening on a place (`vyom ekatva calls`) moves the tab bar to it too.
- Devices: the phone's own notifications permission is named for what it does ("Send its notifications here").

- First version: ekatva's laptop window as a Vyom popup (Overview, Messages, Calls, Files, Log, Devices), replacing the Electron window. Opens instantly; talks to ekatva's service over its socket with a small tRPC client (standard library only).
