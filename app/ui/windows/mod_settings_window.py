import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict

from PIL import Image, ImageColor, ImageTk

from app.core.models.mod_config import ModConfig, ModConfigOption
from app.core.services.mod_config_service import ModConfigError
from app.ui.components.compat_label import Label
from app.ui.components.hover_tooltip import HoverTooltip
from app.ui.components.rounded_button import RoundedButton
from app.ui.components.wide_scrollbar import WideScrollbar
from app.ui.layout_utils import fit_window_to_content
from app.utils.resource_utils import resource_path

class ModSettingsWindow:
    """Generated settings editor for a mod's ini"""

    def __init__(
        self,
        parent,
        mod_title: str,
        config: ModConfig,
        translation_service,
        theme_service,
        save_command: Callable[[Dict[int, Any]], None],
    ):
        self.parent = parent
        self.mod_title = mod_title
        self.config = config
        self.translation_service = translation_service
        self.theme_service = theme_service
        self.save_command = save_command
        self.colors = theme_service.get_color_scheme(theme_service.get_current_theme())
        self.variables: Dict[int, tk.Variable] = {}
        self._slider_guard = set()
        self._tooltips = []
        self._scroll_bindtag = f"MewtatorModSettingsScroll_{id(self)}"
        self._scroll_bound = False

        t = translation_service
        self.win = tk.Toplevel(parent)
        self.win.withdraw()
        self.win.title(
            t.get("mod_settings.window_title", "{mod} - Mod Settings").format(mod=mod_title)
        )
        
        self.win.geometry("760x700")
        self.win.minsize(560, 420)
        self.win.configure(background=self.colors["bg"])
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Escape>", lambda _event: self.close())
        self.win.bind("<Control-s>", lambda _event: self.save())
        theme_service.apply_titlebar(self.win, theme_service.get_current_theme())

        self._spinbox_styles = self._ensure_spinbox_styles()
        self._section_frame_style = self._ensure_section_frame_style()

        self._build()

        fit_window_to_content(
            self.win,
            parent,
            min_width=620,
            min_height=480,
            preferred_width=760,
            preferred_height=700,
            screen_margin_x=36,
            screen_margin_y=70,
            set_minsize=True,
        )

        if parent.winfo_viewable():
            self.win.transient(parent)

        self.win.deiconify()
        self.win.lift()
        self.win.grab_set()

    def _build(self):
        t = self.translation_service

        header = ttk.Frame(self.win, padding=(22, 18, 22, 12))
        header.pack(fill="x")

        Label(
            header,
            text=t.get("mod_settings.title", "Mod Settings"),
            font="MewtatorTitle",
        ).pack(anchor="w")
        Label(
            header,
            text=self.mod_title,
            font="MewtatorSubheading",
        ).pack(anchor="w", pady=(2, 0))
        Label(
            header,
            text=t.get("mod_settings.file", "Config file: {file}").format(
                file=os.path.basename(self.config.path)
            ),
            style="Metadata.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        body = ttk.Frame(self.win)
        body.pack(fill="both", expand=True, padx=(22, 10), pady=(0, 8))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            body,
            highlightthickness=0,
            borderwidth=0,
            background=self.colors["bg"],
        )

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = WideScrollbar(body, orient="vertical", command=self.canvas.yview)
        self.scrollbar.apply_theme(self.colors)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas, padding=(0, 0, 10, 8))
        self.content.columnconfigure(0, weight=1)
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_content)

        if not self.config.options:
            Label(
                self.content,
                text=t.get(
                    "mod_settings.no_options",
                    "This INI does not contain any editable key/value options.",
                ),
                wraplength=580,
                justify="left",
            ).grid(row=0, column=0, sticky="w", padx=4, pady=16)
        else:
            self._build_sections()

        footer = ttk.Frame(self.win, padding=(22, 8, 22, 18))
        footer.pack(fill="x")
        footer.columnconfigure(0, weight=1)

        self.error_label = tk.Label(
            footer,
            text="",
            background=self.colors["bg"],
            foreground=self.colors.get("error_fg", "#ff6b6b"),
            font="MewtatorSmall",
            anchor="w",
            justify="left",
            wraplength=430,
        )

        self.error_label.grid(row=0, column=0, sticky="ew", padx=(0, 14))

        reset_defaults = RoundedButton(
            footer,
            text=t.get("mod_settings.reset_defaults", "Reset to Defaults"),
            font="MewtatorBodyBold",
            width=154,
            height=42,
            command=self.reset_to_defaults,
        )

        reset_defaults.apply_theme(self.colors)

        if not any(option.has_default and not option.gon_binding_error for option in self.config.options):
            reset_defaults.configure(state="disabled")

        reset_defaults.grid(row=0, column=1, padx=(0, 10))

        cancel = RoundedButton(
            footer,
            text=t.get("mod_settings.cancel", "Cancel"),
            font="MewtatorBodyBold",
            width=118,
            height=42,
            command=self.close,
        )

        cancel.apply_theme(self.colors)
        cancel.grid(row=0, column=2, padx=(0, 10))

        save = RoundedButton(
            footer,
            text=t.get("mod_settings.save", "Save Settings"),
            font="MewtatorBodyBold",
            width=150,
            height=42,
            command=self.save,
        )
        save.apply_theme(self.colors)
        save.grid(row=0, column=3)

        self._install_scroll_bindings()

    def _ensure_section_frame_style(self):
        """Style ini [Section] text"""

        style_name = "ModSettingsSection.TLabelframe"

        self._section_header_font = "MewtatorHeading"

        style = ttk.Style(self.win)
        style.configure(style_name, background=self.colors["bg"])
        style.configure(
            f"{style_name}.Label",
            font=self._section_header_font,
            background=self.colors["bg"],
            foreground=self.colors["fg"],
        )

        return style_name

    def _build_sections(self):
        row = 0
        for section in self.config.sections:
            title = section.name or self.translation_service.get(
                "mod_settings.general", "General"
            )

            frame = ttk.LabelFrame(
                self.content,
                padding=(14, 0),
                style=self._section_frame_style,
            )
            section_label = Label(
                frame,
                text=title,
                font=self._section_header_font,
                foreground=self.colors["fg"],
            )
            frame.configure(labelwidget=section_label)

            frame.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 14))
            frame.columnconfigure(1, weight=1)
            row += 1

            for option_row, option in enumerate(section.options):
                label = Label(frame, text=option.display_label)

                label.grid(
                    row=option_row,
                    column=0,
                    sticky="w",
                    padx=(0, 18),
                    pady=7,
                )

                control = self._build_control(frame, option, option_row)
                if option.gon_binding_error:
                    self._set_control_disabled(control)
                if option.tooltip:
                    self._tooltips.append(HoverTooltip(label, option.tooltip, self.colors))
                    self._tooltips.append(HoverTooltip(control, option.tooltip, self.colors))

                    for child in control.winfo_children():
                        self._tooltips.append(
                            HoverTooltip(child, option.tooltip, self.colors)
                        )

    def _build_control(self, parent, option: ModConfigOption, row: int):
        if option.control_type == "bool":
            variable = tk.BooleanVar(value=bool(option.value))
            control = ttk.Checkbutton(parent, variable=variable, cursor="hand2")
            control.grid(row=row, column=1, sticky="w", pady=7)
            self.variables[option.identifier] = variable
            return control

        if option.control_type == "slider":
            return self._build_slider(parent, option, row)

        if option.control_type == "enum":
            variable = tk.StringVar(value=str(option.value))
            self.variables[option.identifier] = variable
            values = tuple(option.enum_values or [str(option.value)])

            control = ttk.Combobox(
                parent,
                textvariable=variable,
                values=values,
                state="readonly",
                cursor="hand2",
            )

            control.grid(row=row, column=1, sticky="ew", pady=7)
            self._suppress_combobox_text_selection(control)
            return control

        variable = tk.StringVar(value=str(option.value))
        self.variables[option.identifier] = variable

        if (option.control_type in ("int", "float") and option.min_value is not None and option.max_value is not None):
            kwargs = {
                "from_": option.min_value,
                "to": option.max_value,
            }
            if option.step is not None:
                kwargs["increment"] = option.step
            elif option.control_type == "int":
                kwargs["increment"] = 1
            if self._spinbox_styles:
                kwargs["style"] = self._spinbox_styles["normal"]
            control = ttk.Spinbox(parent, textvariable=variable, **kwargs)
            self._enhance_spinbox_arrows(control)
            self._suppress_spinbox_text_selection(control)
        else:
            control = ttk.Entry(parent, textvariable=variable)

        if option.control_type in ("int", "float"):
            vcmd = (
                self.win.register(
                    lambda proposed, allow_decimal=option.control_type == "float":
                        self._numeric_key_allowed(proposed, allow_decimal)
                ),
                "%P",
            )
            control.configure(validate="key", validatecommand=vcmd)

        if option.control_type == "string" and option.max_length is not None:
            vcmd = (
                self.win.register(
                    lambda proposed, limit=option.max_length: len(proposed) <= limit
                ),
                "%P",
            )
            control.configure(validate="key", validatecommand=vcmd)

        control.grid(row=row, column=1, sticky="ew", pady=7)
        return control

    def _ensure_spinbox_styles(self):
        style = ttk.Style(self.win)
        theme_name = style.theme_use()
        root = self.theme_service.root
        cache_attr = "_mewtator_mod_settings_spinbox_style_cache"
        cache = getattr(root, cache_attr, None)

        if cache is None:
            cache = {}
            setattr(root, cache_attr, cache)

        cached = cache.get(theme_name)

        if cached:
            try:
                style.layout(cached["normal"])
                return cached
            except tk.TclError:
                cache.pop(theme_name, None)

        icon_theme = "light" if theme_name.endswith("light") else "dark"
        safe_theme = "".join(ch if ch.isalnum() else "_" for ch in theme_name)
        prefix = f"MewtatorModNumeric_{safe_theme}"

        style_names = {
            "normal": f"{prefix}.TSpinbox",
            "up": f"{prefix}UpHover.TSpinbox",
            "down": f"{prefix}DownHover.TSpinbox",
        }

        try:
            up_icon_path = resource_path(
                "assets", "icons", "fontawesome", icon_theme, "chevron-up.png"
            )

            down_icon_path = resource_path(
                "assets", "icons", "fontawesome", icon_theme, "chevron-down.png"
            )

            normal_up = self._spinbox_chevron_image(root, up_icon_path, hover=False)
            normal_down = self._spinbox_chevron_image(root, down_icon_path, hover=False)
            hover_up = self._spinbox_chevron_image(root, up_icon_path, hover=True)
            hover_down = self._spinbox_chevron_image(root, down_icon_path, hover=True)
            arrow_gap = tk.PhotoImage(master=root, width=6, height=1)

            images = [
                normal_up,
                normal_down,
                hover_up,
                hover_down,
                arrow_gap,
            ]

            base_layout = style.layout("TSpinbox")
            existing_elements = set(style.element_names())

            def create_image_element(name, image, *, width, height):
                if name not in existing_elements:
                    style.element_create(
                        name,
                        "image",
                        image,
                        width=width,
                        height=height,
                        sticky="",
                    )
                    existing_elements.add(name)

            gap_element = f"{prefix}.Spinbox.arrowgap"
            create_image_element(gap_element, arrow_gap, width=6, height=20)

            def install_variant(variant, up_image, down_image):
                up_element = f"{prefix}.{variant}.Spinbox.uparrow"
                down_element = f"{prefix}.{variant}.Spinbox.downarrow"
                create_image_element(up_element, up_image, width=34, height=20)
                create_image_element(down_element, down_image, width=34, height=20)

                def replace_arrows(nodes):
                    replaced = []
                    for element_name, options in nodes:
                        options = dict(options)
                        if "children" in options:
                            options["children"] = replace_arrows(options["children"])
                        if element_name == "Spinbox.uparrow":
                            element_name = up_element
                        elif element_name == "Spinbox.downarrow":
                            element_name = down_element
                            replaced.append((element_name, options))
                            replaced.append(
                                (gap_element, {"side": "right", "sticky": "ns"})
                            )
                            continue
                        replaced.append((element_name, options))
                    return replaced

                style.layout(style_names[variant], replace_arrows(base_layout))

            install_variant("normal", normal_up, normal_down)
            install_variant("up", hover_up, normal_down)
            install_variant("down", normal_up, hover_down)

            result = dict(style_names)
            result["images"] = images
            cache[theme_name] = result

            root.update_idletasks()
            return result
        except (tk.TclError, ValueError, OSError):
            return None

    def _enhance_spinbox_arrows(self, spinbox: ttk.Spinbox):
        styles = self._spinbox_styles

        if not styles:
            return

        normal_cursor = spinbox.cget("cursor")
        hovered_part = None

        def arrow_part(event):
            try:
                element = str(spinbox.identify(event.x, event.y)).lower()
            except tk.TclError:
                return None
            if "uparrow" in element:
                return "up"
            if "downarrow" in element:
                return "down"
            return None

        def set_part(part):
            nonlocal hovered_part

            if part == hovered_part:
                return
            hovered_part = part
            target_style = styles[part] if part in ("up", "down") else styles["normal"]
            try:
                spinbox.configure(
                    cursor="hand2" if part else normal_cursor,
                    style=target_style,
                )
            except tk.TclError:
                pass

        def on_motion(event):
            set_part(arrow_part(event))

        def on_leave(_event=None):
            set_part(None)

        spinbox.bind("<Motion>", on_motion, add="+")
        spinbox.bind("<Leave>", on_leave, add="+")

    def _suppress_spinbox_text_selection(self, spinbox: ttk.Spinbox):
        """Do not leave text highlighted after step navigation"""
        def clear(_event=None):
            self._clear_text_selection_after_idle(spinbox)

        spinbox.bind("<<Increment>>", clear, add="+")
        spinbox.bind("<<Decrement>>", clear, add="+")

        def clear_after_arrow_click(event):
            try:
                element = str(spinbox.identify(event.x, event.y)).lower()
            except tk.TclError:
                return
            if "uparrow" in element or "downarrow" in element:
                clear()

        spinbox.bind("<ButtonRelease-1>", clear_after_arrow_click, add="+")

    def _clear_text_selection_after_idle(self, widget):
        """Clear incidental ttk entry selection after widget navigation
        """
        def clear_selection():
            try:
                if widget.winfo_exists():
                    widget.selection_clear()
            except (AttributeError, tk.TclError):
                pass

        try:
            self.win.after(0, clear_selection)
        except tk.TclError:
            pass

    def _suppress_combobox_text_selection(self, combobox: ttk.Combobox):
        """Keep readonly enum text from appearing selected/highlighted
        """
        def clear(_event=None):
            self._clear_text_selection_after_idle(combobox)

        combobox.bind("<<ComboboxSelected>>", clear, add="+")
        combobox.bind("<FocusIn>", clear, add="+")
        combobox.bind("<ButtonRelease-1>", clear, add="+")
        combobox.bind("<KeyRelease-Up>", clear, add="+")
        combobox.bind("<KeyRelease-Down>", clear, add="+")
        combobox.bind("<KeyRelease-Home>", clear, add="+")
        combobox.bind("<KeyRelease-End>", clear, add="+")

    def _spinbox_chevron_image(self, master, icon_path: str, *, hover: bool):
        """Render one fixed-size Font Awesome arrow image
        """
        width = 34
        height = 20
        icon_size = 16

        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        with Image.open(icon_path) as source:
            icon = source.convert("RGBA")
            if icon.size != (icon_size, icon_size):
                icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

        color_key = "button_fg" if hover else "muted_fg"
        rgb = ImageColor.getrgb(self.colors[color_key])
        alpha = icon.getchannel("A")
        icon = Image.new("RGBA", icon.size, (*rgb, 255))
        icon.putalpha(alpha)

        x = (width - icon.width) // 2
        y = (height - icon.height) // 2
        canvas.alpha_composite(icon, (x, y))
        return ImageTk.PhotoImage(canvas, master=master)

    def _build_slider(self, parent, option: ModConfigOption, row: int):
        holder = ttk.Frame(parent)
        holder.grid(row=row, column=1, sticky="ew", pady=5)
        holder.columnconfigure(0, weight=1)

        minimum = option.min_value if option.min_value is not None else 0.0
        maximum = option.max_value if option.max_value is not None else 1.0
        initial = float(option.value)
        initial = min(maximum, max(minimum, initial))

        def format_value(value: float) -> str:
            if option.step is not None and abs(option.step - round(option.step)) < 1e-12:
                return str(int(round(value)))
            return format(value, ".8g")

        scale_variable = tk.DoubleVar(value=initial)
        entry_variable = tk.StringVar(value=format_value(initial))
        # Save from entry variable so typed value is authoritative 
        # even if focus has not left the field yet... - Tim
        self.variables[option.identifier] = entry_variable

        def snapped(value: float) -> float:
            if option.step:
                value = minimum + round((value - minimum) / option.step) * option.step
            return min(maximum, max(minimum, value))

        def set_both(value: float):
            value = snapped(value)
            self._slider_guard.add(option.identifier)

            try:
                scale_variable.set(value)
                entry_variable.set(format_value(value))
            finally:
                self._slider_guard.discard(option.identifier)

        def on_slide(raw):
            if option.identifier in self._slider_guard:
                return
            set_both(float(raw))

        def on_entry_change(*_args):
            if option.identifier in self._slider_guard:
                return
            
            raw = entry_variable.get().strip()

            try:
                value = float(raw)
            except ValueError:
                return
            if not (minimum <= value <= maximum):
                return
            self._slider_guard.add(option.identifier)
            try:
                scale_variable.set(value)
            finally:
                self._slider_guard.discard(option.identifier)

        def commit_entry(_event=None):
            raw = entry_variable.get().strip()
            try:
                value = float(raw)
            except ValueError:
                return
            if minimum <= value <= maximum:
                set_both(value)

        scale = ttk.Scale(
            holder,
            from_=minimum,
            to=maximum,
            variable=scale_variable,
            command=on_slide,
            cursor="hand2",
        )

        scale.grid(row=0, column=0, sticky="ew")

        def track_pointer(event):
            """Move the slider directly under pointer for click-and-drag, like every other good slider implementation in existence"""
            try:
                value = float(scale.get(event.x, event.y))
            except (TypeError, ValueError, tk.TclError):
                return "break"
            set_both(value)
            # Suppress ttk's stupid native drag... - Tim
            return "break"

        scale.bind("<Button-1>", track_pointer)
        scale.bind("<B1-Motion>", track_pointer)
        scale.bind("<ButtonRelease-1>", lambda _event: "break")

        number_entry = ttk.Entry(
            holder,
            textvariable=entry_variable,
            width=10,
            justify="right",
        )

        slider_allows_decimal = not (
            option.step is not None
            and abs(option.step - round(option.step)) < 1e-12
        )

        slider_vcmd = (
            self.win.register(
                lambda proposed, allow_decimal=slider_allows_decimal:
                    self._numeric_key_allowed(proposed, allow_decimal)
            ),
            "%P",
        )

        number_entry.configure(validate="key", validatecommand=slider_vcmd)
        number_entry.grid(row=0, column=1, sticky="e", padx=(12, 0))
        number_entry.bind("<Return>", commit_entry, add="+")
        number_entry.bind("<FocusOut>", commit_entry, add="+")
        entry_variable.trace_add("write", on_entry_change)

        return holder

    @staticmethod
    def _numeric_key_allowed(proposed: str, allow_decimal: bool) -> bool:
        """Return whether keyboard/paste edit is valid for a numeric field
        """
        if proposed == "":
            return True

        unsigned = proposed
        if proposed[0] in "+-":
            unsigned = proposed[1:]
            if unsigned == "":
                return True

        # Sign is only legal in the first position... - Tim
        if "+" in unsigned or "-" in unsigned:
            return False

        if allow_decimal:
            if unsigned.count(".") > 1:
                return False
            return all(char == "." or "0" <= char <= "9" for char in unsigned)
        return bool(unsigned) and all("0" <= char <= "9" for char in unsigned)

    def _set_control_disabled(self, widget):
        try:
            widget.state(["disabled"])
        except (AttributeError, tk.TclError):
            try:
                widget.configure(state="disabled")
            except (AttributeError, tk.TclError):
                pass
        for child in widget.winfo_children():
            self._set_control_disabled(child)

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_content(self, event):
        self.canvas.itemconfigure(self._content_window, width=event.width)

    def _install_scroll_bindings(self):
        """Route wheel input anywhere in this dialog to the settings canvas...
        """
        if self._scroll_bound:
            return

        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.win.bind_class(self._scroll_bindtag, sequence, self._on_mousewheel)

        def attach(widget):
            try:
                tags = tuple(widget.bindtags())
            except tk.TclError:
                return
            if self._scroll_bindtag not in tags:
                widget.bindtags((self._scroll_bindtag,) + tags)
            for child in widget.winfo_children():
                attach(child)

        attach(self.win)
        self._scroll_bound = True

    def _on_mousewheel(self, event):
        if not self.win.winfo_exists():
            return "break"

        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = int(getattr(event, "delta", 0) or 0)
            if not delta:
                return "break"
            notches = max(1, abs(delta) // 120)
            units = (-3 if delta > 0 else 3) * notches

        self.canvas.yview_scroll(units, "units")
        return "break"

    @staticmethod
    def _default_display_value(option: ModConfigOption) -> Any:
        value = option.default_value
        if option.control_type == "bool":
            return bool(value)
        if option.control_type == "int":
            return str(int(value))
        if option.control_type in ("float", "slider"):
            numeric = float(value)
            if (
                option.control_type == "slider"
                and option.step is not None
                and abs(option.step - round(option.step)) < 1e-12
            ):
                return str(int(round(numeric)))
            return format(numeric, ".12g")
        
        return str(value)

    def reset_to_defaults(self):
        """Restore every explicitly defaulted option in the form
        """
        changed = False
        for option in self.config.options:
            if not option.has_default or option.gon_binding_error:
                continue
            variable = self.variables.get(option.identifier)
            if variable is None:
                continue
            variable.set(self._default_display_value(option))
            changed = True

        if changed:
            self.error_label.configure(text="")

    def save(self):
        values = {identifier: variable.get() for identifier, variable in self.variables.items()}
        try:
            self.save_command(values)
        except (ModConfigError, OSError, UnicodeError) as exc:
            self.error_label.configure(text=str(exc))
            return
        except Exception as exc:
            self.error_label.configure(
                text=self.translation_service.get(
                    "mod_settings.save_failed", "Could not save mod settings: {error}"
                ).format(error=str(exc))
            )
            return
        self.close()

    def close(self):
        if not self.win.winfo_exists():
            return
        if self._scroll_bound:
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                try:
                    self.win.unbind_class(self._scroll_bindtag, sequence)
                except tk.TclError:
                    pass
            self._scroll_bound = False
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        self.win.destroy()
