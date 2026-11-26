import tkinter as tk

class HoverTooltip:
    """Small hover tooltip for explanatory ini comments
    """

    _pending_instance = None
    _active_instance = None

    def __init__(self, widget, text: str, colors: dict, delay_ms: int = 450):
        self.widget = widget
        self.text = (text or "").strip()
        self.colors = colors
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip = None

        if self.text:
            widget.bind("<Enter>", self._schedule, add="+")
            widget.bind("<Leave>", self.hide, add="+")
            widget.bind("<ButtonPress>", self.hide, add="+")

    def _cancel_schedule(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        if HoverTooltip._pending_instance is self:
            HoverTooltip._pending_instance = None

    def _destroy_tip(self):
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None
        if HoverTooltip._active_instance is self:
            HoverTooltip._active_instance = None

    def _schedule(self, _event=None):
        self._cancel_schedule()

        pending = HoverTooltip._pending_instance

        if pending is not None and pending is not self:
            pending._cancel_schedule()

        active = HoverTooltip._active_instance

        if active is not None and active is not self:
            active._destroy_tip()

        try:
            self._after_id = self.widget.after(self.delay_ms, self.show)
            HoverTooltip._pending_instance = self
        except tk.TclError:
            self._after_id = None

    def show(self):
        self._after_id = None

        if HoverTooltip._pending_instance is self:
            HoverTooltip._pending_instance = None

        if self._tip is not None or not self.text:
            return

        active = HoverTooltip._active_instance

        if active is not None and active is not self:
            active._destroy_tip()

        try:
            if not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except tk.TclError:
            return

        tip = tk.Toplevel(self.widget)
        tip.withdraw()
        tip.wm_overrideredirect(True)

        try:
            tip.wm_attributes("-topmost", True)
        except tk.TclError:
            pass

        frame = tk.Frame(
            tip,
            background=self.colors.get("menu_bg", "#2b2b2b"),
            highlightbackground=self.colors.get("menu_active_bg", "#3a3a3a"),
            highlightthickness=1,
            padx=10,
            pady=7,
        )
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text=self.text,
            background=self.colors.get("menu_bg", "#2b2b2b"),
            foreground=self.colors.get("menu_fg", "#ffffff"),
            font="TkTooltipFont",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack()

        tip.geometry(f"+{x}+{y}")
        tip.deiconify()
        self._tip = tip
        HoverTooltip._active_instance = self

    def hide(self, _event=None):
        self._cancel_schedule()
        self._destroy_tip()