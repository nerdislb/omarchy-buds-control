# Verification — 0.1.0 preview

Date: 2026-09-20. Reference: Omarchy 4.0.4-1 / Quickshell 0.3.1-1,
Hyprland 0.56.2, BlueZ 5.87, pbpctrl 0.1.8. Plugin sources are derived from
nbshell `bfda154ee3c54b67a96d2f1bf162392dce2802d8` and compose the installed
Omarchy audio/Bluetooth panel primitives.

## Checks

- **29 backend unit tests passed**, covering real pbpctrl output, unsupported modes,
  unknown and zero charge, renamed headsets, disconnects, contention, read-back
  mismatch, BudsLink hold/release and preventing auto-start/takeover.
  A real session-bus Ping confirmed void methods emit empty stdout; the BudsLink
  bridge handles that separately from malformed JSON and has regression coverage.
- Real QML smoke test: two widgets share one controller; immediate repeated
  refreshes are serialized; removing the last widget stops the worker.
- Omarchy manifest validation, Python compilation and installer shell syntax.
- Real installed panel inspected with connected Pixel Buds Pro 2. ANC and a
  right-bud battery reading were returned. Left and case were not reported;
  the UI correctly used `—` rather than inventing charge values.
- A real write of the **already-selected ANC mode** was acknowledged and read
  back successfully. This deliberately did not change the user's listening mode.
- After the final shell restart, runtime status reported two widget instances,
  one shared connected controller, and the original ANC mode. The installed
  payload matched the source. Opening, keyboard navigation/refresh and Escape
  dismissal were verified in the installed panel as well.
- Synthetic real-component preview: dark palette and shipped Catppuccin Latte
  colors, 300×330 narrow viewport, keyboard scrolling, loading, disconnected and
  error states. Tab moved the cursor; Enter selected a fixture mode; Escape
  closed the panel. These fixture actions never touched a headset.
- Compared with the immediate pre-install backup, the final installer preserves
  `shell.json` including unrelated changes made concurrently by the user. Existing
  pairings, Bluetooth/PipeWire settings, keybindings and desktop theme are not
  modified. Its backup path is documented in the README.

## Honest limits

- Switching between different modes on real hardware, other Pixel Buds models,
  multiple simultaneously connected Pixel devices, suspend/reconnect and the
  optional live BudsLink path still need broader hardware acceptance.
- Adaptive is absent in pbpctrl 0.1.8; a future CLI exposing it is detected but
  that alone does not prove device/firmware compatibility.
- Dark/light fixture pictures are sample data, not hardware evidence. The light
  preview loads the shipped palette in a separate process, not a global theme swap.
- This plugin adds no animations. Shared Omarchy controls retain their own
  motion behavior; no separate Reduced Motion guarantee is made for upstream UI.
- An independent Antigravity UI/API review was performed (Gemini 3.8 Flash High
  requested; identity reported by that tool's response, not independently attested).
  Fable and a bounded Opus fallback timed out without review output. No completed
  Claude code review is claimed. The main implementation/checks used GPT-6 Astra.
- GitHub Actions are prepared but are not considered passed until run remotely.
  No public repository or release was created by the local installation.

## Design decisions

The popup uses `Panel`, `KeyboardPanel`, `PanelHero`, `PanelSectionHeader`,
`PanelSeparator`, `Button` and Omarchy color/spacing/type tokens. Mode buttons
wrap rather than forcing a non-wrapping ButtonGroup into narrow panels. Standard
controls retain Omarchy states. A ref-counted QML singleton supplies the shared
controller because replacement bars intentionally have no generic access to
plugin service instances through `bar.shell`. Its one IPC handler selects the
focused monitor rather than registering competing handlers on every screen.

Raw hardware logs and desktop screenshots are deliberately not included in the
repository. Published sample screenshots, if included, are synthetic fixtures.
