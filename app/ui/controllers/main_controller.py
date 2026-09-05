import os
import zipfile
import tkinter as tk
from tkinter import filedialog, simpledialog
from tkinter import ttk
from app.ui.components.dialog_text import dialog_frame, dialog_label
import webbrowser
from app.core.models.mod_list import ModList
from app.core.services.mod_service import ModService
from app.core.services.config_service import ConfigService
from app.core.services.game_launcher_service import GameLauncherService
from app.core.services.dll_injection_service import DllInjectionService
from app.core.services.translation_service import TranslationService
from app.core.services.pack_service import PackService
from app.core.services.modlist_io_service import ModListIOService
from app.core.services.mod_import_service import ModImportService, ExistingModError
from app.core.services.theme_service import ThemeService
from app.ui.windows.main_window import MainWindow
from app.ui.windows.notification_window import NotificationWindow
from app.ui.windows.settings_window import SettingsWindow
from app.ui.windows.about_window import AboutWindow
from app.ui.windows.controls_window import ControlsWindow
from app.ui.windows.progress_window import ProgressWindow
from app.ui.windows.launch_options_window import LaunchOptionsWindow, ExportSuccessWindow
from app.ui.components.pointer_menu import PointerMenu
from app.ui.layout_utils import fit_window_to_content
from app.utils.logging_utils import get_logger
from app.utils.platform_utils import open_file_or_folder


