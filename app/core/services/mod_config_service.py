import math
import os
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.models.mod_config import GonBinding, ModConfig, ModConfigOption, ModConfigSection
from app.core.services.gon_service import GonError, GonService

class ModConfigError(ValueError):
    pass

class ModConfigService:
    """Discover, parse, validate, and update root-level mod config INI files
    """

    FILE_DIRECTIVE = "@mewtator-config"
    OPTION_DIRECTIVE = "@mewtator"
    _SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:[;#].*)?$")
    _KEY_RE = re.compile(r"^(\s*([^=:#\s][^=:#]*?)\s*([=:])\s*)(.*)$")
    _NUMBER_INT_RE = re.compile(r"^[+-]?\d+$")

    _NUMBER_FLOAT_RE = re.compile(
        r"^[+-]?(?:(?:\d+\.\d*)|(?:\d*\.\d+)|(?:\d+))(?:[eE][+-]?\d+)?$"
    )

    _BOOL_WORDS = {
        "true": True,
        "false": False,
        "yes": True,
        "no": False,
        "on": True,
        "off": False,
    }

    _BOOLISH_KEY_RE = re.compile(
        r"(?:^|_)(?:enabled?|disabled?|use|allow|is|has|show|hide|debug|active)(?:_|$)",
        re.IGNORECASE,
    )

    def __init__(self):
        self.gon_service = GonService()

    def discover(self, mod_path: str) -> Optional[ModConfig]:
        """Return the one root ini Mewtator should expose for a mod
        """
        if not mod_path or not os.path.isdir(mod_path):
            return None

        paths = sorted(
            (
                entry.path
                for entry in os.scandir(mod_path)
                if entry.is_file() and entry.name.lower().endswith(".ini")
            ),
            key=lambda path: os.path.basename(path).casefold(),
        )

        if not paths:
            return None

        candidates: List[ModConfig] = []

        for path in paths:
            try:
                config = self.parse(path)
            except (OSError, UnicodeError, ModConfigError):
                # A malformed/fucked up ini should not break mod info... - Tim
                continue
            if config.gui_enabled:
                candidates.append(config)

        if not candidates:
            return None

        primaries = [config for config in candidates if config.primary]

        if primaries:
            return primaries[0]

        mod_name = os.path.basename(os.path.normpath(mod_path)).casefold()

        preferred_names = (
            "settings.ini",
            "config.ini",
            "configuration.ini",
            f"{mod_name}.ini",
        )

        by_name = {
            os.path.basename(config.path).casefold(): config
            for config in candidates
        }

        for name in preferred_names:
            if name in by_name:
                return by_name[name]

        return candidates[0]

    def parse(self, path: str) -> ModConfig:
        raw_bytes = Path(path).read_bytes()
        text, encoding, has_bom = self._decode(raw_bytes)
        # keepends=True is what lets save() replace values without 
        # normalizing line endings or touching comments/order... - Tim
        lines = text.splitlines(keepends=True)

        if text and not lines:
            lines = [text]

        file_metadata: Dict[str, str] = {}
        sections: List[ModConfigSection] = []
        section_lookup: Dict[str, ModConfigSection] = {}
        current_section_name = ""
        pending_metadata: Dict[str, str] = {}
        gon_file_cache: Dict[str, Path] = {}
        gon_document_cache: Dict[str, Any] = {}

        def section_for(name: str) -> ModConfigSection:
            if name not in section_lookup:
                section = ModConfigSection(name=name)
                section_lookup[name] = section
                sections.append(section)
            return section_lookup[name]

        for line_index, full_line in enumerate(lines):
            content, newline = self._split_newline(full_line)
            stripped = content.strip()

            if not stripped:
                # Keep pending option metadata across blank lines... - Tim
                continue

            comment_body = self._whole_line_comment_body(content)

            if comment_body is not None:
                file_directive = self._extract_directive(comment_body, self.FILE_DIRECTIVE)

                if file_directive is not None:
                    file_metadata.update(self._parse_metadata(file_directive))
                    continue

                option_directive = self._extract_option_directive(comment_body)

                if option_directive is not None:
                    pending_metadata.update(self._parse_metadata(option_directive))
                continue

            section_match = self._SECTION_RE.match(content)

            if section_match:
                current_section_name = section_match.group(1).strip()
                section_for(current_section_name)
                pending_metadata = {}
                continue

            key_match = self._KEY_RE.match(content)

            if not key_match:
                pending_metadata = {}
                continue

            prefix = key_match.group(1)
            key = key_match.group(2).strip()
            remainder = key_match.group(4)
            value_part, suffix, inline_comment = self._split_value_and_comment(remainder)
            raw_value = value_part.strip()

            inline_metadata: Dict[str, str] = {}
            tooltip = inline_comment.strip()

            if inline_comment:
                tooltip, inline_metadata = self._strip_inline_metadata(inline_comment)

            metadata = dict(pending_metadata)
            metadata.update(inline_metadata)
            pending_metadata = {}

            gon_binding = None
            gon_binding_error = ""
            source_raw_value = raw_value

            if self._has_gon_binding(metadata):
                try:
                    gon_binding = self._resolve_gon_binding(
                        Path(path).parent,
                        metadata,
                        file_cache=gon_file_cache,
                        document_cache=gon_document_cache,
                    )
                    source_raw_value = gon_binding.raw_value
                except (OSError, UnicodeError, GonError, ModConfigError) as exc:
                    gon_binding_error = str(exc)

            control_type = self._resolve_control_type(key, source_raw_value, metadata)

            option = self._build_option(
                section=current_section_name,
                key=key,
                raw_value=raw_value,
                source_raw_value=source_raw_value,
                control_type=control_type,
                line_index=line_index,
                prefix=prefix,
                suffix=suffix,
                newline=newline,
                tooltip=tooltip.strip(),
                metadata=metadata,
            )

            option.gon_binding = gon_binding
            option.gon_binding_error = gon_binding_error

            if gon_binding_error:
                error_text = f"GON binding error: {gon_binding_error}"

                option.tooltip = (
                    f"{option.tooltip}\n\n{error_text}" if option.tooltip else error_text
                )

            section_for(current_section_name).options.append(option)

        # Do NOT create a visually empty General section when all options are inside explicit headers...
        sections = [section for section in sections if section.options]

        gui_enabled = self._metadata_bool(
            file_metadata,
            ("enabled", "gui", "detect", "show"),
            default=True,
        )

        primary = self._metadata_bool(
            file_metadata,
            ("primary", "main"),
            default=False,
        )

        return ModConfig(
            path=path,
            sections=sections,
            lines=lines,
            encoding=encoding,
            has_bom=has_bom,
            gui_enabled=gui_enabled,
            primary=primary,
            metadata=file_metadata,
        )

    def save(self, config: ModConfig, values: Dict[int, Any]) -> None:
        """Validate and persist ini values plus any linked GON scalar values
        """
        updated_lines = list(config.lines)
        gon_edits: Dict[str, List[Tuple[ModConfigOption, Any]]] = {}

        for option in config.options:
            if option.identifier not in values:
                continue

            if option.gon_binding_error:
                # Invalid bindings are rendered read-only in the UI. Keep the ini
                # declaration intact, still allowing other settings to save... - Tim
                continue

            submitted = values[option.identifier]
            serialized = self.serialize_value(option, submitted)

            updated_lines[option.line_index] = (
                option.prefix + serialized + option.suffix + option.newline
            )

            if option.gon_binding and not self._typed_values_equal(option, submitted, option.value):
                gon_edits.setdefault(option.gon_binding.file_path, []).append(
                    (option, submitted)
                )

        payloads: Dict[Path, bytes] = {}

        for gon_path, edits in gon_edits.items():
            try:
                document = self.gon_service.load(gon_path)
            except GonError as exc:
                raise ModConfigError(f"Could not parse linked GON file {gon_path}: {exc}") from exc

            replacements = []

            for option, submitted in edits:
                binding = option.gon_binding

                if binding is None:
                    continue
                try:
                    scalar = self.gon_service.resolve_scalar(document, binding.object_path)
                except GonError as exc:
                    raise ModConfigError(
                        f"Could not resolve {binding.display_target}: {exc}"
                    ) from exc

                source_quote = self._quote_from_raw(scalar.raw)

                source_true, source_false = self._bool_literals(
                    scalar.raw, option.metadata
                )

                serialized_gon = self._serialize_value_for_raw(
                    option,
                    submitted,
                    scalar.raw,
                    quote=source_quote,
                    bool_true=source_true,
                    bool_false=source_false,
                    gon=True,
                )

                if serialized_gon != scalar.raw:
                    replacements.append(
                        (scalar.start, scalar.end, serialized_gon)
                    )

            try:
                gon_text = self.gon_service.replace_scalars(document, replacements)
            except GonError as exc:
                raise ModConfigError(f"Could not update linked GON file {gon_path}: {exc}") from exc
            payloads[Path(gon_path)] = document.encode(gon_text)

        ini_text = "".join(updated_lines)

        payloads[Path(config.path)] = self._encode(
            ini_text, config.encoding, config.has_bom
        )

        self._write_payloads_transactionally(payloads)

    def serialize_value(self, option: ModConfigOption, value: Any) -> str:
        return self._serialize_value_for_raw(
            option,
            value,
            option.raw_value,
            quote=option.quote,
            bool_true=option.bool_true,
            bool_false=option.bool_false,
            gon=False,
        )

    def _serialize_value_for_raw(
        self,
        option: ModConfigOption,
        value: Any,
        raw_value: str,
        *,
        quote: str,
        bool_true: str,
        bool_false: str,
        gon: bool,
    ) -> str:
        kind = option.control_type

        if kind == "bool":
            boolean = self._coerce_bool(value)

            if self._value_matches_raw(option, value, raw_value):
                return raw_value
            return bool_true if boolean else bool_false

        if kind == "int":
            numeric = self._coerce_int(value, option.key)
            self._validate_numeric_bounds(option, float(numeric))

            if self._value_matches_raw(option, value, raw_value):
                return raw_value
            return str(numeric)

        if kind in ("float", "slider"):
            numeric = self._coerce_float(value, option.key)
            self._validate_numeric_bounds(option, numeric)

            if self._value_matches_raw(option, value, raw_value):
                return raw_value
            if kind == "slider" and option.step:
                numeric = self._snap_to_step(numeric, option)
                self._validate_numeric_bounds(option, numeric)
            if kind == "slider" and self._is_integral_step(option.step):
                return str(int(round(numeric)))
            return self._format_float(numeric)

        string_value = str(value)

        if kind == "enum" and option.enum_values and string_value not in option.enum_values:
            allowed = ", ".join(option.enum_values)

            raise ModConfigError(
                f"{option.key} must be one of: {allowed}."
            )
            
        length = len(string_value)

        if option.min_length is not None and length < option.min_length:
            raise ModConfigError(
                f"{option.key} must contain at least {option.min_length} characters."
            )
        if option.max_length is not None and length > option.max_length:
            raise ModConfigError(
                f"{option.key} must contain no more than {option.max_length} characters."
            )
        if self._value_matches_raw(option, value, raw_value):
            return raw_value
        if gon:
            return self._serialize_gon_string(string_value, quote)
        if quote:
            return f"{quote}{string_value}{quote}"
        return string_value

    @staticmethod
    def _has_gon_binding(metadata: Dict[str, str]) -> bool:
        return any(
            key in metadata
            for key in (
                "gon",
                "gon_file",
                "gonfile",
                "gon_path",
                "gon_key",
                "gon_value",
                "gon_target",
            )
        )

    def discover_gon_files(self, mod_root: str) -> List[str]:
        """Return every .gon file beneath a mod, without following symlink dirs"""
        root = Path(mod_root).resolve()

        if not root.is_dir():
            return []

        found: List[str] = []

        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [
                name
                for name in dirnames
                if not os.path.islink(os.path.join(dirpath, name))
            ]

            for filename in filenames:
                if not filename.lower().endswith(".gon"):
                    continue
                candidate = Path(dirpath, filename)
                try:
                    resolved = candidate.resolve()
                    if os.path.commonpath((str(root), str(resolved))) != str(root):
                        continue
                except (OSError, ValueError):
                    continue
                found.append(str(resolved))
                
        return sorted(found, key=lambda value: value.casefold())

    def _resolve_gon_binding(
        self,
        mod_root: Path,
        metadata: Dict[str, str],
        *,
        file_cache: Optional[Dict[str, Path]] = None,
        document_cache: Optional[Dict[str, Any]] = None,
    ) -> GonBinding:
        file_ref = (
            metadata.get("gon_file")
            or metadata.get("gonfile")
            or metadata.get("gon")
            or metadata.get("gon_target")
            or ""
        ).strip()
        object_path = (
            metadata.get("gon_path")
            or metadata.get("gon_key")
            or metadata.get("gon_value")
            or ""
        ).strip()

        if "::" in file_ref:
            compact_file, compact_path = file_ref.split("::", 1)
            file_ref = compact_file.strip()
            if not object_path:
                object_path = compact_path.strip()

        if not file_ref:
            raise ModConfigError(
                "GON metadata must specify gon_file=. (gon= is also accepted.)"
            )
        if not object_path:
            raise ModConfigError(
                "GON metadata must specify gon_path=. (gon=\"file.gon::path\" is also accepted.)"
            )

        cache_key = file_ref.replace("\\", "/").casefold()
        target = file_cache.get(cache_key) if file_cache is not None else None

        if target is None:
            target = self._resolve_gon_file(mod_root, file_ref)
            if file_cache is not None:
                file_cache[cache_key] = target

        try:
            document_key = str(target)
            document = (
                document_cache.get(document_key)
                if document_cache is not None
                else None
            )
            if document is None:
                document = self.gon_service.load(str(target))
                if document_cache is not None:
                    document_cache[document_key] = document
            scalar = self.gon_service.resolve_scalar(document, object_path)
        except GonError as exc:
            relative = target.relative_to(mod_root.resolve()).as_posix()
            raise ModConfigError(
                f"{relative} :: {object_path}: {exc}"
            ) from exc

        return GonBinding(
            file_path=str(target),
            relative_path=target.relative_to(mod_root.resolve()).as_posix(),
            object_path=object_path,
            raw_value=scalar.raw,
        )

    def _resolve_gon_file(self, mod_root: Path, reference: str) -> Path:
        root = mod_root.resolve()
        normalized = reference.strip().replace("\\", "/")

        if not normalized:
            raise ModConfigError("GON filename cannot be empty.")
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
            raise ModConfigError("GON paths must be relative to the mod folder.")
        if not normalized.lower().endswith(".gon"):
            raise ModConfigError("GON bindings may only target .gon files.")

        contains_subfolder = "/" in normalized

        if contains_subfolder:
            candidate = (root / Path(*normalized.split("/"))).resolve()
            try:
                inside_root = os.path.commonpath((str(root), str(candidate))) == str(root)
            except ValueError:
                inside_root = False
            if not inside_root:
                raise ModConfigError("GON binding escapes the mod folder.")
            if candidate.is_file():
                return candidate

        all_gon = [Path(path) for path in self.discover_gon_files(str(root))]

        if contains_subfolder:
            wanted = normalized.casefold()
            matches = [
                path
                for path in all_gon
                if path.relative_to(root).as_posix().casefold() == wanted
            ]
        else:
            wanted = normalized.casefold()
            matches = [path for path in all_gon if path.name.casefold() == wanted]

        if not matches:
            raise ModConfigError(
                f"Linked GON file {reference!r} was not found anywhere in the mod."
            )
        if len(matches) > 1:
            choices = ", ".join(
                path.relative_to(root).as_posix() for path in matches[:4]
            )
            if len(matches) > 4:
                choices += ", ..."
            raise ModConfigError(
                f"Linked GON filename {reference!r} is ambiguous ({choices}); "
                "use relative subfolder path."
            )
        return matches[0]

    @staticmethod
    def _quote_from_raw(raw_value: str) -> str:
        stripped = raw_value.strip()
        if (
            len(stripped) >= 2
            and stripped[0] == stripped[-1]
            and stripped[0] in ('"', "'")
        ):
            return stripped[0]
        return ""

    @staticmethod
    def _serialize_gon_string(value: str, preferred_quote: str = "") -> str:
        unsafe = (
            not value
            or any(char.isspace() or char in "{}[],:=" for char in value)
            or "#" in value
            or "//" in value
            or "/*" in value
        )
        quote = preferred_quote or ('"' if unsafe else "")
        if not quote:
            return value

        escaped = (
            value.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
            .replace(quote, "\\" + quote)
        )
        return f"{quote}{escaped}{quote}"

    @classmethod
    def _typed_values_equal(cls, option: ModConfigOption, left: Any, right: Any) -> bool:
        try:
            if option.control_type == "bool":
                return cls._coerce_bool(left) == cls._coerce_bool(right)
            if option.control_type == "int":
                return cls._coerce_int(left, option.key) == cls._coerce_int(right, option.key)
            if option.control_type in ("float", "slider"):
                return math.isclose(
                    cls._coerce_float(left, option.key),
                    cls._coerce_float(right, option.key),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            return str(left) == str(right)
        except (ModConfigError, TypeError, ValueError):
            return False

    @classmethod
    def _value_matches_raw(
        cls, option: ModConfigOption, value: Any, raw_value: str
    ) -> bool:
        try:
            if option.control_type == "bool":
                return cls._coerce_bool(value) == cls._coerce_bool(raw_value)
            if option.control_type == "int":
                if not cls._NUMBER_INT_RE.fullmatch(raw_value.strip()):
                    return False
                return cls._coerce_int(value, option.key) == int(raw_value.strip())
            if option.control_type in ("float", "slider"):
                return math.isclose(
                    cls._coerce_float(value, option.key),
                    cls._coerce_float(raw_value, option.key),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            original = cls._parse_typed_value(raw_value, "string")
            return str(value) == str(original)
        except (ModConfigError, TypeError, ValueError):
            return False

    @staticmethod
    def _write_payloads_transactionally(payloads: Dict[Path, bytes]) -> None:
        """Stage every file, then replace targets with rollback"""
        if not payloads:
            return

        temp_paths: Dict[Path, str] = {}
        originals: Dict[Path, Optional[bytes]] = {}
        replaced: List[Path] = []

        try:
            for target, data in payloads.items():
                target = target.resolve()
                originals[target] = target.read_bytes() if target.exists() else None
                fd, temp_path = tempfile.mkstemp(
                    prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
                )
                temp_paths[target] = temp_path
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())

            for target in sorted(temp_paths, key=lambda path: str(path).casefold()):
                os.replace(temp_paths[target], target)
                temp_paths[target] = ""
                replaced.append(target)
        except Exception:
            for target in reversed(replaced):
                original = originals.get(target)
                if original is None:
                    try:
                        target.unlink()
                    except OSError:
                        pass
                    continue
                try:
                    fd, restore_path = tempfile.mkstemp(
                        prefix=f".{target.name}.restore.",
                        suffix=".tmp",
                        dir=str(target.parent),
                    )
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(original)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(restore_path, target)
                except OSError:
                    pass
            raise
        finally:
            for temp_path in temp_paths.values():
                if not temp_path:
                    continue
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _build_option(
        self,
        *,
        section: str,
        key: str,
        raw_value: str,
        source_raw_value: Optional[str] = None,
        control_type: str,
        line_index: int,
        prefix: str,
        suffix: str,
        newline: str,
        tooltip: str,
        metadata: Dict[str, str],
    ) -> ModConfigOption:
        min_value = self._metadata_float(metadata, ("min", "minimum"))
        max_value = self._metadata_float(metadata, ("max", "maximum"))
        step = self._metadata_float(metadata, ("step", "increment"))
        min_length = self._metadata_int(
            metadata,
            ("min_length", "minlength", "min_chars", "minchars"),
        )

        max_length = self._metadata_int(
            metadata,
            ("max_length", "maxlength", "max_chars", "maxchars"),
        )

        enum_values = self._metadata_enum_values(metadata) if control_type == "enum" else []

        if control_type == "string":
            # For strings, min/max are accepted as aliases for
            # character-count bounds when explicit length names were omitted because yeahhh... - Tim
            if min_length is None:
                min_length = self._metadata_int(metadata, ("min", "minimum"))
            if max_length is None:
                max_length = self._metadata_int(metadata, ("max", "maximum"))
            min_value = None
            max_value = None

        if min_value is not None and max_value is not None and min_value > max_value:
            min_value, max_value = max_value, min_value
        if min_length is not None and max_length is not None and min_length > max_length:
            min_length, max_length = max_length, min_length

        bool_true, bool_false = self._bool_literals(raw_value, metadata)
        typed_raw_value = source_raw_value if source_raw_value is not None else raw_value
        value = self._parse_typed_value(typed_raw_value, control_type)
        quote = ""
        stripped_raw = raw_value.strip()

        if (control_type in ("string", "enum") and len(stripped_raw) >= 2 and stripped_raw[0] == stripped_raw[-1] and stripped_raw[0] in ("\"", "'")):
            quote = stripped_raw[0]

        if control_type == "enum":
            current_value = str(value)
            if current_value and current_value not in enum_values:
                # A live ini/GON value may come before declared option list. Keep
                # it visible/selectable instead of opening a blank combobox... - Tim
                enum_values.insert(0, current_value)
            min_value = None
            max_value = None
            step = None

        if control_type == "slider":
            numeric_value = float(value) if isinstance(value, (int, float)) else 0.0

            if min_value is None:
                min_value = min(0.0, numeric_value, max_value if max_value is not None else 0.0)
            if max_value is None:
                max_value = max(1.0, numeric_value, min_value)
            if min_value > max_value:
                min_value, max_value = max_value, min_value
            if step is None:
                declared_type = (metadata.get("type") or "").strip().lower().replace("_", "-")
                if declared_type == "slider-float":
                    step = 0.01
                elif declared_type == "slider-int":
                    step = 1.0
                else:
                    step = 1.0 if self._NUMBER_INT_RE.fullmatch(typed_raw_value.strip()) else 0.01
            if step <= 0:
                step = 1.0

        option = ModConfigOption(
            section=section,
            key=key,
            raw_value=raw_value,
            value=value,
            control_type=control_type,
            line_index=line_index,
            prefix=prefix,
            suffix=suffix,
            newline=newline,
            tooltip=tooltip,
            label=metadata.get("label", "").strip(),
            min_value=min_value,
            max_value=max_value,
            step=step,
            min_length=min_length,
            max_length=max_length,
            enum_values=enum_values,
            bool_true=bool_true,
            bool_false=bool_false,
            quote=quote,
            metadata=metadata,
        )

        default_raw = self._metadata_first(
            metadata, ("default", "default_value", "defaultvalue")
        )

        if default_raw is not None:
            try:
                option.default_value = self._normalize_default_value(option, default_raw)
                option.has_default = True
            except ModConfigError as exc:
                option.default_error = str(exc)
                error_text = f"Default value error: {exc}"
                option.tooltip = (
                    f"{option.tooltip}\n\n{error_text}"
                    if option.tooltip
                    else error_text
                )

        return option

    @staticmethod
    def _metadata_first(metadata: Dict[str, str], keys: Iterable[str]) -> Optional[str]:
        for key in keys:
            if key in metadata:
                return metadata[key]
        return None

    def _normalize_default_value(self, option: ModConfigOption, raw_default: str) -> Any:
        """Parse and validate explicit per-option default value
        """
        kind = option.control_type

        if kind == "bool":
            return self._coerce_bool(raw_default)

        if kind == "int":
            value = self._coerce_int(raw_default, option.key)
            self._validate_numeric_bounds(option, float(value))
            return value

        if kind in ("float", "slider"):
            value = self._coerce_float(raw_default, option.key)
            self._validate_numeric_bounds(option, value)
            if kind == "slider" and option.step:
                value = self._snap_to_step(value, option)
                self._validate_numeric_bounds(option, value)
            return value

        value = str(raw_default)
        if kind == "enum" and option.enum_values and value not in option.enum_values:
            allowed = ", ".join(option.enum_values)
            raise ModConfigError(f"{option.key} default must be one of: {allowed}.")

        length = len(value)

        if option.min_length is not None and length < option.min_length:
            raise ModConfigError(
                f"{option.key} default must contain at least {option.min_length} characters."
            )
        if option.max_length is not None and length > option.max_length:
            raise ModConfigError(
                f"{option.key} default must contain no more than {option.max_length} characters."
            )
        return value

    def _resolve_control_type(self, key: str, raw_value: str, metadata: Dict[str, str]) -> str:
        declared = (
            metadata.get("type")
            or metadata.get("control")
            or metadata.get("kind")
            or ""
        ).strip().lower().replace("_", "-")

        aliases = {
            "boolean": "bool",
            "toggle": "bool",
            "checkbox": "bool",
            "integer": "int",
            "number": "float",
            "double": "float",
            "decimal": "float",
            "text": "string",
            "input": "string",
            "dropdown": "enum",
            "select": "enum",
            "choice": "enum",
            "choices": "enum",
            "range": "slider",
            "slider-int": "slider",
            "slider-float": "slider",
        }

        declared = aliases.get(declared, declared)

        if declared in {"bool", "string", "int", "float", "slider", "enum"}:
            return declared

        value = raw_value.strip()
        lower = value.lower()

        if lower in self._BOOL_WORDS:
            return "bool"
        if value in {"0", "1"} and self._looks_boolish_key(key):
            return "bool"
        if self._NUMBER_INT_RE.fullmatch(value):
            return "int"
        if self._NUMBER_FLOAT_RE.fullmatch(value) and ("." in value or "e" in lower):
            return "float"
        return "string"

    def _parse_typed_value(self, raw_value: str, control_type: str) -> Any:
        value = raw_value.strip()

        if control_type == "bool":
            try:
                return self._coerce_bool(value)
            except ModConfigError:
                return False
        if control_type == "int":
            try:
                return int(value)
            except ValueError:
                return 0
        if control_type in ("float", "slider"):
            try:
                return float(value)
            except ValueError:
                return 0.0
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
            return value[1:-1]
        return value

    def _bool_literals(self, raw_value: str, metadata: Dict[str, str]) -> Tuple[str, str]:
        explicit_true = metadata.get("true") or metadata.get("true_value")
        explicit_false = metadata.get("false") or metadata.get("false_value")

        if explicit_true is not None or explicit_false is not None:
            return explicit_true or "1", explicit_false or "0"

        value = raw_value.strip()
        lower = value.lower()

        pairs = {
            "true": ("true", "false"),
            "false": ("true", "false"),
            "yes": ("yes", "no"),
            "no": ("yes", "no"),
            "on": ("on", "off"),
            "off": ("on", "off"),
            "1": ("1", "0"),
            "0": ("1", "0"),
        }

        true_literal, false_literal = pairs.get(lower, ("1", "0"))

        if value.isupper():
            true_literal = true_literal.upper()
            false_literal = false_literal.upper()
        elif value[:1].isupper():
            true_literal = true_literal.capitalize()
            false_literal = false_literal.capitalize()
        return true_literal, false_literal

    def _strip_inline_metadata(self, comment: str) -> Tuple[str, Dict[str, str]]:
        marker_match = re.search(r"(?i)(?:^|\s)@mewtator\b", comment)

        if not marker_match:
            return comment.strip(), {}

        tooltip = comment[: marker_match.start()].rstrip(" |\t")
        directive = comment[marker_match.end() :].strip()

        if directive.startswith(":"):
            directive = directive[1:].strip()
        return tooltip.strip(), self._parse_metadata(directive)

    def _extract_option_directive(self, comment_body: str) -> Optional[str]:
        # Longer file-level marker has to be checked first so it never gets
        # misread as option directive due to shared prefix... - Tim
        if re.search(r"(?i)@mewtator-config\b", comment_body):
            return None
        return self._extract_directive(comment_body, self.OPTION_DIRECTIVE)

    @staticmethod
    def _extract_directive(comment_body: str, marker: str) -> Optional[str]:
        match = re.search(re.escape(marker) + r"\b", comment_body, re.IGNORECASE)
        if not match:
            return None
        value = comment_body[match.end() :].strip()
        if value.startswith(":"):
            value = value[1:].strip()
        return value

    @staticmethod
    def _parse_metadata(text: str) -> Dict[str, str]:
        metadata: Dict[str, str] = {}
        if not text:
            return metadata

        normalized = text
        try:
            tokens = shlex.split(normalized, comments=False, posix=True)
        except ValueError:
            tokens = normalized.split()

        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                metadata[key.strip().lower().replace("-", "_")] = value.strip()
            elif token:
                # Bare flags are treated as true, so primary is shorthand for primary=true...
                metadata[token.strip().lower().replace("-", "_")] = "true"
        return metadata

    @staticmethod
    def _metadata_enum_values(metadata: Dict[str, str]) -> List[str]:
        raw = (
            metadata.get("options")
            or metadata.get("choices")
            or metadata.get("values")
            or metadata.get("enum_values")
            or ""
        ).strip()
        if not raw:
            return []

        # Pipe is preferred separator because... commas commonly appear in
        # human-readable labels... duhh... comma remains accepted for simple lists... - Tim
        separator = "|" if "|" in raw else ","
        values: List[str] = []

        for item in raw.split(separator):
            value = item.strip()
            if value and value not in values:
                values.append(value)
        return values

    @staticmethod
    def _whole_line_comment_body(content: str) -> Optional[str]:
        stripped = content.lstrip()

        if stripped.startswith(";") or stripped.startswith("#"):
            return stripped[1:].strip()
        return None

    @staticmethod
    def _split_value_and_comment(remainder: str) -> Tuple[str, str, str]:
        # ini syntax does not universally make ;/# inline comments, so we
        # only treat marker as commentary when whitespace precedes it 
        # and the marker is outside a quoted value! - Tim
        quote = None
        escaped = False

        for index, char in enumerate(remainder):
            if escaped:
                escaped = False
                continue
            if char == "\\" and quote is not None:
                escaped = True
                continue
            if char in ("\"", "'"):
                if quote is None:
                    quote = char
                elif quote == char:
                    quote = None
                continue
            if quote is None and char in (";", "#") and index > 0 and remainder[index - 1].isspace():
                whitespace_start = index - 1

                while whitespace_start > 0 and remainder[whitespace_start - 1].isspace():
                    whitespace_start -= 1
                return (
                    remainder[:whitespace_start],
                    remainder[whitespace_start:],
                    remainder[index + 1 :],
                )

        # Preserve trailing whitespace even when no inline comment exists... - Tim
        stripped = remainder.rstrip()
        return stripped, remainder[len(stripped):], ""

    @staticmethod
    def _split_newline(line: str) -> Tuple[str, str]:
        if line.endswith("\r\n"):
            return line[:-2], "\r\n"
        if line.endswith("\n") or line.endswith("\r"):
            return line[:-1], line[-1]
        return line, ""

    @staticmethod
    def _decode(raw_bytes: bytes) -> Tuple[str, str, bool]:
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            return raw_bytes[3:].decode("utf-8"), "utf-8", True
        try:
            return raw_bytes.decode("utf-8"), "utf-8", False
        except UnicodeDecodeError:
            return raw_bytes.decode("cp1252"), "cp1252", False

    @staticmethod
    def _encode(text: str, encoding: str, has_bom: bool) -> bytes:
        raw = text.encode(encoding)
        if has_bom and encoding.lower().replace("_", "-") == "utf-8":
            return b"\xef\xbb\xbf" + raw
        return raw

    @staticmethod
    def _metadata_bool(
        metadata: Dict[str, str], keys: Iterable[str], default: bool
    ) -> bool:
        for key in keys:
            if key in metadata:
                return ModConfigService._coerce_bool(metadata[key])
        return default

    @staticmethod
    def _metadata_float(metadata: Dict[str, str], keys: Iterable[str]) -> Optional[float]:
        for key in keys:
            value = metadata.get(key)
            if value is None:
                continue
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return None
            return parsed if math.isfinite(parsed) else None
        return None

    @staticmethod
    def _metadata_int(metadata: Dict[str, str], keys: Iterable[str]) -> Optional[int]:
        for key in keys:
            value = metadata.get(key)
            if value is None:
                continue
            try:
                return max(0, int(value))
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled", ""}:
            return False
        raise ModConfigError(f"Invalid boolean value: {value}")

    @staticmethod
    def _coerce_int(value: Any, key: str) -> int:
        text = str(value).strip()
        if not ModConfigService._NUMBER_INT_RE.fullmatch(text):
            raise ModConfigError(f"{key} must be a whole number.")
        return int(text)

    @staticmethod
    def _coerce_float(value: Any, key: str) -> float:
        try:
            numeric = float(str(value).strip())
        except ValueError as exc:
            raise ModConfigError(f"{key} must be a number.") from exc
        if not math.isfinite(numeric):
            raise ModConfigError(f"{key} must be a finite number.")
        return numeric

    @staticmethod
    def _validate_numeric_bounds(option: ModConfigOption, value: float) -> None:
        if option.min_value is not None and value < option.min_value:
            raise ModConfigError(f"{option.key} must be at least {ModConfigService._format_float(option.min_value)}.")
        if option.max_value is not None and value > option.max_value:
            raise ModConfigError(f"{option.key} must be at most {ModConfigService._format_float(option.max_value)}.")

    @staticmethod
    def _snap_to_step(value: float, option: ModConfigOption) -> float:
        step = option.step or 1.0
        origin = option.min_value if option.min_value is not None else 0.0
        snapped = origin + round((value - origin) / step) * step
        return round(snapped, 12)

    @staticmethod
    def _is_integral_step(step: Optional[float]) -> bool:
        return step is not None and abs(step - round(step)) < 1e-12

    @staticmethod
    def _format_float(value: float) -> str:
        if abs(value) < 1e-15:
            value = 0.0
        return format(value, ".12g")

    @classmethod
    def _looks_boolish_key(cls, key: str) -> bool:
        normalized = re.sub(r"(?<!^)(?=[A-Z])", "_", key).replace("-", "_")
        return bool(cls._BOOLISH_KEY_RE.search(normalized))
