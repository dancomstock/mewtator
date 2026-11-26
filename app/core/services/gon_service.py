from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Tuple

class GonError(ValueError):
    pass

@dataclass
class GonToken:
    kind: str
    raw: str
    value: str
    start: int
    end: int

@dataclass
class GonNode:
    kind: str
    start: int
    end: int
    raw: str = ""
    value: str = ""
    entries: List[Tuple[str, "GonNode"]] = field(default_factory=list)
    items: List["GonNode"] = field(default_factory=list)

@dataclass
class GonScalar:
    raw: str
    value: str
    start: int
    end: int

@dataclass
class GonDocument:
    path: str
    text: str
    encoding: str
    has_bom: bool
    root: GonNode

    def encode(self, text: str) -> bytes:
        raw = text.encode(self.encoding)
        if self.has_bom and self.encoding.lower().replace("_", "-") == "utf-8":
            return b"\xef\xbb\xbf" + raw
        return raw

@dataclass(frozen=True)
class _PathStep:
    key: str
    occurrence: int = 1
    indexes: Tuple[int, ...] = ()
    explicit_occurrence: bool = False

class GonService:
    """Small source-preserving GON reader for mod-setting bindings!
    GON is pretty damn permissive!
    """

    _IGNORED_SYMBOLS = {",", "=", ":"}
    _STRUCTURAL_SYMBOLS = {"{", "}", "[", "]"}
    _ALL_SYMBOLS = _IGNORED_SYMBOLS | _STRUCTURAL_SYMBOLS

    def load(self, path: str) -> GonDocument:
        raw_bytes = Path(path).read_bytes()
        text, encoding, has_bom = self._decode(raw_bytes)

        tokens = self._tokenize(text)
        root, index = self._parse_object(tokens, 0, braced=False)

        index = self._skip_ignored(tokens, index)

        if index != len(tokens):
            token = tokens[index]

            raise GonError(
                f"Unexpected GON token {token.raw!r} at character {token.start}."
            )

        root.end = len(text)

        return GonDocument(
            path=path,
            text=text,
            encoding=encoding,
            has_bom=has_bom,
            root=root,
        )

    def resolve_scalar(self, document: GonDocument, object_path: str) -> GonScalar:
        steps = self._parse_path(object_path)

        if not steps:
            raise GonError("GON path cannot be empty.")

        node = document.root
        traversed: List[str] = []

        for step in steps:
            if node.kind != "object":
                prefix = ".".join(traversed) or "<root>"

                raise GonError(
                    f"GON path {object_path!r} expected an object at {prefix}."
                )

            matches = [value for key, value in node.entries if key == step.key]

            if not matches:
                prefix = ".".join(traversed) or "<root>"

                raise GonError(
                    f"GON key {step.key!r} was not found under {prefix}."
                )

            if step.occurrence > len(matches):
                raise GonError(
                    f"GON key {step.key!r} only occurs {len(matches)} time(s), "
                    f"#{step.occurrence} was requested."
                )

            if len(matches) > 1 and not step.explicit_occurrence:
                raise GonError(
                    f"GON key {step.key!r} occurs {len(matches)} times at this level, "
                    f"use {step.key}#1, {step.key}#2, etc. to choose one."
                )

            node = matches[step.occurrence - 1]
            traversed.append(step.key)

            for array_index in step.indexes:
                if node.kind != "array":
                    prefix = ".".join(traversed)

                    raise GonError(
                        f"GON path {object_path!r} expected an array at {prefix}."
                    )

                if array_index < 0 or array_index >= len(node.items):
                    raise GonError(
                        f"GON array index {array_index} is out of range at "
                        f"{'.'.join(traversed)} (size {len(node.items)})."
                    )

                node = node.items[array_index]
                traversed[-1] += f"[{array_index}]"

        if node.kind != "scalar":
            raise GonError(
                f"GON path {object_path!r} resolves to a {node.kind}, not a scalar value."
            )
        
        return GonScalar(raw=node.raw, value=node.value, start=node.start, end=node.end)

    def replace_scalars(self, document: GonDocument, replacements: Sequence[Tuple[int, int, str]],) -> str:
        if not replacements:
            return document.text

        normalized = sorted(replacements, key=lambda item: (item[0], item[1]))
        previous_end = -1

        for start, end, _ in normalized:
            if start < 0 or end < start or end > len(document.text):
                raise GonError("Invalid GON replacement span.")
            if start < previous_end:
                raise GonError("Two mod settings target overlapping GON values.")
            previous_end = end

        text = document.text

        for start, end, replacement in reversed(normalized):
            text = text[:start] + replacement + text[end:]
        return text

    def _tokenize(self, text: str) -> List[GonToken]:
        tokens: List[GonToken] = []
        length = len(text)
        index = 0

        while index < length:
            char = text[index]

            if char.isspace():
                index += 1
                continue

            if text.startswith("//", index):
                newline = text.find("\n", index + 2)
                index = length if newline < 0 else newline + 1
                continue

            if text.startswith("/*", index):
                close = text.find("*/", index + 2)

                if close < 0:
                    raise GonError("Unterminated /* */ comment in GON file.")
                index = close + 2
                continue

            # Mewgenics data can use # for comments, (believe it or not) and #include-like directives...
            # neither will contribute a key/value to the file's object tree... - Tim
            if char == "#":
                newline = text.find("\n", index + 1)
                index = length if newline < 0 else newline + 1
                continue

            if char in self._ALL_SYMBOLS:
                tokens.append(GonToken("symbol", char, char, index, index + 1))
                index += 1
                continue

            if char in ('"', "'"):
                quote = char
                start = index
                index += 1
                value_chars: List[str] = []

                while index < length:
                    current = text[index]

                    if current == "\\" and index + 1 < length:
                        # Preserve escapes semantically while keeping the original
                        # raw token available for lossless rewrites... - Tim
                        escaped = text[index + 1]

                        escape_map = {
                            "n": "\n",
                            "r": "\r",
                            "t": "\t",
                            "\\": "\\",
                            '"': '"',
                            "'": "'",
                        }

                        value_chars.append(escape_map.get(escaped, escaped))
                        index += 2
                        continue

                    if current == quote:
                        index += 1
                        raw = text[start:index]
                        tokens.append(
                            GonToken("scalar", raw, "".join(value_chars), start, index)
                        )
                        break

                    value_chars.append(current)
                    index += 1
                else:
                    raise GonError(f"Unterminated quoted GON string at character {start}.")
                continue

            start = index

            while index < length:
                current = text[index]

                if current.isspace() or current in self._ALL_SYMBOLS:
                    break

                if text.startswith("//", index) or text.startswith("/*", index):
                    break

                # A # begins a GON comment/directive outside quotes. Treat as
                # part of token only when not first character and is
                # escaped, normal data containing # should be quoted... - Tim
                if current == "#":
                    break
                index += 1

            if index == start:
                # (Defensive progress for a character that is neither a known
                # symbol nor valid token content)... - Tim
                index += 1
                continue

            raw = text[start:index]
            tokens.append(GonToken("scalar", raw, raw, start, index))

        return tokens

    def _parse_value(self, tokens: Sequence[GonToken], index: int) -> Tuple[GonNode, int]:
        index = self._skip_ignored(tokens, index)

        if index >= len(tokens):
            raise GonError("Expected a GON value but reached the end of the file.")

        token = tokens[index]

        if token.kind == "scalar":
            return (
                GonNode(
                    kind="scalar",
                    start=token.start,
                    end=token.end,
                    raw=token.raw,
                    value=token.value,
                ),
                index + 1,
            )

        if token.raw == "{":
            return self._parse_object(tokens, index, braced=True)

        if token.raw == "[":
            return self._parse_array(tokens, index)

        raise GonError(
            f"Expected a GON value at character {token.start}, found {token.raw!r}."
        )

    def _parse_object(self, tokens: Sequence[GonToken], index: int, *, braced: bool,) -> Tuple[GonNode, int]:
        start = 0

        if braced:
            if index >= len(tokens) or tokens[index].raw != "{":
                raise GonError("Internal GON parser error: expected '{'.")
            start = tokens[index].start
            index += 1
        elif tokens:
            start = tokens[0].start

        entries: List[Tuple[str, GonNode]] = []

        while True:
            index = self._skip_ignored(tokens, index)

            if index >= len(tokens):
                if braced:
                    raise GonError("Unterminated GON object, missing '}'.")
                end = tokens[-1].end if tokens else 0
                return GonNode("object", start, end, entries=entries), index

            token = tokens[index]

            if token.raw == "}":
                if not braced:
                    raise GonError(f"Unexpected '}}' at character {token.start}.")
                return (
                    GonNode("object", start, token.end, entries=entries),
                    index + 1,
                )

            if token.raw == "]":
                raise GonError(f"Unexpected ']' at character {token.start}.")

            if token.kind != "scalar":
                # Some GON files contain permissive extra values. They are irrelevant to key-path lookup... - Tim
                _, index = self._parse_value(tokens, index)
                continue

            key = token.value
            index += 1
            value, index = self._parse_value(tokens, index)
            entries.append((key, value))

    def _parse_array(self, tokens: Sequence[GonToken], index: int,) -> Tuple[GonNode, int]:
        if index >= len(tokens) or tokens[index].raw != "[":
            raise GonError("Internal GON parser error: expected '['.")
        start = tokens[index].start
        index += 1

        items: List[GonNode] = []

        while True:
            index = self._skip_ignored(tokens, index)

            if index >= len(tokens):
                raise GonError("Unterminated GON array, missing ']'.")

            token = tokens[index]

            if token.raw == "]":
                return GonNode("array", start, token.end, items=items), index + 1

            if token.raw == "}":
                raise GonError(f"Unexpected '}}' at character {token.start} inside array.")

            value, index = self._parse_value(tokens, index)
            items.append(value)

    def _skip_ignored(self, tokens: Sequence[GonToken], index: int) -> int:
        while (index < len(tokens) and tokens[index].kind == "symbol" and tokens[index].raw in self._IGNORED_SYMBOLS):
            index += 1
        return index

    def _parse_path(self, path: str) -> List[_PathStep]:
        raw_segments = self._split_escaped(path.strip(), ".")

        if not raw_segments or any(segment == "" for segment in raw_segments):
            raise GonError(f"Invalid GON path {path!r}.")

        steps: List[_PathStep] = []

        for raw_segment in raw_segments:
            segment = raw_segment
            indexes_reversed: List[int] = []

            while segment.endswith("]"):
                open_index = self._find_unescaped_open_bracket(segment)

                if open_index < 0:
                    break

                index_text = segment[open_index + 1 : -1]

                if not index_text.isdigit():
                    raise GonError(
                        f"Invalid array index [{index_text}] in GON path {path!r}."
                    )
                
                indexes_reversed.append(int(index_text))
                segment = segment[:open_index]

            occurrence = 1
            explicit_occurrence = False
            hash_index = self._find_unescaped_occurrence(segment)

            if hash_index >= 0:
                explicit_occurrence = True
                occurrence_text = segment[hash_index + 1 :]

                if not occurrence_text.isdigit() or int(occurrence_text) < 1:
                    raise GonError(
                        f"Invalid duplicate selector #{occurrence_text} in GON path {path!r}."
                    )
                occurrence = int(occurrence_text)
                segment = segment[:hash_index]

            key = self._unescape_path_component(segment)

            if not key:
                raise GonError(f"Invalid empty key in GON path {path!r}.")

            steps.append(
                _PathStep(
                    key=key,
                    occurrence=occurrence,
                    indexes=tuple(reversed(indexes_reversed)),
                    explicit_occurrence=explicit_occurrence,
                )
            )

        return steps

    @staticmethod
    def _split_escaped(text: str, separator: str) -> List[str]:
        parts: List[str] = []
        current: List[str] = []
        escaped = False

        for char in text:
            if escaped:
                current.append("\\" + char)
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == separator:
                parts.append("".join(current))
                current = []
            else:
                current.append(char)
        if escaped:
            current.append("\\")
        parts.append("".join(current))
        return parts

    @staticmethod
    def _find_unescaped_open_bracket(segment: str) -> int:
        escaped = False
        last = -1

        for index, char in enumerate(segment[:-1]):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == "[":
                last = index
        return last

    @staticmethod
    def _find_unescaped_occurrence(segment: str) -> int:
        escaped = False
        last = -1
        for index, char in enumerate(segment):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == "#":
                last = index
        return last

    @staticmethod
    def _unescape_path_component(value: str) -> str:
        result: List[str] = []
        escaped = False
        for char in value:
            if escaped:
                result.append(char)
                escaped = False
            elif char == "\\":
                escaped = True
            else:
                result.append(char)
        if escaped:
            result.append("\\")
        return "".join(result)

    @staticmethod
    def _decode(raw_bytes: bytes) -> Tuple[str, str, bool]:
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            return raw_bytes[3:].decode("utf-8"), "utf-8", True
        try:
            return raw_bytes.decode("utf-8"), "utf-8", False
        except UnicodeDecodeError:
            return raw_bytes.decode("cp1252"), "cp1252", False