class MainController:
    def __init__(
        self,
        root: tk.Tk,
        config_service: ConfigService,
        mod_service: ModService,
        launcher_service: GameLauncherService,
        translation_service: TranslationService,
        pack_service: PackService,
        modlist_io_service: ModListIOService,
        theme_service: ThemeService,
        dll_injection_service: DllInjectionService = None
    ):
        self.root = root
        self.config_service = config_service
        self.mod_service = mod_service
        self.launcher_service = launcher_service
        self.dll_injection_service = dll_injection_service or DllInjectionService()
        self.translation_service = translation_service
        self.pack_service = pack_service
        self.modlist_io_service = modlist_io_service
        self.mod_import_service = ModImportService()
        self.theme_service = theme_service
        
        self.config = config_service.load_config()
        self.mod_list: ModList = None
        self.window: MainWindow = None
        
        self.drag_data = {"source": None, "index": None, "changed": False}
        self.drag_indicator = None

        # Poll for edits made outside Mewtator... - Tim
        self._mod_filesystem_watch_job = None
        self._mod_filesystem_watch_interval_ms = 750
        self._last_mod_filesystem_state = None
    
    def start(self):
        if not self.config_service.validate_config(self.config):
            self.theme_service.set_theme(self.config.theme)
            self.root.withdraw()
            self._show_settings(first_run=True)
            self.root.mainloop()
            return
        
        self._build_main_window()
        self.root.deiconify()
        self.root.lift()
        self.root.mainloop()
    
    def _build_main_window(self):
        self.theme_service.set_theme(self.config.theme)
        self.window = MainWindow(self.root, self.translation_service)

        self.mod_list = self.mod_service.load_mods()
        self.mod_list.add_observer(self._on_mod_list_changed)

        self.window.set_toggle_action(self._toggle_mod)
        self.window.set_enable_all_action(self._enable_all)
        self.window.set_disable_all_action(self._disable_all)
        self.window.set_auto_sort_action(self._auto_sort)
        self.window.set_import_mod_action(self._import_mod_zip)
        self.window.set_refresh_action(self._force_refresh_mods)
        self.window.set_order_actions(
            self._move_up,
            self._move_down,
        )
        self.window.set_launch_action(self._launch_game)
        self.window.set_stop_action(self._stop_game)
        self.window.set_settings_action(self._show_settings)

        self._setup_menu_bar()
        self._setup_list_bindings()
        self._setup_keyboard_shortcuts()

        # Validate requirements before first refresh
        self._validate_requirements()
        self._refresh_lists()
        self.window.apply_theme(self.theme_service, self.config.theme)
        self.window.fit_to_content()
        self._auto_configure_chainloader()
        self._start_mod_filesystem_watch()

    def _setup_menu_bar(self):
        self.window.menu_bar.create_file_menu(
            on_settings=self._show_settings,
            on_import=self._import_modlist,
            on_export=self._export_modlist,
            on_unpack=self._unpack,
            on_repack=self._repack,
            on_open_mods=lambda: open_file_or_folder(self.config.mod_folder),
            on_open_game=lambda: open_file_or_folder(self.config.game_install_dir),
            on_launch=self._launch_game,
            on_copy_launch=self._copy_launch_options,
            on_stop=self._stop_game,
            on_cleanup_dlls=self._cleanup_dll_injection,
            on_exit=self.root.quit
        )
        
        available_langs = self.translation_service.get_available_languages()
        self.window.menu_bar.create_language_menu(
            available_langs,
            self.config.language,
            self._change_language
        )
        
        self.window.menu_bar.create_settings_button(self._show_settings)
        self.window.menu_bar.create_controls_button(self._show_controls)
        self.window.menu_bar.create_about_button(self._show_about)
    
    def _setup_list_bindings(self):
        mod_widget = self.window.mod_list_widget

        mod_widget.bind_event("<<TreeviewSelect>>", lambda e: self._update_preview())
        mod_widget.bind_event("<Double-Button-1>", self._toggle_row_at_event)
        mod_widget.bind_event("<Button-3>", self._show_context_menu)
        mod_widget.bind_event("<Delete>", self._delete_selected)

        mod_widget.bind_event("<Return>", lambda e: self._toggle_selected())
        mod_widget.bind_event("<space>", lambda e: self._toggle_selected())

        mod_widget.bind_event("<w>", lambda e: self._move_up())
        mod_widget.bind_event("<s>", lambda e: self._move_down())
        mod_widget.bind_event("<W>", lambda e: self._move_to_top())
        mod_widget.bind_event("<S>", lambda e: self._move_to_bottom())

    def _setup_keyboard_shortcuts(self):
        shortcuts = {
            "<F1>": lambda e: self._show_controls(),
            "<F2>": lambda e: self._show_settings(),
            "<F3>": lambda e: self._copy_launch_options(),
            "<F5>": lambda e: self._launch_game(),
            "<Control-q>": lambda e: self.root.quit()
        }
        self.window.bind_keyboard_shortcuts(shortcuts)
    
    def _validate_requirements(self):
        """Validate requirements using UI-localized circular dependency text."""
        return self.mod_service.validate_requirements(
            self.mod_list,
            circular_dependency_template=self.translation_service.get(
                "messages.circular_dependency_requirement",
                "Circular dependency detected between enabled mods: {mods}. "
                "No valid load order can satisfy these requirements.",
            ),
        )

    def _refresh_lists(self, preserve_selection=None):
        mod_widget = self.window.mod_list_widget

        if preserve_selection is None:
            selection = mod_widget.get_selection()
            if selection:
                preserve_selection = selection[1]

        mod_widget.clear()
        enabled_count = 0
        disabled_count = 0

        all_mods = self.mod_list.all_mods
        enabled_mods = [mod for mod in all_mods if mod.enabled]

        disabled_mods = sorted(
            (mod for mod in all_mods if not mod.enabled),
            key=lambda mod: mod.title.casefold(),
        )

        ordered_mods = enabled_mods + disabled_mods

        for mod in ordered_mods:
            if mod.enabled:
                enabled_count += 1
            else:
                disabled_count += 1

            status = None
            if mod.missing:
                # Enabled modlist entry without a matching folder is always red... - Tim
                status = "error"
            elif mod.has_unmet_requirements:
                status = mod.requirement_status or "error"

            mod_widget.add_item(
                mod.name,
                mod.author,
                mod.version,
                mod.enabled,
                status,
                display_name=mod.title,
            )

        self.window.set_mod_counts(disabled_count, enabled_count)

        if preserve_selection:
            mod_widget.select_name(preserve_selection)

    def _on_mod_list_changed(self):
        self._validate_requirements()
        self.mod_service.save_mod_order(self.mod_list)
        # This write came from the UI itself, advance watcher
        # and avoid unnecessary disk reload on next poll... - Tim
        self._record_mod_filesystem_state()

        self._refresh_lists()
        self.root.update_idletasks()
        self._update_dll_manifest()

    def _update_preview(self):
        selection = self.window.mod_list_widget.get_selection()
        if not selection:
            return

        _, name = selection
        mod = self.mod_list.get_mod_by_name(name)
        if mod:
            has_dlls = self.dll_injection_service.mod_has_dlls(mod)
            self.window.preview_panel.update_preview(
                mod.title,
                mod.author,
                mod.version,
                mod.description,
                mod.preview_path,
                mod.url,
                has_dlls,
            )

    def _enable_all(self):
        # Check for DLL mods before enabling all
        if self.dll_injection_service.has_dll_mods(self.mod_list):
            if not self._check_dll_injection_prompt():
                return  # User declined or DLL support is disabled
        self.mod_list.enable_all()
    
    def _disable_all(self):
        self.mod_list.disable_all()
    
    def _enable_mod_with_dll_check(self, mod_name: str):
        """Enable a mod and check if DLL injection prompt should be shown."""
        mod = self.mod_list.get_mod_by_name(mod_name)
        if mod:
            # Check if this mod has DLLs
            if self.dll_injection_service.mod_has_dlls(mod):
                if not self._check_dll_injection_prompt():
                    return  # User declined or DLL support is disabled
        
        # Enable the mod
        self.mod_list.enable_mod(mod_name)
    
    def _auto_configure_chainloader(self):
        """Auto-detect chainloader.ini and configure it if found."""
        if not self.config.game_install_dir:
            return
        
        # Check if chainloader exists and DLL support is enabled
        if self.dll_injection_service.chainloader_exists(self.config.game_install_dir):
            if self.config.dll_injection_enabled:
                # Update manifest immediately
                self._update_dll_manifest()
    
    def _update_dll_manifest(self):
        """Update the DLL manifest file if DLL support is enabled."""
        if not self.config.game_install_dir or not self.config.mod_folder:
            return
        
        # Only update if DLL support is enabled and chainloader exists
        if self.config.dll_injection_enabled and self.dll_injection_service.chainloader_exists(self.config.game_install_dir):
            dll_mods = self.dll_injection_service.scan_for_dll_mods(self.mod_list)
            if dll_mods:
                self.dll_injection_service.update_chainloader_manifest(self.config.game_install_dir, self.config.mod_folder, dll_mods)
            else:
                # No DLL mods enabled, clear the manifest
                self.dll_injection_service.clear_chainloader_manifest(self.config.game_install_dir, self.config.mod_folder)
    
    def _check_dll_injection_prompt(self):
        """Check if DLL injection prompt should be shown and show it. Returns True if DLL support is enabled."""
        if not self.config.dll_injection_enabled:
            # Check if chainloader.ini exists in game directory
            chainloader_exists = False
            show_link = False
            
            if self.config.game_install_dir:
                chainloader_exists = self.dll_injection_service.chainloader_exists(self.config.game_install_dir)
                if not chainloader_exists:
                    show_link = True
            
            result = self._show_dll_prompt_dialog(
                self.translation_service.get("messages.dll_injection_title"),
                self.translation_service.get("messages.dll_injection_prompt"),
                show_link=show_link
            )
            
            self.config.dll_injection_enabled = result
            self.config_service.save_config(self.config)
            
            # Update manifest immediately if enabled
            if result:
                self._update_dll_manifest()
            
            return result
        
        return True
    
    def _swap_selected(self):
        self._toggle_selected()

    def _toggle_disabled(self):
        self._toggle_selected()

    def _toggle_enabled(self):
        self._toggle_selected()

    def _enable_selected_disabled(self, event):
        self._toggle_row_at_event(event)

    def _disable_selected_enabled(self, event):
        self._toggle_row_at_event(event)

    def _toggle_mod(self, mod_name: str):
        mod = self.mod_list.get_mod_by_name(mod_name)
        if not mod:
            return
        if mod.enabled:
            self.mod_list.disable_mod(mod_name)
        else:
            self._enable_mod_with_dll_check(mod_name)

    def _toggle_selected(self):
        selection = self.window.mod_list_widget.get_selection()
        if selection:
            _, name = selection
            self._toggle_mod(name)

    def _toggle_row_at_event(self, event):
        if self.window.mod_list_widget.is_checkbox_at(event.x, event.y):
            return
        name = self.window.mod_list_widget.get_name_at(event.y)
        if name:
            self._toggle_mod(name)

    def _move_up(self):
        selection = self.window.mod_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_up(name)

    def _move_down(self):
        selection = self.window.mod_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_down(name)

    def _move_to_top(self):
        selection = self.window.mod_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_to_top(name)

    def _move_to_bottom(self):
        selection = self.window.mod_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_to_bottom(name)

    def _switch_to_enabled(self):
        self.window.mod_list_widget.focus()

    def _switch_to_disabled(self):
        self.window.mod_list_widget.focus()

    def _start_drag(self, event, source_list=None):
        pass

    def _do_drag(self, event, source_list=None):
        pass

    def _end_drag(self, event, source_list=None, target_list=None):
        pass

    def _delete_selected(self, event=None):
        selection = self.window.mod_list_widget.get_selection()
        if selection:
            _, name = selection
            self._delete_mod(name)
        if event is not None:
            return "break"

    def _delete_mod(self, mod_name: str):
        mod = self.mod_list.get_mod_by_name(mod_name)
        if (
            not mod
            or mod.missing
            or not self.mod_service.repository.mod_exists(mod_name)
        ):
            return

        selection = self.window.mod_list_widget.get_selection()
        selected_index = selection[0] if selection else 0
        confirmed = self._ask_confirmation(
            self.translation_service.get(
                "messages.delete_mod_title"
            ),
            self.translation_service.get(
                "messages.delete_mod_confirm"
            ).format(name=mod.name, path=mod.path),
        )

        if not confirmed:
            return

        try:
            self.mod_service.delete_mod(self.mod_list, mod_name)

            # Reload immediately after deleting the folder...
            self.mod_list = self.mod_service.load_mods()
            self.mod_list.add_observer(self._on_mod_list_changed)
            self._validate_requirements()
            self._refresh_lists()

            remaining = self.window.mod_list_widget.get_items()

            if remaining:
                self.window.mod_list_widget.select_item(
                    min(selected_index, len(remaining) - 1)
                )
                self._update_preview()
            else:
                self.window.preview_panel.clear()

            self._update_dll_manifest()
            self._record_mod_filesystem_state()
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.delete_mod_failed"
                ).format(error=str(e)),
                kind="error",
            )

    def _show_context_menu_disabled(self, event):
        self._show_context_menu(event)

    def _show_context_menu_enabled(self, event):
        self._show_context_menu(event)

    def _show_context_menu(self, event):
        tree = self.window.mod_list_widget.tree
        row_id = tree.identify_row(event.y)
        if not row_id:
            return

        tree.selection_set(row_id)
        tree.focus(row_id)
        name = self.window.mod_list_widget.get_name_at(event.y)
        mod = self.mod_list.get_mod_by_name(name) if name else None
        if not mod:
            return

        menu = PointerMenu(self.root, cursor="hand2")
        colors = self.theme_service.get_color_scheme(self.config.theme)
        menu.configure(
            background=colors["menu_bg"],
            foreground=colors["menu_fg"],
            activebackground=colors["menu_active_bg"],
            activeforeground=colors["menu_active_fg"],
            font="MewtatorMenu",
        )
        if mod.enabled:
            menu.add_command(
                label=self.translation_service.get("context_menu.move_top"),
                command=lambda: self.mod_list.move_to_top(name),
            )
            menu.add_command(
                label=self.translation_service.get("context_menu.move_bottom"),
                command=lambda: self.mod_list.move_to_bottom(name),
            )
            menu.add_separator()
            menu.add_command(
                label=self.translation_service.get("context_menu.disable"),
                command=lambda: self.mod_list.disable_mod(name),
            )
        else:
            menu.add_command(
                label=self.translation_service.get("context_menu.enable"),
                command=lambda: self._enable_mod_with_dll_check(name),
            )
        menu.add_separator()
        mod_folder_available = (
            not mod.missing and self.mod_service.repository.mod_exists(name)
        )
        menu.add_command(
            label=self.translation_service.get(
                "context_menu.open_mod_folder"
            ),
            command=lambda: self._open_mod_folder(name),
            state="normal" if mod_folder_available else "disabled",
        )
        menu.add_separator()
        menu.add_command(
            label=self.translation_service.get(
                "context_menu.delete"
            ),
            command=lambda: self._delete_mod(name),
            state="normal" if mod_folder_available else "disabled",
        )
        menu.post(event.x_root, event.y_root)

    def _open_mod_folder(self, mod_name: str):
        mod = self.mod_list.get_mod_by_name(mod_name)
        if not mod or mod.missing or not self.mod_service.repository.mod_exists(mod_name):
            return
        try:
            open_file_or_folder(mod.path)
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.open_mod_folder_failed"
                ).format(error=str(e)),
                kind="error",
            )

    def _launch_game(self):
        # Check for another game instance before launching
        if not self.config.concurrent_launches_enabled:
            if self.launcher_service.collect_launched_processes(self.config.game_install_dir):
                self._show_notification(
                    self.translation_service.get("messages.launch_error"),
                    self.translation_service.get("messages.already_running"),
                    kind="error",
                )
                return

        # Re-read mods once at launch time so edits made after startup cannot bypass validation.
        # This is deliberately only when Launch is invoked, but could probably also be used in a background filesystem watcher... - Tim
        req_errors = self._reload_mods_from_disk()

        missing = self.mod_service.get_missing_mod_names(self.mod_list)
        if missing:
            self._show_notification(
                self.translation_service.get("messages.missing_mods_title"),
                self.translation_service.get(
                    "messages.missing_mods_text"
                ).replace("{missing}", "\n".join(missing)),
                kind="error",
            )
            return
        
        if req_errors:
            error_msg = "\n".join(req_errors)
            result = self._ask_confirmation(
                self.translation_service.get("alerts.requirement_conflict"),
                self.translation_service.get("alerts.requirement_conflict_text").format(errors=error_msg)
            )
            if not result:
                return
        
        # Check for conflicts in savefile_suffix and inherit_save
        conflicts = self.mod_service.detect_conflicts(self.mod_list, self.config)
        if conflicts:
            conflict_msg = "\n".join(conflicts)
            self._show_notification(
                self.translation_service.get("alerts.savefile_conflict"),
                conflict_msg
            )
        
        user_enabled_paths = self.mod_service.get_enabled_mod_paths(self.mod_list)
        enabled_paths = self.mod_service.get_launch_mod_paths(self.mod_list, self.config)
        logger = get_logger()
        enabled_mods = [(mod.name, mod.path) for mod in self.mod_list.enabled_mods]
        logger.info("Launching game with %d user-enabled mods", len(enabled_mods))
        for name, path in enabled_mods:
            logger.info("Enabled mod: %s | %s", name, path)
        if self.config.mewtator_intro_enabled and user_enabled_paths:
            logger.info("Bundled Mewtator intro mod enabled: %s", enabled_paths[-1])
        elif self.config.mewtator_intro_enabled:
            logger.info("Bundled Mewtator intro mod skipped: no user mods enabled")
        
        # The bundled intro lives with Mewtator by design, so Proton's external
        # mod warning should only consider user-managed mods... - Tim
        if self.launcher_service.should_warn_external_mods(self.config.game_install_dir, user_enabled_paths):
            result = self._ask_confirmation(
                self.translation_service.get("messages.proton_warning_title"),
                self.translation_service.get("messages.proton_warning_text")
            )
            if not result:
                return
        
        try:
            self.launcher_service.launch_game(
                self.config.game_install_dir,
                enabled_paths,
                self.config,
                self.mod_list,
                self.translation_service
            )
            
            # Close launcher if option is enabled
            if self.config.close_on_launch:
                self.root.destroy()
                
        except FileNotFoundError:
            self._show_notification(
                self.translation_service.get("messages.launch_error"),
                self.translation_service.get("messages.exe_not_found"),
                kind="error",
            )
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.launch_error"),
                str(e),
                kind="error",
            )
    
    def _copy_launch_options(self):
        missing = self.mod_service.get_missing_mod_names(self.mod_list)
        if missing:
            self._show_notification(
                self.translation_service.get("messages.missing_mods_title"),
                self.translation_service.get(
                    "messages.missing_mods_text"
                ).replace("{missing}", "\n".join(missing)),
                kind="error",
            )
            return

        enabled_paths = self.mod_service.get_launch_mod_paths(self.mod_list, self.config)
        launch_opts = self.launcher_service.get_launch_options(
            self.config.game_install_dir,
            enabled_paths,
            self.config,
            self.mod_list,
        )

        self.root.clipboard_clear()
        self.root.clipboard_append(launch_opts)
        self.root.update()

        LaunchOptionsWindow(
            self.root,
            self.translation_service,
            self.theme_service,
            launch_opts,
            on_export=lambda parent: self._export_bat_file(enabled_paths, parent),
        )

    def _stop_game(self):
        # Check for another game instance before presenting confirmation
        if not self.launcher_service.collect_launched_processes(self.config.game_install_dir):
            self._show_notification(
                self.translation_service.get("messages.launch_error"),
                self.translation_service.get("messages.not_running"),
                kind="error",
            )
            return

        # Ask for confirmation
        result = self._ask_confirmation(
            self.translation_service.get("messages.stop_game_title"),
            self.translation_service.get("messages.stop_game_text")
        )
        if not result:
            return

        try:
            self.launcher_service.stop_game(
                self.config.game_install_dir,
                self.config,
                self.translation_service
            )
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.launch_error"),
                str(e),
                kind="error",
            )

    def _export_bat_file(self, enabled_paths, parent_dialog=None):
        """Export launch configuration to a .bat file."""
        default_name = "launch_mewgenics_mods.bat"

        with self.theme_service.file_dialog_safe_theme():
            filepath = filedialog.asksaveasfilename(
                parent=parent_dialog or self.root,
                title=self.translation_service.get("messages.export_bat_title"),
                initialfile=default_name,
                initialdir=self.config.game_install_dir,
                defaultextension=".bat",
                filetypes=[
                    (self.translation_service.get("messages.batch_files"), "*.bat"),
                    (self.translation_service.get("messages.all_files"), "*.*"),
                ]
            )
        
        if not filepath:
            return
        
        try:
            steam_launch_option = self.launcher_service.export_bat_file(
                self.config.game_install_dir,
                enabled_paths,
                filepath,
                self.config,
                self.mod_list
            )
            
            ExportSuccessWindow(
                parent_dialog or self.root,
                self.translation_service,
                self.theme_service,
                steam_launch_option,
            )
            
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.export_launch_failed"
                ).format(error=str(e)),
                kind="error",
            )
    
    def _cleanup_dll_injection(self):
        """Clean up DLL manifest and chainloader configuration."""
        if not self.config.game_install_dir:
            self._show_notification(
                self.translation_service.get("messages.warning"),
                self.translation_service.get(
                    "messages.game_dir_not_set"
                ),
                kind="warning",
            )
            return
        
        # Check if chainloader configuration exists
        if not self.dll_injection_service.is_chainloader_configured(self.config.game_install_dir):
            self._show_notification(
                self.translation_service.get("messages.dll_cleanup_title"),
                self.translation_service.get(
                    "messages.dll_cleanup_nothing"
                )
            )
            return
        
        # Confirm cleanup
        result = self._ask_confirmation(
            self.translation_service.get("messages.dll_cleanup_title"),
            self.translation_service.get(
                "messages.dll_cleanup_confirm"
            )
        )
        
        if not result:
            return
        
        # Perform cleanup
        try:
            self.dll_injection_service.clear_chainloader_manifest(self.config.game_install_dir, self.config.mod_folder)
            
            self._show_notification(
                self.translation_service.get("messages.dll_cleanup_title"),
                self.translation_service.get(
                    "messages.dll_cleanup_success"
                )
            )
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error", "Error"),
                self.translation_service.get(
                    "messages.dll_cleanup_failed"
                ).format(error=str(e)),
                kind="error",
            )
    
    def _auto_sort(self):
        """Auto-sort enabled mods alphabetically and by requirements."""
        if not self.mod_list.enabled_mods:
            self._show_notification(
                self.translation_service.get("mod_list.auto_sort"),
                self.translation_service.get(
                    "messages.no_mods_to_sort"
                ),
            )
            return
        
        sorted_names, warnings = self.mod_service.auto_sort(
            self.mod_list,
            circular_dependency_warning=self.translation_service.get(
                "messages.circular_dependency_auto_sort",
                "Circular dependencies detected. Some requirements may not be satisfied.",
            ),
        )
        
        if sorted_names:
            self.mod_list.set_order(sorted_names)
            
            if warnings:
                warning_msg = "\n".join(warnings)
                self._show_notification(
                    self.translation_service.get("mod_list.auto_sort"),
                    self.translation_service.get(
                        "messages.auto_sort_warnings"
                    ).format(warnings=warning_msg),
                    kind="warning",
                )
            else:
                self._show_notification(
                    self.translation_service.get("mod_list.auto_sort"),
                    self.translation_service.get(
                        "messages.auto_sort_success"
                    ),
                )

    def _show_notification(
        self,
        title: str,
        message: str,
        kind: str = "info",
    ):
        NotificationWindow(
            self.root,
            title,
            message,
            self.theme_service,
            button_text=self.translation_service.get("common.ok"),
            kind=kind,
        ).show()

    def _ask_confirmation(self, title: str, message: str) -> bool:
        return NotificationWindow(
            self.root,
            title,
            message,
            self.theme_service,
            button_text=self.translation_service.get("dialog.yes"),
            cancel_text=self.translation_service.get("dialog.no"),
            kind="warning",
        ).show()
    
    def _unpack(self):
        output_dir = os.path.join(self.config.mod_folder, "_unpacked")
        os.makedirs(output_dir, exist_ok=True)
        
        pw = ProgressWindow(self.root, self.translation_service.get("progress.unpacking"), 100, self.theme_service)
        
        try:
            def progress(current, total):
                pw.update(int((current / total) * 100))
            
            self.pack_service.unpack(self.config.game_install_dir, output_dir, progress)
            pw.close()
            self._show_notification(
                self.translation_service.get("messages.success"),
                self.translation_service.get("messages.unpack_complete")
            )
        except Exception as e:
            pw.close()
            self._show_notification(
                self.translation_service.get("messages.error"),
                str(e),
                kind="error",
            )
    
    def _repack(self):
        source_dir = os.path.join(self.config.mod_folder, "_unpacked")
        gpak_output = os.path.join(self.config.game_install_dir, "resources.gpak")
        
        pw = ProgressWindow(self.root, self.translation_service.get("progress.repacking"), 100, self.theme_service)
        
        try:
            def progress(current, total):
                pw.update(int((current / total) * 100))
            
            self.pack_service.repack(source_dir, gpak_output, progress)
            pw.close()
            self._show_notification(
                self.translation_service.get("messages.success"),
                self.translation_service.get("messages.repack_complete")
            )
        except Exception as e:
            pw.close()
            self._show_notification(
                self.translation_service.get("messages.error"),
                str(e),
                kind="error",
            )
    
    def _import_mod_zip(self):
        """Import a mod ZIP into configured mods folder..."""

        with self.theme_service.file_dialog_safe_theme():
            filepath = filedialog.askopenfilename(
                parent=self.root,
                title=self.translation_service.get("messages.import_mod"),
                filetypes=[
                    (self.translation_service.get("messages.zip_files"), "*.zip"),
                    (self.translation_service.get("messages.all_files"), "*.*"),
                ],
            )

        if not filepath:
            return

        try:
            try:
                mod_name, _ = self.mod_import_service.import_zip(
                    filepath,
                    self.config.mod_folder,
                    replace=False,
                )
            except ExistingModError as existing:
                replace = self._ask_confirmation(
                    self.translation_service.get("messages.import_mod"),
                    self.translation_service.get(
                        "messages.mod_already_exists"
                    ).format(name=existing.mod_name),
                )
                if not replace:
                    return

                mod_name, _ = self.mod_import_service.import_zip(
                    filepath,
                    self.config.mod_folder,
                    replace=True,
                )

            # Reload immediately so the imported folder appears. Imported mods
            # remain disabled until the user checks them... - Tim
            self.mod_list = self.mod_service.load_mods()
            self.mod_list.add_observer(self._on_mod_list_changed)
            self._validate_requirements()
            self._refresh_lists(preserve_selection=mod_name)
            self._record_mod_filesystem_state()

            self._show_notification(
                self.translation_service.get("messages.success"),
                self.translation_service.get(
                    "messages.import_mod_success"
                ).format(name=mod_name),
            )
        except zipfile.BadZipFile:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.invalid_mod_zip"
                ),
                kind="error",
            )
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.import_mod_failed"
                ).format(error=str(e)),
                kind="error",
            )

    def _import_modlist(self):
        with self.theme_service.file_dialog_safe_theme():
            filepath = filedialog.askopenfilename(
                parent=self.root,
                title=self.translation_service.get("messages.import_modlist"),
                filetypes=[
                    (self.translation_service.get("messages.json_files"), "*.json"),
                    (self.translation_service.get("messages.text_files"), "*.txt"),
                    (self.translation_service.get("messages.all_files"), "*.*"),
                ]
            )
        
        if not filepath:
            return
        
        try:
            imported_names = self.modlist_io_service.import_modlist_file(filepath)
            
            available_mod_names = {
                mod.name for mod in self.mod_list.all_mods if not mod.missing
            }

            valid_names = []
            seen_names = set()
            missing_count = 0

            for name in imported_names:
                if name not in available_mod_names:
                    missing_count += 1
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)
                valid_names.append(name)

            if missing_count:
                self._show_notification(
                    self.translation_service.get("messages.warning"),
                    self.translation_service.get(
                        "messages.import_modlist_missing"
                    ).format(
                        imported=len(valid_names),
                        missing=missing_count,
                    ),
                    kind="warning",
                )

            # Importing a modlist must reproduce its enabled state, not merely
            # reorder mods that happened to already be enabled... - Tim
            self.mod_list.apply_enabled_names(valid_names)
            self._show_notification(
                self.translation_service.get("messages.success"),
                self.translation_service.get(
                    "messages.import_modlist_success"
                ).format(
                    count=len(valid_names),
                ),
            )
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.import_modlist_failed"
                ).format(error=str(e)),
                kind="error",
            )
    
    def _export_modlist(self):
        json_files_label = self.translation_service.get("messages.json_files")
        text_files_label = self.translation_service.get("messages.text_files")
        selected_filetype = tk.StringVar(master=self.root, value=json_files_label)

        with self.theme_service.file_dialog_safe_theme():
            filepath = filedialog.asksaveasfilename(
                parent=self.root,
                title=self.translation_service.get("messages.export_modlist"),
                # Leave this empty so the selected file filter can determine
                # the extension instead of always forcing .json... - Tim
                defaultextension="",
                typevariable=selected_filetype,
                filetypes=[
                    (json_files_label, "*.json"),
                    (text_files_label, "*.txt"),
                    (self.translation_service.get("messages.all_files"), "*.*"),
                ]
            )
        
        if not filepath:
            return

        # Some native dialogs do not append the selected filter extension.
        # Add it ourselves only when the user did not type an extension... - Tim
        if not os.path.splitext(filepath)[1]:
            extension = ".txt" if selected_filetype.get() == text_files_label else ".json"
            filepath += extension
        
        try:
            enabled_names = self.mod_list.enabled_mod_names
            
            modlist_name = None
            if self.modlist_io_service.get_format(filepath) == "json":
                default_name = os.path.splitext(os.path.basename(filepath))[0]
                modlist_name = simpledialog.askstring(
                    self.translation_service.get("messages.export_modlist"),
                    self.translation_service.get("messages.modlist_name_prompt"),
                    initialvalue=default_name,
                    parent=self.root
                )
                if modlist_name is None:
                    return

            self.modlist_io_service.export_modlist_file(
                enabled_names, filepath, modlist_name
            )
            
            self._show_notification(
                self.translation_service.get("messages.success"),
                self.translation_service.get(
                    "messages.export_modlist_success"
                ).format(
                    count=len(enabled_names),
                ),
            )
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.export_modlist_failed"
                ).format(error=str(e)),
                kind="error",
            )
    
    def _show_controls(self):
        ControlsWindow(
            self.root,
            self.translation_service,
            self.theme_service,
            self.config.theme,
        )

    def _show_about(self):
        AboutWindow(
            self.root,
            self.translation_service,
            self.theme_service,
            self.config.theme,
        )

    def _show_settings(self, first_run: bool = False):
        def on_save(new_config):
            self.config = new_config
            self.config_service.save_config(new_config)
            self.translation_service.load_language(new_config.language)
            self._reload_ui()
        
        SettingsWindow(
            self.root,
            self.config,
            self.translation_service,
            self.theme_service,
            on_save,
            on_cancel=self.root.destroy if first_run else None,
        )
    
    def _show_dll_prompt_dialog(self, title: str, message: str, show_link: bool = True):
        """Show a custom yes/no dialog with optional clickable Mewjector link. Returns True if user clicks Yes."""
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", lambda: on_no())

        if self.root.winfo_viewable():
            dialog.transient(self.root)

        theme_name = self.theme_service.normalize_theme_name(self.config.theme)
        colors = self.theme_service.get_color_scheme(theme_name)
        dialog.configure(bg=colors["bg"])
        self.theme_service.apply_titlebar(dialog, theme_name)

        container = dialog_frame(dialog, colors, padx=24, pady=22)
        container.pack(fill="both", expand=True)

        dialog_label(
            container,
            colors,
            text=title,
            font="MewtatorHeading",
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 12))

        dialog_label(
            container,
            colors,
            text=message or "",
            font="MewtatorBody",
            wraplength=552,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 14))

        if show_link:
            link_frame = dialog_frame(container, colors)
            link_frame.pack(fill="x", pady=(0, 12))

            dialog_label(
                link_frame,
                colors,
                text=self.translation_service.get(
                    "messages.mewjector_link_text", "Get Mewjector here: "
                ),
                font="MewtatorBody",
                anchor="w",
            ).pack(side="left")

            mewjector_url = "https://www.nexusmods.com/mewgenics/mods/218"
            link_color = "#5DADE2" if theme_name == "dark" else "#2E7DBE"
            link_label = dialog_label(
                link_frame,
                colors,
                text=self.translation_service.get(
                    "messages.mewjector_url_display",
                    "nexusmods.com/mewgenics/mods/218",
                ),
                font="MewtatorBodyUnderline",
                foreground=link_color,
                cursor="hand2",
                anchor="w",
            )
            link_label.pack(side="left")
            link_label.bind("<Button-1>", lambda _event: webbrowser.open(mewjector_url))

        button_frame = dialog_frame(container, colors)
        button_frame.pack(fill="x", pady=(18, 0))

        result = {"value": False}

        def on_yes():
            result["value"] = True
            if dialog.winfo_exists():
                dialog.destroy()

        def on_no():
            result["value"] = False
            if dialog.winfo_exists():
                dialog.destroy()

        ttk.Button(
            button_frame,
            text=self.translation_service.get("dialog.yes", "Yes"),
            command=on_yes,
            cursor="hand2",
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            button_frame,
            text=self.translation_service.get("dialog.no", "No"),
            command=on_no,
            cursor="hand2",
        ).pack(side="right")

        # Size from actual content instead of clipping translated/wrapped text into a fixed height dialog... - Tim
        fit_window_to_content(
            dialog,
            self.root,
            min_width=600,
            min_height=300,
            preferred_width=600,
            preferred_height=300,
            screen_margin_x=80,
            screen_margin_y=80,
        )
        
        dialog.deiconify()
        dialog.lift()
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

        return result["value"]

    def _change_language(self, language: str):
        self.config.language = language
        self.config_service.save_config(self.config)
        self.translation_service.load_language(language)
        self._reload_ui()
    
    def _change_theme(self, theme: str):
        try:
            normalized = self.theme_service.normalize_theme_name(theme)
            self.theme_service.set_theme(normalized)
            self.config.theme = normalized
            self.config_service.save_config(self.config)
            if self.window is not None:
                self.window.apply_theme(self.theme_service, normalized)
                self.window.menu_bar.update_theme_selection(normalized)
        except Exception as e:
            self._show_notification(
                self.translation_service.get("messages.error"),
                self.translation_service.get(
                    "messages.theme_change_failed"
                ).format(error=str(e)),
                kind="error",
            )
    
    def _reload_ui(self):
        """Rebuild the application inside the existing Tk interpreter...
        """
        if self._mod_filesystem_watch_job is not None:
            try:
                self.root.after_cancel(self._mod_filesystem_watch_job)
            except tk.TclError:
                pass
            self._mod_filesystem_watch_job = None

        self.root.withdraw()

        for sequence in (
            "<Button-1>",
            "<Escape>",
            "<F1>",
            "<F2>",
            "<F3>",
            "<F5>",
            "<Control-q>",
        ):
            try:
                self.root.unbind(sequence)
            except tk.TclError:
                pass

        for child in list(self.root.winfo_children()):
            try:
                child.destroy()
            except tk.TclError:
                pass

        from app.infrastructure.mod_repository import ModRepository
        self.mod_service = ModService(ModRepository(self.config.mod_folder))
        self.mod_list = None
        self.window = None
        self._last_mod_filesystem_state = None

        self.theme_service.bind_root(self.root)
        self.theme_service.configure_fonts(self.config.use_generic_font)
        self.theme_service.set_theme(self.config.theme)

        self._build_main_window()
        self.root.deiconify()
        self.root.lift()
    
    def _record_mod_filesystem_state(self):
        """Capture the current disk state as the watcher's baseline..."""
        try:
            self._last_mod_filesystem_state = (
                self.mod_service.repository.get_filesystem_state()
            )
        except OSError:
            # Transient filesystem failure should not stop future polling... - Tim
            pass

    def _start_mod_filesystem_watch(self):
        """Start polling for external modlist, folder, and metadata changes..."""
        self._record_mod_filesystem_state()
        self._schedule_mod_filesystem_watch()

    def _schedule_mod_filesystem_watch(self):
        try:
            self._mod_filesystem_watch_job = self.root.after(
                self._mod_filesystem_watch_interval_ms,
                self._poll_mod_filesystem,
            )
        except tk.TclError:
            self._mod_filesystem_watch_job = None

    def _poll_mod_filesystem(self):
        """Reload mods when modlist.txt, folders, or mod metadata changes..."""
        self._mod_filesystem_watch_job = None

        try:
            current_state = self.mod_service.repository.get_filesystem_state()

            if self._last_mod_filesystem_state is None:
                self._last_mod_filesystem_state = current_state
            elif current_state != self._last_mod_filesystem_state:
                # Record the state that caused this reload. If another external
                # edit lands while we're reloading, the next poll will still
                # see it as a new change instead of accidentally swallowing... - Tim
                self._last_mod_filesystem_state = current_state
                self._reload_mods_from_disk()
        except tk.TclError:
            return
        except Exception as exc:
            get_logger().warning(
                "Failed to refresh mods after filesystem change: %s", exc
            )
        finally:
            self._schedule_mod_filesystem_watch()

    def _reload_mods_from_disk(self, preserve_selection=None):
        """Fully re-read mod folders, metadata, and requirement state..."""

        if preserve_selection is None and self.window is not None:
            selection = self.window.mod_list_widget.get_selection()
            if selection:
                preserve_selection = selection[1]

        self.mod_list = self.mod_service.load_mods()
        self.mod_list.add_observer(self._on_mod_list_changed)
        requirement_errors = self._validate_requirements()
        self._refresh_lists(preserve_selection=preserve_selection)

        # Repaint Mod Info immediately...
        if self.window.mod_list_widget.get_selection():
            self._update_preview()
        else:
            self.window.preview_panel.clear()

        return requirement_errors

    def _force_refresh_mods(self):
        self._reload_mods_from_disk()
        self._record_mod_filesystem_state()

