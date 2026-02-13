import os
import shutil
import subprocess
from pathlib import Path
from tkinter import messagebox
import logging
import json
from app.configloader import load_config

# ---------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------
LOG_PATH = Path(os.getcwd()) / "mewtator_launcher.log"

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("launcher")

# ---------------------------------------------------------
# File Helpers
# ---------------------------------------------------------
def _wait_for_file_ready(path: Path, timeout=10):
    """Wait for a file to be ready (exists and is readable)."""
    log.debug(f"Waiting for file to be ready: {path}")
    import time
    start = time.time()

    while time.time() - start < timeout:
        try:
            if path.exists():
                size = path.stat().st_size
                if size > 0:
                    # Try to read a byte to ensure file is accessible
                    with open(path, "rb") as f:
                        f.read(1)
                    log.debug(f"File ready: {path}")
                    return True
        except Exception as e:
            log.debug(f"File not ready yet: {e}")

        time.sleep(0.2)

    log.error(f"File did not become ready within {timeout} seconds: {path}")
    return False


def _backup_original_if_needed(original: Path, backup: Path):
    """Backup the original resources if not already backed up."""
    if not original.exists():
        return True
    
    if backup.exists():
        # Backup already exists - prompt user before overwriting
        log.warning(f"Backup already exists: {backup}")
        
        response = messagebox.askyesno(
            "Backup Already Exists",
            f"A backup file already exists:\n{backup}\n\n"
            "Overwriting it means replacing it with the current resources.gpak. "
            "This could overwrite vanilla files with modded files.\n\n"
            "Click YES to overwrite the existing backup.\n"
            "Click NO to cancel and use the existing backup.\n\n"
            "If you want vanilla files back, you can:\n"
            "- Repack with only the game files (no mods)\n"
            "- Validate game files through Steam"
        )
        
        if response:
            # User wants to overwrite
            try:
                log.info(f"Overwriting backup: {backup}")
                backup.unlink()
                original.rename(backup)
                return True
            except Exception as e:
                log.error(f"Backup overwrite failed: {e}")
                messagebox.showerror("Backup Failed", str(e))
                return False
        else:
            # User chose not to overwrite
            log.info("User chose not to overwrite existing backup, using existing backup")
            return True
    else:
        # No backup exists, create one
        try:
            log.info(f"Backing up original: {original} -> {backup}")
            original.rename(backup)
            return True
        except Exception as e:
            log.error(f"Backup failed: {e}")
            messagebox.showerror("Backup Failed", str(e))
            return False


def _swap_resources(modded: Path, original: Path):
    """Swap in the modded resources file."""
    try:
        # Remove the original if it exists (could be a symlink or copy)
        if original.exists() or original.is_symlink():
            original.unlink()
        
        # Try to create a symlink first, fall back to copy if it fails
        try:
            log.debug(f"Creating symlink: {original} -> {modded}")
            original.symlink_to(modded)
            log.info("Resources swapped via symlink")
        except Exception as symlink_error:
            log.debug(f"Symlink failed, copying instead: {symlink_error}")
            shutil.copy2(modded, original)
            log.info("Resources swapped via copy")
        
        return True
    except Exception as e:
        log.error(f"Resource swap failed: {e}")
        messagebox.showerror("Resource Swap Failed", str(e))
        return False


def _restore_original_resources(original: Path, backup: Path):
    """Restore the original resources from backup."""
    if not backup.exists():
        log.warning("Backup file not found; cannot restore")
        return

    try:
        log.info(f"Restoring original resources: {backup} -> {original}")
        if original.exists() or original.is_symlink():
            original.unlink()
        backup.rename(original)
        log.info("Resources restored successfully")
    except Exception as e:
        log.error(f"Restore failed: {e}")
        messagebox.showerror("Restore Failed", str(e))


