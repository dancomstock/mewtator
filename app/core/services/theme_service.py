import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
import sys
from contextlib import contextmanager
from pathlib import Path

import sv_ttk
from app.utils.resource_utils import register_private_font, resource_path

try:
    import pywinstyles
except Exception:
    pywinstyles = None


class ThemeService:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.font_family = self._generic_font_family()
        self.app_fonts = {}
        self.current_theme = "dark"
        self.available_themes = ["dark"]
    
    def get_available_themes(self):
        return self.available_themes

    def normalize_theme_name(self, theme_name: str) -> str:
        return "dark"

    def _apply_titlebar_theme(self, window: tk.Misc):
        if sys.platform != "win32" or pywinstyles is None:
            return

        try:
            version = sys.getwindowsversion()
            is_dark = self.current_theme == "dark"

            if version.major == 10 and version.build >= 22000:
                pywinstyles.change_header_color(window, "#1c1c1c" if is_dark else "#fafafa")
                pywinstyles.change_title_color(window, "#ffffff" if is_dark else "#000000")
            elif version.major == 10:
                pywinstyles.apply_style(window, "dark" if is_dark else "normal")
                window.wm_attributes("-alpha", 0.99)
                window.wm_attributes("-alpha", 1)
        except Exception:
            pass
    
    def set_theme(self, theme_name: str):
        normalized = self.normalize_theme_name(theme_name)
        self.current_theme = normalized

        # Always target this ThemeService's Tk interpreter explicitly...
        theme_applied = False
        theme_error = None
        try:
            try:
                sv_ttk.set_theme(normalized, root=self.root)
            except TypeError:
                style = ttk.Style(self.root)
                target_theme = f"sun-valley-{normalized}"
                if target_theme not in style.theme_names():
                    theme_file = Path(sv_ttk.__file__).with_name("sv.tcl")
                    self.root.tk.call("source", str(theme_file))
                style.theme_use(target_theme)
            theme_applied = (
                ttk.Style(self.root).theme_use() == f"sun-valley-{normalized}"
            )
        except Exception as exc:
            theme_error = exc

        self._configure_widget_styles()
        self._apply_tk_palette()
        self._apply_titlebar_theme(self.root)

        if not theme_applied and theme_error is not None:
            try:
                from app.utils.logging_utils import get_logger
                get_logger().warning(
                    "Sun Valley theme failed; using explicit dark fallback: %s",
                    theme_error,
                )
            except Exception:
                pass

    def _apply_tk_palette(self):
        """Apply Mewtator colors to classic Tk widgets and the root surface..."""
        colors = self.get_color_scheme(self.current_theme)
        try:
            self.root.configure(background=colors["bg"])
        except Exception:
            pass

        try:
            self.root.tk.call(
                "tk_setPalette",
                "background", colors["bg"],
                "foreground", colors["fg"],
                "activeBackground", colors["button_active_bg"],
                "activeForeground", colors["fg"],
                "selectBackground", colors["select_bg"],
                "selectForeground", colors["select_fg"],
                "highlightColor", colors["select_bg"],
            )
        except Exception:
            pass

    def _generic_font_family(self) -> str:
        if sys.platform == "win32":
            return "Segoe UI"
        if sys.platform == "darwin":
            return "Helvetica Neue"
        return "DejaVu Sans"

    def configure_fonts(self, use_generic_font: bool = False):
        """Set app-wide named fonts and (optionally) load bundled Sour Gummy..."""

        family = self._generic_font_family()

        if not use_generic_font:
            regular_loaded = register_private_font(resource_path("assets", "fonts", "SourGummy-Regular.ttf"))
            bold_loaded = register_private_font(resource_path("assets", "fonts", "SourGummy-Bold.ttf"))

            if regular_loaded or bold_loaded or "Sour Gummy" in tkfont.families(self.root):
                family = "Sour Gummy"

        self.font_family = family

        font_specs = {
            "MewtatorBody": (11, "normal"),
            "MewtatorBodyBold": (11, "bold"),
            "MewtatorMenu": (10, "normal"),
            "MewtatorSmall": (9, "normal"),
            "MewtatorSmallBold": (9, "bold"),
            "MewtatorSmallUnderline": (9, "normal"),
            "MewtatorBodyUnderline": (11, "normal"),
            "MewtatorSubheading": (12, "bold"),
            "MewtatorFooterStatus": (22, "bold"),
            "MewtatorWarning": (10, "italic"),
            "MewtatorHeading": (14, "bold"),
            "MewtatorHeadingUnderline": (14, "bold"),
            "MewtatorTitle": (20, "bold"),
        }

        self.app_fonts = { }

        for name, (size, weight) in font_specs.items():
            try:
                if name in tkfont.names(self.root):
                    app_font = tkfont.nametofont(name, root=self.root)
                    app_font.configure(family=family, size=size, weight=weight)
                else:
                    app_font = tkfont.Font(root=self.root, name=name, family=family, size=size, weight=weight)
                if name.endswith("Underline"):
                    app_font.configure(underline=True)
                if name == "MewtatorWarning":
                    app_font.configure(slant="italic")
                self.app_fonts[name] = app_font
            except Exception:
                pass

        named_font_sizes = {
            "TkDefaultFont": 11,
            "TkTextFont": 11,
            "TkMenuFont": 10,
            "TkHeadingFont": 12,
            "TkCaptionFont": 11,
            "TkSmallCaptionFont": 10,
            "TkIconFont": 10,
            "TkTooltipFont": 10,
        }

        for font_name, size in named_font_sizes.items():
            try:
                tkfont.nametofont(font_name, root=self.root).configure(
                    family=family,
                    size=size,
                )
            except Exception:
                pass

        # Set an explicit application-wide fallback...
        try:
            colors = self.get_color_scheme(self.current_theme)
            self.root.option_add("*Font", "MewtatorBody")
            self.root.option_add("*Menu.Font", "MewtatorMenu")
            self.root.option_add("*Menu.cursor", "hand2")
            self.root.option_add("*TCombobox*Listbox.font", "MewtatorBody")
            self.root.option_add("*TCombobox*Listbox.cursor", "hand2")
            self.root.option_add("*TCombobox*Listbox.background", colors["menu_bg"])
            self.root.option_add("*TCombobox*Listbox.foreground", colors["menu_fg"])
            self.root.option_add("*TCombobox*Listbox.selectBackground", colors["menu_active_bg"])
            self.root.option_add("*TCombobox*Listbox.selectForeground", colors["menu_active_fg"])
        except Exception:
            pass

        self._configure_widget_styles()

    def get_font_family(self) -> str:
        return self.font_family

    def _configure_widget_styles(self):
        try:
            style = ttk.Style(self.root)
            family = self.font_family
            colors = self.get_color_scheme(self.current_theme)
            body_font = self.app_fonts.get("MewtatorBody", (family, 11))
            bold_font = self.app_fonts.get("MewtatorBodyBold", (family, 11, "bold"))
            heading_font = self.app_fonts.get("MewtatorHeading", (family, 14, "bold"))
            footer_status_font = self.app_fonts.get("MewtatorFooterStatus", (family, 22, "bold"))
            title_font = self.app_fonts.get("MewtatorTitle", (family, 20, "bold"))
            menu_font = self.app_fonts.get("MewtatorMenu", (family, 10))
            small_font = self.app_fonts.get("MewtatorSmall", (family, 9))
            warning_font = self.app_fonts.get("MewtatorWarning", (family, 10, "italic"))

            # Set base colors explicitly as well as the font...
            style.configure(
                ".",
                font=body_font,
                background=colors["bg"],
                foreground=colors["fg"],
                fieldbackground=colors["text_bg"],
                troughcolor=colors["scrollbar_trough_bg"],
                selectbackground=colors["select_bg"],
                selectforeground=colors["select_fg"],
            )
            style.configure("TFrame", background=colors["bg"])
            style.configure(
                "TLabel",
                background=colors["bg"],
                foreground=colors["fg"],
            )
            style.configure(
                "TCheckbutton",
                background=colors["bg"],
                foreground=colors["fg"],
            )
            style.configure(
                "TRadiobutton",
                background=colors["bg"],
                foreground=colors["fg"],
            )
            style.configure(
                "TEntry",
                fieldbackground=colors["text_bg"],
                foreground=colors["text_fg"],
                insertcolor=colors["text_fg"],
            )
            style.configure(
                "TCombobox",
                fieldbackground=colors["button_bg"],
                background=colors["button_bg"],
                foreground=colors["fg"],
            )
            style.configure(
                "Treeview",
                background=colors["text_bg"],
                fieldbackground=colors["text_bg"],
                foreground=colors["text_fg"],
            )
            style.configure(
                "Treeview.Heading",
                background=colors["button_bg"],
                foreground=colors["fg"],
            )
            style.configure("TSeparator", background=colors["menu_active_bg"])

            style.map(
                "TCheckbutton",
                foreground=[
                    ("disabled", colors["disabled_fg"]),
                    ("!disabled", colors["fg"]),
                ],
                background=[("!disabled", colors["bg"])],
            )
            style.map(
                "TRadiobutton",
                foreground=[
                    ("disabled", colors["disabled_fg"]),
                    ("!disabled", colors["fg"]),
                ],
                background=[("!disabled", colors["bg"])],
            )

            for style_name in (
                "TLabel",
                "TCheckbutton",
                "TRadiobutton",
                "TEntry",
                "TCombobox",
                "TMenubutton",
                "TNotebook.Tab",
                "Treeview",
            ):
                style.configure(style_name, font=body_font)

            # The settings language picker should never fall back to the
            # stupid bright-blue text-selection color! - Tim
            style.configure(
                "Settings.Language.TCombobox",
                font=body_font,
                foreground=colors["fg"],
                fieldbackground=colors["button_bg"],
                selectbackground=colors["button_bg"],
                selectforeground=colors["fg"],
            )

            style.map(
                "Settings.Language.TCombobox",
                foreground=[
                    ("disabled", colors["disabled_fg"]),
                    ("readonly", colors["fg"]),
                ],
                fieldbackground=[
                    ("readonly", colors["button_bg"]),
                    ("focus", colors["button_bg"]),
                ],
                selectbackground=[
                    ("readonly", colors["button_bg"]),
                    ("focus", colors["button_bg"]),
                ],
                selectforeground=[
                    ("readonly", colors["fg"]),
                    ("focus", colors["fg"]),
                ],
            )

            style.configure("Treeview.Heading", font=bold_font)

            self._configure_focusless_button_element(style)

            style.configure(
                "TButton",
                font=body_font,
                padding=(12, 8),
                foreground=colors["fg"],
                background=colors["button_bg"],
            )

            style.map(
                "TButton",
                foreground=[
                    ("disabled", colors["disabled_fg"]),
                    ("!disabled", colors["fg"]),
                ],
                background=[
                    ("pressed", colors["button_pressed_bg"]),
                    ("active", colors["button_active_bg"]),
                    ("!disabled", colors["button_bg"]),
                ],
            )

            style.configure(
                "Primary.TButton",
                font=bold_font,
                padding=(16, 9),
                foreground=colors["button_fg"],
                background=colors["button_bg"],
            )

            style.map(
                "Primary.TButton",
                foreground=[
                    ("disabled", colors["disabled_fg"]),
                    ("!disabled", colors["button_fg"]),
                ],
                background=[
                    ("pressed", colors["button_pressed_bg"]),
                    ("active", colors["button_active_bg"]),
                    ("!disabled", colors["button_bg"]),
                ],
            )

            style.configure(
                "Compact.TButton",
                font=small_font,
                padding=(10, 6),
                foreground=colors["fg"],
            )

            style.configure(
                "ModAction.TButton",
                font=bold_font,
                padding=(12, 6),
                foreground=colors["fg"],
            )

            style.configure(
                "SectionTitle.TLabel",
                font=heading_font,
            )

            style.configure(
                "PreviewTitle.TLabel",
                font=title_font,
            )

            style.configure(
                "Metadata.TLabel",
                font=body_font,
            )

            style.configure(
                "Warning.TLabel",
                font=warning_font,
                foreground="#FF8C00",
            )

            style.configure("HeroTitle.TLabel", font=title_font, background=colors["menu_bg"])

            style.configure(
                "HeroSubtitle.TLabel",
                font=body_font,
                foreground=colors["muted_fg"],
                background=colors["menu_bg"],
            )
            
            style.configure(
                "HeaderHint.TLabel",
                font=small_font,
                foreground=colors["muted_fg"],
                background=colors["menu_bg"],
            )

            style.configure("Header.TFrame", background=colors["menu_bg"])

            style.configure("Footer.TFrame", background=colors["menu_bg"])

            style.configure(
                "Footer.TSeparator",
                background=colors["menu_active_bg"],
            )

            style.configure(
                "Status.TLabel",
                font=bold_font,
                foreground=colors["fg"],
            )

            style.configure(
                "FooterStatus.TLabel",
                font=footer_status_font,
                foreground=colors["fg"],
                background=colors["menu_bg"],
            )

            style.configure(
                "Hint.TLabel",
                font=small_font,
                foreground=colors["muted_fg"],
            )
        except Exception:
            pass
    
    def _configure_focusless_button_element(self, style: ttk.Style):
        """Use Sun Valley button artwork without its white/blue focus outline thingy..."""

        try:
            element_name = "MewtatorButton.button"
            if element_name not in style.element_names():
                tk = self.root.tk
                image = lambda name: tk.eval(f"set ::ttk::theme::sv_dark::I({name})")

                style.element_create(
                    element_name,
                    "image",
                    image("button-rest"),
                    ("selected", "disabled", image("button-dis")),
                    ("disabled", image("button-dis")),
                    ("selected", image("button-rest")),
                    ("pressed", image("button-pressed")),
                    ("active", image("button-hover")),
                    border=4,
                    sticky="nsew",
                )

            # Primary.TButton and Compact.TButton inherit TButton layout,
            # so this removes the annoying persistent focus ring from every ttk button... - Tim
            style.layout(
                "TButton",
                [
                    (
                        element_name,
                        {
                            "sticky": "nsew",
                            "children": [
                                (
                                    "Button.padding",
                                    {
                                        "sticky": "nsew",
                                        "children": [
                                            (
                                                "Button.label",
                                                {"side": "left", "expand": 1},
                                            )
                                        ],
                                    },
                                )
                            ],
                        },
                    )
                ],
            )
        except Exception:
            pass

    def get_current_theme(self):
        return self.current_theme

    def bind_root(self, root: tk.Tk):
        self.root = root
        self._apply_titlebar_theme(self.root)

    def apply_titlebar(self, window: tk.Misc, theme_name: str):
        self.current_theme = self.normalize_theme_name(theme_name)
        self._apply_titlebar_theme(window)

    def get_color_scheme(self, theme_name: str) -> dict:
        return {
            "bg": "#1c1c1c",
            "fg": "#e6e6e6",
            "select_bg": "#2e62b8",
            "select_fg": "#ffffff",
            "text_bg": "#1c1c1c",
            "text_fg": "#e6e6e6",
            "menu_bg": "#2b2b2b",
            "menu_fg": "#ffffff",
            "menu_active_bg": "#3a3a3a",
            "menu_active_fg": "#ffffff",
            "card_bg": "#1c1c1c",
            "muted_fg": "#b5b5b5",
            "warning_fg": "#f2c94c",
            "error_fg": "#ff6b6b",
            "disabled_fg": "#858585",
            "nav_bg": "#5a5a5a",
            "nav_active_bg": "#6a6a6a",
            "nav_pressed_bg": "#4a4a4a",
            "nav_fg": "#ffffff",
            "scrollbar_bg": "#666666",
            "scrollbar_active_bg": "#7a7a7a",
            "scrollbar_trough_bg": "#292929",
            "scrollbar_arrow_fg": "#f2f2f2",
            "button_bg": "#343434",
            "button_active_bg": "#454545",
            "button_pressed_bg": "#292929",
            "button_fg": "#ffffff",
        }

    @contextmanager
    def file_dialog_safe_theme(self):
        yield
