# Mod Requirements System

This guide explains how to use Mewtator's requirements and dependency system for mods.

## Overview

The requirements system allows you to specify that your mod depends on other mods. This ensures players have all necessary dependencies installed and loaded in the correct order.

## Basic Requirements

Add a `requirements` array to your mod's `description.json` to specify which mods are needed:

```json
{
  "requirements": [
    "CoreMod",
    "FrameworkMod",
    "UtilityMod"
  ]
}
```

This means:
- These mods must be **enabled** in Mewtator
- They must be loaded **before** your mod (higher in the list)
- If not met, your mod shows in **orange** and a warning appears at launch

## Version Constraints

Specify minimum (or maximum) versions using comparison operators:

### Supported Operators

- `>=` - Greater than or equal to (most common - "at least this version")
- `<=` - Less than or equal to
- `>` - Greater than
- `<` - Less than  
- `==` - Exactly equal to
- `!=` - Not equal to

### String Format

The simplest way to specify version constraints:

```json
{
  "requirements": [
    "CoreMod>=1.0.0",
    "FrameworkMod>=2.0.0",
    "CompatLayer>1.5.0"
  ]
}
```

### Object Format

Alternative format using objects:

```json
{
  "requirements": [
    {
      "mod": "CoreMod",
      "version": ">=1.0.0"
    },
    {
      "mod": "FrameworkMod",
      "version": ">=2.0.0"
    }
  ]
}
```

Both formats work identically - use whichever you prefer.

### Version Format

Always use semantic versioning with three numbers:
- `"1.0.0"` - Correct
- `"2.3.1"` - Correct
- `"0.5.0-beta"` - Correct (pre-release tag allowed)
- `"1.0"` - Missing patch version
- `"v1.0.0"` - Don't include "v" prefix

### Common Patterns

**Minimum version (most common):**
```json
"CoreMod>=1.5.0"
```

**Exclude a broken version:**
```json
"BuggyMod>1.2.0"
```

**Maximum version (compatibility ceiling):**
```json
"OldAPI<=2.9.9"
```

**Exact version (use sparingly):**
```json
"SpecificMod==2.1.0"
```

### Multiple Constraints Example

```json
{
  "name": "MyComplexMod",
  "version": "1.0.0",
  "requirements": [
    "CoreFramework>=2.0.0",
    "UILibrary>=1.5.0",
    "LegacyCompat<=3.9.9",
    "UtilityMod"
  ]
}
```

## Validation and Warnings

When requirements aren't met, Mewtator provides clear feedback:

### Visual Indicators

- **Orange text** - Mod in enabled list has unmet requirements
- **Red text** - Mod files are missing from disk

### Launch Validation

When you click "Launch Game", Mewtator checks:

1. **Missing mods** - If required mod not enabled → Warning dialog
2. **Wrong order** - If required mod loaded after your mod → Warning dialog  
3. **Version mismatch** - If version doesn't satisfy constraint → Warning dialog

**You can still launch** - Warnings allow you to continue or cancel.

### Example Error Messages

**Missing mod:**
```
MyMod: Required mod 'CoreFramework' is not enabled
```
**Fix:** Enable CoreFramework in Mewtator

**Wrong load order:**
```
MyMod: Required mod 'CoreFramework' must be loaded before this mod (move it up in the list)
```
**Fix:** Move CoreFramework above MyMod, or use Auto-Sort

**Version mismatch:**
```
MyMod: Required mod 'CoreFramework' version 1.0.0 does not satisfy >=1.5.0
```
**Fix:** Update CoreFramework to version 1.5.0 or higher

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
"CoreMod>=1.5.0"  Good - flexible
"CoreMod==1.5.0"  Too strict - breaks on updates

### 4. Document Requirements

Include requirement info in your description:

```json
{
  "description": "My awesome mod.\n\nRequires:\n- Core Framework v1.5.0+\n- UI Library v2.0.0+"
}
```

### 5. Test Load Order

- Enable your mod and its requirements in Mewtator
- Click Auto-Sort to verify order
- Launch and test that everything works

---

For more information on creating mods, see [MOD_AUTHOR_GUIDE.md](MOD_AUTHOR_GUIDE.md).
