# Provenance and dependencies

- The Python bridge is adapted from **Buds Control in nbshell**, commit
  `bfda154ee3c54b67a96d2f1bf162392dce2802d8`,
  <https://github.com/nerdislb/nbshell/tree/bfda154ee3c54b67a96d2f1bf162392dce2802d8/plugins/buds-control>.
  Copyright (c) 2026 Bernhard Slatinsek, MIT. The original notice is retained in
  this repository's LICENSE.
- The QML UI composes the installed **Omarchy** `qs.Ui` and `qs.Commons` APIs.
  Reference surfaces: `shell/plugins/panels/audio/Panel.qml` and
  `shell/plugins/panels/bluetooth/Panel.qml` from the Omarchy 4.0.4-1 package.
  No Omarchy source code, fonts or theme assets are vendored.
  Upstream: <https://github.com/omacom/omarchy> (MIT).
- **pbpctrl**, <https://github.com/qzed/pbpctrl>, MIT OR Apache-2.0. Invoked as
  an independently installed executable; no binary or Rust code is bundled.
- **BudsLink**, <https://github.com/maniacx/BudsLink>, is an optional independently
  installed application. This plugin only calls its public session D-Bus API.
  No BudsLink source, assets or binaries are bundled.

This repository contains no Bluetooth identifiers, user-specific configuration,
private account data, or screenshots from a personal desktop.
