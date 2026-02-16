import os
import json
from pathlib import Path
from tkinter import (
    Frame, Label, Listbox, Scrollbar, Text, Menu,
    BOTH, LEFT, RIGHT, Y, END, SINGLE, VERTICAL, Button, messagebox
)
from tkinter.ttk import Button as TTKButton
from PIL import Image, ImageTk

from app.settings_window import open_settings_window
from app.modutils import list_mods
from app.launcher import launch_game
from app.rebuild import manual_unpack, manual_repack
from app.i18n import t, init_translator
from app.configloader import save_config


# -----------------------------------------------------
# Reload UI
# -----------------------------------------------------

def reload_ui(old_root, cfg):
    try:
        old_root.after_cancel(old_root._check_reload_id)
    except (AttributeError, ValueError):
        pass  # Callback may have already fired or doesn't exist
    
    old_root.destroy()
    import tkinter as tk
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
    root.geometry("1200x650")

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
        )
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
    file_menu.add_command(label=t("menu.file.open_mods"), command=lambda: os.startfile(mod_root))
    file_menu.add_command(label=t("menu.file.open_game"), command=lambda: os.startfile(cfg["game_install_dir"]))

    file_menu.add_separator()

    # LAUNCH GAME
    file_menu.add_command(label=t("menu.file.launch_game"), command=on_launch_game)
    
    file_menu.add_separator()
    file_menu.add_command(label=t("menu.file.exit"), command=root.quit)

    menubar.add_cascade(label=t("menu.file.label"), menu=file_menu)
    
    # LANGUAGE MENU
    lang_menu = Menu(menubar, tearoff=0)
    
    def get_available_languages():
        lang_dir = Path(__file__).parent / "locales"
        langs = []
        for file in lang_dir.glob("*.json"):
            langs.append(file.stem)
        return sorted(langs)
    
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
    root.config(menu=menubar)

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

    Button(left_frame, text=t("ui.disable_all"), command=lambda: disable_all()).pack(pady=5)

    left_scroll = Scrollbar(left_frame, orient=VERTICAL)
    left_scroll.pack(side=RIGHT, fill=Y)

    disabled_list = Listbox(left_frame, width=30, height=30,
                            yscrollcommand=left_scroll.set,
                            selectmode=SINGLE)
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

    swap_btn = Button(center_frame, text="<--->", command=swap_selected, font=("Arial", 12, "bold"), width=4)
    swap_btn.pack()

    # =======================================================
    # RIGHT: Enabled Mods
    # =======================================================

    right_frame = Frame(lists_area)
    right_frame.pack(side=LEFT, fill=BOTH, padx=10)

    Label(right_frame, text=t("ui.enabled_mods"), font=("Arial", 14, "bold")).pack()

    Button(right_frame, text=t("ui.enable_all"), command=lambda: enable_all()).pack(pady=5)

    right_scroll = Scrollbar(right_frame, orient=VERTICAL)
    right_scroll.pack(side=RIGHT, fill=Y)

    enabled_list = Listbox(right_frame, width=30, height=30,
                           yscrollcommand=right_scroll.set,
                           selectmode=SINGLE)
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

    def refresh_lists():
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
            refresh_lists()
            root._check_reload_id = root.after(1000, check_reload)
            return

        # 2. Check for added/removed mod folders
        current_mod_folders = set([
            d for d in os.listdir(mod_root)
            if os.path.isdir(os.path.join(mod_root, d))
        ])

        if current_mod_folders != last_mod_folders:
            last_mod_folders = current_mod_folders
            refresh_lists()
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


    TTKButton(footer, text=t("ui.launch_game"), command=on_launch_game).pack(pady=20)
