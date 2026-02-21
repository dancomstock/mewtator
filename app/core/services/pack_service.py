import os
import struct
from pathlib import Path


class PackService:
    def unpack(self, game_dir: str, output_dir: str, progress_callback=None):
        gpak_path = Path(game_dir) / "resources.gpak"
        out_dir = Path(output_dir)
        
        if not gpak_path.exists():
            raise FileNotFoundError(f"resources.gpak not found in: {game_dir}")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
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
                
                if progress_callback:
                    progress_callback(i + 1, count)
    
    def repack(self, source_dir: str, output_gpak: str, progress_callback=None):
        source_root = Path(source_dir)
        output_gpak_path = Path(output_gpak)
        
        if not source_root.exists():
            raise FileNotFoundError(f"Source folder does not exist: {source_dir}")
        
        output_gpak_path.parent.mkdir(parents=True, exist_ok=True)
        
        files = [p for p in source_root.rglob("*") if p.is_file()]
        
        with output_gpak_path.open("wb") as f:
            f.write(struct.pack("<i", len(files)))
            
            for relpath in files:
                rel = relpath.relative_to(source_root).as_posix()
                rel_bytes = rel.encode("utf-8")
                f.write(struct.pack("<h", len(rel_bytes)))
                f.write(rel_bytes)
                f.write(struct.pack("<i", relpath.stat().st_size))
            
            for i, relpath in enumerate(files):
                with relpath.open("rb") as src:
                    f.write(src.read())
                
                if progress_callback:
                    progress_callback(i + 1, len(files))
