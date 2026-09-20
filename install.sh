#!/usr/bin/env bash
# Install only this plugin; Omarchy merges its bar entry into the live config.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ${1:-} == --help ]]; then
  echo 'Usage: ./install.sh [--no-enable]'
  echo 'Install the plugin locally with a backup; dependencies are not installed.'
  exit 0
fi
[[ $# == 0 || ( $# == 1 && $1 == --no-enable ) ]] || { echo 'Use --help for usage.' >&2; exit 2; }
omarchy plugin validate "$source_dir"
python3 - "$source_dir" <<'PY'
from datetime import datetime
import json, os, pathlib, shutil, sys, tempfile
source = pathlib.Path(sys.argv[1])
config = pathlib.Path(os.environ.get('XDG_CONFIG_HOME', pathlib.Path.home()/'.config'))/'omarchy'
state = pathlib.Path(os.environ.get('XDG_STATE_HOME', pathlib.Path.home()/'.local/state'))/'omarchy-buds-control'
plugin_id = json.loads((source/'manifest.json').read_text())['id']
target = config/'plugins'/plugin_id
if target.resolve() == source.resolve():
    raise SystemExit('Run install.sh from your source checkout, not the installed plugin.')
if (target/'.git').exists():
    raise SystemExit('Git-managed install detected. Use omarchy plugin update instead of replacing its checkout.')
target.parent.mkdir(parents=True, exist_ok=True)
backup = state/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup.mkdir(parents=True, mode=0o700)
shell_config = config/'shell.json'
if shell_config.exists():
    shutil.copy2(shell_config, backup/'shell.json')
if target.exists() or target.is_symlink():
    if not target.is_dir():
        raise SystemExit(f'Refusing to overwrite a non-directory: {target}')
    shutil.copytree(target, backup/'plugin', symlinks=True)
staging = pathlib.Path(tempfile.mkdtemp(prefix='.buds-control-', dir=target.parent))
try:
    for name in ('manifest.json','BarWidget.qml','budsctl.py','LICENSE','README.md','THIRD_PARTY.md'):
        shutil.copy2(source/name, staging/name)
    shutil.copytree(source/'backend', staging/'backend', ignore=shutil.ignore_patterns('__pycache__'))
    if (source/'docs').exists():
        shutil.copytree(source/'docs', staging/'docs')
    # Rename the previous install into the backup rather than deleting it.
    if target.exists() or target.is_symlink():
        target.rename(backup/'previous-install')
    try:
        staging.rename(target)
    except OSError:
        if (backup/'previous-install').exists():
            (backup/'previous-install').rename(target)
        raise
finally:
    if staging.exists():
        shutil.rmtree(staging)
print(f'Installed: {target}\nBackup: {backup}')
PY
omarchy-shell shell rescanPlugins
if [[ ${1:-} != --no-enable ]]; then
  # Preserve the current position on reinstall; never rewrite other entries.
  if omarchy plugin list --json | python3 -c 'import json,sys; rows=json.load(sys.stdin); sys.exit(0 if any(r.get("id")=="io.github.nerdislb.buds-control" and r.get("enabled") for r in rows) else 1)'; then
    omarchy plugin enable io.github.nerdislb.buds-control
  else
    omarchy plugin enable io.github.nerdislb.buds-control --section right
  fi
fi
if ! command -v pbpctrl >/dev/null; then
  echo 'For Pixel Buds, install the optional backend: omarchy pkg aur add pbpctrl'
fi
echo 'If an already-loaded version remains cached after an upgrade: omarchy restart shell'
