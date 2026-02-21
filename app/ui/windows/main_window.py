import tkinter as tk
from tkinter import LEFT, RIGHT, BOTH, Y
from tkinter import ttk
from app.ui.components.mod_list_widget import ModListWidget
from app.ui.components.preview_panel import PreviewPanel
from app.ui.components.menu_bar import MenuBarComponent


class MainWindow:
    def __init__(self, root, translation_service):
        self.root = root
        self.translation_service = translation_service
        
        self.root.title(translation_service.get("window.app_title"))
        self.root.geometry("1280x720")
        self.root.minsize(900, 500)
        
        self.menu_bar = MenuBarComponent(root, translation_service)

        self.footer = ttk.Frame(root)
        self.footer.pack(side="bottom", fill="x", pady=5)
        
        self.content = ttk.Frame(root)
        self.content.pack(side="top", fill=BOTH, expand=True)
        
        self.lists_area = ttk.Frame(self.content)
        self.lists_area.pack(side=LEFT, fill=BOTH, expand=False)
        
        self.preview_frame = ttk.Frame(self.content)
        self.preview_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        self.disabled_list_widget = ModListWidget(
            self.lists_area,
            translation_service.get("ui.disabled_mods"),
            translation_service.get("ui.disable_all"),
            lambda: None
        )
        self.disabled_list_widget.pack(side=LEFT, fill=BOTH, padx=10)
        
        self.center_frame = ttk.Frame(self.lists_area)
        self.center_frame.pack(side=LEFT, fill=Y, padx=5)
        
        ttk.Label(self.center_frame, text=" ").pack(pady=10)
        ttk.Label(self.center_frame, text=" ").pack(pady=5)
        ttk.Label(self.center_frame, text=" ").pack(pady=15)
        
        self.swap_button = ttk.Button(
            self.center_frame,
            text="<--->",
            width=6
        )
        self.swap_button.pack()
        
        self.enabled_list_widget = ModListWidget(
            self.lists_area,
            translation_service.get("ui.enabled_mods"),
            translation_service.get("ui.enable_all"),
            lambda: None
        )
        self.enabled_list_widget.pack(side=LEFT, fill=BOTH, padx=10)
        
        self.preview_panel = PreviewPanel(self.preview_frame, translation_service)
        self.preview_panel.pack(fill=BOTH, expand=True)
        
        self.launch_button = ttk.Button(
            self.footer,
            text=translation_service.get("ui.launch_game"),
            width=40
        )
        self.launch_button.pack(pady=10, padx=10)
        
        

    def apply_theme(self, theme_service, theme_name: str):
        self.menu_bar.apply_theme(theme_service, theme_name)
        self.disabled_list_widget.apply_theme(theme_service, theme_name)
        self.enabled_list_widget.apply_theme(theme_service, theme_name)
        self.preview_panel.apply_theme(theme_service, theme_name)
    def set_disabled_list_action(self, command):
        self.disabled_list_widget.action_button.config(command=command)
    
    def set_enabled_list_action(self, command):
        self.enabled_list_widget.action_button.config(command=command)
    
    def set_swap_action(self, command):
        self.swap_button.config(command=command)
    
    def set_launch_action(self, command):
        self.launch_button.config(command=command)
    
    def bind_keyboard_shortcuts(self, shortcuts: dict):
        for key, command in shortcuts.items():
            self.root.bind(key, command)
