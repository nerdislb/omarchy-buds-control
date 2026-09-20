# Publishing

The repository is ready for a **preview**, not a claim of broad hardware support.
Repository: https://github.com/nerdislb/omarchy-buds-control.
Local installation never creates, pushes or publishes a GitHub repository.

Before a public release:

1. Read `verification.md` and retain the unverified hardware limitations.
2. Run the backend tests, `tests/qml_smoke.py` in an Omarchy session, and
   `omarchy plugin validate .`.
3. Confirm the repository URL in `manifest.json` and README is correct.
4. Push the reviewed tree, verify the included GitHub Actions checks, then tag
   the tested version. Include `CHANGELOG.md`, LICENSE and THIRD_PARTY.md.
5. Test the README's `omarchy plugin add` command from a clean user setup.
6. Only then submit a separate listing to an Omarchy plugin directory if desired.

Never include helper status dumps, Bluetooth addresses, personal device aliases,
home-directory paths, private screenshots, account files, or local review logs.
Do not bundle pbpctrl or BudsLink binaries; they are independent dependencies.
