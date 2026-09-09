"""Service for managing DLL mod manifests and chainloader integration.

This service handles scanning for DLL mods and creating a manifest file
that the chainloader (external DLL loader) can read.
"""

import os
from typing import List, Tuple
from pathlib import Path
from app.core.strategies.path_strategy import PathStrategyFactory


class DllInjectionService:
    """Manages DLL mod manifests for chainloader integration.
    
    Works with an external chainloader that reads from chainloader.ini.
    Mewtator generates a manifest of DLL paths and updates the ini file.
    """
    
    CHAINLOADER_INI = "chainloader.ini"
    MANIFEST_FILE = "mewtator_dll_manifest.txt"
    
    def __init__(self):
        """Initialize the DLL injection service."""
        pass
    
    def chainloader_exists(self, game_dir: str) -> bool:
        """Check if chainloader.ini exists in the game directory.
        
        Args:
            game_dir: Path to game installation directory
            
        Returns:
            True if chainloader.ini exists
        """
        ini_path = Path(game_dir) / self.CHAINLOADER_INI
        return ini_path.exists()
    
    def scan_for_dll_mods(self, mod_list) -> List[Tuple[str, List[str]]]:
        """Scan enabled mods for DLL files.
        
        Args:
            mod_list: ModList object containing all mods
            
        Returns:
            List of tuples (mod_name, [dll_paths]) for mods with DLLs,
            in the order they appear in the modlist
        """
        dll_mods = []
        
        for mod in mod_list.enabled_mods:
            dll_files = self._find_dlls_in_mod(mod)
            if dll_files:
                dll_mods.append((mod.name, dll_files))
        
        return dll_mods
    
    def has_dll_mods(self, mod_list) -> bool:
        """Quick check if any enabled mod contains DLL files.
        
        Args:
            mod_list: ModList object containing all mods
            
        Returns:
            True if at least one enabled mod has .dll files
        """
        for mod in mod_list.enabled_mods:
            if self._find_dlls_in_mod(mod):
                return True
        return False
    
    def mod_has_dlls(self, mod) -> bool:
        """Check if a specific mod contains DLL files.
        
        Args:
            mod: Mod object to check
            
        Returns:
            True if mod contains .dll files
        """
        return len(self._find_dlls_in_mod(mod)) > 0
    
    def _find_dlls_in_mod(self, mod) -> List[str]:
        """Find all DLL files in a mod's directory.
        
        Args:
            mod: Mod object with path attribute
            
        Returns:
            List of absolute paths to .dll files, ordered by dll_order in metadata or alphabetically
        """
        dll_files = []
        mod_path = Path(mod.path)
        
        if not mod_path.exists():
            return dll_files
        
        # Search recursively for .dll files
        for dll_file in mod_path.rglob("*.dll"):
            if dll_file.is_file():
                # Record absolute path
                dll_files.append(dll_file.absolute())
        
        # Sort DLLs: use dll_order from metadata if available, otherwise alphabetical
        if mod.dll_order:
            # Create a map of filename -> full path
            dll_map = {Path(dll).name.lower(): dll for dll in dll_files}
            
            # Build ordered list based on dll_order
            ordered_dlls = []
            for dll_name in mod.dll_order:
                dll_name_lower = dll_name.lower()
                if dll_name_lower in dll_map:
                    ordered_dlls.append(dll_map[dll_name_lower])
                    del dll_map[dll_name_lower]  # Remove from map
            
            # Append any remaining DLLs not in dll_order (alphabetically)
            remaining = sorted(dll_map.values(), key=lambda p: Path(p).name.lower())
            ordered_dlls.extend(remaining)
            
            return ordered_dlls
        else:
            # No dll_order specified, sort alphabetically by filename
            return sorted(dll_files, key=lambda p: Path(p).name.lower())
    
    def update_chainloader_manifest(self, game_dir: str, mod_folder: str, dll_mods: List[Tuple[str, List[str]]]) -> bool:
        """Create manifest file and update chainloader.ini to point to it.
        
        Args:
            game_dir: Path to game installation directory
            mod_folder: Path to mods folder (where manifest will be created)
            dll_mods: List of (mod_name, [dll_paths]) tuples in load order
            
        Returns:
            True if successful, False otherwise
        """
        game_path = Path(game_dir)
        mod_path = Path(mod_folder)
        ini_path = game_path / self.CHAINLOADER_INI
        manifest_path = mod_path / self.MANIFEST_FILE
        
        # Check if chainloader.ini exists
        if not ini_path.exists():
            return False
        
        try:
            # Convert paths for cross-platform compatibility (Windows/Proton)
            path_strategy = PathStrategyFactory.create(game_dir)

            # Create manifest file with DLL paths in mod folder
            with open(manifest_path, 'w', encoding='utf-8') as f:
                for mod_name, dll_paths in dll_mods:
                    for dll_path in dll_paths:
                        f.write(f"{path_strategy.convert_mod_paths([dll_path], game_dir)[0]}\n")
            
            # Update chainloader.ini by manually editing the MewtatorManifest line
            # This preserves comments and formatting
            with open(ini_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and update MewtatorManifest line
            in_chainloader_section = False
            manifest_found = False
            manifest_line = f"MewtatorManifest={path_strategy.convert_mod_paths([manifest_path], game_dir)[0]}\n"
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Check for section headers
                if stripped.startswith('['):
                    in_chainloader_section = stripped.lower() == '[chainloader]'
                
                # Update MewtatorManifest if in Chainloader section
                elif in_chainloader_section and stripped.lower().startswith('mewtatormanifest'):
                    lines[i] = manifest_line
                    manifest_found = True
                    break
            
            # If MewtatorManifest wasn't found, add it to the Chainloader section
            if not manifest_found:
                for i, line in enumerate(lines):
                    if line.strip().lower() == '[chainloader]':
                        # Insert after the section header
                        lines.insert(i + 1, manifest_line)
                        break
            
            # Write back to ini file
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"Error updating chainloader manifest: {e}")
            return False
    
    def clear_chainloader_manifest(self, game_dir: str, mod_folder: str) -> bool:
        """Clear the MewtatorManifest setting in chainloader.ini and remove manifest file.
        
        Args:
            game_dir: Path to game installation directory
            mod_folder: Path to mods folder (where manifest is located)
            
        Returns:
            True if successful, False otherwise
        """
        game_path = Path(game_dir)
        mod_path = Path(mod_folder)
        ini_path = game_path / self.CHAINLOADER_INI
        manifest_path = mod_path / self.MANIFEST_FILE
        
        if not ini_path.exists():
            return True  # Nothing to clean
        
        try:
            # Update chainloader.ini to clear MewtatorManifest by manually editing
            # This preserves comments and formatting
            with open(ini_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and clear MewtatorManifest line
            in_chainloader_section = False
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Check for section headers
                if stripped.startswith('['):
                    in_chainloader_section = stripped.lower() == '[chainloader]'
                
                # Clear MewtatorManifest if in Chainloader section
                elif in_chainloader_section and stripped.lower().startswith('mewtatormanifest'):
                    lines[i] = "MewtatorManifest=\n"
                    break
            
            # Write back to ini file
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # Remove manifest file if it exists
            if manifest_path.exists():
                manifest_path.unlink()
            
            return True
            
        except Exception as e:
            print(f"Error clearing chainloader manifest: {e}")
            return False
    
    def is_chainloader_configured(self, game_dir: str) -> bool:
        """Check if chainloader is configured with Mewtator manifest.
        
        Args:
            game_dir: Path to game installation directory
            
        Returns:
            True if MewtatorManifest is set in chainloader.ini
        """
        game_path = Path(game_dir)
        ini_path = game_path / self.CHAINLOADER_INI
        
        if not ini_path.exists():
            return False
        
        try:
            with open(ini_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            in_chainloader_section = False
            for line in lines:
                stripped = line.strip()
                
                # Check for section headers
                if stripped.startswith('['):
                    in_chainloader_section = stripped.lower() == '[chainloader]'
                
                # Check MewtatorManifest if in Chainloader section
                elif in_chainloader_section and stripped.lower().startswith('mewtatormanifest'):
                    # Extract value after =
                    if '=' in stripped:
                        value = stripped.split('=', 1)[1].strip()
                        return bool(value)
            
            return False
        except:
            return False
