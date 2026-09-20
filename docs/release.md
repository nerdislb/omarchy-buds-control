# Publishing

The repository is ready for a **preview**, not a claim of broad hardware support.
Local installation does not create, push or publish a GitHub repository.

Before a public release:

1. Read `verification.md` and retain the unverified hardware limitations.
2. Run the backend tests, `tests/qml_smoke.py` in an Omarchy session, and
   `omarchy plugin validate .`.
3. Confirm the public repository name and visibility. Add its URL to
   `manifest.json` (`repository`) and replace the README's placeholder command.
4. Push the reviewed tree, verify the included GitHub Actions checks, then tag
   the tested version. Include `CHANGELOG.md`, LICENSE and THIRD_PARTY.md.
5. Test `omarchy plugin add <repository-url> --enable` from a clean user setup.
6. Only then submit a separate listing to an Omarchy plugin directory if desired.

Never include helper status dumps, Bluetooth addresses, personal device aliases,
home-directory paths, private screenshots, account files, or local review logs.
Do not bundle pbpctrl or BudsLink binaries; they are independent dependencies.
