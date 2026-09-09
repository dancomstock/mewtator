from tkinter import BOTH
from tkinter import ttk
from app.ui.components.compat_label import Label

from app.ui.components.menu_bar import MenuBarComponent
from app.ui.components.mod_list_widget import ModListWidget
from app.ui.components.preview_panel import PreviewPanel
from app.ui.components.rounded_button import RoundedButton
from app.ui.icon_set import IconSet
from app.ui.layout_utils import fit_window_to_content
from app.version import versioned_title


class MainWindow:
    def __init__(self, root, translation_service):
        self.root = root
        self.translation_service = translation_service
        self.icons = IconSet(root)

        self.root.title(versioned_title(translation_service.get("window.app_title", "Mewtator")))
        self.root.geometry("1380x820")
        self.root.minsize(1040, 660)

        self.menu_bar = MenuBarComponent(root, translation_service)
        self._build_header()
        self._build_footer()
        self._build_content()

    def _build_header(self):
        t = self.translation_service
        self.header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 12))
        self.header.pack(side="top", fill="x")
        self.header.columnconfigure(1, weight=1)

        self.brand_image = self.icons.brand()
        Label(
            self.header,
            image=self.brand_image,
            style="HeroSubtitle.TLabel",
        ).grid(row=0, column=0, rowspan=3, padx=(0, 14))

        Label(
            self.header,
            text=t.get("ui.app_name", "Mewtator"),
            style="HeroTitle.TLabel",
        ).grid(row=0, column=1, sticky="sw")
        Label(
            self.header,
            text=t.get("ui.app_subtitle", "Mewgenics Mod Manager"),
            style="HeroSubtitle.TLabel",
        ).grid(row=1, column=1, sticky="nw")
        self.shared_list_hint_label = Label(
            self.header,
            text=t.get(
                "ui.shared_list_hint"
            ),
            style="HeaderHint.TLabel",
            justify="left",
            wraplength=760,
        )
        self.shared_list_hint_label.grid(row=2, column=1, sticky="nw", pady=(3, 0))
        self.header.bind("<Configure>", self._resize_header_wrap, add="+")

    def _resize_header_wrap(self, event):
        """Wrap localized header to the space beside the brand icon..."""
        try:
            brand_width = self.brand_image.width() + 14
        except Exception:
            brand_width = 80
        wrap_width = max(260, event.width - brand_width - 40)
        try:
            self.shared_list_hint_label.configure(wraplength=wrap_width)
        except Exception:
            pass

    def _build_footer(self):
        t = self.translation_service
        self.footer = ttk.Frame(
            self.root,
            style="Footer.TFrame",
            padding=(20, 21, 20, 16),
        )
        self.footer.pack(side="bottom", fill="x")
        self.footer.columnconfigure(0, weight=1)
        self.footer.columnconfigure(1, minsize=340)

        self.summary_label = Label(
            self.footer,
            text=t.get("ui.mod_summary", "Mods: 0 of 0 enabled"),
            style="FooterStatus.TLabel",
            font="MewtatorFooterStatus",
        )
        self.summary_label.grid(row=0, column=0, sticky="w")

        self.stop_button = RoundedButton(
            self.footer,
            text=t.get("ui.stop_game", "Stop Game"),
            font="MewtatorHeading",
            width=340,
            height=56,
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(20, 0))

        self.launch_button = RoundedButton(
            self.footer,
            text=t.get("ui.launch_game", "Launch Game"),
            font="MewtatorHeading",
            width=340,
            height=56,
        )
        self.launch_button.grid(row=0, column=2, sticky="ew", padx=(20, 0))

    def _build_content(self):
        t = self.translation_service
        self.content = ttk.Frame(self.root)
        self.content.pack(side="top", fill=BOTH, expand=True, padx=20, pady=(14, 6))
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=3, uniform="main_content")
        self.content.columnconfigure(1, weight=2, uniform="main_content")

        self.list_frame = ttk.Frame(self.content, padding=(0, 0, 12, 0))
        self.list_frame.grid(row=0, column=0, sticky="nsew")
        self.list_frame.rowconfigure(0, weight=1)
        self.list_frame.columnconfigure(0, weight=1)

        self.preview_frame = ttk.Frame(self.content, padding=(12, 0, 0, 0))
        self.preview_frame.grid(row=0, column=1, sticky="nsew")

        self.mod_list_widget = ModListWidget(
            self.list_frame,
            t.get("ui.mods", "Mods"),
        )
        self.mod_list_widget.grid(row=0, column=0, sticky="nsew")
        self.mod_list_widget.set_headings(
            t.get("ui.name", "Name"),
            t.get("ui.author", "Author"),
            t.get("ui.version", "Version"),
        )
        self.mod_list_widget.set_action_labels(
            t.get("ui.enable_all", "Enable All"),
            t.get("ui.disable_all", "Disable All"),
            t.get("mod_list.auto_sort", "Auto-Sort"),
            t.get("ui.import_mod", "Import Mod"),
            t.get("ui.refresh_mods", "Refresh Mods"),
        )

        self.preview_panel = PreviewPanel(self.preview_frame, t)
        self.preview_panel.pack(fill=BOTH, expand=True)

    def fit_to_content(self):
        """Grow main window when localized controls need more room..."""
        fit_window_to_content(
            self.root,
            None,
            min_width=1040,
            min_height=660,
            preferred_width=1380,
            preferred_height=820,
            screen_margin_x=24,
            screen_margin_y=60,
            set_minsize=True,
        )

    def _apply_icons(self, theme_name: str):
        self.mod_list_widget.enable_all_button.config(
            image=self.icons.get("check", theme_name),
            compound="left",
        )
        self.mod_list_widget.disable_all_button.config(
            image=self.icons.get("xmark", theme_name),
            compound="left",
        )
        self.mod_list_widget.auto_sort_button.config(
            image=self.icons.get("sort", theme_name),
            compound="left",
        )
        self.mod_list_widget.import_mod_button.config(
            image=self.icons.get("plus", theme_name),
            compound="left",
        )
        self.mod_list_widget.refresh_button.config(
            image=self.icons.get("arrows-rotate", theme_name),
            compound="none",
        )
        self.mod_list_widget.set_order_icons(
            self.icons.get("arrow-up", theme_name),
            self.icons.get("arrow-up-disabled", theme_name),
            self.icons.get("arrow-down", theme_name),
            self.icons.get("arrow-down-disabled", theme_name),
        )
        self.launch_button.config(image=self.icons.get("play", theme_name))
        self.stop_button.config(image=self.icons.get("stop", theme_name))

    def apply_theme(self, theme_service, theme_name: str):
        self.menu_bar.apply_theme(theme_service, theme_name)
        self.mod_list_widget.apply_theme(theme_service, theme_name)
        self.preview_panel.apply_theme(theme_service, theme_name)
        self.launch_button.apply_theme(theme_service.get_color_scheme(theme_name))
        self._apply_icons(theme_name)

    def set_toggle_action(self, command):
        self.mod_list_widget.set_toggle_action(command)

    def set_enable_all_action(self, command):
        self.mod_list_widget.set_enable_all_action(command)

    def set_disable_all_action(self, command):
        self.mod_list_widget.set_disable_all_action(command)

    def set_auto_sort_action(self, command):
        self.mod_list_widget.set_auto_sort_action(command)

    def set_import_mod_action(self, command):
        self.mod_list_widget.set_import_mod_action(command)

    def set_refresh_action(self, command):
        self.mod_list_widget.set_refresh_action(command)

    def set_order_actions(self, move_up, move_down):
        self.mod_list_widget.set_order_actions(move_up, move_down)

    def set_launch_action(self, command):
        self.launch_button.config(command=command)

    def set_stop_action(self, command):
        def command_with_button_lockout():
            t = self.translation_service
            self.stop_button.config(state="disabled", text=t.get("ui.stopping", "Stopping..."))
            # TODO command() can take multiple seconds to complete, especially with Proton.
            # It should be spun onto a new thread to prevent UI freeze.
            self.root.update()
            command()
            self.stop_button.config(state="normal", text=t.get("ui.stop_game", "Stop Game"))
        self.stop_button.config(command=command_with_button_lockout)

    def set_settings_action(self, command):
        self.menu_bar.set_settings_action(command)

    def set_mod_counts(self, disabled: int, enabled: int):
        total = disabled + enabled

        if total == 0:
            summary = self.translation_service.get(
                "ui.no_mods_installed",
                "No mods installed!",
            )
        else:
            summary = self.translation_service.get(
                "ui.mod_summary",
                "Mods: {enabled} of {total} enabled",
            ).format(enabled=enabled, total=total)

        self.summary_label.config(text=summary)

    def bind_keyboard_shortcuts(self, shortcuts: dict):
        for key, command in shortcuts.items():
            self.root.bind(key, command)
