import tkinter as tk
from tkinter import Text, BOTH, RIGHT, Y, END, WORD
from tkinter import ttk
from PIL import Image, ImageTk
from typing import Optional


class PreviewPanel(ttk.Frame):
    def __init__(self, parent, translation_service):
        super().__init__(parent)
        self.translation_service = translation_service
        
        self.img_label = ttk.Label(self)
        self.img_label.pack(pady=10)
        
        self.title_label = ttk.Label(self, font=("Arial", 16, "bold"))
        self.title_label.pack(anchor="w", padx=10)
        
        self.author_label = ttk.Label(self, font=("Arial", 12))
        self.author_label.pack(anchor="w", padx=10)
        
        self.version_label = ttk.Label(self, font=("Arial", 12))
        self.version_label.pack(anchor="w", padx=10)
        
        self.desc_scroll = ttk.Scrollbar(self, orient="vertical")
        self.desc_scroll.pack(side=RIGHT, fill=Y)
        
        self.desc_box = Text(
            self,
            wrap=WORD,
            height=15,
            font=("Arial", 11),
            yscrollcommand=self.desc_scroll.set
        )
        self.desc_box.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.desc_scroll.config(command=self.desc_box.yview)
    
    def update_preview(self, title: str, author: str, version: str, description: str, preview_path: Optional[str]):
        self.title_label.config(text=f"Title: {title}")
        self.author_label.config(text=f"Author: {author}")
        self.version_label.config(text=f"Version: {version}")
        
        self.desc_box.config(state="normal")
        self.desc_box.delete("1.0", END)
        self.desc_box.insert("1.0", description)
        self.desc_box.config(state="disabled")
        
        if preview_path:
            try:
                img = Image.open(preview_path)
                img.thumbnail((800, 600), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.img_label.config(image=tk_img, text="")
                self.img_label.image = tk_img
            except Exception:
                self.img_label.config(image="", text=self.translation_service.get("ui.no_preview"))
        else:
            self.img_label.config(image="", text=self.translation_service.get("ui.no_preview"))
    
    def clear(self):
        self.title_label.config(text="")
        self.author_label.config(text="")
        self.version_label.config(text="")
        self.desc_box.config(state="normal")
        self.desc_box.delete("1.0", END)
        self.desc_box.config(state="disabled")
        self.img_label.config(image="", text="")

    def apply_theme(self, theme_service, theme_name: str):
        colors = theme_service.get_color_scheme(theme_name)
        self.desc_box.config(
            bg=colors["text_bg"],
            fg=colors["text_fg"],
            insertbackground=colors["text_fg"]
        )