# ---------------------------------------------------------
# Main Launch Function
# ---------------------------------------------------------
def launch_game_with_temp_gpak(game_install_dir: str, modded_gpak_path: str, cfg):
    """
    Launch the game with modded resources.
    
    Args:
        game_install_dir: Path to the game installation directory
        modded_gpak_path: Path to the modded resources file
    """
    log.info("=== Launch Sequence Started ===")
    
    skip_restore = cfg.get("skip_process_restore", True)
    
    log.info(f"Configuration: skip_process_restore={skip_restore}")

    game_dir = Path(game_install_dir)
    original = game_dir / "resources.gpak"
    backup = game_dir / "resources_original.gpak"
    modded = Path(modded_gpak_path)
    exe = game_dir / "Mewgenics.exe"

    # Validate paths
    if not game_dir.exists():
        messagebox.showerror("Game Folder Not Found", f"Path does not exist: {game_dir}")
        log.error(f"Game directory not found: {game_dir}")
        return

    if not exe.exists():
        messagebox.showerror("Executable Not Found", f"Path does not exist: {exe}")
        log.error(f"Executable not found: {exe}")
        return

    if not modded.exists():
        messagebox.showerror("Modded Resources Missing", f"Path does not exist: {modded}")
        log.error(f"Modded resources not found: {modded}")
        return

    # Ensure modded file is ready
    if not _wait_for_file_ready(modded):
        messagebox.showerror("Modded File Error", "Modded file did not become ready in time.")
        log.error("Modded file failed readiness check")
        return

    # Backup original if needed
    if not _backup_original_if_needed(original, backup):
        return

    # Swap in modded resources
    if not _swap_resources(modded, original):
        return

    # Launch the game
    try:
        log.debug(f"Launching game: {exe}")
        subprocess.Popen(
            [str(exe)],
            cwd=str(game_dir),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        log.info("Game launched successfully")
    except Exception as e:
        log.error(f"Game launch failed: {e}")
        messagebox.showerror("Launch Failed", str(e))
        # Restore original on failure
        _restore_original_resources(original, backup)
        return

    # Handle post-launch restoration if configured
    if not skip_restore:
        log.info("Monitoring game process (skip_process_restore=False)")
        import time
        import psutil
        
        exe_name = "Mewgenics.exe"
        timeout = 600
        poll_interval = 1
        search_timeout = 30
        grace_period = 5  # Wait after process exit to detect new ones
        
        # Search for the game process
        log.debug(f"Searching for game process: {exe_name}")
        start = time.time()
        game_pid = None
        
        while time.time() - start < search_timeout:
            try:
                for proc in psutil.process_iter(attrs=['pid', 'name']):
                    if proc.info['name'].lower() == exe_name.lower():
                        game_pid = proc.info['pid']
                        break
                if game_pid:
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            time.sleep(0.2)
        
        if game_pid is None:
            log.warning(f"Game process did not appear within {search_timeout} seconds")
            log.info("Launch sequence complete (process not monitored)")
        else:
            # Monitor for game processes, handling Steam's potential multi-process launch
            overall_start = time.time()
            while time.time() - overall_start < timeout:
                log.info(f"Monitoring game process (PID: {game_pid}), waiting for exit...")
                
                # Wait for the current process to exit
                process_start = time.time()
                while time.time() - process_start < timeout:
                    try:
                        proc = psutil.Process(game_pid)
                        if not proc.is_running():
                            log.info(f"Game process {game_pid} exited")
                            break
                    except psutil.NoSuchProcess:
                        log.info(f"Game process {game_pid} exited")
                        break
                    except psutil.AccessDenied:
                        log.debug("Access denied to process, continuing to wait")
                    
                    time.sleep(poll_interval)
                
                # Process has exited. Wait a grace period to see if a new one appears.
                log.debug(f"Waiting {grace_period}s grace period to detect new game processes...")
                grace_start = time.time()
                new_game_pid = None
                
                while time.time() - grace_start < grace_period:
                    try:
                        for proc in psutil.process_iter(attrs=['pid', 'name']):
                            if proc.info['name'].lower() == exe_name.lower():
                                # Make sure it's not the old process we just monitored
                                if proc.info['pid'] != game_pid:
                                    new_game_pid = proc.info['pid']
                                    log.info(f"New game process detected (PID: {new_game_pid})")
                                    break
                        if new_game_pid:
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    time.sleep(0.2)
                
                if new_game_pid:
                    # New process found, continue monitoring
                    game_pid = new_game_pid
                    continue
                else:
                    # No new process appeared, game is done
                    log.info("No new game processes detected after grace period, game session complete")
                    break
            else:
                log.warning(f"Game monitoring timed out after {timeout} seconds")
            
            # Restore original after all game processes exit
            _restore_original_resources(original, backup)
    else:
        log.info("Skipping process monitoring (skip_process_restore=True)")
        log.info("Game launched with modded resources. Manual restore may be required.")

    log.info("=== Launch Sequence Completed ===")
