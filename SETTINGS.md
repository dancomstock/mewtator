# Settings

This page describes the various options exposed in Mewtator's settings menu and configuration file.

## Basic Options

### Auto-Detect Game Install
When pressed, automatically populates `game_install_dir`, `mod_folder`, `linux_steam_runtime_path`, and `linux_proton_path`.

### Game Install Directory (`game_install_dir`)
Path to the directory where the game was installed. 

### Mods Folder (`mod_folder`)
Path to the directory used by Mewtator to load mods.

### Steam Linux Runtime (`linux_steam_runtime_path`)
(Linux only)

Path to a [Steam Linux Runtime](https://github.com/valvesoftware/steam-runtime) launch wrapper (`run`).

Steam Linux Runtime is used to start Proton with a packaged set of dynamic libraries.

When `linux_allow_undefined_steam_runtime_or_proton` is checked, this field may be empty.

Without Steam Linux Runtime, Proton would be launched with native system libraries.

### Proton (`linux_proton_path`)
(Linux only)

Path to a [Proton](https://github.com/valvesoftware/proton) launch wrapper (`proton`).

Proton is used to start the game with a preconfigured instance of Wine.

When `linux_allow_undefined_steam_runtime_or_proton` is checked, this field may be empty.

Without Proton, the system would launch the game with an interpreter determined by `binfmt_misc`, which could be a native Wine installation.

### Language (`language`)
Mewtator's selected display language.


## Launch Options

### Custom Launch Options (`custom_launch_options`)
Text string appended to the game's launch command.

### Enable Dev Mode (-dev mode true) (`dev_mode_enabled`)
When checked, appends `-dev mode true` to the game's launch command, which enables dev mode.

Dev mode starts the game in a special menu, which allows access to various debugging and test utilities.

### Enable Debug Console (-enable_debugconsole true) (`debug_console_enabled`)
When checked, appends `-enable_debugconsole true` to the game's launch command, which enables the game's debug console.

The debug console may be accessed by pressing the backtick key (`` ` ``) on a compatible keyboard.

### Enable Mewtator custom game intro (`mewtator_intro_enabled`)
When checked, Mewtator will load a built-in mod that customizes the game's start sequence.

### Enable DLL Mod Support (`dll_injection_enabled`)
When checked, Mewtator will:

- allow mods containing `.dll` files to be loaded.
- create a manifest file listing `.dll` files to load within enabled mods
- interoperate with [Mewtator](https://github.com/githubuser508/mewjector), including
    - writing `chainloader.ini`
    - on Linux, instructing Proton to load `version.dll`


## Appearance

### Use standard system font (`use_generic_font`)
When checked, Mewtator will use a conventional screen font for displaying text.

Otherwise, Mewtator renders most text with a built-in script font.

## Advanced

### Close Launcher When Game Launches (`close_on_launch`)
When checked, Mewtator will close after "Launch Game" is pressed.

### Allow launch without Steam Linux Runtime or Proton (`linux_allow_undefined_steam_runtime_or_proton`)
(Linux only)

When checked, allows launching the game without Steam Linux Runtime or Proton.

When unchecked, requires `linux_steam_runtime_path` and `linux_proton_path` both be valid paths.

This option may be useful for advanced users who wish to use a native Wine installation instead of Proton.

### Allow launching concurrent game instances (`concurrent_launches_enabled`)
When checked, allows the Launch Game button to launch another instance of the game, when one or more are already running on the system.

This option may be useful for advanced users who wish to run multiple instances of Mewgenics.

### Stop game ungracefully (`always_ungraceful_stop_enabled`)
When checked, the "Stop Game" button will ungracefully stop Mewgenics by terminating the game's process.

An ungraceful stop bears the side effect of defeating Steven's savescum checks.

When unchecked, "Stop Game" will first attempt to gracefully stop the game by closing the game's window, before resorting to process termination.

It may take a long time (several seconds) to gracefully stop the game on Linux through Mewtator.

## Hidden

These options are currently only exposed in `config.json`.

### Theme (`theme`)
Mewtator's selected theme.

### Disable Steam game overlay (`linux_steam_gameoverlayrenderer_disabled`)
(Linux only)

When checked, disables loading the Steam game overlay.

### compatdata override (`linux_compatdata_override_dir`)
(Linux only)

Path to the `compatdata` directory used to store the Proton prefix, where game save data is stored.

If this path is blank, defaults to `<game_install_dir>/../../compatdata/686060/`

This option may be useful for advanced users who wish to place their save data outside of Steam's default location.
