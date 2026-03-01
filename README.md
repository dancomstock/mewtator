# Mewtator

A mod manager for Mewgenics.

Download here:
[Mewtator on Nexus](https://www.nexusmods.com/mewgenics/mods/1)

## Features

- Manage and organize mods
- Enable/disable mods with a simple interface
- **Mod requirements and dependency system** - See [MOD_REQUIREMENTS.md](MOD_REQUIREMENTS.md)
- **Auto-sort mods by dependencies** - Automatically arrange mods in correct load order
- Version constraints and validation
- Launch game with mod configurations
- Customizable launch options (dev mode, debug console, custom arguments)
- Export launch scripts (.BAT files for easy launching)
- Unpack and repack game resources
- Multi-language support
- Import/export modlists

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

## For Mod Authors

Mewtator supports advanced modding features to help you create better mods.

### Documentation

- **[MOD_AUTHOR_GUIDE.md](MOD_AUTHOR_GUIDE.md)** - Complete guide on creating mods, including all available `description.json` fields and best practices
- **[MOD_REQUIREMENTS.md](MOD_REQUIREMENTS.md)** - Detailed documentation on the requirements and dependency system

### Quick Example

```json
{
  "title": "My Awesome Mod",
  "author": "YourName",
  "version": "1.0.0",
  "description": "Does something cool.",
  "requirements": [
    "CoreFramework>=1.5.0"
  ]
}
```

**Note:** The mod's folder name (e.g., `MyMod`) serves as its identifier - not a field in the JSON.

## Using Auto-Sort

Mewtator can automatically arrange your mods in the correct load order based on their requirements.
Currently it sorts alphetically and then applies requirements.  I plan to update this if better logic is needed in the future (like checking for merege conflics or whole file overwrites.)

**How to use:**
- Click "Auto-Sort" button in main window

**Circular dependency detection:**
If ModA requires ModB and ModB requires ModA, you'll see:
```
Circular dependency detected: ModA → ModB → ModA
```
To fix: Remove one of the requirement links so dependencies flow in one direction.

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

