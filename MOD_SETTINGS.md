# Mod Settings Author Guide

Mewtator's Mod Settings feature allows mod authors to expose linked GON settings that are configurable through a user-friendly GUI, making it easy for players to customize configurable balance changes, optional functionality, and other values, without having to manually edit any GON files themselves.

## Quick start

1. Put an INI file in the root of the mod folder (This can be named anything, so long as it ends in .ini)
2. Add `; @mewtator-config` on the first comment line, so Mewtator knows this is the mod's settings file, and not just some "unrelated and possibly DLL related" configuration file.
3. Add INI sections and key/value settings. Use various `@mewtator` metadata to choose how an option is displayed.
4. To edit a GON value, add `gon_file=` and `gon_path=` metadata to the option.

Here's an example mod layout for a mod that adjusts the health of the vanilla "Rat" enemy:

```text
MyMod/
├── settings.ini
└── data/
    └── characters/
        └── enemies.gon.merge
```

`settings.ini`:

```ini
; @mewtator-config

[Enemy Balance]
rat_health = 5 ; Adjust the vanilla Rat's health @mewtator type=slider min=1 max=50 step=1 default=5 label="Rat Health" gon_file=data/characters/enemies.gon.merge gon_path=Rat.properties.health
```

`data/characters/enemies.gon.merge`:

```gon
Rat {
    properties {
        health 5
    }
}
```

The field path and starting value shown here come from vanilla `data/characters/enemies.gon`. The mod includes its `.gon.merge` override, `gon_file=` points to that mod file, and `gon_path=` selects or links the matching vanilla field within GON. When the player opens Mod Settings, Mewtator reads the current value from the mod's merge file. Saving a changed value updates that GON field value and the matching value in `settings.ini`.

The examples below use vanilla file paths, object names, and starting values as reference points. The `gon_file=` path always points to a GON file shipped inside the mod, such as a `.append` or `.patch` file. It does not point directly to any GON files directly inside the game's `resources.gpak`.

## Settings INI

The INI must be in the mod's root folder and contain the `@mewtator-config` marker. Please use one marked settings file to avoid ambiguity.

The marker can be written as either `; @mewtator-config` or `# @mewtator-config` on its own line. INI section headers such as `[Enemy Balance]` will become groups in the window. Settings before the first section appear will simply appear in a general group.

Not everything stored in the file needs a GON binding. Of course, this file can be used for settings that are used specifically from DLL mods if desired, and is recommended.

```ini
; @mewtator-config

[Display]
show_debug_text = false ; Show extra diagnostic text for this mod's DLL specifically @mewtator type=bool label="Debug Text"
cat_name = "Cool Dude" ; Display name text used specifically by this mod's DLL @mewtator type=string max_length=32 label="Cat Name"
```

## Linking to GON

Use `gon_file=` for a path relative to the mod folder and `gon_path=` for the path to a field value inside that file:

```ini
; @mewtator-config

[Balance]
rat_health = 5 ; @mewtator type=int min=1 max=50 step=1 default=5 gon_file=data/characters/enemies.gon.merge gon_path=Rat.properties.health
```

You can also use a more compact form of linkage like so:

```ini
rat_health = 5 ; @mewtator type=int gon="data/characters/enemies.gon.merge::Rat.properties.health"
```

All gon file suffixes are `.gon`, `.gon.merge`, `.gon.append`, and `.gon.patch` are supported. The binding has to resolve to one field value, such as a number, boolean-like value, or string. It can't target an entire object or array.

Paths use dots between object keys. Array elements can be selected with `[index]`, (zero based) duplicate keys can be selected with `#1`, `#2`, and so on:

```ini
fighter_palette = 54 ; @mewtator type=int min=0 max=255 gon_file=data/classes/classes.gon.merge gon_path=Fighter.graphics.palette
glass_shard_min_durability = 7 ; @mewtator type=int min=1 max=12 gon_file=data/items/weapons.gon.merge gon_path=GlassShard.durability[0]
```

These paths correspond to vanilla fields in `data/classes/classes.gon` and `data/items/weapons.gon`. `GlassShard.durability` is a two-value array in vanilla data, `[0]` selects its first value.

## Control types

Mewtator can infer common types from the current value, but declaring `type=` makes intended control explicit and is recommended.

| Type | Window control | Example |
| --- | --- | --- |
| `bool` | Checkbox | `enabled = true` |
| `int` | Whole number input, bounded values use a spinbox | `Rat.properties.health = 5` |
| `float` | Decimal input; bounded values use a spinbox | `drop_rate = 0.25` |
| `slider` | Slider with numeric entry | `Rat.properties.health = 5` |
| `enum` | Read only choice list | `GlassShard.rarity = common` |
| `string` | Text input | `title = "My Feature"` |

