import tkinter as tk
from tkinter import ttk
from app.ui.components.compat_label import Label
from PIL import Image, ImageChops, ImageDraw
from typing import Optional
import webbrowser

from app.ui.components.wide_scrollbar import WideScrollbar
from app.ui.icon_set import IconSet
from app.ui.tk_image_utils import pillow_to_photoimage


class PreviewPanel(ttk.Frame):
    PREVIEW_MAX_HEIGHT = 330
    PREVIEW_SIDE_PADDING = 16
    EMPTY_PREVIEW_HEIGHT = 150
    LIVE_PREVIEW_MAX_SIZE = (1600, 600)
    PREVIEW_CORNER_RADIUS = 8

    def __init__(self, parent, translation_service):
        super().__init__(parent)
        self.translation_service = translation_service
        self.icons = IconSet(self)
        self.current_url = ""
        self.source_image = None
        self.live_source_image = None
        self.tk_image = None
        self._resize_job = None
        self._resize_finish_job = None
        self._empty_text = self.translation_service.get(
            "ui.select_mod",
            "Select a mod to see its preview",
        )
        self._stage_text_color = "#777777"

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=WideScrollbar.THICKNESS) # Keep the scrollbar gutter so the damn layout doesn't bounce around... - Tim
        self.rowconfigure(1, weight=1)

        # Keep the underlined Mod Info heading visually attached to the details below it... - Tim
        self.header = ttk.Frame(self, padding=(16, 14, 16, 2))
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.mod_info_label = Label(
            self.header,
            text=self.translation_service.get(
                "preview.mod_info",
                "Mod Info",
            ),
            font="MewtatorHeadingUnderline",
        )

        self.mod_info_label.grid(row=0, column=0, sticky="w")

        self.empty_state = ttk.Frame(self, padding=(32, 24))
        self.empty_state.columnconfigure(0, weight=1)
        self.empty_state.rowconfigure(0, weight=1)
        self.empty_state.rowconfigure(3, weight=1)
        self.empty_icon = self.icons.brand()

        self.empty_icon_label = Label(
            self.empty_state,
            image=self.empty_icon,
        )

        self.empty_icon_label.grid(
            row=1,
            column=0,
            pady=(0, 14),
        )

        self.empty_message_label = Label(
            self.empty_state,
            text=self._empty_text,
            font="MewtatorSubheading",
            anchor="center",
            justify="center",
            wraplength=360,
        )

        self.empty_message_label.grid(row=2, column=0)

        self.panel_canvas = tk.Canvas(
            self,
            highlightthickness=0,
            borderwidth=0,
        )

        self.panel_canvas.grid(row=1, column=0, sticky="nsew")

        self.panel_scroll = WideScrollbar(
            self,
            orient="vertical",
            command=self.panel_canvas.yview,
        )

        self.panel_scroll.grid(row=1, column=1, sticky="ns")
        self.panel_canvas.configure(yscrollcommand=self.panel_scroll.set)

        self.content = ttk.Frame(self.panel_canvas, padding=(16, 4, 16, 14))
        self.content.columnconfigure(0, weight=1)

        self._content_window = self.panel_canvas.create_window(
            (0, 0),
            window=self.content,
            anchor="nw",
        )

        self.content.bind("<Configure>", self._update_scroll_region)
        self.panel_canvas.bind("<Configure>", self._resize_content)

        self.title_label = Label(self.content, style="PreviewTitle.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w", padx=4)

        self.metadata_frame = ttk.Frame(self.content)
        self.metadata_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(3, 0))

        self.author_label = Label(self.metadata_frame, style="Metadata.TLabel")
        self.author_label.pack(side="left")

        self.version_label = Label(self.metadata_frame, style="Metadata.TLabel")
        self.version_label.pack(side="left", padx=(16, 0))

        self.dll_info_label = Label(self.content, style="Warning.TLabel")
        self.dll_info_label.grid(row=2, column=0, sticky="w", padx=4, pady=(4, 0))

        self.url_label = tk.Label(
            self.content,
            font="TkDefaultFont",
            fg="#3399FF",
            cursor="hand2",
            text="",
            anchor="w",
        )

        self.url_label.grid(row=3, column=0, sticky="ew", padx=4, pady=(2, 8))
        self.url_label.bind("<Button-1>", self._on_url_click)

        self.image_stage = tk.Canvas(
            self.content,
            height=self.EMPTY_PREVIEW_HEIGHT,
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
        )

        self.image_stage.grid(row=4, column=0, sticky="ew", padx=4)
        self.image_stage.bind("<Configure>", self._schedule_image_render)

        # Description text follows the preview directly... - Tim
        desc_frame = ttk.Frame(self.content)
        desc_frame.grid(row=5, column=0, sticky="ew", padx=4, pady=(12, 0))
        desc_frame.columnconfigure(0, weight=1)

        self.desc_label = tk.Label(
            desc_frame,
            text="",
            font="TkTextFont",
            anchor="nw",
            justify="left",
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            padx=4,
            pady=0,
        )

        self.desc_label.grid(row=0, column=0, sticky="ew")
        desc_frame.bind("<Configure>", self._resize_description_wrap)

        for widget in (
            self.header,
            self.mod_info_label,
            self.panel_canvas,
            self.content,
            self.title_label,
            self.metadata_frame,
            self.author_label,
            self.version_label,
            self.dll_info_label,
            self.url_label,
            self.image_stage,
            desc_frame,
            self.desc_label,
        ):
            self._bind_panel_wheel(widget)
        self._show_empty_state()

    def _resize_description_wrap(self, event):
        # Account for the label's 4 px internal padding on both sides 
        # so requested height matches the text users actually see... - Tim
        wrap_width = max(1, event.width - 8)
        if int(float(self.desc_label.cget("wraplength") or 0)) != wrap_width:
            self.desc_label.configure(wraplength=wrap_width)

    def _show_empty_state(self):
        self.panel_canvas.grid_remove()
        self.panel_scroll.set_forced_hidden(True)
        self.empty_state.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

    def _show_details(self):
        self.empty_state.grid_remove()
        self.panel_canvas.grid()
        self.panel_scroll.set_forced_hidden(False)
        self.after_idle(
            lambda: self.panel_scroll.set(*self.panel_canvas.yview())
        )

    def _update_scroll_region(self, _event=None):
        self.panel_canvas.configure(scrollregion=self.panel_canvas.bbox("all"))
        if not self._panel_has_vertical_overflow():
            self.panel_canvas.yview_moveto(0.0)

    def _resize_content(self, event):
        self.panel_canvas.itemconfigure(self._content_window, width=event.width)

    def _panel_has_vertical_overflow(self):
        bbox = self.panel_canvas.bbox("all")
        if not bbox:
            return False
        content_height = max(0, bbox[3] - bbox[1])
        viewport_height = max(1, self.panel_canvas.winfo_height())
        return content_height > viewport_height + 1

    def _bind_panel_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_panel_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_panel_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_panel_mousewheel, add="+")

    def _on_panel_mousewheel(self, event):
        # Scrollbar auto-hides when the content fits... - Tim
        if (
            not self._panel_has_vertical_overflow()
            or not self.panel_scroll.winfo_ismapped()
        ):
            if not self._panel_has_vertical_overflow():
                self.panel_canvas.yview_moveto(0.0)
            return "break"

        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = getattr(event, "delta", 0)
            units = -3 if delta > 0 else 3 if delta < 0 else 0
        if units:
            self.panel_canvas.yview_scroll(units, "units")
        return "break"

    def update_preview(
        self,
        title: str,
        author: str,
        version: str,
        description: str,
        preview_path: Optional[str],
        url: str = "",
        has_dlls: bool = False,
    ):
        self._show_details()
        self.title_label.config(text=title)
        author_text = self.translation_service.get("preview.author", "By {author}").format(
            author=author
        )
        version_text = self.translation_service.get(
            "preview.version",
            "Version {version}",
        ).format(version=version)
        self.author_label.config(text=author_text)
        self.version_label.config(text=version_text)

        if has_dlls:
            dll_text = self.translation_service.get(
                "preview.contains_dlls",
                "⚠ Contains DLL files - Only install from trusted sources!",
            )
            self.dll_info_label.config(text=dll_text)
        else:
            self.dll_info_label.config(text="")

        self.current_url = url
        if url:
            url_text = self.translation_service.get("preview.url", "URL: {url}").format(url=url)
            self.url_label.config(text=url_text)
        else:
            self.url_label.config(text="")

        self.desc_label.config(text=description or "")

        self.source_image = None
        self.live_source_image = None
        self._empty_text = self.translation_service.get("ui.no_preview")
        if preview_path:
            try:
                with Image.open(preview_path) as image:
                    self.source_image = image.convert("RGBA")
                    self.live_source_image = self.source_image.copy()
                    resampling = getattr(Image, "Resampling", Image)
                    self.live_source_image.thumbnail(
                        self.LIVE_PREVIEW_MAX_SIZE,
                        resampling.LANCZOS,
                    )
            except Exception:
                self.source_image = None
                self.live_source_image = None
        self._render_image()

    def _schedule_image_render(self, _event=None):
        # Throttle live updates instead of debouncing them. Debouncing caused
        # the preview to remain stale until the user stopped resizing.
        if self._resize_job is None:
            self._resize_job = self.after(33, self._render_live_image)

        if self._resize_finish_job is not None:
            self.after_cancel(self._resize_finish_job)
        self._resize_finish_job = self.after(100, self._render_final_image)

    def _render_live_image(self):
        self._resize_job = None
        self._render_image(fast=True)

    def _render_final_image(self):
        self._resize_finish_job = None
        self._render_image()

    def _render_image(self, fast: bool = False):
        width = max(1, self.image_stage.winfo_width())

        if self.source_image is None:
            height = self.EMPTY_PREVIEW_HEIGHT
            if int(float(self.image_stage.cget("height"))) != height:
                self.image_stage.configure(height=height)
            self.tk_image = None
            self.image_stage.delete("all")
            self.image_stage.create_text(
                width // 2,
                height // 2,
                text=self._empty_text,
                font="TkDefaultFont",
                fill=self._stage_text_color,
            )
            return

        # The canvas used to stay at a fixed 330 px height even when a wide
        # preview rendered much shorter than that. That left large strips of
        # empty panel background above and below the image. Size the stage to
        # the rendered image instead, while retaining the 330 px height cap.
        max_size = (
            max(1, width - self.PREVIEW_SIDE_PADDING * 2),
            self.PREVIEW_MAX_HEIGHT,
        )
        source = self.live_source_image if fast and self.live_source_image else self.source_image
        image = source.copy()
        resampling = getattr(Image, "Resampling", Image)
        resize_filter = resampling.BILINEAR if fast else resampling.LANCZOS
        image.thumbnail(max_size, resize_filter)
        image = self._round_preview_corners(image)

        stage_height = max(1, image.height)
        if int(float(self.image_stage.cget("height"))) != stage_height:
            self.image_stage.configure(height=stage_height)

        # Prepare the replacement before clearing the canvas. This prevents
        # an empty/black frame while a resized preview is being generated.
        next_tk_image = pillow_to_photoimage(image, master=self.image_stage)
        self.tk_image = next_tk_image
        self.image_stage.delete("all")
        self.image_stage.create_image(
            width // 2,
            stage_height // 2,
            image=self.tk_image,
        )

    def _round_preview_corners(self, image: Image.Image) -> Image.Image:
        """Return an RGBA preview with transparent rounded corners."""
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        width, height = image.size
        if width <= 1 or height <= 1:
            return image

        radius = min(self.PREVIEW_CORNER_RADIUS, width // 2, height // 2)
        if radius <= 0:
            return image

        corner_mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(corner_mask)
        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1),
            radius=radius,
            fill=255,
        )
        existing_alpha = image.getchannel("A")
        image.putalpha(ImageChops.multiply(existing_alpha, corner_mask))
        return image

    def clear(self):
        self.title_label.config(text="")
        self.author_label.config(text="")
        self.version_label.config(text="")
        self.dll_info_label.config(text="")
        self.url_label.config(text="")
        self.current_url = ""
        self.source_image = None
        self.live_source_image = None
        self.desc_label.config(text="")
        self._empty_text = self.translation_service.get(
            "ui.select_mod",
            "Select a mod to see its preview",
        )
        self.empty_message_label.config(text=self._empty_text)
        self._show_empty_state()

    def _on_url_click(self, _event):
        """Open the URL in a web browser."""
        if self.current_url:
            try:
                webbrowser.open(self.current_url)
            except Exception:
                pass

    def apply_theme(self, theme_service, theme_name: str):
        colors = theme_service.get_color_scheme(theme_name)
        self._stage_text_color = colors["fg"]
        self.panel_scroll.apply_theme(colors)
        self.panel_canvas.config(bg=colors["bg"])
        self.image_stage.config(bg=colors["bg"])
        self.url_label.config(bg=colors["bg"])
        # Description is a normal non-selectable label now, along with the rest of 
        # Mod Info rather than an text field... - Tim
        self.desc_label.config(
            bg=colors["bg"],
            fg=colors["text_fg"],
        )
        self._render_image()
