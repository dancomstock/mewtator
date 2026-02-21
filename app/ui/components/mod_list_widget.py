import tkinter as tk
from tkinter import Listbox, BOTH, LEFT, RIGHT, Y, END, SINGLE
from tkinter import ttk
from typing import Callable, Optional, List


class ModListWidget(ttk.Frame):
    def __init__(self, parent, title: str, button_text: str, button_command: Callable):
        super().__init__(parent)
        
        self.title_label = ttk.Label(self, text=title, font=("Arial", 14, "bold"))
        self.title_label.pack()
        
        self.action_button = ttk.Button(
            self, 
            text=button_text, 
            command=button_command, 
            width=20
        )
        self.action_button.pack(pady=5)
        
        self.scrollbar = ttk.Scrollbar(self, orient="vertical")
        self.scrollbar.pack(side=RIGHT, fill=Y)
        
        self.listbox = Listbox(
            self,
            width=30,
            height=20,
            yscrollcommand=self.scrollbar.set,
            selectmode=SINGLE,
            font=("Arial", 11)
        )
        self.listbox.pack(side=LEFT, fill=BOTH, expand=True)
        self.scrollbar.config(command=self.listbox.yview)

    def apply_theme(self, theme_service, theme_name: str):
        colors = theme_service.get_color_scheme(theme_name)
        self.listbox.config(
            bg=colors["bg"],
            fg=colors["fg"],
            selectbackground=colors["select_bg"],
            selectforeground=colors["select_fg"]
        )
    
    def clear(self):
        self.listbox.delete(0, END)
    
    def add_item(self, text: str, color: Optional[str] = None):
        self.listbox.insert(END, text)
        if color:
            self.listbox.itemconfig(END, {"fg": color})
    
    def get_items(self) -> List[str]:
        return list(self.listbox.get(0, END))
    
    def get_selection(self) -> Optional[tuple]:
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            return index, self.listbox.get(index)
        return None
    
    def select_item(self, index: int):
        self.listbox.selection_clear(0, END)
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)
    
    def bind_event(self, event: str, handler: Callable):
        self.listbox.bind(event, handler)
    
    def focus(self):
        self.listbox.focus_set()
        if self.listbox.size() > 0:
            self.listbox.selection_clear(0, END)
            self.listbox.selection_set(0)
            self.listbox.see(0)
