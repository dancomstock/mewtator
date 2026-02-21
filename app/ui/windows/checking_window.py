import tkinter as tk


class CheckingWindow:
    def __init__(self, root, title="Please wait...", message="Checking..."):
        self.win = tk.Toplevel(root)
        self.win.title(title)
        self.win.geometry("420x140")  # Larger for Steam Deck
        self.win.resizable(False, False)

        # Prevent closing
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        label = tk.Label(self.win, text=message, font=("Arial", 13))
        label.pack(expand=True, pady=20)

        # Force draw
        self.win.update()

    def close(self):
        self.win.destroy()
