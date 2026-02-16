import os
import sys
import json
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import (
    Frame, Label, Listbox, Scrollbar, Text, Menu,
    BOTH, LEFT, RIGHT, Y, END, SINGLE, VERTICAL, Button, messagebox, Toplevel, WORD
)
from tkinter.ttk import Button as TTKButton
from PIL import Image, ImageTk

from app.settings_window import open_settings_window
from app.modutils import list_mods
from app.launcher import launch_game, get_launch_options
from app.rebuild import manual_unpack, manual_repack
from app.i18n import t, init_translator
from app.configloader import save_config


# -----------------------------------------------------
# Cross-platform file/folder opener
# -----------------------------------------------------

def open_file_or_folder(path):
    """
    Open a file or folder in the system's default file manager.
    Works cross-platform.
    """
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


# -----------------------------------------------------
# Reload UI
# -----------------------------------------------------

def reload_ui(old_root, cfg):
    try:
        old_root.after_cancel(old_root._check_reload_id)
    except (AttributeError, ValueError):
        pass  # Callback may have already fired or doesn't exist
    
    old_root.destroy()
    new_root = tk.Tk()

    def reload_callback(new_cfg, changed=None):
        reload_ui(new_root, new_cfg)

    build_ui(cfg, new_root, reload_callback)
    new_root.mainloop()


# -----------------------------------------------------
# Load mod metadata + preview
# -----------------------------------------------------

