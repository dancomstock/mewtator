import os
import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Text, Button, WORD, BOTH, filedialog, simpledialog
from tkinter import ttk
from app.core.models.mod_list import ModList
from app.core.services.mod_service import ModService
from app.core.services.config_service import ConfigService
from app.core.services.game_launcher_service import GameLauncherService
from app.core.services.translation_service import TranslationService
from app.core.services.pack_service import PackService
from app.core.services.modlist_io_service import ModListIOService
from app.core.services.theme_service import ThemeService
from app.ui.windows.main_window import MainWindow
from app.ui.windows.settings_window import SettingsWindow
from app.ui.windows.progress_window import ProgressWindow
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
        theme_service: ThemeService
    ):
        self.root = root
        self.config_service = config_service
        self.mod_service = mod_service
        self.launcher_service = launcher_service
        self.translation_service = translation_service
        self.pack_service = pack_service
        self.modlist_io_service = modlist_io_service
        self.theme_service = theme_service
        
        self.config = config_service.load_config()
        self.mod_list: ModList = None
        self.window: MainWindow = None
        
        self.last_mtime = 0
        self.last_mod_folders = set()
        
        self.drag_data = {"source": None, "index": None, "changed": False}
        self.drag_indicator = None
    
    def start(self):
        if not self.config_service.validate_config(self.config):
            self.theme_service.set_theme(self.config.theme)
            self._show_info_dialog(
                self.translation_service.get("messages.setup_required_title"),
                self.translation_service.get("messages.setup_required_text")
            )
            self._show_settings()
            self.root.mainloop()
            return
        
        self._build_main_window()
        self._setup_auto_refresh()
        self.root.mainloop()
    
    def _build_main_window(self):
        self.theme_service.set_theme(self.config.theme)
        self.window = MainWindow(self.root, self.translation_service)
        
        self.mod_list = self.mod_service.load_mods()
        self.mod_list.add_observer(self._on_mod_list_changed)
        
        self.window.set_disabled_list_action(self._disable_all)
        self.window.set_enabled_list_action(self._enable_all)
        self.window.set_swap_action(self._swap_selected)
        self.window.set_launch_action(self._launch_game)
        
        self._setup_menu_bar()
        self._setup_list_bindings()
        self._setup_keyboard_shortcuts()
        
        self._refresh_lists()
        self.window.apply_theme(self.theme_service, self.config.theme)
    
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
            on_exit=self.root.quit
        )
        
        available_langs = self.translation_service.get_available_languages()
        self.window.menu_bar.create_language_menu(
            available_langs,
            self.config.language,
            self._change_language
        )
        
        available_themes = self.theme_service.get_available_themes()
        self.window.menu_bar.create_theme_menu(
            available_themes,
            self.config.theme,
            self._change_theme
        )
    
    def _setup_list_bindings(self):
        disabled_widget = self.window.disabled_list_widget
        enabled_widget = self.window.enabled_list_widget
        
        disabled_widget.bind_event("<<ListboxSelect>>", lambda e: self._update_preview_from_disabled())
        enabled_widget.bind_event("<<ListboxSelect>>", lambda e: self._update_preview_from_enabled())
        
        disabled_widget.bind_event("<Double-Button-1>", lambda e: self._enable_selected_disabled(e))
        enabled_widget.bind_event("<Double-Button-1>", lambda e: self._disable_selected_enabled(e))
        
        disabled_widget.bind_event("<Button-3>", lambda e: self._show_context_menu_disabled(e))
        enabled_widget.bind_event("<Button-3>", lambda e: self._show_context_menu_enabled(e))
        
        disabled_widget.bind_event("<Return>", lambda e: self._toggle_disabled())
        disabled_widget.bind_event("<space>", lambda e: self._toggle_disabled())
        enabled_widget.bind_event("<Return>", lambda e: self._toggle_enabled())
        enabled_widget.bind_event("<space>", lambda e: self._toggle_enabled())
        
        enabled_widget.bind_event("<w>", lambda e: self._move_up())
        enabled_widget.bind_event("<s>", lambda e: self._move_down())
        enabled_widget.bind_event("<W>", lambda e: self._move_to_top())
        enabled_widget.bind_event("<S>", lambda e: self._move_to_bottom())
        
        disabled_widget.bind_event("<bracketleft>", lambda e: self._switch_to_enabled())
        disabled_widget.bind_event("<bracketright>", lambda e: self._switch_to_enabled())
        enabled_widget.bind_event("<bracketleft>", lambda e: self._switch_to_disabled())
        enabled_widget.bind_event("<bracketright>", lambda e: self._switch_to_disabled())
        
        disabled_widget.bind_event("<Button-1>", lambda e: self._start_drag(e, disabled_widget.listbox))
        disabled_widget.bind_event("<B1-Motion>", lambda e: self._do_drag(e, disabled_widget.listbox))
        disabled_widget.bind_event("<ButtonRelease-1>", lambda e: self._end_drag(e, disabled_widget.listbox, enabled_widget.listbox))
        
        enabled_widget.bind_event("<Button-1>", lambda e: self._start_drag(e, enabled_widget.listbox))
        enabled_widget.bind_event("<B1-Motion>", lambda e: self._do_drag(e, enabled_widget.listbox))
        enabled_widget.bind_event("<ButtonRelease-1>", lambda e: self._end_drag(e, enabled_widget.listbox, disabled_widget.listbox))
    
    def _setup_keyboard_shortcuts(self):
        shortcuts = {
            "<F2>": lambda e: self._show_settings(),
            "<F3>": lambda e: self._copy_launch_options(),
            "<F5>": lambda e: self._launch_game(),
            "<Control-q>": lambda e: self.root.quit()
        }
        self.window.bind_keyboard_shortcuts(shortcuts)
    
    def _refresh_lists(self, preserve_selection=None):
        disabled_widget = self.window.disabled_list_widget
        enabled_widget = self.window.enabled_list_widget
        
        if preserve_selection is None:
            enabled_sel = enabled_widget.get_selection()
            disabled_sel = disabled_widget.get_selection()
            if enabled_sel:
                preserve_selection = ('enabled', enabled_sel[1])
            elif disabled_sel:
                preserve_selection = ('disabled', disabled_sel[1])
        
        disabled_widget.clear()
        enabled_widget.clear()
        
        for mod in self.mod_list.all_mods:
            if mod.enabled:
                color = "red" if mod.missing else None
                enabled_widget.add_item(mod.name, color)
            else:
                disabled_widget.add_item(mod.name)
        
        if preserve_selection:
            list_type, item_name = preserve_selection
            target_widget = enabled_widget if list_type == 'enabled' else disabled_widget
            items = target_widget.get_items()
            if item_name in items:
                target_widget.select_item(items.index(item_name))
    
    def _on_mod_list_changed(self):
        self.mod_service.save_mod_order(self.mod_list)
        self._refresh_lists()
    
    def _update_preview_from_disabled(self):
        selection = self.window.disabled_list_widget.get_selection()
        if selection:
            _, name = selection
            mod = self.mod_list.get_mod_by_name(name)
            if mod:
                self.window.preview_panel.update_preview(
                    mod.title, mod.author, mod.version, mod.description, mod.preview_path
                )
    
    def _update_preview_from_enabled(self):
        selection = self.window.enabled_list_widget.get_selection()
        if selection:
            _, name = selection
            mod = self.mod_list.get_mod_by_name(name)
            if mod:
                self.window.preview_panel.update_preview(
                    mod.title, mod.author, mod.version, mod.description, mod.preview_path
                )
    
    def _enable_all(self):
        self.mod_list.enable_all()
    
    def _disable_all(self):
        self.mod_list.disable_all()
    
    def _swap_selected(self):
        disabled_selection = self.window.disabled_list_widget.get_selection()
        enabled_selection = self.window.enabled_list_widget.get_selection()
        
        if disabled_selection:
            _, name = disabled_selection
            self.mod_list.enable_mod(name)
        elif enabled_selection:
            _, name = enabled_selection
            self.mod_list.disable_mod(name)
    
    def _toggle_disabled(self):
        selection = self.window.disabled_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.enable_mod(name)
    
    def _toggle_enabled(self):
        selection = self.window.enabled_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.disable_mod(name)
    
    def _enable_selected_disabled(self, event):
        widget = event.widget
        index = widget.nearest(event.y)
        if index >= 0:
            name = widget.get(index)
            self.mod_list.enable_mod(name)
    
    def _disable_selected_enabled(self, event):
        widget = event.widget
        index = widget.nearest(event.y)
        if index >= 0:
            name = widget.get(index)
            self.mod_list.disable_mod(name)
    
    def _move_up(self):
        selection = self.window.enabled_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_up(name)
    
    def _move_down(self):
        selection = self.window.enabled_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_down(name)
    
    def _move_to_top(self):
        selection = self.window.enabled_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_to_top(name)
    
    def _move_to_bottom(self):
        selection = self.window.enabled_list_widget.get_selection()
        if selection:
            _, name = selection
            self.mod_list.move_to_bottom(name)
    
    def _switch_to_enabled(self):
        self.window.enabled_list_widget.focus()
    
    def _switch_to_disabled(self):
        self.window.disabled_list_widget.focus()
    
    def _start_drag(self, event, source_list):
        self.drag_data["source"] = source_list
        self.drag_data["index"] = source_list.nearest(event.y)
        self.drag_data["changed"] = False
        
        if self.drag_data["index"] >= 0 and self.drag_data["index"] < source_list.size():
            item_text = source_list.get(self.drag_data["index"])
            
            self.drag_indicator = tk.Toplevel(self.root)
            self.drag_indicator.wm_overrideredirect(True)
            self.drag_indicator.wm_attributes("-alpha", 0.8)
            self.drag_indicator.wm_attributes("-topmost", True)
            
            label = tk.Label(
                self.drag_indicator,
                text=f"📦 {item_text}",
                bg="#4a90e2",
                fg="white",
                font=("Arial", 10, "bold"),
                padx=10,
                pady=5,
                relief="raised",
                borderwidth=2
            )
            label.pack()
            
            self.drag_indicator.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
    
    def _do_drag(self, event, source_list):
        if self.drag_indicator:
            self.drag_indicator.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        
        if self.drag_data["source"] != source_list:
            return
        
        old_index = self.drag_data["index"]
        if old_index < 0 or old_index >= source_list.size():
            return
        
        new_index = source_list.nearest(event.y)
        
        if new_index != old_index and new_index >= 0 and new_index < source_list.size():
            item = source_list.get(old_index)
            source_list.delete(old_index)
            source_list.insert(new_index, item)
            source_list.selection_clear(0, tk.END)
            source_list.selection_set(new_index)
            self.drag_data["index"] = new_index
            self.drag_data["changed"] = True
    
    def _end_drag(self, event, source_list, target_list):
        if self.drag_indicator:
            self.drag_indicator.destroy()
            self.drag_indicator = None
        
        if self.drag_data["source"] != source_list:
            self.drag_data["changed"] = False
            return
        
        old_index = self.drag_data["index"]
        if old_index < 0 or old_index >= source_list.size():
            self.drag_data["changed"] = False
            return
        
        item = source_list.get(old_index)
        
        x, y = event.x_root, event.y_root
        widget = self.root.winfo_containing(x, y)
        
        moved_between_lists = False
        if widget == target_list:
            if source_list == self.window.enabled_list_widget.listbox:
                self.mod_list.disable_mod(item)
            else:
                self.mod_list.enable_mod(item)
            moved_between_lists = True
        
        if not moved_between_lists and self.drag_data["changed"]:
            enabled_names = list(self.window.enabled_list_widget.get_items())
            self.mod_list.set_order(enabled_names)
        
        self.drag_data["source"] = None
        self.drag_data["index"] = None
        self.drag_data["changed"] = False
    
    def _show_context_menu_disabled(self, event):
        widget = event.widget
        index = widget.nearest(event.y)
        if index < 0:
            return
        
        widget.selection_clear(0, tk.END)
        widget.selection_set(index)
        
        name = widget.get(index)
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label=self.translation_service.get("context_menu.enable"),
            command=lambda: self.mod_list.enable_mod(name)
        )
        menu.post(event.x_root, event.y_root)
    
    def _show_context_menu_enabled(self, event):
        widget = event.widget
        index = widget.nearest(event.y)
        if index < 0:
            return
        
        widget.selection_clear(0, tk.END)
        widget.selection_set(index)
        
        name = widget.get(index)
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label=self.translation_service.get("context_menu.move_top"),
            command=lambda: self.mod_list.move_to_top(name)
        )
        menu.add_command(
            label=self.translation_service.get("context_menu.move_bottom"),
            command=lambda: self.mod_list.move_to_bottom(name)
        )
        menu.add_command(
            label=self.translation_service.get("context_menu.disable"),
            command=lambda: self.mod_list.disable_mod(name)
        )
        menu.post(event.x_root, event.y_root)
    
    def _launch_game(self):
        missing = self.mod_service.get_missing_mod_names(self.mod_list)
        if missing:
            messagebox.showerror(
                self.translation_service.get("messages.missing_mods_title"),
                self.translation_service.get("messages.missing_mods_text", "").replace("{missing}", "\n".join(missing))
            )
            return
        
        enabled_paths = self.mod_service.get_enabled_mod_paths(self.mod_list)
        logger = get_logger()
        enabled_mods = [(mod.name, mod.path) for mod in self.mod_list.enabled_mods]
        logger.info("Launching game with %d enabled mods", len(enabled_mods))
        for name, path in enabled_mods:
            logger.info("Enabled mod: %s | %s", name, path)
        
        if self.launcher_service.should_warn_external_mods(self.config.game_install_dir, enabled_paths):
            result = messagebox.askyesno(
                self.translation_service.get("messages.proton_warning_title", "Proton/Steam Deck Warning"),
                self.translation_service.get("messages.proton_warning_text", "")
            )
            if not result:
                return
        
        try:
            self.launcher_service.launch_game(self.config.game_install_dir, enabled_paths)
        except FileNotFoundError as e:
            messagebox.showerror(
                self.translation_service.get("messages.launch_error"),
                self.translation_service.get("messages.exe_not_found")
            )
        except Exception as e:
            messagebox.showerror(
                self.translation_service.get("messages.launch_error"),
                str(e)
            )
    
    def _copy_launch_options(self):
        missing = self.mod_service.get_missing_mod_names(self.mod_list)
        if missing:
            messagebox.showerror(
                self.translation_service.get("messages.missing_mods_title"),
                self.translation_service.get("messages.missing_mods_text", "").replace("{missing}", "\n".join(missing))
            )
            return
        
        enabled_paths = self.mod_service.get_enabled_mod_paths(self.mod_list)
        
        if not enabled_paths:
            messagebox.showinfo(
                self.translation_service.get("messages.no_mods_title", "No Mods Enabled"),
                self.translation_service.get("messages.no_mods_text", "No mods are enabled. Enable some mods first.")
            )
            return
        
        launch_opts = self.launcher_service.get_launch_options(self.config.game_install_dir, enabled_paths)
        
        self.root.clipboard_clear()
        self.root.clipboard_append(launch_opts)
        self.root.update()
        
        dialog = Toplevel(self.root)
        dialog.title(self.translation_service.get("messages.launch_options_title", "Steam Launch Options"))
        dialog.geometry("700x400")
        dialog.transient(self.root)
        
        Label(
            dialog,
            text=self.translation_service.get("messages.launch_options_instructions", ""),
            wraplength=650,
            justify="left",
            pady=10
        ).pack()
        
        text_widget = Text(dialog, wrap=WORD, height=15, font=("Consolas", 9))
        text_widget.pack(fill=BOTH, expand=True, padx=10, pady=5)
        text_widget.insert("1.0", launch_opts)
        text_widget.config(state="normal")
        
        Button(
            dialog,
            text=self.translation_service.get("messages.copy_to_clipboard", "Copy to Clipboard"),
            command=lambda: [self.root.clipboard_clear(), self.root.clipboard_append(launch_opts), self.root.update()],
            width=30,
            height=2
        ).pack(pady=5)
        
        Button(
            dialog,
            text=self.translation_service.get("messages.close", "Close"),
            command=dialog.destroy,
            width=30,
            height=2
        ).pack(pady=5)
    
    def _unpack(self):
        output_dir = os.path.join(self.config.mod_folder, "_unpacked")
        os.makedirs(output_dir, exist_ok=True)
        
        pw = ProgressWindow(self.root, self.translation_service.get("progress.unpacking"), 100)
        
        try:
            def progress(current, total):
                pw.update(int((current / total) * 100))
            
            self.pack_service.unpack(self.config.game_install_dir, output_dir, progress)
            pw.close()
            messagebox.showinfo("Success", "Unpacking complete!")
        except Exception as e:
            pw.close()
            messagebox.showerror("Error", str(e))
    
    def _repack(self):
        source_dir = os.path.join(self.config.mod_folder, "_unpacked")
        gpak_output = os.path.join(self.config.game_install_dir, "resources.gpak")
        
        pw = ProgressWindow(self.root, self.translation_service.get("progress.repacking"), 100)
        
        try:
            def progress(current, total):
                pw.update(int((current / total) * 100))
            
            self.pack_service.repack(source_dir, gpak_output, progress)
            pw.close()
            messagebox.showinfo("Success", "Repacking complete!")
        except Exception as e:
            pw.close()
            messagebox.showerror("Error", str(e))
    
    def _import_modlist(self):
        filepath = filedialog.askopenfilename(
            parent=self.root,
            title=self.translation_service.get("messages.import_modlist", "Import Modlist"),
            filetypes=[
                ("JSON files", "*.json"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not filepath:
            return
        
        try:
            if filepath.endswith(".json"):
                imported_names = self.modlist_io_service.import_modlist(filepath)
            else:
                imported_names = self.modlist_io_service.import_modlist_text(filepath)
            
            available_mod_names = {mod.name for mod in self.mod_list.all_mods}
            valid_names = [name for name in imported_names if name in available_mod_names]
            
            if len(valid_names) < len(imported_names):
                missing_count = len(imported_names) - len(valid_names)
                messagebox.showwarning(
                    "Warning",
                    f"Imported {len(valid_names)} mods successfully.\n{missing_count} mods were not found in your mods folder."
                )
            
            self.mod_list.set_order(valid_names)
            messagebox.showinfo("Success", f"Imported {len(valid_names)} mods!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import modlist: {str(e)}")
    
    def _export_modlist(self):
        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title=self.translation_service.get("messages.export_modlist", "Export Modlist"),
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not filepath:
            return
        
        try:
            enabled_names = self.mod_list.enabled_mod_names
            
            if filepath.endswith(".json"):
                default_name = os.path.splitext(os.path.basename(filepath))[0]
                modlist_name = simpledialog.askstring(
                    self.translation_service.get("messages.export_modlist", "Export Modlist"),
                    self.translation_service.get("messages.modlist_name_prompt", "Modlist name:"),
                    initialvalue=default_name,
                    parent=self.root
                )
                if modlist_name is None:
                    return

                self.modlist_io_service.export_modlist(enabled_names, filepath, modlist_name)
            else:
                self.modlist_io_service.export_modlist_text(enabled_names, filepath)
            
            messagebox.showinfo("Success", f"Exported {len(enabled_names)} mods!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export modlist: {str(e)}")
    
    def _show_settings(self):
        def on_save(new_config):
            self.config = new_config
            self.config_service.save_config(new_config)
            self.translation_service.load_language(new_config.language)
            self._reload_ui()
        
        SettingsWindow(self.root, self.config, self.translation_service, self.theme_service, on_save)

    def _show_info_dialog(self, title: str, message: str):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("500x220")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        theme_name = self.theme_service.normalize_theme_name(self.config.theme)
        colors = self.theme_service.get_color_scheme(theme_name)
        dialog.configure(bg=colors["bg"])
        self.theme_service.apply_titlebar(dialog, theme_name)

        container = ttk.Frame(dialog)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(container, text=title, font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(container, text=message, wraplength=460, justify="left").pack(anchor="w", pady=(0, 12))

        ttk.Button(container, text=self.translation_service.get("settings.confirm", "OK"), command=dialog.destroy).pack(anchor="e")
    
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
            messagebox.showerror(
                self.translation_service.get("messages.error"),
                f"Failed to change theme: {str(e)}"
            )
    
    def _reload_ui(self):
        try:
            self.root.after_cancel(self._check_reload_id)
        except (AttributeError, ValueError):
            pass
        
        self.root.destroy()
        
        new_root = tk.Tk()
        self.theme_service.bind_root(new_root)
        self.theme_service.set_theme(self.config.theme)
        new_controller = MainController(
            new_root,
            self.config_service,
            self.mod_service,
            self.launcher_service,
            self.translation_service,
            self.pack_service,
            self.modlist_io_service,
            self.theme_service
        )
        new_controller.start()
    
    def _setup_auto_refresh(self):
        from app.infrastructure.mod_repository import ModRepository
        
        repo = ModRepository(self.config.mod_folder)
        self.last_mtime = repo.get_modlist_mtime()
        self.last_mod_folders = set(repo.get_mod_folders())
        
        self._check_reload_id = self.root.after(1000, self._check_reload)
    
    def _check_reload(self):
        from app.infrastructure.mod_repository import ModRepository
        
        repo = ModRepository(self.config.mod_folder)
        
        mtime = repo.get_modlist_mtime()
        if mtime != self.last_mtime:
            self.last_mtime = mtime
            self.mod_list = self.mod_service.load_mods()
            self.mod_list.add_observer(self._on_mod_list_changed)
            self._refresh_lists()
        
        current_mod_folders = set(repo.get_mod_folders())
        if current_mod_folders != self.last_mod_folders:
            self.last_mod_folders = current_mod_folders
            self.mod_list = self.mod_service.load_mods()
            self.mod_list.add_observer(self._on_mod_list_changed)
            self._refresh_lists()
        
        self._check_reload_id = self.root.after(1000, self._check_reload)
