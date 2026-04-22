# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

from pathlib import Path
import shutil

def save_backup(p: Path | str) -> Path:
    """
    Create a rotating backup (0..99) of all .asm files in the given folder.

    Layout:
        <p>/
            backups/
                index.txt          # current backup index for next run
                000/               # backup set 0
                001/               # backup set 1
                ...

    Algorithm:
    - p must be a directory.
    - Ensure <p>/backups exists.
    - Read index from <p>/backups/index.txt; if missing or invalid, assume 0.
      This index is used for the *current* backup.
    - After using current index, increment it; if it reaches 100, wrap to 0,
      and write the new value back to index.txt for the next call.
    - Create (or recreate) subfolder "NNN" (3 digits) inside backups/
      corresponding to the current index.
    - Copy all *.asm files from <p> into that subfolder.
    - Return the path to the created backup folder.
    """
    base_dir = Path(p).resolve()

    if not base_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {base_dir}")

    backups_dir = base_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    index_file = backups_dir / "index.txt"

    # Read current index; if file is missing or broken, start from 0
    if index_file.is_file():
        try:
            current_index = int(index_file.read_text(encoding="utf-8").strip())
        except ValueError:
            current_index = 0
    else:
        current_index = 0

    # Use current_index for this backup
    if current_index < 0 or current_index >= 100:
        current_index = 0

    backup_dir_name = f"{current_index:03d}"
    backup_dir = backups_dir / backup_dir_name

    # Rotate index for next time
    next_index = current_index + 1
    if next_index >= 100:
        next_index = 0
    index_file.write_text(str(next_index), encoding="utf-8")

    # Recreate backup folder (remove old contents if any)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Copy all .asm files from base_dir into backup_dir
    for entry in base_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".asm":
            dst = backup_dir / entry.name
            shutil.copy2(entry, dst)

    return backup_dir
