from abc import ABC, abstractmethod
from typing import List
import os
import subprocess
from pathlib import Path
import shlex
from app.core.models.config import Config
from app.utils.logging_utils import get_logger
from app.utils.resource_utils import resource_path
from app.core.services.translation_service import TranslationService
import psutil
import time
import sys
if sys.platform == "win32":
    import win32con
    import win32api
    import win32gui
    import win32process

MEWGENICS_STEAM_APP_ID = "686060"

def _steam_game_env():
    """Return child-process environment identifying Mewgenics to Steamworks!"""
    env = os.environ.copy()
    env["SteamAppId"] = MEWGENICS_STEAM_APP_ID
    env["SteamGameId"] = MEWGENICS_STEAM_APP_ID
    return env

def _poll_processes_for_stop(processes: set[psutil.Process], recheck_period_sec: float, max_retries: int):
    """Repeatedly poll a psutil Process set and remove dead processes until the set is emptied or maximum retries have elapsed."""
    while True:
        for proc in processes.copy():
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                processes.remove(proc)
        if processes:
            max_retries -= 1
            if max_retries <= 0:
                return False
            time.sleep(recheck_period_sec)
        else:
            return True

class LaunchStrategy(ABC):
    @abstractmethod
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str, config: Config, extra_args: List[str], translation_service: TranslationService):
        pass
    
    @abstractmethod
    def get_launch_options(self, mod_paths: List[str], game_dir: str, config: Config, extra_args: List[str]) -> str:
        pass

    @abstractmethod
    def collect_launched_processes(self, executable_path: str, game_dir: str) -> set[psutil.Process]:
        pass

    @abstractmethod
    def stop(self, executable_path: str, game_dir: str, config: Config, translation_service: TranslationService):
        pass

class DirectLaunchStrategy(LaunchStrategy):
    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str, config: Config, extra_args: List[str], translation_service: TranslationService):
        args = [executable_path]
        
        if extra_args:
            args.extend(extra_args)
        
        if mod_paths:
            args.append("-modpaths")
            args.extend(mod_paths)
        
        subprocess.Popen(args, cwd=game_dir, env=_steam_game_env())
    
    def get_launch_options(self, mod_paths: List[str], game_dir: str, config: Config, extra_args: List[str]) -> str:
        parts = []
        
        if extra_args:
            parts.extend(extra_args)
        
        if mod_paths:
            parts.append("-modpaths")
            parts.extend(f'"{p}"' for p in mod_paths)
        
        return " ".join(parts)

    def collect_launched_processes(self, executable_path: str, game_dir: str) -> set[psutil.Process]:
        logger = get_logger()

        processes = set()

        # Fetch the current user's handle
        current_user = psutil.Process().username()

        # Collect processes
        for proc in psutil.process_iter(['pid', 'username', 'exe']):
            # Filter processes by the current user if their identity is known
            if current_user is not None:
                if proc.info['username'] != current_user:
                    continue

            # Exclude dead and zombie processes
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                continue

            # Collect processes that are instances of the game executable
            if proc.info['exe'] and Path(proc.info['exe']).is_file() and Path(executable_path).samefile(proc.info['exe']):
                processes.add(proc)

        return processes

    def stop(self, executable_path: str, game_dir: str, config: Config, translation_service: TranslationService):
        logger = get_logger()

        processes_to_kill = self.collect_launched_processes(executable_path, game_dir)

        if not config.always_ungraceful_stop_enabled:
            # Try to gracefully exit (SDL_EVENT_QUIT?) in order to allow savescumming to be flagged.
            if sys.platform == "win32":
                # On Windows, the game gracefully exits after receiving a WM_CLOSE message.
                # https://stackoverflow.com/a/56310557
                # https://github.com/wine-mirror/wine/blob/9ce1651515d93d9760e2438a53bf2c117238bc2b/programs/taskkill/taskkill.c#L119-L134
                def __win32_enum_windows_proc_wm_close(hwnd, l_param):
                    if l_param == win32process.GetWindowThreadProcessId(hwnd)[1]:
                        # Send two in case the savescum confirmation prompt is shown
                        # (the second would actually close the window in the case)
                        win32api.SendMessage(hwnd, win32con.WM_CLOSE)
                        win32api.SendMessage(hwnd, win32con.WM_CLOSE)
                def __win32_taskkill(pid: int):
                    win32gui.EnumWindows(__win32_enum_windows_proc_wm_close, pid)
                for proc in processes_to_kill:
                    logger.info(f"WM_CLOSE {proc.info['pid']}")
                    __win32_taskkill(proc.info['pid'])
            else:
                # Presumably on Linux/macOS, SIGTERM would trigger a graceful exit.
                # However, a native Mewgenics build has not been released for Linux/macOS when this code was written.
                for proc in processes_to_kill:
                    logger.info(f"Terminate {proc.info['pid']}")
                    proc.terminate()

            # 10 sec
            if _poll_processes_for_stop(processes_to_kill, 0.5, 20):
                return

        # TerminateProcess on Windows, SIGKILL on Linux/macOS
        for proc in processes_to_kill:
            logger.info(f"Kill {proc.info['pid']}")
            proc.kill()

        # 5 sec
        if _poll_processes_for_stop(processes_to_kill, 0.5, 10):
            return

        for proc in processes_to_kill:
            logger.warning(f"Failed to kill {proc.info['pid']}")

