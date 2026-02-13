import tkinter as tk
from tkinter import ttk

class ProgressWindow:
    def __init__(self, root, title, maximum):
        # Create a top-level window
        self.win = tk.Toplevel(root)
        self.win.title(title)
        self.win.geometry("420x140")
        self.win.resizable(False, False)

        # Prevent user from closing mid-operation
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        # Title label
        self.label = tk.Label(self.win, text=title, font=("Arial", 12))
        self.label.pack(pady=10)

        # Progress bar
        self.pb = ttk.Progressbar(
            self.win,
            orient="horizontal",
            length=380,
            mode="determinate",
            maximum=maximum
        )
        self.pb.pack(pady=10)

        # Percentage label
        self.percent_label = tk.Label(self.win, text="0%", font=("Arial", 10))
        self.percent_label.pack()

        # Force initial draw
        self.win.update()

    def update(self, value):
        self.pb["value"] = value

        # Update percentage text
        percent = int((value / self.pb["maximum"]) * 100)
        self.percent_label.config(text=f"{percent}%")

        # Keep UI responsive
        self.win.update()

    def close(self):
        self.win.destroy()
