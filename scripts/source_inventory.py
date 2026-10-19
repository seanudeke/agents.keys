"""Inventory tracked regular files; exclude only this inventory's own output.

Run after merging the reviewed source to main, commit source_inventory.txt,
then read HEAD for the manuscript pin. A file cannot contain its own digest.
"""
from pathlib import Path
import hashlib
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
target=root/'source_inventory.txt'
paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
paths=sorted(p for p in paths if p!='source_inventory.txt')
lines=[]
for relative in paths:
    p=root/relative
    if not p.is_file() or p.is_symlink():
        raise SystemExit('inventory requires tracked regular files')
    lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+relative)
content='\n'.join(lines)+'\n'
if '--check' in sys.argv:
    if not target.exists() or target.read_text()!=content:
        raise SystemExit('source inventory does not match the tracked files')
else:
    target.write_text(content)
print(f'{len(paths)} files hashed; source_inventory.txt excluded to avoid self-reference')
