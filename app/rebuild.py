import os
import struct
import shutil
from pathlib import Path

from app.progress_window import ProgressWindow
from app.i18n import t


# ---------------------------------------------------------
# Unpack resources.gpak → output_dir (with progress)
# ---------------------------------------------------------
def manual_unpack(game_dir, output_dir):
    """
    Manually unpack resources.gpak into output_dir.
    Called only from the Tools menu.
    """

    gpak_path = Path(game_dir) / "resources.gpak"
    out_dir = Path(output_dir)

    if not gpak_path.exists():
        raise FileNotFoundError(f"resources.gpak not found in: {game_dir}")

    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    # First pass: count entries
    with gpak_path.open("rb") as f:
        count = struct.unpack("<i", f.read(4))[0]

    pw = ProgressWindow(None, t("progress.unpacking"), count)

    # Actual unpack
    with gpak_path.open("rb") as f:
        count = struct.unpack("<i", f.read(4))[0]

        entries = []
        for _ in range(count):
            path_len = struct.unpack("<h", f.read(2))[0]
            path = f.read(path_len).decode("utf-8")
            file_len = struct.unpack("<i", f.read(4))[0]
            entries.append((path, file_len))

        for i, (path, file_len) in enumerate(entries):
            out_path = out_dir / path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            data = f.read(file_len)
            with out_path.open("wb") as out:
                out.write(data)

            pw.update(i + 1)

    pw.close()


# ---------------------------------------------------------
# Repack a folder → resources.gpak (with progress)
# ---------------------------------------------------------
def manual_repack(source_dir, output_gpak):
    """
    Manually repack all files in source_dir into output_gpak.
    Called only from the Tools menu.
    """

    source_root = Path(source_dir)
    output_gpak = Path(output_gpak)

    if not source_root.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_dir}")

    output_gpak.parent.mkdir(parents=True, exist_ok=True)

    # Collect all files
    files = [p for p in source_root.rglob("*") if p.is_file()]
    pw = ProgressWindow(None, t("progress.repacking"), len(files))

    with output_gpak.open("wb") as f:
        # Write file count
        f.write(struct.pack("<i", len(files)))

        # Write file headers
        for relpath in files:
            rel = relpath.relative_to(source_root).as_posix()
            rel_bytes = rel.encode("utf-8")
            f.write(struct.pack("<h", len(rel_bytes)))
            f.write(rel_bytes)
            f.write(struct.pack("<i", relpath.stat().st_size))

        # Write file contents
        for i, relpath in enumerate(files):
            with relpath.open("rb") as src:
                f.write(src.read())
            pw.update(i + 1)

    pw.close()
