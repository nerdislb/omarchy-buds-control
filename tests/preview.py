#!/usr/bin/env python3
"""Run a separate synthetic preview; never changes the desktop theme or earbuds."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--light', action='store_true', help='Use installed Catppuccin Latte colors in this process only')
parser.add_argument('--screen', default='', help='Optional Wayland output name')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
omarchy = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))
with tempfile.TemporaryDirectory(prefix='buds-preview-') as directory:
    root = Path(directory)
    for name in ('Commons', 'Ui'):
        (root/name).symlink_to(omarchy/'shell'/name)
    (root/'Plugin').symlink_to(repo)
    (root/'shell.qml').write_text((repo/'tests/Preview.qml').read_text())
    env = dict(os.environ, BUDS_PREVIEW_SCREEN=args.screen)
    if args.light:
        env['BUDS_PREVIEW_COLORS'] = (omarchy/'themes/catppuccin-latte/colors.toml').read_text()
    print(f'Preview config: {root}', flush=True)
    try:
        subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env, check=True)
    except KeyboardInterrupt:
        pass
