# Mewtator

A mod manager for Mewgenics.

Download here:
[Mewtator on Nexus](https://www.nexusmods.com/mewgenics/mods/1)

## Features

- Manage and organize mods
- Enable/disable mods with a simple interface
- Launch game with mod configurations
- Unpack and repack game resources
- Multi-language support

## Translations

Mewtator supports multiple languages. Currently available:

**Standard Languages:**
- English (native)
- Français (French)
- Italiano (Italian)
- Deutsch (German)
- Español (Spanish)
- Português (Portuguese - Brazil)
- 中文 (Chinese)
- 日本語 (Japanese)

**Note:** Most standard translations are machine-generated. If you would like to contribute a better translation, please submit:

1. A corrected/improved version of the existing translation file from the `locales/` folder
2. Or a new language translation altogether

Translation files are JSON format. See `locales/English.json` for the base structure.

To submit translations, please open an issue or pull request on the repository, or contact the developer.

## Building

```bash
pyinstaller Mewtator.spec
```

## Running From Source

1) Create and activate a virtual environment (recommended).

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

2) Install requirements.

```bash
pip install -r requirements.txt
```

3) Run the app.

```bash
python -m app.main
```

