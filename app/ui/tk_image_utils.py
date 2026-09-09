from io import BytesIO
import tkinter as tk

from PIL import Image

def pillow_to_photoimage(image: Image.Image, master=None) -> tk.PhotoImage:
    """Convert a Pillow image to Tk without Pillow's private ImageTk bridge...
    """
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return tk.PhotoImage(master=master, data=buffer.getvalue(), format="png")