class ProtonLaunchStrategy(LaunchStrategy):
    def __init__(self, game_dir: str):
        self.game_dir = game_dir

    def launch(self, executable_path: str, mod_paths: List[str], game_dir: str, config: Config, extra_args: List[str], translation_service: TranslationService):
        # Launch Mewgenics.exe directly rather than through the Steam client...
        env = _steam_game_env()

        path_steam_client_root = Path.home() / '.steam/root'
        path_steam_gameoverlayrenderer64 = path_steam_client_root / 'ubuntu12_64/gameoverlayrenderer.so'

        path_game_dir = Path(game_dir)
        path_mod_folder = Path(config.mod_folder)
        path_steam_linux_runtime = Path(config.linux_steam_runtime_path) if config.linux_steam_runtime_path else None
        path_proton = Path(config.linux_proton_path) if config.linux_proton_path else None
        path_bundled_mods_dir = Path(resource_path("bundled_mods"))

        path_library_game = path_game_dir.parent.parent
        path_library_steam_linux_runtime = Path(config.linux_steam_runtime_path).parent.parent.parent if path_steam_linux_runtime else None
        path_library_proton = Path(config.linux_proton_path).parent.parent.parent if path_proton else None

        path_compat_data = (
            Path(config.linux_compatdata_override_dir)
            if config.linux_compatdata_override_dir
            else path_library_game / 'compatdata' / MEWGENICS_STEAM_APP_ID
        )

        mod_folder_in_game_dir = path_mod_folder.resolve().is_relative_to(path_game_dir.resolve())
        bundled_mods_dir_in_game_dir = path_bundled_mods_dir.resolve().is_relative_to(path_game_dir.resolve())

        steam_gameoverlayrenderer64_exists = path_steam_gameoverlayrenderer64.is_file()
        steam_linux_runtime_exists = path_steam_linux_runtime is not None and path_steam_linux_runtime.is_file()
        proton_exists = path_proton is not None and path_proton.is_file()
        path_compat_data_exists = path_compat_data.is_dir()

        if not config.linux_allow_undefined_steam_runtime_or_proton:
            missing_launchers = []
            if not steam_linux_runtime_exists:
                missing_launchers.append("Steam Linux Runtime")
            if not proton_exists:
                missing_launchers.append("Proton")
            if missing_launchers:
                required = "\n".join(
                    translation_service.get("messages.path_required").format(name=name)
                    for name in missing_launchers
                )
                raise RuntimeError(required)

        # We avoid blindly initializing Steam-managed compatdata (by making a directory that does not
        # already exist under steamapps/compatdata), because we'd potentially bypass first-time Steam Cloud
        # sync performed by the Steam client. Doing so could overwrite existing save data stored on the Steam Cloud.
        if not path_compat_data_exists:
            raise RuntimeError(
                translation_service.get("messages.proton_missing_compatdata_error") + 
                "\n\n" +
                translation_service.get("messages.copy_launch_options_advice")
            )

        # Steam Linux Runtime/Proton logging controls
        # env['PRESSURE_VESSEL_LOG_INFO'] = '1' # writes to stdout
        # env['PROTON_LOG'] = '1' # writes to ~/steam-686060.log

        # inject the library that enables Steam overlay functionality
        # https://partner.steamgames.com/doc/store/application/platforms/linux#FAQ
        if not config.linux_steam_gameoverlayrenderer_disabled and steam_gameoverlayrenderer64_exists:
            if 'LD_PRELOAD' not in env:
                env['LD_PRELOAD'] = ''
            env['LD_PRELOAD'] += ':' + str(path_steam_gameoverlayrenderer64.resolve())

        # prescribed Steam Linux Runtime/Proton configuration variables
        # https://gitlab.steamos.cloud/steamrt/steam-runtime-tools/-/blob/main/docs/slr-for-game-developers.md#running-a-game-under-proton-in-the-steam-linux-runtime-environment
        env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = path_steam_client_root.resolve()
        env['STEAM_COMPAT_DATA_PATH'] = path_compat_data.resolve()
        env['STEAM_COMPAT_INSTALL_PATH'] = path_game_dir.resolve()
        env['STEAM_COMPAT_LIBRARY_PATHS'] = ':'.join(list(dict.fromkeys(str(x.resolve()) for x in [
            path_library_game,
            path_library_steam_linux_runtime,
            path_library_proton
        ] if x is not None)))

        # expose the mod directory under Z:\, in case it was not placed within Mewgenics' directory
        # https://gitlab.steamos.cloud/steamrt/steam-runtime-tools/-/blob/main/docs/slr-for-game-developers.md#making-more-files-available-in-the-container
        env['STEAM_COMPAT_MOUNTS'] = ':'.join(list(dict.fromkeys(str(x.resolve()) for x in [
            path_mod_folder if not mod_folder_in_game_dir else None,
            path_bundled_mods_dir if not bundled_mods_dir_in_game_dir else None
        ] if x is not None)))

        # set WINEDLLOVERRIDES to enable loading Mewjector, which shadows version.dll
        if config.dll_injection_enabled:
            env['WINEDLLOVERRIDES'] = 'version=n,b'

        args = []
        # Steam Linux Runtime is not necessarily required if the user's system has the right
        # libraries to support the chosen Proton version.
        if steam_linux_runtime_exists:
            args.extend([config.linux_steam_runtime_path, '--'])

        # There probably isn't a good reason to launch without Proton, but if so, the system
        # will try to dispatch the exe file via binfmt, possibly using a native Wine installation.
        if proton_exists:
            args.extend([config.linux_proton_path, 'run'])

        args.append(executable_path)

        if extra_args:
            args.extend(extra_args)

        if mod_paths:
            args.append("-modpaths")
            args.extend(mod_paths)

        subprocess.Popen(args, cwd=game_dir, env=env)

    def get_launch_options(self, mod_paths: List[str], game_dir: str, config: Config, extra_args: List[str]) -> str:
        parts = []

        parts_has_prefix = False

        path_game_dir = Path(game_dir)
        path_mod_folder = Path(config.mod_folder)
        path_bundled_mods_dir = Path(resource_path("bundled_mods"))
        mod_folder_in_game_dir = path_mod_folder.resolve().is_relative_to(path_game_dir.resolve())
        bundled_mods_dir_in_game_dir = path_bundled_mods_dir.resolve().is_relative_to(path_game_dir.resolve())

        # expose the mod directory under Z:\, in case it was not placed within Mewgenics' directory
        # https://gitlab.steamos.cloud/steamrt/steam-runtime-tools/-/blob/main/docs/slr-for-game-developers.md#making-more-files-available-in-the-container
        compat_mounts = ':'.join(list(dict.fromkeys(str(x.resolve()) for x in [
            path_mod_folder if not mod_folder_in_game_dir else None,
            path_bundled_mods_dir if not bundled_mods_dir_in_game_dir else None
        ] if x is not None)))
        if compat_mounts:
            parts.append(f'STEAM_COMPAT_MOUNTS={shlex.quote(compat_mounts)}')
            parts_has_prefix = True

        # set WINEDLLOVERRIDES to enable loading Mewjector, which shadows version.dll
        if config.dll_injection_enabled:
            parts.append(f'WINEDLLOVERRIDES=version=n,b')
            parts_has_prefix = True

        if parts_has_prefix:
            parts.append('%command%')

        if extra_args:
            parts.extend(extra_args)

        if mod_paths:
            parts.append("-modpaths")
            parts.extend(shlex.quote(str(p)) for p in mod_paths)

        return " ".join(parts)

    def collect_launched_processes(self, executable_path: str, game_dir: str) -> set[psutil.Process]:
        logger = get_logger()

        # Process tracker
        processes = set()
        wineserver_process = None

        # Fetch the current user's handle
        current_user = psutil.Process().username()

        # Collect processes
        for proc in psutil.process_iter(['pid', 'username', 'exe']):
            # Filter processes by the current user if their identity is known
            if current_user is not None:
                if proc.info['username'] != current_user:
                    continue

            # Exclude dead and zombie processes
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                continue

            # We need to collect multiple processes related to Mewgenics.exe
            # SteamAppId/SteamGameId env vars are specific to the game, and
            # set by both the Steam client and Mewtator.
            try:
                environ = proc.environ()
            except:
                # usually fails if the process is owned by another user
                # and if the requesting user is not root
                continue
            if environ.get('SteamAppId') == MEWGENICS_STEAM_APP_ID or environ.get('SteamGameId') == MEWGENICS_STEAM_APP_ID:
                processes.add(proc)

        return processes

    def stop(self, executable_path: str, game_dir: str, config: Config, translation_service: TranslationService):
        logger = get_logger()

        processes_to_kill = self.collect_launched_processes(executable_path, game_dir)
        wineserver_process = None

        # Paths for running taskkill
        path_steam_client_root = Path.home() / '.steam/root'
        path_game_dir = Path(game_dir)
        path_steam_linux_runtime = Path(config.linux_steam_runtime_path) if config.linux_steam_runtime_path else None
        path_proton = Path(config.linux_proton_path) if config.linux_proton_path else None

        steam_linux_runtime_exists = path_steam_linux_runtime is not None and path_steam_linux_runtime.is_file()
        proton_exists = path_proton is not None and path_proton.is_file()

        if not config.always_ungraceful_stop_enabled:
            # Try to gracefully exit (SDL_EVENT_QUIT?) in order to allow savescumming to be flagged.
            def __proton_taskkill_mewgenics():
                # On Windows, the game gracefully exits after receiving a WM_CLOSE message.
                # We descend into the Wine prefix and run taskkill to signal WM_CLOSE.
                # (there doesn't appear to be a way to initiate WM_CLOSE through Unix signalling)
                if not config.linux_allow_undefined_steam_runtime_or_proton:
                    if not steam_linux_runtime_exists:
                        return
                if not proton_exists:
                    return

                wineserver_environ = wineserver_process.environ()
                env = os.environ.copy()

                # prescribed Steam Linux Runtime/Proton configuration variables
                # https://gitlab.steamos.cloud/steamrt/steam-runtime-tools/-/blob/main/docs/slr-for-game-developers.md#running-a-game-under-proton-in-the-steam-linux-runtime-environment
                env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = wineserver_environ['STEAM_COMPAT_CLIENT_INSTALL_PATH']
                env['STEAM_COMPAT_DATA_PATH'] = wineserver_environ['STEAM_COMPAT_DATA_PATH']
                env['STEAM_COMPAT_INSTALL_PATH'] = wineserver_environ['STEAM_COMPAT_INSTALL_PATH']
                env['STEAM_COMPAT_LIBRARY_PATHS'] = wineserver_environ['STEAM_COMPAT_LIBRARY_PATHS']

                args = []
                # Steam Linux Runtime is not necessarily required if the user's system has the right
                # libraries to support the chosen Proton version.
                if steam_linux_runtime_exists:
                    args.extend([config.linux_steam_runtime_path, '--'])

                # We checked that Proton exists earlier
                args.extend([config.linux_proton_path, 'run'])

                # Run taskkill twice in case the savescum confirmation prompt is shown the first time
                # (the second would actually close the window in this case)
                args.extend(['cmd', '/c', 'taskkill /IM Mewgenics.exe & taskkill /IM Mewgenics.exe'])

                process = subprocess.Popen(args, cwd=game_dir, env=env)
                process.wait()

            wineserver_process = None
            # Try to find a wineserver instance corresponding to our Proton launcher
            # If the user has multiple prefixes running multiple instances of
            # Mewgenics.exe, we'll execute taskkill in one prefix only.
            for proc in processes_to_kill:
                if proton_exists:
                    exe = proc.info['exe']
                    if exe and exe.startswith(str(path_proton.parent)) and exe.endswith('wineserver'):
                        wineserver_process = proc
                        break

            if wineserver_process is not None:
                logger.info("WM_CLOSE Mewgenics.exe")
                __proton_taskkill_mewgenics()

            # 10 sec
            if _poll_processes_for_stop(processes_to_kill, 0.5, 20):
                return

        # SIGTERM any remaining processes
        # Wine converts SIGTERM to TerminateProcess, not WM_CLOSE
        for proc in processes_to_kill:
            logger.info(f"SIGTERM {proc.info['pid']}")
            proc.terminate()

        # 5 sec
        if _poll_processes_for_stop(processes_to_kill, 0.5, 10):
            return

        # SIGKILL any remaining processes
        for proc in processes_to_kill:
            logger.info(f"SIGKILL {proc.info['pid']}")
            proc.kill()

        # 5 sec
        if _poll_processes_for_stop(processes_to_kill, 0.5, 10):
            return

        for proc in processes_to_kill:
            logger.warning(f"Failed to kill {proc.info['pid']}")

class LaunchStrategyFactory:
    @staticmethod
    def create(game_dir: str) -> LaunchStrategy:
        from app.core.strategies.path_strategy import PathStrategyFactory, ProtonPathStrategy
        
        path_strategy = PathStrategyFactory.create(game_dir)
        
        if isinstance(path_strategy, ProtonPathStrategy):
            return ProtonLaunchStrategy(game_dir)
        
        return DirectLaunchStrategy()
