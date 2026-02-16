import ast
import json
import re
from pathlib import Path

# ---------------------------------------------
# CONFIG
# ---------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = PROJECT_ROOT / "app" / "locales"
EN_LOCALE = LOCALES_DIR / "en.json"

TEXT_ARG_NAMES = {"text", "title", "message", "label"}
MESSAGEBOX_FUNCS = {
    "showinfo", "showwarning", "showerror", "askyesno", "askokcancel"
}

TRANSLATED_PATTERN = re.compile(r't\s*\(')

# ---------------------------------------------
# HARD-CODED STRING → KEY MAP
# This enforces your desired structure.
# ---------------------------------------------
STRING_KEY_MAP = {
    # Window title
    "Mewtator: Mewgenics Mod Manager": "ui.window_title",

    # Menu: File
    "File": "menu.file._label",
    "Settings": "menu.file.settings",
    "Unpack Base Resources": "menu.file.unpack",
    "Repack Resources": "menu.file.repack",
    "Open Mods Folder": "menu.file.open_mods",
    "Open Game Folder": "menu.file.open_game",
    "Exit": "menu.file.exit",

    # UI panels
    "Disabled Mods": "ui.disabled_mods",
    "Enabled Mods": "ui.enabled_mods",
    "Disable All": "ui.disable_all",
    "Enable All": "ui.enable_all",

    # Preview panel
    "Title:": "ui.preview.title",
    "Author:": "ui.preview.author",
    "Version:": "ui.preview.version",
    "No Preview Image": "ui.no_preview",

    # Launch button
    "Launch Game": "ui.launch_game",

    # Settings window (from earlier)
    "Settings (window title)": "settings.title",  # not literal, just example
    "Auto-Detect Game Install": "settings.auto_detect",
    "Game Install Directory": "settings.game_install_dir",
    "Mods Folder": "settings.mods_folder",
    "Browse": "settings.browse",
    "Language": "settings.language",
    "Save Settings": "settings.save",
    "Not Found": "settings.not_found_title",
    "Unable to detect the Mewgenics installation.": "settings.not_found_body",
    "Error": "settings.error_title",
    "Game install directory is required.": "settings.error_missing_game",
    "Game install directory is invalid.": "settings.error_invalid_game",

    # Context menu
    "Move to Top": "context_menu.move_top",
    "Move to Bottom": "context_menu.move_bottom",
    "Disable": "context_menu.disable",
    "Enable": "context_menu.enable",

    # Errors
    "Missing Mods": "errors.missing_mods_title",
}

MISSING_MODS_BODY_PREFIX = (
    "The following enabled mods are missing from the mods folder:"
)


# ---------------------------------------------
# Helpers
# ---------------------------------------------
def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def suggest_key(text: str, context: str = "") -> str:
    text = normalize_text(text)

    # Exact match first
    if text in STRING_KEY_MAP:
        return STRING_KEY_MAP[text]

    # Special-case missing mods body (multi-line)
    if text.startswith(MISSING_MODS_BODY_PREFIX):
        return "errors.missing_mods_body"

    # Fallback: auto namespace
    slug = (
        text.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
    )
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    if not slug:
        slug = "string"
    return f"auto.{slug}"


def flatten_dict(d, prefix=""):
    items = {}
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key))
        else:
            items[new_key] = v
    return items


def add_parents(node):
    for child in ast.iter_child_nodes(node):
        child.parent = node
        add_parents(child)


# ---------------------------------------------
# AST Scanner
# ---------------------------------------------
class TranslationScanner(ast.NodeVisitor):
    def __init__(self, filename: Path):
        self.filename = filename
        self.results = []

    def visit_Call(self, node: ast.Call):
        # messagebox.showerror("Error", "Something")
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

            # Window title: root.title("...")
            if func_name == "title" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    text = arg.value
                    if not TRANSLATED_PATTERN.search(text):
                        key = suggest_key(text, context="window.title")
                        replacement = f't("{key}")'
                        self.results.append(
                            (node.lineno, text, key, replacement)
                        )

            # Messageboxes
            if func_name in MESSAGEBOX_FUNCS:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        text = arg.value
                        if not TRANSLATED_PATTERN.search(text):
                            key = suggest_key(text, context=f"messagebox.{func_name}")
                            replacement = f't("{key}")'
                            self.results.append(
                                (node.lineno, text, key, replacement)
                            )

        # widget(text="Something", label="Something", title="Something", message="Something")
        if isinstance(node.func, ast.Name):
            widget_name = node.func.id.lower()
            for kw in node.keywords:
                if kw.arg in TEXT_ARG_NAMES:
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        text = kw.value.value
                        if not TRANSLATED_PATTERN.search(text):
                            context = f"{widget_name}.{kw.arg}"
                            key = suggest_key(text, context=context)
                            replacement = f'{kw.arg}=t("{key}")'
                            self.results.append(
                                (node.lineno, text, key, replacement)
                            )

        self.generic_visit(node)


def scan_file(path: Path):
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return []

    add_parents(tree)
    scanner = TranslationScanner(path)
    scanner.visit(tree)
    return scanner.results


def scan_project(root: Path):
    all_results = []
    for py_file in root.rglob("*.py"):
        results = scan_file(py_file)
        if results:
            all_results.append((py_file, results))
    return all_results


# ---------------------------------------------
# Locale Handling
# ---------------------------------------------
def load_locale():
    if EN_LOCALE.exists():
        return json.loads(EN_LOCALE.read_text(encoding="utf-8"))
    return {}


def save_locale(locale):
    EN_LOCALE.write_text(
        json.dumps(locale, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )


def insert_key(locale, dotted_key, value):
    parts = dotted_key.split(".")
    d = locale
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


# ---------------------------------------------
# MAIN
# ---------------------------------------------
if __name__ == "__main__":
    print("\n=== I18N AUDIT TOOL ===\n")

    locale = load_locale()
    flat_locale = flatten_dict(locale)

    untranslated = scan_project(PROJECT_ROOT)

    missing_keys = {}
    used_keys = set()

    print("Scanning for untranslated strings...\n")

    for file, entries in untranslated:
        print(f"\n{file}:")
        for lineno, text, key, replacement in entries:
            print(f"  Line {lineno}:")
            print(f"    Found:        {repr(text)}")
            print(f"    Key:          {key}")
            print(f"    Replace with: {replacement}")
            if key not in missing_keys:
                missing_keys[key] = text

    # -----------------------------------------
    # Insert missing keys into en.json
    # -----------------------------------------
    if missing_keys:
        print("\nAdding missing keys to en.json...")

        for key, text in missing_keys.items():
            if key not in flat_locale:
                insert_key(locale, key, text)
                print(f"  + {key}")

        save_locale(locale)
        print("\nUpdated en.json with missing keys.")
    else:
        print("\nNo missing translation keys found.")

    # -----------------------------------------
    # Detect unused keys
    # -----------------------------------------
    print("\nChecking for unused translation keys...")

    for py_file in PROJECT_ROOT.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for match in re.findall(r't\s*\(\s*"(.*?)"', content):
            used_keys.add(match)

    flat_locale = flatten_dict(locale)
    unused = [k for k in flat_locale if k not in used_keys]

    if unused:
        print("\nUnused keys:")
        for k in unused:
            print(f"  - {k}")
    else:
        print("No unused keys.")

    # -----------------------------------------
    # Coverage report
    # -----------------------------------------
    total = len(flat_locale)
    used = len(used_keys)
    coverage = (used / total * 100) if total else 100

    print(f"\nTranslation coverage: {coverage:.1f}% ({used}/{total})")
    print("\nDone.\n")
