# Buds Control for Omarchy

A native Omarchy bar plugin for **Google Pixel Buds Pro / Pro 2**, ported from
[nbshell's Buds Control](https://github.com/nerdislb/nbshell/tree/main/plugins/buds-control).
Uses [pbpctrl](https://github.com/qzed/pbpctrl) rather than reimplementing the
Bluetooth protocol. Optional [BudsLink](https://github.com/maniacx/BudsLink)
support retains the original plugin's fallback for other headsets.

## Features

- Quiet headphones icon; click to open a native, theme-aware Omarchy panel.
- Separate left, right and case battery readings, including charging status.
- Off, Transparency and ANC; Adaptive only when the installed pbpctrl exposes it.
- Pixel Buds changes are read back before showing **Noise control confirmed**.
- Native keyboard navigation, scrollable small-screen layout and English UI.
- Compatible with the stock bar and the Fold Bar replacement, with one shared
  controller across monitors and serialized Bluetooth requests.
- Optional running BudsLink backend, device switching and full-settings shortcut.

**Preview release:** software checks and device verification are recorded in
[docs/verification.md](docs/verification.md). Do not infer hardware support from
fixture screenshots or from the presence of a CLI option.

## Requirements

- Omarchy 4's Quickshell plugin system (developed against **Omarchy 4.0.4**, Quickshell 0.3.1).
  Not a Waybar plugin for older Omarchy versions.
- Python 3.10+, `bluetoothctl`, `busctl`, `dbus-monitor` (standard Omarchy packages).
- `pbpctrl` for direct Pixel Buds controls. Install separately:

```sh
omarchy pkg aur add pbpctrl
```

This AUR package is built locally; its build dependencies include Rust and
protobuf. Review its PKGBUILD as with any AUR package. The plugin never installs
packages or requests root itself.

## Install

```sh
omarchy plugin add https://github.com/nerdislb/omarchy-buds-control --enable
```

This does **not** install pbpctrl; install that dependency separately as above.
Alternatively, from a checkout:

```sh
./install.sh
```

The installer copies only this plugin to
`~/.config/omarchy/plugins/io.github.nerdislb.buds-control`, backs up an existing
copy and `shell.json` under `~/.local/state/omarchy-buds-control/backups`, then
uses Omarchy's own enable command. It does not replace your bar or edit BlueZ,
PipeWire, pairings, accounts, keybindings or other plugins. Use `--no-enable` to
copy without adding a bar entry. First installation is discovered live. If an
upgrade still uses cached QML, run `omarchy restart shell` once (this briefly
restarts the bar and the other shell plugins too). The installer does not force
that restart. Git-managed installs should use `omarchy plugin update` instead.

Move the icon using Omarchy's bar editor. Open it from a terminal with:

```sh
omarchy-shell io.github.nerdislb.buds-control open
omarchy-shell io.github.nerdislb.buds-control status
```

## Controls

| Input | Action |
| --- | --- |
| Click the bar icon | Open / close |
| Arrows, j/k/h/l, Tab / Shift+Tab | Move the visible cursor through controls |
| Enter / Space | Activate the selected control |
| R | Refresh |
| Escape / outside click | Close |
| Right-click (BudsLink backend) | Open full settings |

The selected ANC mode always reflects the backend, not an optimistic local
change. A failed or disconnected device clears controls; unknown battery charge
is shown as `—`, not 0%. Case charge is only available when relayed by a bud and
may be absent or older than the earbud readings. The stable pbpctrl **0.1.8**
offers Off / Transparency / ANC, not Adaptive. EQ, firmware updates, conversation
detection and other phone-app settings were not part of the old plugin and are
not implemented here. The direct backend selects the first connected Pixel
Buds Pro device; BudsLink's devices can be cycled with **Next headset**.

### BudsLink (optional)

Open BudsLink yourself if you want to use it. While it is running, the plugin
uses its reported devices/modes and never starts a competing pbpctrl connection.
Close BudsLink to return to direct Pixel Buds control. The plugin does not
auto-start or kill BudsLink, and balances temporary D-Bus service holds.
Full settings supports a `budslink` executable or the official Flatpak
`io.github.maniacx.BudsLink`. Other packaging launchers are not auto-detected.

## Remove / recover

```sh
omarchy plugin disable io.github.nerdislb.buds-control
omarchy plugin remove io.github.nerdislb.buds-control
```

Disabling the last widget stops this plugin's polling and helper processes.
Your Bluetooth pairings and installed backend packages remain unchanged. Restore
only the plugin from its backup if needed; restoring an entire old `shell.json`
would also undo any unrelated bar changes made since the backup.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 tests/qml_smoke.py
omarchy plugin validate .
python3 budsctl.py status
```

Helper output contains local Bluetooth device identifiers; do not publish real
status dumps. Tests use fictional addresses and mocked backends. No cloud service,
telemetry, credentials, daemon, automatic pairing or Bluetooth experimental mode
is required. Like other Omarchy QML plugins this runs unsandboxed in your shell.

Run `python3 tests/preview.py` or add `--light` for a separate synthetic UI
preview. `--screen OUTPUT` selects its monitor. This fixture never controls
headsets or changes your desktop theme. Stop it with Ctrl+C. The QML smoke test
requires a running Omarchy Wayland session; the backend tests are headless.

MIT licensed. See [THIRD_PARTY.md](THIRD_PARTY.md) for provenance and upstream
dependencies. Pixel Buds is a Google trademark; this is an independent project.