def load_mod_info(folder_path):
    desc_path = os.path.join(folder_path, "description.json")

    data = {}
    if os.path.isfile(desc_path):
        try:
            with open(desc_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    preview_img = None
    for name in os.listdir(folder_path):
        ext = name.lower().split(".")[-1]
        if name.lower().startswith("preview") and ext in ("png", "jpg", "jpeg", "webp"):
            preview_img = os.path.join(folder_path, name)
            break

    return data, preview_img


# -----------------------------------------------------
# Save modlist.txt
# -----------------------------------------------------

def save_mod_list(path, mods):
    try:
        with open(path, "w", encoding="utf-8") as f:
            for m in mods:
                f.write(m + "\n")
    except PermissionError:
        messagebox.showerror(
            t("messages.error"),
            t("messages.permission_denied_modlist")
        )
    except Exception as e:
        messagebox.showerror(
            t("messages.error"),
            t("messages.save_error", default="Error saving mod list:\n{error}").replace("{error}", str(e))
        )


# -----------------------------------------------------
# Build UI
# -----------------------------------------------------

def build_ui(cfg, root, reload_ui_callback):
    mod_root = cfg["mod_folder"]
    modlist_path = os.path.join(mod_root, "modlist.txt")

    root.title(t("window.app_title"))
    root.geometry("1280x720")  # Optimized for Steam Deck resolution

    # =======================================================
    # Define Launch Game function (early, for menu use)
    # =======================================================
    def on_launch_game():
        mods = list_mods(mod_root)

        # Find enabled mods that are missing
        missing = [m["name"] for m in mods if m["enabled"] and m["missing"]]

        if missing:
            messagebox.showerror(
                t("messages.missing_mods_title"),
                t("messages.missing_mods_text", default="").replace("{missing}", "\n".join(missing))
            )
            return

        # Build list of enabled mod paths
        enabled_mod_paths = [m["path"] for m in mods if m["enabled"]]

        launch_game(cfg["game_install_dir"], enabled_mod_paths)

    def on_copy_launch_options():
        """Copy Steam launch options to clipboard"""
        mods = list_mods(mod_root)
        
        # Find enabled mods that are missing
        missing = [m["name"] for m in mods if m["enabled"] and m["missing"]]
        
        if missing:
            messagebox.showerror(
                t("messages.missing_mods_title"),
                t("messages.missing_mods_text", default="").replace("{missing}", "\n".join(missing))
            )
            return
        
        # Build list of enabled mod paths
        enabled_mod_paths = [m["path"] for m in mods if m["enabled"]]
        
        if not enabled_mod_paths:
            messagebox.showinfo(
                t("messages.no_mods_title", "No Mods Enabled"),
                t("messages.no_mods_text", "No mods are enabled. Enable some mods first.")
            )
            return
        
        # Generate launch options
        launch_opts = get_launch_options(enabled_mod_paths, cfg["game_install_dir"])
        
        # Copy to clipboard
        root.clipboard_clear()
        root.clipboard_append(launch_opts)
        root.update()
        
        # Show in dialog with instructions
        dialog = Toplevel(root)
        dialog.title(t("messages.launch_options_title", "Steam Launch Options"))
        dialog.geometry("700x400")
        dialog.transient(root)
        
        Label(dialog, text=t("messages.launch_options_instructions", 
                            "Copy these launch options and paste them in Steam:\n"
                            "Right-click game → Properties → Launch Options\n\n"
                            "Note: On Linux/Proton/Steam Deck, keep mods in the game directory for best compatibility."),
              wraplength=650, justify="left", pady=10).pack()
        
        text_widget = Text(dialog, wrap=WORD, height=15, font=("Consolas", 9))
        text_widget.pack(fill=BOTH, expand=True, padx=10, pady=5)
        text_widget.insert("1.0", launch_opts)
        text_widget.config(state="normal")
        
        # Larger buttons for touch/controller
        Button(dialog, text=t("messages.copy_to_clipboard", "Copy to Clipboard"), 
               command=lambda: [root.clipboard_clear(), root.clipboard_append(launch_opts), root.update()],
               width=30, height=2).pack(pady=5)
        Button(dialog, text=t("messages.close", "Close"), command=dialog.destroy, width=30, height=2).pack(pady=5)

    # =======================================================
    # Menu Bar
    # =======================================================

    menubar = Menu(root)

    # FILE MENU
    file_menu = Menu(menubar, tearoff=0)
    file_menu.add_command(
        label=t("menu.file.settings"),
        command=lambda: open_settings_window(
            root,
            "config.json",
            lambda new_cfg, changed: reload_ui_callback(new_cfg)
        ),
        accelerator="F2"
    )

    file_menu.add_separator()

    # TOOLS MENU (manual unpack/repack)
    def menu_unpack():
        game_dir = cfg["game_install_dir"]
        output_dir = os.path.join(mod_root, "_unpacked")
        os.makedirs(output_dir, exist_ok=True)
        manual_unpack(game_dir, output_dir)

    def menu_repack():
        source_dir = os.path.join(mod_root, "_unpacked")
        game_dir = cfg["game_install_dir"]
        gpak_output = os.path.join(game_dir, "resources.gpak")
        manual_repack(source_dir, gpak_output)

    file_menu.add_command(label=t("menu.file.unpack"), command=menu_unpack)
    file_menu.add_command(label=t("menu.file.repack"), command=menu_repack)

    file_menu.add_separator()

    # OPEN FOLDERS
    file_menu.add_command(label=t("menu.file.open_mods"), command=lambda: open_file_or_folder(mod_root))
    file_menu.add_command(label=t("menu.file.open_game"), command=lambda: open_file_or_folder(cfg["game_install_dir"]))

    file_menu.add_separator()

    # LAUNCH GAME
    file_menu.add_command(label=t("menu.file.launch_game"), command=on_launch_game, accelerator="F5")
    file_menu.add_command(label=t("menu.file.copy_launch_options", "Copy Launch Options (for Steam)"), 
                          command=on_copy_launch_options, accelerator="F3")
    
    file_menu.add_separator()
    file_menu.add_command(label=t("menu.file.exit"), command=root.quit, accelerator="Ctrl+Q")

    menubar.add_cascade(label=t("menu.file.label"), menu=file_menu)
    
    # LANGUAGE MENU
    lang_menu = Menu(menubar, tearoff=0)
    
    def get_available_languages():
        # Handle both frozen (PyInstaller) and normal execution
        if getattr(sys, 'frozen', False):
            # Running as compiled executable - locales next to .exe
            lang_dir = Path(sys.executable).parent / "locales"
        else:
            # Running as script - locales in project root
            lang_dir = Path(__file__).parent.parent / "locales"
        
        langs = []
        if lang_dir.exists():
            for file in lang_dir.glob("*.json"):
                langs.append(file.stem)
        
        if not langs:
            return ["English"]
        
        # Sort alphabetically
        langs = sorted(langs)
        
        # Move English to the top if it exists
        if "English" in langs:
            langs.remove("English")
            langs.insert(0, "English")
        
        return langs
    
    def change_language(lang_code):
        # Update config
        cfg["language"] = lang_code
        save_config("config.json", cfg)
        # Reinit translator
        init_translator(lang_code)
        # Reload UI
        reload_ui_callback(cfg)
    
    available_langs = get_available_languages()
    current_lang = cfg.get("language", "English")
    
    for lang in available_langs:
        is_current = "✓ " if lang == current_lang else ""
        lang_menu.add_command(label=f"{is_current}{lang.upper()}", command=lambda l=lang: change_language(l))
    
    menubar.add_cascade(label=t("menu.language"), menu=lang_menu)
    
    # =======================================================
    # Controller Help Function
    # =======================================================
    
    def show_controller_help():
        """Display controller/keyboard shortcuts help dialog"""
        help_win = Toplevel(root)
        help_win.title(t("window.controller_help", "Controller & Keyboard Shortcuts"))
        help_win.geometry("600x500")
        help_win.resizable(False, False)
        help_win.transient(root)
        
        Label(help_win, text=t("window.controller_help", "Controller & Keyboard Shortcuts"), 
              font=("Arial", 14, "bold")).pack(pady=10)
        
        # Create scrollable frame
        canvas = tk.Canvas(help_win)
        scrollbar = Scrollbar(help_win, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Shortcuts list
        shortcuts = [
            ("General", ""),
            ("  F1", "Show this help"),
            ("  F2", "Open Settings"),
            ("  F3", "Copy Steam Launch Options"),
            ("  F5", "Launch Game"),
            ("  Ctrl+Q", "Quit Application"),
            ("", ""),
            ("Mod List Navigation", ""),
            ("  [ ] or PgUp/PgDn", "Switch between disabled/enabled lists"),
            ("  Arrow Keys", "Navigate within a list"),
            ("  Space / Enter", "Enable/Disable selected mod"),
            ("  Double-Click", "Quick enable/disable"),
            ("", ""),
            ("Mod Organization (Enabled List)", ""),
            ("  W", "Move mod up one position"),
            ("  S", "Move mod down one position"),
            ("  Shift+W", "Move mod to top"),
            ("  Shift+S", "Move mod to bottom"),
            ("  Right-Click", "Context menu (Move Top/Bottom/Disable)"),
            ("", ""),
            # ("Controller (Steam Deck)", ""),
            # ("  D-Pad / Left Stick", "Navigate menus and lists"),
            # ("  A Button (South)", "Confirm / Enable-Disable mod"),
            # ("  B Button (East)", "Back / Cancel"),
            # ("  L1/R1 Bumpers", "Move mods up/down in load order"),
            # ("  L2/R2 Triggers", "Switch between lists"),
            # ("  Start Button", "Launch game"),
            # ("  Select Button", "Open settings"),
            # ("", ""),
            # ("Tips", ""),
            # ("  • Touch screen works for all controls", ""),
            # ("  • Use trackpad for precise selection", ""),
            # ("  • Hold Steam button for on-screen keyboard", ""),
        ]
        
        for shortcut, description in shortcuts:
            if not shortcut and not description:
                Frame(scrollable_frame, height=10).pack()
                continue
            if not description:
                Label(scrollable_frame, text=shortcut, font=("Arial", 11, "bold"), 
                      anchor="w").pack(fill="x", padx=20, pady=(10, 2))
            else:
                frame = Frame(scrollable_frame)
                frame.pack(fill="x", padx=20, pady=1)
                Label(frame, text=shortcut, font=("Courier", 10, "bold"), 
                      width=20, anchor="w").pack(side="left")
                Label(frame, text=description, font=("Arial", 10), 
                      anchor="w").pack(side="left", padx=10)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Close button
        Button(help_win, text=t("messages.close", "Close"), command=help_win.destroy, 
               width=25, height=2).pack(pady=10)

    # HELP MENU - added after show_controller_help is defined
    # help_menu = Menu(menubar, tearoff=0)
    # help_menu.add_command(label=t("menu.help.shortcuts", "Hotkeys"), 
    #                       command=show_controller_help, accelerator="F1")
    # help_menu.add_command(label=t("menu.help.readme", "README"), 
    #                       command=lambda: open_file_or_folder("README.md"))
    # menubar.add_cascade(label=t("menu.help.label", "Help"), menu=help_menu)
    
    root.config(menu=menubar)

    # Bind keyboard shortcuts
    root.bind("<F1>", lambda e: show_controller_help())
    root.bind("<F2>", lambda e: open_settings_window(
        root, "config.json",
        lambda new_cfg, changed: reload_ui_callback(new_cfg)
    ))
    root.bind("<F3>", lambda e: on_copy_launch_options())
    root.bind("<F5>", lambda e: on_launch_game())
    root.bind("<Control-q>", lambda e: root.quit())

    # =======================================================
    # Layout Frames
    # =======================================================

    content = Frame(root)
    content.pack(side="top", fill="both", expand=True)

    footer = Frame(root)
    footer.pack(side="bottom", fill="x")

    # Main content split: lists area on left, preview on right
    lists_area = Frame(content)
    lists_area.pack(side=LEFT, fill=BOTH, expand=False)

    preview_frame = Frame(content)
    preview_frame.pack(side=RIGHT, fill=BOTH, expand=True)

    # =======================================================
    # LEFT: Disabled Mods
    # =======================================================

    left_frame = Frame(lists_area)
    left_frame.pack(side=LEFT, fill=BOTH, padx=10)

    Label(left_frame, text=t("ui.disabled_mods"), font=("Arial", 14, "bold")).pack()

    # Larger button for touch/controller
    Button(left_frame, text=t("ui.disable_all"), command=lambda: disable_all(), width=20, height=2).pack(pady=5)

    left_scroll = Scrollbar(left_frame, orient=VERTICAL)
    left_scroll.pack(side=RIGHT, fill=Y)

    # Increased font size for better readability on Steam Deck
    disabled_list = Listbox(left_frame, width=30, height=20,
                            yscrollcommand=left_scroll.set,
                            selectmode=SINGLE, font=("Arial", 11))
    disabled_list.pack(side=LEFT, fill=BOTH, expand=True)
    left_scroll.config(command=disabled_list.yview)

    # =======================================================
    # CENTER: Swap Buttons
    # =======================================================

    center_frame = Frame(lists_area)
    center_frame.pack(side=LEFT, fill=Y, padx=5)

    # Add some padding at top to align with the listboxes
    Label(center_frame, text=" ").pack(pady=10)
    Label(center_frame, text=" ").pack(pady=5)
    Label(center_frame, text=" ").pack(pady=15)

    def swap_selected():
        """Move selected item from one list to other"""
        if disabled_list.curselection():
            index = disabled_list.curselection()[0]
            item = disabled_list.get(index)
            disabled_list.delete(index)
            enabled_list.insert(END, item)
            save_mod_list(modlist_path, list(enabled_list.get(0, END)))
        elif enabled_list.curselection():
            index = enabled_list.curselection()[0]
            item = enabled_list.get(index)
            enabled_list.delete(index)
            disabled_list.insert(END, item)
            save_mod_list(modlist_path, list(enabled_list.get(0, END)))

    # Larger swap button for touch/controller
    swap_btn = Button(center_frame, text="<--->", command=swap_selected, font=("Arial", 14, "bold"), width=6, height=3)
    swap_btn.pack()

    # =======================================================
    # RIGHT: Enabled Mods
    # =======================================================

    right_frame = Frame(lists_area)
    right_frame.pack(side=LEFT, fill=BOTH, padx=10)

    Label(right_frame, text=t("ui.enabled_mods"), font=("Arial", 14, "bold")).pack()

    # Larger button for touch/controller
    Button(right_frame, text=t("ui.enable_all"), command=lambda: enable_all(), width=20, height=2).pack(pady=5)

    right_scroll = Scrollbar(right_frame, orient=VERTICAL)
    right_scroll.pack(side=RIGHT, fill=Y)

    # Increased font size for better readability on Steam Deck
    enabled_list = Listbox(right_frame, width=30, height=20,
                           yscrollcommand=right_scroll.set,
                           selectmode=SINGLE, font=("Arial", 11))
    enabled_list.pack(side=LEFT, fill=BOTH, expand=True)
    right_scroll.config(command=enabled_list.yview)

    # =======================================================
    # PREVIEW PANEL
    # =======================================================

    img_label = Label(preview_frame)
    img_label.pack(pady=10)

    title_label = Label(preview_frame, font=("Arial", 16, "bold"))
    title_label.pack(anchor="w", padx=10)

    author_label = Label(preview_frame, font=("Arial", 12))
    author_label.pack(anchor="w", padx=10)

    version_label = Label(preview_frame, font=("Arial", 12))
    version_label.pack(anchor="w", padx=10)

    desc_scroll = Scrollbar(preview_frame, orient=VERTICAL)
    desc_scroll.pack(side=RIGHT, fill=Y)

    desc_box = Text(preview_frame, wrap="word", height=15,
                    font=("Arial", 11), yscrollcommand=desc_scroll.set)
    desc_box.pack(fill=BOTH, expand=True, padx=10, pady=10)
    desc_scroll.config(command=desc_box.yview)

    # -----------------------------------------------------
    # Refresh lists
    # -----------------------------------------------------

    def refresh_lists(preserve_selection=None):
        """Refresh both lists, optionally preserving selection"""
        # Store current selection if needed
        if preserve_selection is None:
            try:
                if enabled_list.curselection():
                    preserve_selection = ('enabled', enabled_list.get(enabled_list.curselection()[0]))
                elif disabled_list.curselection():
                    preserve_selection = ('disabled', disabled_list.get(disabled_list.curselection()[0]))
            except:
                preserve_selection = None
        
        enabled_list.delete(0, END)
        disabled_list.delete(0, END)

        mods = list_mods(mod_root)

        for mod in mods:
            if mod["enabled"]:
                enabled_list.insert(END, mod["name"])

                if mod["missing"]:
                    enabled_list.itemconfig(END, {"fg": "red"})
            else:
                disabled_list.insert(END, mod["name"])
        
        # Restore selection if requested
        if preserve_selection:
            list_type, item_name = preserve_selection
            target_list = enabled_list if list_type == 'enabled' else disabled_list
            try:
                # Find the item in the list
                for i in range(target_list.size()):
                    if target_list.get(i) == item_name:
                        target_list.selection_set(i)
                        target_list.activate(i)
                        target_list.see(i)
                        break
            except:
                pass



    refresh_lists()

    # -----------------------------------------------------
    # Right-click context menu
    # -----------------------------------------------------

    context_menu = Menu(root, tearoff=0)

    def show_context_menu(event, listbox):
        index = listbox.nearest(event.y)
        if index < 0:
            return

        listbox.selection_clear(0, END)
        listbox.selection_set(index)

        context_menu.delete(0, END)

        item = listbox.get(index)

        if listbox == enabled_list:
            context_menu.add_command(label=t("context_menu.move_top"),
                                     command=lambda: move_to_top(index))
            context_menu.add_command(label=t("context_menu.move_bottom"),
                                     command=lambda: move_to_bottom(index))
            context_menu.add_command(label=t("context_menu.disable"),
                                     command=lambda: disable_item(index))
        else:
            context_menu.add_command(label=t("context_menu.enable"),
                                     command=lambda: enable_item(index))

        context_menu.post(event.x_root, event.y_root)

    # -----------------------------------------------------
    # Context menu actions
    # -----------------------------------------------------

    def move_to_top(index):
        item = enabled_list.get(index)
        enabled_list.delete(index)
        enabled_list.insert(0, item)
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))

    def move_to_bottom(index):
        item = enabled_list.get(index)
        enabled_list.delete(index)
        enabled_list.insert(END, item)
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))

    def disable_item(index):
        item = enabled_list.get(index)
        enabled_list.delete(index)
        disabled_list.insert(END, item)
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))

    def enable_item(index):
        item = disabled_list.get(index)
        disabled_list.delete(index)
        enabled_list.insert(END, item)
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))

    def on_double_click_disabled(event):
        """Double-click on disabled list to enable"""
        index = disabled_list.nearest(event.y)
        if index >= 0:
            enable_item(index)

    def on_double_click_enabled(event):
        """Double-click on enabled list to disable"""
        index = enabled_list.nearest(event.y)
        if index >= 0:
            disable_item(index)

    # Bind double-click
    enabled_list.bind("<Double-Button-1>", on_double_click_enabled)
    disabled_list.bind("<Double-Button-1>", on_double_click_disabled)

    # Bind right-click
    enabled_list.bind("<Button-3>", lambda e: show_context_menu(e, enabled_list))
    disabled_list.bind("<Button-3>", lambda e: show_context_menu(e, disabled_list))

    # Keyboard shortcuts for controller/keyboard navigation
    def move_item_up(event):
        widget = event.widget
        if widget != enabled_list:
            return "break"
        selection = widget.curselection()
        if not selection or selection[0] == 0:
            return "break"
        index = selection[0]
        item = widget.get(index)
        widget.delete(index)
        widget.insert(index - 1, item)
        widget.selection_clear(0, END)
        widget.selection_set(index - 1)
        widget.activate(index - 1)
        widget.see(index - 1)
        widget.focus_set()
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))
        return "break"

    def move_item_down(event):
        widget = event.widget
        if widget != enabled_list:
            return "break"
        selection = widget.curselection()
        if not selection or selection[0] >= widget.size() - 1:
            return "break"
        index = selection[0]
        item = widget.get(index)
        widget.delete(index)
        widget.insert(index + 1, item)
        widget.selection_clear(0, END)
        widget.selection_set(index + 1)
        widget.activate(index + 1)
        widget.see(index + 1)
        widget.focus_set()
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))
        return "break"

    def toggle_item(event):
        widget = event.widget
        selection = widget.curselection()
        if not selection:
            return "break"
        index = selection[0]
        if widget == enabled_list:
            disable_item(index)
        else:
            enable_item(index)
        return "break"

    def switch_list_focus(event, target_list):
        """Switch focus between disabled and enabled lists"""
        target_list.focus_set()
        if target_list.size() > 0:
            target_list.selection_clear(0, END)
            target_list.selection_set(0)
            target_list.see(0)
        return "break"

    # Keyboard shortcuts using W/S keys (WASD-style navigation)
    def move_with_w(event):
        """Move item up with W key"""
        widget = enabled_list
        selection = widget.curselection()
        if not selection:
            # If nothing selected, try to use the active item
            try:
                index = widget.index("active")
                widget.selection_set(index)
                selection = widget.curselection()
            except:
                return "break"
        if not selection or selection[0] == 0:
            return "break"
        
        # Store the old index
        old_index = selection[0]
        new_index = old_index - 1
        
        # Move item up
        item = widget.get(old_index)
        widget.delete(old_index)
        widget.insert(new_index, item)
        
        # Save and preserve selection through any auto-refresh
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))
        
        # Set selection explicitly on the moved item
        widget.selection_clear(0, END)
        widget.selection_set(new_index)
        widget.activate(new_index)
        widget.see(new_index)
        return "break"
    
    def move_with_s(event):
        """Move item down with S key"""
        widget = enabled_list
        selection = widget.curselection()
        if not selection:
            # If nothing selected, try to use the active item
            try:
                index = widget.index("active")
                widget.selection_set(index)
                selection = widget.curselection()
            except:
                return "break"
        if not selection or selection[0] >= widget.size() - 1:
            return "break"
        
        # Store the old index
        old_index = selection[0]
        new_index = old_index + 1
        
        # Move item down
        item = widget.get(old_index)
        widget.delete(old_index)
        widget.insert(new_index, item)
        
        # Save and preserve selection through any auto-refresh
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))
        
        # Set selection explicitly on the moved item
        widget.selection_clear(0, END)
        widget.selection_set(new_index)
        widget.activate(new_index)
        widget.see(new_index)
        return "break"
    
    def move_to_top_shortcut(event):
        """Move item to top with Shift+W"""
        widget = enabled_list
        selection = widget.curselection()
        if not selection:
            # If nothing selected, try to use the active item
            try:
                index = widget.index("active")
                widget.selection_set(index)
            except:
                return "break"
            selection = widget.curselection()
        if not selection:
            return "break"
        index = selection[0]
        move_to_top(index)
        widget.selection_clear(0, END)
        widget.selection_set(0)
        widget.activate(0)
        widget.see(0)
        widget.focus_set()
        return "break"
    
    def move_to_bottom_shortcut(event):
        """Move item to bottom with Shift+S"""
        widget = enabled_list
        selection = widget.curselection()
        if not selection:
            # If nothing selected, try to use the active item
            try:
                index = widget.index("active")
                widget.selection_set(index)
            except:
                return "break"
            selection = widget.curselection()
        if not selection:
            return "break"
        index = selection[0]
        move_to_bottom(index)
        last_index = widget.size() - 1
        widget.selection_clear(0, END)
        widget.selection_set(last_index)
        widget.activate(last_index)
        widget.see(last_index)
        widget.focus_set()
        return "break"
    
    # Fix arrow key navigation to properly select items
    def fix_arrow_selection(event):
        """Ensure arrow keys select items, not just activate them"""
        widget = event.widget
        # Allow default arrow behavior first
        widget.after(1, lambda: _ensure_selection(widget))
        return None
    
    def _ensure_selection(widget):
        """Helper to convert active item to selected item"""
        try:
            active_index = widget.index("active")
            if not widget.curselection() or widget.curselection()[0] != active_index:
                widget.selection_clear(0, END)
                widget.selection_set(active_index)
        except:
            pass
    
    # Bind arrow keys to ensure proper selection
    enabled_list.bind("<Up>", fix_arrow_selection)
    enabled_list.bind("<Down>", fix_arrow_selection)
    disabled_list.bind("<Up>", fix_arrow_selection)
    disabled_list.bind("<Down>", fix_arrow_selection)

    # Bind W/S keys for moving up/down in enabled list
    enabled_list.bind("<w>", move_with_w)
    enabled_list.bind("<s>", move_with_s)
    enabled_list.bind("<W>", move_to_top_shortcut)  # Shift+W
    enabled_list.bind("<S>", move_to_bottom_shortcut)  # Shift+S
    
    enabled_list.bind("<Return>", toggle_item)
    enabled_list.bind("<space>", toggle_item)
    disabled_list.bind("<Return>", toggle_item)
    disabled_list.bind("<space>", toggle_item)
    
    # Use bracket keys [ and ] OR Page Up/Page Down to switch between lists
    # Bracket keys for keyboard users, Page Up/Down maps to L2/R2 triggers on controllers
    enabled_list.bind("<bracketleft>", lambda e: switch_list_focus(e, disabled_list))
    enabled_list.bind("<bracketright>", lambda e: switch_list_focus(e, disabled_list))
    enabled_list.bind("<Prior>", lambda e: switch_list_focus(e, disabled_list))  # Page Up
    enabled_list.bind("<Next>", lambda e: switch_list_focus(e, disabled_list))   # Page Down
    disabled_list.bind("<bracketleft>", lambda e: switch_list_focus(e, enabled_list))
    disabled_list.bind("<bracketright>", lambda e: switch_list_focus(e, enabled_list))
    disabled_list.bind("<Prior>", lambda e: switch_list_focus(e, enabled_list))  # Page Up
    disabled_list.bind("<Next>", lambda e: switch_list_focus(e, enabled_list))   # Page Down


    # -----------------------------------------------------
    # Preview update
    # -----------------------------------------------------

    def update_preview(mod_name):
        mod_path = os.path.join(mod_root, mod_name)
        if not os.path.isdir(mod_path):
            return

        data, preview_path = load_mod_info(mod_path)

        title_label.config(text=f"Title: {data.get('title', mod_name)}")
        author_label.config(text=f"Author: {data.get('author', 'Unknown')}")
        version_label.config(text=f"Version: {data.get('version', 'Unknown')}")

        desc_box.config(state="normal")
        desc_box.delete("1.0", END)
        desc_box.insert("1.0", data.get("description", ""))
        desc_box.config(state="disabled")

        if preview_path:
            img = Image.open(preview_path)
            img.thumbnail((800, 600), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            img_label.config(image=tk_img)
            img_label.image = tk_img
        else:
            img_label.config(image="", text=t("ui.no_preview"))

    enabled_list.bind("<<ListboxSelect>>",
                      lambda e: update_preview(enabled_list.get(enabled_list.curselection()[0]))
                      if enabled_list.curselection() else None)

    disabled_list.bind("<<ListboxSelect>>",
                       lambda e: update_preview(disabled_list.get(disabled_list.curselection()[0]))
                       if disabled_list.curselection() else None)

    # -----------------------------------------------------
    # Enable / Disable All
    # -----------------------------------------------------

    def enable_all():
        mods = [d for d in os.listdir(mod_root)
                if os.path.isdir(os.path.join(mod_root, d))]
        save_mod_list(modlist_path, mods)
        refresh_lists()

    def disable_all():
        save_mod_list(modlist_path, [])
        refresh_lists()

    # -----------------------------------------------------
    # Drag & Drop
    # -----------------------------------------------------

    drag_data = {"source": None, "index": None, "changed": False}

    def start_drag(event, source_list):
        drag_data["source"] = source_list
        drag_data["index"] = source_list.nearest(event.y)
        drag_data["changed"] = False

    def do_drag(event, source_list):
        if drag_data["source"] != source_list:
            return

        new_index = source_list.nearest(event.y)
        old_index = drag_data["index"]

        if new_index != old_index:
            item = source_list.get(old_index)
            source_list.delete(old_index)
            source_list.insert(new_index, item)
            drag_data["index"] = new_index
            drag_data["changed"] = True

    def end_drag(event, source_list, target_list):
        if drag_data["source"] != source_list:
            drag_data["changed"] = False
            return

        item = source_list.get(drag_data["index"])

        # Move between lists
        x, y = event.x_root, event.y_root
        widget = root.winfo_containing(x, y)

        moved = False
        if widget == target_list:
            source_list.delete(drag_data["index"])
            target_list.insert(END, item)
            moved = True

        # Save if item was moved between lists OR reordered within the same list
        if moved or drag_data["changed"]:
            enabled = list(enabled_list.get(0, END))
            save_mod_list(modlist_path, enabled)

        drag_data["source"] = None
        drag_data["index"] = None
        drag_data["changed"] = False

    enabled_list.bind("<Button-1>", lambda e: start_drag(e, enabled_list))
    enabled_list.bind("<B1-Motion>", lambda e: do_drag(e, enabled_list))
    enabled_list.bind("<ButtonRelease-1>", lambda e: end_drag(e, enabled_list, disabled_list))

    disabled_list.bind("<Button-1>", lambda e: start_drag(e, disabled_list))
    disabled_list.bind("<B1-Motion>", lambda e: do_drag(e, disabled_list))
    disabled_list.bind("<ButtonRelease-1>", lambda e: end_drag(e, disabled_list, enabled_list))

    # -----------------------------------------------------
    # Live reload (modlist.txt + folder changes)
    # -----------------------------------------------------

    last_mtime = os.path.getmtime(modlist_path) if os.path.exists(modlist_path) else 0
    last_mod_folders = set([
        d for d in os.listdir(mod_root)
        if os.path.isdir(os.path.join(mod_root, d))
    ])

    def check_reload():
        nonlocal last_mtime, last_mod_folders

        # 1. Check modlist.txt timestamp
        try:
            mtime = os.path.getmtime(modlist_path)
        except FileNotFoundError:
            mtime = 0

        if mtime != last_mtime:
            last_mtime = mtime
            refresh_lists(preserve_selection=True)
            root._check_reload_id = root.after(1000, check_reload)
            return

        # 2. Check for added/removed mod folders
        current_mod_folders = set([
            d for d in os.listdir(mod_root)
            if os.path.isdir(os.path.join(mod_root, d))
        ])

        if current_mod_folders != last_mod_folders:
            last_mod_folders = current_mod_folders
            refresh_lists(preserve_selection=True)
            root._check_reload_id = root.after(1000, check_reload)
            return

        # No changes detected, just reschedule
        root._check_reload_id = root.after(1000, check_reload)

    check_reload()
    

    # -----------------------------------------------------
    # Launch Game
    # -----------------------------------------------------

    def on_launch_game():
        mods = list_mods(mod_root)

        # Find enabled mods that are missing
        missing = [m["name"] for m in mods if m["enabled"] and m["missing"]]

        if missing:
            messagebox.showerror(
                t("messages.missing_mods_title"),
                t("messages.missing_mods_text", default="").replace("{missing}", "\n".join(missing))
            )
            return

        # Build list of enabled mod paths
        enabled_mod_paths = [m["path"] for m in mods if m["enabled"]]

        launch_game(cfg["game_install_dir"], enabled_mod_paths)

    # Add comprehensive keyboard/controller shortcut hints
    # hints_frame = Frame(footer)
    # hints_frame.pack(pady=(10, 5))
    
    # hint_line1 = t("ui.shortcuts_line1", 
    #                default="Quick Keys: F1=Help • F2=Settings • F3=Steam Launch • F5=Launch Game • Ctrl+Q=Quit")
    # hint_line2 = t("ui.shortcuts_line2", 
    #                default="Mod Controls: [ ] PgUp/PgDn=Switch • Space/Enter=Toggle • W/S=Move • Shift+W/S=Top/Bottom")
    
    # Label(hints_frame, text=hint_line1, font=("Arial", 9, "bold"), fg="#2563eb").pack()
    # Label(hints_frame, text=hint_line2, font=("Arial", 9), fg="gray").pack()
    
    # Larger launch button for touch/controller
    TTKButton(footer, text=t("ui.launch_game"), command=on_launch_game, width=30).pack(pady=(5, 20))
