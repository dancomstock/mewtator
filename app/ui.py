import json
import os
from tkinter import (
    Tk, Frame, Label, Listbox, Scrollbar, Text, Menu,
    BOTH, LEFT, RIGHT, Y, END, SINGLE, VERTICAL, Button, ttk, messagebox, BOTTOM
)
from PIL import Image, ImageTk
from app.settings_window import open_settings_window
from app.configloader import load_config, save_config
from app.launcher import launch_game_with_temp_gpak
from app.hashing import hash_list
from pathlib import Path
from app.rebuild import perform_unpack, check_rebuild_requirements, perform_repack, compute_modlist_hash


def reload_ui(old_root, cfg):
    old_root.destroy()

    new_root = Tk()

    # Wrap reload_ui again so the new root is bound
    def reload_and_rebuild(new_cfg):
        reload_ui(new_root, new_cfg)

    build_ui(cfg, new_root, reload_and_rebuild)
    new_root.mainloop()



def load_mod_info(folder_path):
    desc_path = os.path.join(folder_path, "description.json")

    with open(desc_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    preview_img = None
    for name in os.listdir(folder_path):
        ext = name.lower().split(".")[-1]
        if name.lower().startswith("preview") and ext in ("png", "jpg", "jpeg", "webp"):
            preview_img = os.path.join(folder_path, name)
            break

    return data, preview_img


def load_mod_list(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def save_mod_list(path, mods):
    with open(path, "w", encoding="utf-8") as f:
        for m in mods:
            f.write(m + "\n")


def build_ui(cfg, root, reload_ui_callback):
    mod_root = cfg["mod_folder"]
    modlist_path = os.path.join(mod_root, "modlist.txt")
    root.title("Mewtator: Mewgenics Mod Manager")
    root.geometry("1200x650")
    ui_state = {"missing_enabled_mods": False}


    last_mtime = os.path.getmtime(modlist_path) if os.path.exists(modlist_path) else 0
    last_mod_folders = set([
        d for d in os.listdir(mod_root)
        if os.path.isdir(os.path.join(mod_root, d))
    ])



    menubar = Menu(root)

    file_menu = Menu(menubar, tearoff=0)

    # SETTINGS
    file_menu.add_command(
        label="Settings",
        command=lambda: open_settings_window(
            root,
            "config.json",
            lambda new_cfg, changed: reload_ui_callback(new_cfg, changed)
        )
    )

    file_menu.add_separator()

    # UNPACK BASE RESOURCES
    def menu_unpack():
        
        needs_unpack, _, new_hash, _ = check_rebuild_requirements(cfg, root)

        if not needs_unpack:
            if not messagebox.askyesno(
                "Unpack Anyway?",
                "Base resources are already unpacked.\nDo you want to unpack again?"
            ):
                return

        perform_unpack(cfg, root, new_hash)
        reload_ui_callback(cfg, {"game_changed": False, "mods_changed": False})

    file_menu.add_command(label="Unpack Base Resources", command=menu_unpack)

    # REPACK ENABLED MODS
    def menu_repack():
        modlist_path = os.path.join(cfg["mod_folder"], "modlist.txt")
        modlist = load_mod_list(modlist_path)
        new_hash = hash_list(modlist)

        perform_repack(cfg, root, new_hash)
        messagebox.showinfo("Repack Complete", "Modded resources have been rebuilt.")
        reload_ui_callback(cfg, {"game_changed": False, "mods_changed": False})

    file_menu.add_command(label="Repack Enabled Mods", command=menu_repack)

    def menu_restore_original():
        game_dir = Path(cfg["game_install_dir"])

        if not game_dir.exists():
            messagebox.showerror(
                "Invalid Game Directory",
                f"The configured game directory does not exist:\n{game_dir}"
            )
            return

        if messagebox.askyesno(
            "Restore Original Files",
            "This will restore the original resources.gpak file.\n"
            "Use this if the game fails to launch or files were left in a bad state.\n\n"
            "Continue?"
        ):
            game_dir = Path(cfg.get("game_install_dir", ""))
            original = game_dir / "resources.gpak"
            backup = game_dir / "resources_original.gpak"
            backup.rename(original)
            messagebox.showinfo(
                "Restore Complete",
                "Original game files have been restored."
            )

    file_menu.add_command(label="Restore Original Files", command=menu_restore_original)


    file_menu.add_separator()

    # OPEN FOLDERS
    def open_mods_folder():
        os.startfile(cfg["mod_folder"])

    def open_game_folder():
        os.startfile(cfg["game_install_dir"])

    file_menu.add_command(label="Open Mods Folder", command=open_mods_folder)
    file_menu.add_command(label="Open Game Folder", command=open_game_folder)

    file_menu.add_separator()

    # EXIT
    file_menu.add_command(label="Exit", command=root.quit)

    menubar.add_cascade(label="File", menu=file_menu)
    root.config(menu=menubar)

    content = Frame(root)
    content.pack(side="top", fill="both", expand=True)

    footer = Frame(root)
    footer.pack(side="bottom", fill="x")


    # -----------------------------
    # LEFT: DISABLED LIST
    # -----------------------------
    left_frame = Frame(content)
    left_frame.pack(side=LEFT, fill=Y, padx=10)

    Label(left_frame, text="Disabled Mods", font=("Arial", 14, "bold")).pack()

    Button(left_frame, text="Disable All", command=lambda: disable_all()).pack(pady=5)

    left_scroll = Scrollbar(left_frame, orient=VERTICAL)
    left_scroll.pack(side=RIGHT, fill=Y)

    disabled_list = Listbox(left_frame, width=30, height=30,
                            yscrollcommand=left_scroll.set,
                            selectmode=SINGLE)
    disabled_list.pack(side=LEFT, fill=Y)
    left_scroll.config(command=disabled_list.yview)


    # -----------------------------
    # RIGHT: ENABLED LIST
    # -----------------------------
    right_frame = Frame(content)
    right_frame.pack(side=LEFT, fill=Y, padx=10)

    Label(right_frame, text="Enabled Mods", font=("Arial", 14, "bold")).pack()

    Button(right_frame, text="Enable All", command=lambda: enable_all()).pack(pady=5)

    right_scroll = Scrollbar(right_frame, orient=VERTICAL)
    right_scroll.pack(side=RIGHT, fill=Y)

    enabled_list = Listbox(right_frame, width=30, height=30,
                        yscrollcommand=right_scroll.set,
                        selectmode=SINGLE)
    enabled_list.pack(side=LEFT, fill=Y)
    right_scroll.config(command=enabled_list.yview)

    

    # -----------------------------
    # PREVIEW PANEL
    # -----------------------------
    preview_frame = Frame(content)
    preview_frame.pack(side=RIGHT, fill=BOTH, expand=True)

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

    # -----------------------------
    # Refresh lists
    # -----------------------------
    def refresh_lists():
        enabled_list.delete(0, END)
        disabled_list.delete(0, END)

        enabled = load_mod_list(modlist_path)

        # Ensure Mewgenics is always enabled
        if "Mewgenics" not in enabled:
            enabled.insert(0, "Mewgenics")
            save_mod_list(modlist_path, enabled)

        all_mods = sorted([d for d in os.listdir(mod_root)
                           if os.path.isdir(os.path.join(mod_root, d))])

        disabled = [m for m in all_mods if m not in enabled]

        missing_enabled_mods = False
        

        for m in enabled:
            enabled_list.insert(END, m)
            mod_path = os.path.join(mod_root, m)
            if not os.path.isdir(mod_path):
                enabled_list.itemconfig(END, {'fg': 'red'})
                missing_enabled_mods = True

        ui_state["missing_enabled_mods"] = missing_enabled_mods



        for m in disabled:
            disabled_list.insert(END, m)


        mewgenics_path = os.path.join(mod_root, "Mewgenics")
        if not os.path.isdir(mewgenics_path):
            messagebox.showerror(
                "Missing Base Resources",
                "The Mewgenics base resources folder is missing.\n"
                "Please re-run the unpack process in Settings."
            )
            ui_state["missing_mewgenics"] = True
        else:
            ui_state["missing_mewgenics"] = False


    refresh_lists()

    # -----------------------------
    # Preview update
    # -----------------------------
    def update_preview(mod_name):
        mod_path = os.path.join(mod_root, mod_name)
        if not os.path.isdir(mod_path):
            return

        data, preview_path = load_mod_info(mod_path)

        title_label.config(text=f"Title: {data.get('title', 'Untitled')}")
        author_label.config(text=f"Author: {data.get('author', 'Unknown')}")
        version_label.config(text=f"Version: {data.get('version', 'Unknown')}")

        desc_box.config(state="normal")
        desc_box.delete("1.0", END)
        desc_box.insert("1.0", data.get("description", ""))
        desc_box.config(state="disabled")

        if preview_path:
            img = Image.open(preview_path)

            max_w, max_h = 800, 600
            img.thumbnail((max_w, max_h), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            img_label.config(image=tk_img)
            img_label.image = tk_img
        else:
            img_label.config(image="", text="No Preview Image")

    enabled_list.bind("<<ListboxSelect>>", lambda e: update_preview(enabled_list.get(enabled_list.curselection()[0])) if enabled_list.curselection() else None)
    disabled_list.bind("<<ListboxSelect>>", lambda e: update_preview(disabled_list.get(disabled_list.curselection()[0])) if disabled_list.curselection() else None)

    # -----------------------------
    # Enable All / Disable All
    # -----------------------------
    def enable_all():
        all_mods = sorted([d for d in os.listdir(mod_root)
                           if os.path.isdir(os.path.join(mod_root, d))])
        save_mod_list(modlist_path, all_mods)
        refresh_lists()

    def disable_all():
        save_mod_list(modlist_path, [])
        refresh_lists()

    # -----------------------------
    # Drag & Drop Logic
    # -----------------------------
    drag_data = {"source": None, "index": None}

    def start_drag(event, source_list):
        drag_data["source"] = source_list
        drag_data["index"] = source_list.nearest(event.y)

    def do_drag(event, source_list, target_list):
        if drag_data["source"] != source_list:
            return

        new_index = source_list.nearest(event.y)
        old_index = drag_data["index"]

        if new_index != old_index:
            item = source_list.get(old_index)
            source_list.delete(old_index)
            source_list.insert(new_index, item)
            drag_data["index"] = new_index

    def end_drag(event, source_list, target_list):
        if drag_data["source"] != source_list:
            return
        
        item = source_list.get(drag_data["index"])
        if item == "Mewgenics" and target_list == disabled_list:
            messagebox.showwarning("Cannot Disable", "The Mewgenics base resources cannot be disabled.")
            return

        x, y = event.x_root, event.y_root
        widget = root.winfo_containing(x, y)

        # Move between lists
        if widget == target_list:
            item = source_list.get(drag_data["index"])
            source_list.delete(drag_data["index"])
            target_list.insert(END, item)

        # Save enabled list
        enabled = list(enabled_list.get(0, END))
        save_mod_list(modlist_path, enabled)

        drag_data["source"] = None
        drag_data["index"] = None

    enabled_list.bind("<Button-1>", lambda e: start_drag(e, enabled_list))
    enabled_list.bind("<B1-Motion>", lambda e: do_drag(e, enabled_list, disabled_list))
    enabled_list.bind("<ButtonRelease-1>", lambda e: end_drag(e, enabled_list, disabled_list))

    disabled_list.bind("<Button-1>", lambda e: start_drag(e, disabled_list))
    disabled_list.bind("<B1-Motion>", lambda e: do_drag(e, disabled_list, enabled_list))
    disabled_list.bind("<ButtonRelease-1>", lambda e: end_drag(e, disabled_list, enabled_list))

    # -----------------------------
    # Right-click context menu
    # -----------------------------
    menu = Menu(root, tearoff=0)

    def show_context_menu(event, listbox):
        index = listbox.nearest(event.y)
        if index < 0:
            return

        listbox.selection_clear(0, END)
        listbox.selection_set(index)

        menu.delete(0, END)

        item = listbox.get(index)

        if listbox == enabled_list:
            menu.add_command(label="Move to Top", command=lambda: move_to_top(index))
            menu.add_command(label="Move to Bottom", command=lambda: move_to_bottom(index))
            menu.add_command(label="Disable", command=lambda: disable_item(index))
        else:
            menu.add_command(label="Enable", command=lambda: enable_item(index))

        menu.post(event.x_root, event.y_root)

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
        if item == "Mewgenics":
            messagebox.showwarning("Cannot Disable", "The Mewgenics base resources cannot be disabled.")
            return
        enabled_list.delete(index)
        disabled_list.insert(END, item)
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))

    def enable_item(index):
        item = disabled_list.get(index)
        disabled_list.delete(index)
        enabled_list.insert(END, item)
        save_mod_list(modlist_path, list(enabled_list.get(0, END)))

    enabled_list.bind("<Button-3>", lambda e: show_context_menu(e, enabled_list))
    disabled_list.bind("<Button-3>", lambda e: show_context_menu(e, disabled_list))

    # -----------------------------
    # Double Click to Move
    # -----------------------------
    def on_double_click_enabled(event):
        index = enabled_list.nearest(event.y)
        if index >= 0:
            disable_item(index)

    def on_double_click_disabled(event):
        index = disabled_list.nearest(event.y)
        if index >= 0:
            if enabled_list.get(index) == "Mewgenics":
                return
            enable_item(index)

    enabled_list.bind("<Double-Button-1>", lambda e: on_double_click_enabled(e))
    disabled_list.bind("<Double-Button-1>", lambda e: on_double_click_disabled(e))

    # -----------------------------
    # Live reload
    # -----------------------------
    def check_reload():
        nonlocal last_mtime, last_mod_folders

        # 1. Check modlist.txt changes
        try:
            mtime = os.path.getmtime(modlist_path)
        except FileNotFoundError:
            mtime = 0

        if mtime != last_mtime:
            last_mtime = mtime
            refresh_lists()

        # 2. Check mod folder changes
        current_mod_folders = set([
            d for d in os.listdir(mod_root)
            if os.path.isdir(os.path.join(mod_root, d))
        ])

        if current_mod_folders != last_mod_folders:
            last_mod_folders = current_mod_folders
            refresh_lists()

        root.after(1000, check_reload)


    check_reload()


    def on_launch_game():
        if ui_state["missing_enabled_mods"]:
            messagebox.showerror(
                "Missing Mods",
                "One or more enabled mods are missing from the mods folder.\n"
                "Please remove them from the enabled list or restore the folders."
            )
            return
        
        if ui_state.get("missing_mewgenics", False):
            messagebox.showerror(
                "Missing Base Resources",
                "The Mewgenics base resources are missing.\n"
                "Please re-run the unpack process in Settings."
            )
            return


        # Load modlist from mod_folder (no more modlist_path)
        # modlist_path = os.path.join(cfg["mod_folder"], "modlist.txt") 
        # modlist = load_mod_list(modlist_path)
        # current_modlist_hash = compute_modlist_hash(cfg, root)
        current_modlist_hash = ""

        temp_dir = Path(os.getcwd()) / "_temp"
        modded_gpak = temp_dir / "resources_modded.gpak"
        modded_exists = modded_gpak.exists() and modded_gpak.stat().st_size > 0

        needs_repack = (cfg.get("modlist_hash") != current_modlist_hash) or not modded_exists



        if needs_repack:
            if messagebox.askyesno(
                "Repack Needed",
                "Enabled mods have changed.\nRepack resources before launching?"
            ):perform_repack(cfg, root, current_modlist_hash)

        # Launch using the modded gpak
        launch_game_with_temp_gpak( cfg["game_install_dir"], str(modded_gpak), cfg)




    launch_btn = ttk.Button(footer, text="Launch Game", command=lambda: on_launch_game())
    # launch_btn = ttk.Button( root, text="▶ Launch Mewgenics", style="Launch.TButton", command=lambda: on_launch_game() )
    # launch_btn.pack(side="bottom", pady=30, ipadx=20, ipady=10)
    # launch_btn.pack(side="bottom", pady=20)

    # launch_btn = ttk.Button(
    #     footer,
    #     text="▶  Launch Game",
    #     style="Launch.TButton",
    #     command=lambda: on_launch_game()
    # )
    # launch_btn.pack(pady=15, ipadx=20, ipady=10)


    # launch_btn = ttk.Button(footer, text="Launch Game", command=on_launch_game)
    launch_btn.pack(pady=20)


        



# if __name__ == "__main__":
#     build_ui("F:\src\modmewlar\gamedonotupload\mods", "F:\src\modmewlar\gamedonotupload\mods\modlist.txt")
    

# Example usage:
# build_ui("C:/path/to/mods", "C:/path/to/modlist.txt")
