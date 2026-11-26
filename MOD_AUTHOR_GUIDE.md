# Mod Author Guide

This guide explains how to create mods for Mewgenics and use Mewtator.

## Table of Contents

- [Overview](#overview)
- [Mod Settings](#mod-settings)
- [description.json Format](#descriptionjson-format)
  - [Available Fields](#available-fields)
  - [Complete Example](#complete-example)
- [Best Practices](#best-practices)
- [Quick Reference](#quick-reference)

## Overview

Mods for Mewgenics are folders placed in the `mods` directory. Each mod folder should contain a `description.json` file that tells Mewtator about your mod. Mewtator also supports `info.json` or `modinfo.json` as alternative filenames.

## Mod Settings

Mewtator's Mod Settings feature allows mod authors to expose linked GON settings that are configurable through a user-friendly GUI. See the [Mod Settings Author Guide](MOD_SETTINGS.md) for the format, supported controls and metadata, GON bindings, and various examples.

## description.json Format

### Available Fields

Your mod's folder name identifies the mod. The `description.json` file contains optional metadata.

**Note:** All fields are optional with sensible defaults. However, it's recommended to include at least `title`, `author`, `version`, and `description` for a good user experience.

**Field Descriptions:**

- **`title`** (string, optional) - also accepts **`name`** as an alias
  - The display name shown in Mewtator's UI
  - Default: Uses the folder name if not specified
  - Can contain spaces and special characters
  - Example: `"Core Framework - Base Systems"`

- **`author`** (string, optional)
  - Your name or username
  - Default: `"Unknown"`
  - Example: `"YourName"` or `"ModdingTeam"`

- **`version`** (string, optional)
  - Semantic version number: `major.minor.patch`
  - Default: `"Unknown"`
  - Used for requirement validation
  - Examples: `"1.0.0"`, `"2.3.1"`, `"0.5.0-beta"`

- **`description`** (string, optional)
  - Description of your mod
  - Default: Empty string
  - Use `\n` for line breaks
  - Displayed in the preview panel
  - Example: `"Adds new gameplay mechanics.\n\nFeatures:\n- New items\n- New enemies"`

- **`url`** (string, optional)
  - Link to your mod's page (Nexus, GitHub, etc.)
  - Clickable in Mewtator's preview panel
  - Default: Empty string (no link)
  - Example: `"https://www.nexusmods.com/mewgenics/mods/123"`

- **`requirements`** (array, optional)
  - List of mods required for this mod to work
  - Default: Empty array (no requirements)
  - See [MOD_REQUIREMENTS.md](MOD_REQUIREMENTS.md) for detailed information
  - Example: `["CoreMod>=1.0.0", "UIFramework"]`

- **`dll_order`** (array, optional) - **For DLL mods only**
  - Specifies the load order for multiple DLL files within your mod
  - Default: Alphabetical order if not specified
  - Only include the DLL filenames, not full paths
  - Case-insensitive matching
  - Any DLLs not listed will be loaded alphabetically after the specified ones
  - Example: `["core.dll", "plugin.dll", "hooks.dll"]`
  - **Use case:** When your mod has multiple DLLs with dependencies on each other
  - **⚠️ Security Note:** DLL mods execute with full system privileges. Users should only install DLL mods from trusted sources.

**Preview Images:**
Preview images are auto-detected (not specified in JSON). Place a file named `preview.png`, `preview.jpg`, `preview.jpeg`, or `preview.webp` in your mod folder and Mewtator will find it automatically.

### Complete Example

Here's a complete `description.json` with all fields:

**Folder structure:**
```
mods/
  AdvancedGameplay/         ← Folder name (used as mod ID)
    description.json        ← Metadata file
    preview.png            ← Auto-detected preview image
    ... (mod files)
```

**description.json:**
```json
{
  "title": "Advanced Gameplay Overhaul",
  "author": "ModAuthor",
  "version": "2.1.0",
  "description": "A comprehensive gameplay overhaul that adds new mechanics and rebalances the game.\n\nFeatures:\n- New items and enemies\n- Rebalanced stats\n- Quality of life improvements\n\nRequires:\n- Core Framework v1.5.0+\n- UI Enhancements v2.0.0+",
  "url": "https://www.nexusmods.com/mewgenics/mods/456",
  "requirements": [
    "CoreFramework>=1.5.0",
    "UIEnhancements>=2.0.0"
  ],
  "dll_order": [
    "core.dll",
    "plugin.dll"
  ]
}
```

For more information about the requirements system, see [MOD_REQUIREMENTS.md](MOD_REQUIREMENTS.md).

## Best Practices

### 1. Always Specify Version

Include a version in your `description.json`:
```json
{
  "version": "1.0.0"
}
```

Without a version, Mewtator treats it as `"0.0.0"`, which may break requirement checks.

### 2. Use Semantic Versioning

Follow the `major.minor.patch` format:
- **Major** - Breaking changes (2.0.0 → 3.0.0)
- **Minor** - New features, backwards compatible (1.0.0 → 1.1.0)
- **Patch** - Bug fixes (1.0.0 → 1.0.1)

This helps other mod authors write good version constraints.

### 3. Prefer `>=` for Requirements

```json
"CoreMod>=1.5.0"  //Good - flexible
"CoreMod==1.5.0"  //Too strict - breaks on updates
```

### 4. Document Requirements

Include requirement info in your description:

```json
{
  "description": "My awesome mod.\n\nRequires:\n- Core Framework v1.5.0+\n- UI Library v2.0.0+"
}
```

### 5. Include a URL

Help users find your mod page:
```json
{
  "url": "https://www.nexusmods.com/mewgenics/mods/123"
}
```

### 6. Add a Preview Image

Make your mod easy to identify:
- Create `preview.png` in your mod folder
- Recommended size: 800x600 or similar
- Shows in Mewtator's preview panel

### 7. DLL Mod Security (For DLL mod authors)

**⚠️ IMPORTANT SECURITY CONSIDERATIONS:**

If your mod contains DLL files, be aware that:
- DLL files execute with full system privileges
- Malicious DLLs can compromise the user's system
- Users are warned about security risks when enabling DLL mods
- **Users need Mewjector (DLL chainloader)** to load DLL mods: https://www.nexusmods.com/mewgenics/mods/218

**Best practices for DLL mod authors:**
- **Build trust:** Publish your mod on reputable platforms (Nexus Mods, GitHub, etc.)
- **Open source when possible:** Share your source code to allow security review
- **Sign your DLLs:** Use code signing certificates to prove authenticity
- **Document functionality:** Clearly explain what your DLL does
- **Use `dll_order`:** If you have multiple DLLs with dependencies, specify load order in metadata
- **Test thoroughly:** Ensure your DLLs don't cause crashes or conflicts
- **Mention the Mewjector requirement:** Let users know they need Mewjector installed

**Example for DLL mods:**
```json
{
  "title": "Advanced Hooks",
  "author": "TrustedModder",
  "version": "1.0.0",
  "description": "Game hooks for extended functionality.\n\nRequires Mewjector (DLL Chainloader): https://www.nexusmods.com/mewgenics/mods/218\n\nSource code: https://github.com/...",
  "url": "https://www.nexusmods.com/mewgenics/mods/123",
  "dll_order": ["core.dll", "hooks.dll"]
}
```

## Quick Reference

### Minimal mod (recommended fields)

```json
{
  "title": "My Mod",
  "author": "Me",
  "version": "1.0.0",
  "description": "Does something cool."
}
```

**Alternative:** You can use `"name"` instead of `"title"` if you prefer.

### Full-featured mod

```json
{
  "title": "My Complex Mod",
  "author": "ModAuthor",  
  "version": "2.1.0",
  "description": "A complex mod with lots of features.\n\nRequires Core Framework.",
  "url": "https://www.nexusmods.com/mewgenics/mods/123",
  "requirements": [
    "CoreFramework>=2.0.0",
    "UILibrary>=1.5.0"
  ]
}
```

**Note:** The mod's folder name (e.g., `MyComplexMod`) is used as its identifier, not a field in the JSON.

### Common version constraint patterns

```json
{
  "requirements": [
    "Mod",                    // Any version
    "Mod>=1.0.0",            // At least 1.0.0 (most common)
    "Mod>1.2.0",             // Greater than 1.2.0 (skip buggy version)
    "Mod<=2.9.9",            // Up to 2.9.9 (before breaking change)
    "Mod==1.5.0"             // Exactly 1.5.0 (use rarely)
  ]
}
```

## Additional Resources

- **[MOD_REQUIREMENTS.md](MOD_REQUIREMENTS.md)** - Detailed guide on the requirements and dependency system

For help with mod creation or Mewtator issues:

1. Check requirements are spelled correctly (must match folder name exactly)
2. Verify all required mods are enabled  
3. Check version numbers match constraints

For Mewtator bugs or feature requests, visit the project repository.

---

**Happy modding!**
