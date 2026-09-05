"""Application version information.
Update APP_VERSION here when preparing a new Mewtator release! - Tim
"""

APP_VERSION = "1.0.0"
APP_VERSION_DISPLAY = f"v{APP_VERSION}"

def versioned_title(title: str) -> str:
    """Return an application/window title with the current version appended..."""
    return f"{title} {APP_VERSION_DISPLAY}"