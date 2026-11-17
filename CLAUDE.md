# ekatva for Vyom -- notes for agents

ekatva's laptop window as a Vyom tool, in its own repo per Vayu's plugin rule. ekatva itself (the service, the phone app, the protocol) is github.com/Theyashsawarkar/ekatva: a change there that this needs (a new procedure) goes there first.

- `ekatva/rpc.py`: tRPC over ekatva's Unix socket (RFC 6455 by hand, no dependencies). Calls block: only from worker threads (`plugin.run` / `panel.background`); subscription data arrives on the main loop.
- `ekatva/__init__.py`: the Plugin, the shared state, the call banner; `ekatva/views/*`: one module per place (a View: build, update from state, shown loads what only it needs).
- Reads that the phone logs (messages, calls, its clipboard) only on demand, never on every opening.
- Keys: `ekatva/vim.py` (Space grammar); run `python3 scripts/keybinds.py` after changing it.
- Colours: the theme's (Vyom's names) only, except jyoti's @jyoti-akhanda / @jyoti-nanda, ekatva's own.
- Test headless only (a nested sway, `EKATVA_SOCKET` pointing at the service's socket); never press anything that acts on the real phone in a test.
- Every change: a CHANGELOG.md entry. `python -m py_compile ekatva/*.py ekatva/views/*.py` must pass.
