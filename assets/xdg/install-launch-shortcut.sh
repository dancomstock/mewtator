#!/bin/sh

# This script places Mewtator.desktop in the user's local applications directory so that it:
# 1) may be launched through an app picker or program launch menu, and
# 2) has a non-generic app icon in desktop environments that strictly use a .desktop file to specify an app icon 

cd "$(dirname "$0")"

desktop-file-install --dir="$HOME/.local/share/applications" \
    --set-key=Exec --set-value="\"$(realpath ../../Mewtator)\"" \
    --set-icon="$(realpath ../icons/mewtator.png)" \
    Mewtator.desktop

update-desktop-database "$HOME/.local/share/applications"

echo 'This script has placed a launch shortcut at ~/.local/share/applications/Mewtator.desktop'