For boolean values, Mewtator recognizes `true/false`, `yes/no`, `on/off`, and `1/0`. For `1/0`, declare `type=bool` (or use a boolean-like key such as `enabled`) to avoid it being treated as an integer. Boolean writes preserve source value style when possible. You can set custom literals with `true=` and `false=`.

Common type aliases are accepted, including `boolean`, `toggle`, and `checkbox` for `bool`. `integer` for `int`, `number`, `double`, and `decimal` for `float`, `text` and `input` for `string`, `dropdown`, `select`, and `choice` for `enum`, and `range`, `slider-int`, and `slider-float` for `slider`.

## Option metadata

Metadata follows `@mewtator` in an inline comment, or can be placed in preceding comment line. Values containing spaces should be quoted.

```ini
rat_health = 5 ; The vanilla Rat starts with 5 health @mewtator type=slider min=1 max=50 step=1 default=5 label="Rat Health" gon_file=data/characters/enemies.gon.merge gon_path=Rat.properties.health
```

The text before `@mewtator` in an inline comment is the tooltip that is shown when hovering the field name!

| Metadata | Purpose |
| --- | --- |
| `type=` | Selects `bool`, `int`, `float`, `slider`, `enum`, or `string`. |
| `label=` | Sets the field display name shown in the window. |
| `min=` / `max=` | Sets numeric bounds. For strings, these are length bounds when `min_length`/`max_length` are not supplied. |
| `step=` | Sets the numeric spinbox or slider incrementation. |
| `min_length=` / `max_length=` | Sets string length limits. (`min_chars`/`max_chars` are also accepted). |
| `options=` | Defines enum values, separated by `|` (preferred) or commas. `choices=` and `values=` are aliases. |
| `default=` | Value used by the "Reset to Defaults" button. This does not change the current setting until the player resets and saves. |
| `true=` / `false=` | Explicit GON/INI literals to write for a boolean checkbox. |
| `gon_file=` | GON filename relative to the mod folder. Just `gon=` is also accepted. |
| `gon_path=` | Dot-separated GON object path to a field value. `gon_key=` and `gon_value=` are aliases. |

Example choice list using vanilla weapon rarities:

```ini
glass_shard_rarity = common ; @mewtator type=enum options="common|uncommon|rare|very_rare" default=common gon_file=data/items/weapons.gon.merge gon_path=GlassShard.rarity
```

## Common use cases

### Let players tune balancing values

You can bind a vanilla stat such as an enemy's health, strength, or movement value to a slider or bounded number control. This example shown throughout the tutorial changes the vanilla Rat's health field through a merge file. You can choose limits that restrict it to a reasonable range and add a tooltip explaining.

```ini
rat_health = 5 ; Vanilla Rat health is 5 @mewtator type=slider min=1 max=50 step=1 default=5 gon_file=data/characters/enemies.gon.merge gon_path=Rat.properties.health
```

### Let players adjust an item's rarity

Vanilla data uses rarity values such as `common`, `uncommon`, `rare`, and `very_rare`. An enum can expose a deliberate subset of those values.

```ini
glass_shard_rarity = common ; @mewtator type=enum options="common|uncommon|rare|very_rare" default=common gon_file=data/items/weapons.gon.merge gon_path=GlassShard.rarity
```

### Expose a vanilla progression switch

Some vanilla progression entries have boolean fields. For example, `map_unlock_junkyard.requires_hard_path` is `true` in the vanilla unlock data. A mod could expose this as a checkbox to let players choose whether that unlock requires the hard path. For mods like this that change progression behavior, make sure to describe the impact clearly in the label and tooltip.

```ini
require_hard_path = true ; Set the vanilla hard-path requirement for Junkyard @mewtator type=bool default=true gon_file=data/adventure_progression_unlocks.gon.merge gon_path=map_unlock_junkyard.requires_hard_path
```

The mod's merge file would contain the corresponding vanilla entry:

```gon
map_unlock_junkyard {
    requires_hard_path true
}
```

## Saving, defaults, and errors

- Opening Mod Settings reads linked controls from the current GON field value, so the GON value is authoritative for a bound setting.
- Save Settings writes changed values to the INI and linked GON field values. Mewtator preserves unrelated GON text, comments, ordering, and formatting while replacing the targeted value.
- Reset to Defaults changes controls that declare `default=`. The player still needs to save for those reset values to be written.
- Invalid/missing GON bindings are shown as errors and the affected control is disabled, but other valid settings can still be used.
- Numeric bounds, slider increments, enum choices, and string lengths are validated when saving.

## Limitations

The Mod Settings feature is meant for specifically individual GON field values. It does not use it's own proper scripting language, create entire new GON entries, remove GON objects/sections, or make whole modded gon files load conditionally. For content that players should be able to enable separately, it is still recommended package it as a separate mod download if practical.