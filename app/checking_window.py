import tkinter as tk

class CheckingWindow:
    def __init__(self, root, message="Checking..."):
        self.win = tk.Toplevel(root)
        self.win.title("Please Wait")
        self.win.geometry("360x120")
        self.win.resizable(False, False)

        # Prevent closing
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        label = tk.Label(self.win, text=message, font=("Arial", 12))
        label.pack(expand=True, pady=20)

        # Force draw
        self.win.update()

    def close(self):
        self.win.destroy()
