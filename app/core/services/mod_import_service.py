import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Tuple

class ExistingModError(FileExistsError):
    """Raised when imported mod would overwrite existing mod folder..."""

    def __init__(self, mod_name: str, destination: str):
        super().__init__(f"Mod folder already exists: {destination}")
        self.mod_name = mod_name
        self.destination = destination

class ModImportService:
    """Import mod ZIP while collapsing redundant directories..."""

    _IGNORED_NAMES = {"__MACOSX", ".DS_Store", "Thumbs.db", "desktop.ini"} # I doubt someone will make mods on macOS but, just in case I guess! hahaha... - Tim
    _MOD_METADATA_FILES = {"description.json", "info.json", "modinfo.json"}

    def import_zip(self, zip_path: str, mod_folder: str, replace: bool = False) -> Tuple[str, str]:
        zip_file = Path(zip_path)

        if not zip_file.is_file():
            raise FileNotFoundError(f"ZIP file was not found: {zip_path}")
        if zip_file.suffix.lower() != ".zip":
            raise ValueError("Only ZIP files can be imported!")

        destination_root = Path(mod_folder)
        destination_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="mewtator_mod_import_") as temp_dir:
            extracted_root = Path(temp_dir)
            self._safe_extract(zip_file, extracted_root)
            content_root = self._find_content_root(extracted_root)

            if not self._contains_payload_file(content_root):
                raise ValueError("The selected ZIP does not contain any mod files.")

            mod_name = self._choose_mod_name(content_root, extracted_root, zip_file)
            destination = destination_root / mod_name

            if destination.exists():
                if not replace:
                    raise ExistingModError(mod_name, str(destination))
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()

            # Always create one immediate child folder in the configured mods
            # directory, because each child folder is treated as one mod...
            shutil.copytree(content_root, destination, ignore=self._copy_ignore)

        return mod_name, str(destination)

    def _safe_extract(self, zip_path: Path, target_root: Path) -> None:
        """Extract regular ZIP entries without allowing path traversal/symlinks..."""

        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in archive.infolist():
                raw_name = info.filename.replace("\\", "/")

                if not raw_name or raw_name.endswith("/"):
                    continue

                path = PurePosixPath(raw_name)
                if (path.is_absolute() or ".." in path.parts or (path.parts and path.parts[0].endswith(":"))):
                    raise ValueError(f"Unsafe path in ZIP: {info.filename}")
                if not path.parts or info.is_dir():
                    continue
                if any(part in self._IGNORED_NAMES for part in path.parts):
                    continue

                # ZIP symlinks can point outside temporary dir by later file operations, so they're not imported...
                unix_mode = (info.external_attr >> 16) & 0xFFFF

                if unix_mode and stat.S_ISLNK(unix_mode):
                    continue

                output = target_root.joinpath(*path.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, open(output, "wb") as dest:
                    shutil.copyfileobj(source, dest)

    def _find_content_root(self, extracted_root: Path) -> Path:
        """
        Collapse wrapper-only directory layers...

        (If exactly one folder contains Mewtator mod metadata, prefer that
        folder, even when the ZIP root also contains packaging files)...
        """

        metadata_roots = set()

        for path in extracted_root.rglob("*"):
            if path.is_file() and path.name.lower() in self._MOD_METADATA_FILES:
                metadata_roots.add(path.parent)

        if len(metadata_roots) == 1:
            return metadata_roots.pop()

        current = extracted_root

        while True:
            entries = [entry for entry in current.iterdir() if not self._is_ignored(entry)]
            files = [entry for entry in entries if entry.is_file()]
            dirs = [entry for entry in entries if entry.is_dir() and self._contains_payload_file(entry)]

            if files:
                return current
            if len(dirs) == 1:
                current = dirs[0]
                continue

            return current

    def _contains_payload_file(self, root: Path) -> bool:
        if not root.exists():
            return False
        
        for path in root.rglob("*"):
            if path.is_file() and not any(part in self._IGNORED_NAMES for part in path.parts):
                return True
            
        return False

    def _choose_mod_name(self, content_root: Path, extracted_root: Path, zip_path: Path) -> str:
        if content_root != extracted_root:
            candidate = content_root.name
        else:
            candidate = zip_path.stem

        candidate = candidate.strip().rstrip(". ")

        if not candidate or candidate in {".", ".."}:
            candidate = "Imported Mod"

        # Keep names valid on Windows...
        invalid = '<>:"/\\|?*'
        candidate = "".join("_" if char in invalid else char for char in candidate)
        candidate = candidate.rstrip(". ") or "Imported Mod"
        return candidate

    def _is_ignored(self, path: Path) -> bool:
        return path.name in self._IGNORED_NAMES

    def _copy_ignore(self, directory: str, names):
        return [name for name in names if name in self._IGNORED_NAMES]
