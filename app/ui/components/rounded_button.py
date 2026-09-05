import tkinter as tk
import tkinter.font as tkfont


class RoundedButton(tk.Canvas):
    """Nice rounded buttons with optional icons!"""

    def __init__(
        self,
        parent,
        text: str,
        font,
        width: int = 0,
        height: int = 0,
        radius: int = 8,
        command=None,
        image=None,
        trailing_image=None,
        icon_gap: int = 8,
        content_offset_x: float = 0,
        content_offset_y: float = 0,
    ):
        super().__init__(
            parent,
            width=max(1, width),
            height=max(1, height),
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            takefocus=True,
            cursor="hand2",
        )

        self._text = text
        self._font = font
        # Explicit minimums sizes, localized text, fonts, and icons are always allowed to grow the physical button beyond them... - Tim
        self._min_width = max(0, int(width))
        self._min_height = max(0, int(height))
        self._button_width = max(1, self._min_width)
        self._button_height = max(1, self._min_height)
        self._horizontal_padding = 18
        self._vertical_padding = 9
        self._radius = radius
        self._command = command
        self._image = image
        self._trailing_image = trailing_image
        self._icon_gap = icon_gap
        self._content_offset_x = content_offset_x
        self._content_offset_y = content_offset_y
        self._state = "normal"
        self._hovered = False
        self._pressed = False
        self._focused = False

        self._surface_color = "#2b2b2b"
        self._normal_color = "#5a5a5a"
        self._hover_color = "#6a6a6a"
        self._pressed_color = "#4a4a4a"
        self._foreground = "#ffffff"
        self._disabled_foreground = "#858585"
        self._focus_color = "#2e62b8"

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<KeyPress-space>", self._on_key_press)
        self.bind("<KeyRelease-space>", self._on_key_release)
        self.bind("<Return>", self._on_return)
        self._recalculate_size()
        self._draw()

    def apply_theme(self, colors: dict):
        self._surface_color = colors["menu_bg"]
        self._normal_color = colors["nav_bg"]
        self._hover_color = colors["nav_active_bg"]
        self._pressed_color = colors["nav_pressed_bg"]
        self._foreground = colors["nav_fg"]
        self._disabled_foreground = colors["disabled_fg"]
        self._focus_color = colors["select_bg"]
        super().configure(background=self._surface_color)
        self._draw()

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, str):
            return super().configure(cnf)
        if cnf:
            kwargs = {**cnf, **kwargs}
        if not kwargs:
            return super().configure()

        redraw = False

        for option, attribute in (
            ("text", "_text"),
            ("font", "_font"),
            ("image", "_image"),
            ("trailing_image", "_trailing_image"),
            ("command", "_command"),
            ("state", "_state"),
            ("icon_gap", "_icon_gap"),
            ("content_offset_x", "_content_offset_x"),
            ("content_offset_y", "_content_offset_y"),
        ):
            if option in kwargs:
                setattr(self, attribute, kwargs.pop(option))
                redraw = True

        kwargs.pop("compound", None)

        if "width" in kwargs:
            self._min_width = max(0, int(kwargs.pop("width")))
            redraw = True
        if "height" in kwargs:
            self._min_height = max(0, int(kwargs.pop("height")))
            redraw = True

        result = super().configure(**kwargs) if kwargs else None

        if redraw:
            self._recalculate_size()
            super().configure(
                cursor="arrow" if self._state == "disabled" else "hand2"
            )
            self._draw()

        return result

    config = configure

    def _font_object(self):
        try:
            return tkfont.nametofont(self._font, root=self)
        except tk.TclError:
            return tkfont.Font(root=self, font=self._font)

    def _content_size(self):
        font = self._font_object()
        lines = str(self._text or "").splitlines() or [""]
        text_width = max((font.measure(line) for line in lines), default=0)
        text_height = font.metrics("linespace") * max(1, len(lines)) if self._text else 0

        leading_width = self._image.width() if self._image is not None else 0
        leading_height = self._image.height() if self._image is not None else 0
        trailing_width = self._trailing_image.width() if self._trailing_image is not None else 0
        trailing_height = self._trailing_image.height() if self._trailing_image is not None else 0

        content_width = text_width
        if leading_width:
            content_width += leading_width + (self._icon_gap if self._text else 0)
        if trailing_width:
            content_width += trailing_width + (self._icon_gap if self._text else 0)
        if not self._text and leading_width and trailing_width:
            content_width += self._icon_gap

        content_height = max(text_height, leading_height, trailing_height)
        return content_width, content_height

    def _recalculate_size(self):
        """Grow to fit the rendered label/icons while preserving configured minimums..."""
        content_width, content_height = self._content_size()
        width = max(self._min_width, content_width + (self._horizontal_padding * 2), 1)
        height = max(self._min_height, content_height + (self._vertical_padding * 2), 1)

        self._button_width = int(round(width))
        self._button_height = int(round(height))
        super().configure(width=self._button_width, height=self._button_height)

    def _rounded_points(self):
        width = self._button_width - 1
        height = self._button_height - 1
        radius = min(self._radius, width // 2, height // 2)

        return (
            radius, 0,
            width - radius, 0,
            width, 0,
            width, radius,
            width, height - radius,
            width, height,
            width - radius, height,
            radius, height,
            0, height,
            0, height - radius,
            0, radius,
            0, 0,
        )

    def _draw(self):
        self.delete("button")

        if self._state == "disabled":
            fill = self._normal_color
            foreground = self._disabled_foreground
        else:
            foreground = self._foreground
            if self._pressed:
                fill = self._pressed_color
            elif self._hovered:
                fill = self._hover_color
            else:
                fill = self._normal_color

        # Keep keyboard focus behavior without drawing a persistent focus ring... - Tim
        self.create_polygon(
            *self._rounded_points(),
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=fill,
            width=0,
            tags=("button", "background"),
        )

        leading_width = self._image.width() if self._image is not None else 0

        trailing_width = (
            self._trailing_image.width() if self._trailing_image is not None else 0
        )

        font = self._font_object()
        text_width = max(
            (font.measure(line) for line in str(self._text or "").splitlines() or [""]),
            default=0,
        )

        group_width = text_width

        if leading_width:
            group_width += leading_width + (self._icon_gap if self._text else 0)
            
        if trailing_width:
            group_width += trailing_width + (self._icon_gap if self._text else 0)

        x = (self._button_width - group_width) / 2 + self._content_offset_x
        center_y = self._button_height / 2 + self._content_offset_y

        if self._image is not None:
            self.create_image(
                x,
                center_y,
                image=self._image,
                anchor="w",
                tags=("button", "content"),
            )

            x += leading_width + (self._icon_gap if self._text else 0)

        self.create_text(
            x,
            center_y,
            text=self._text,
            font=self._font,
            fill=foreground,
            anchor="w",
            tags=("button", "content"),
        )

        x += text_width

        if self._trailing_image is not None:
            x += self._icon_gap if self._text else 0
            self.create_image(
                x,
                center_y,
                image=self._trailing_image,
                anchor="w",
                tags=("button", "content"),
            )

    def _on_enter(self, _event):
        self._hovered = True
        self._draw()

    def _on_leave(self, _event):
        self._hovered = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event):
        if self._state == "disabled":
            return "break"
        self.focus_set()
        self._pressed = True
        self._draw()
        return "break"

    def _on_release(self, event):
        if self._state == "disabled":
            return "break"
        
        invoke = (
            self._pressed
            and 0 <= event.x <= self._button_width
            and 0 <= event.y <= self._button_height
        )

        self._pressed = False
        self._draw()
        
        if invoke and self._command is not None:
            self._command()
        return "break"

    def _on_focus_in(self, _event):
        self._focused = True
        self._draw()

    def _on_focus_out(self, _event):
        self._focused = False
        self._pressed = False
        self._draw()

    def _on_key_press(self, _event):
        if self._state != "disabled":
            self._pressed = True
            self._draw()
        return "break"

    def _on_key_release(self, _event):
        if self._state != "disabled":
            self._pressed = False
            self._draw()
            if self._command is not None:
                self._command()
        return "break"

    def _on_return(self, _event):
        if self._state != "disabled" and self._command is not None:
            self._command()
        return "break"
