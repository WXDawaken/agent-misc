from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any


class PromptKitError(Exception):
    """Raised when prompt parsing, rendering, or validation fails."""


@dataclasses.dataclass(frozen=True)
class PromptDocument:
    path: Path
    metadata: dict[str, Any]
    body: str
    raw_text: str


@dataclasses.dataclass(frozen=True)
class LintMessage:
    level: str
    message: str


@dataclasses.dataclass(frozen=True)
class TextNode:
    text: str


@dataclasses.dataclass(frozen=True)
class VarNode:
    name: str


@dataclasses.dataclass(frozen=True)
class SectionNode:
    name: str
    inverted: bool
    children: list["TemplateNode"]


@dataclasses.dataclass(frozen=True)
class PartialNode:
    name: str


@dataclasses.dataclass(frozen=True)
class VariantNode:
    name: str
    children: list["TemplateNode"]


TemplateNode = TextNode | VarNode | SectionNode | PartialNode | VariantNode
_FRONT_MATTER_RE = re.compile(r"\A---\r?\n(?P<meta>.*?)\r?\n---\r?\n?", re.DOTALL)
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_SUPPORTED_ENGINES = {"mini-mustache", "mustache", "text"}


def load_prompt_document(path: str | Path) -> PromptDocument:
    prompt_path = Path(path)
    raw_text = prompt_path.read_text(encoding="utf-8")
    metadata, body = parse_prompt_text(raw_text)
    return PromptDocument(path=prompt_path, metadata=metadata, body=body, raw_text=raw_text)


def parse_prompt_text(raw_text: str) -> tuple[dict[str, Any], str]:
    match = _FRONT_MATTER_RE.match(raw_text)
    if not match:
        return {}, raw_text
    metadata = _parse_front_matter(match.group("meta"))
    return metadata, raw_text[match.end() :]


def _parse_front_matter(block: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    current_map: dict[str, Any] | None = None
    current_key: str | None = None

    for line_number, raw_line in enumerate(block.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 0:
            key, value = _split_front_matter_pair(raw_line, line_number)
            current_key = key
            if value == "":
                current_map = {}
                metadata[key] = current_map
            else:
                current_map = None
                metadata[key] = _parse_scalar(value)
            continue
        if current_map is None or current_key is None:
            raise PromptKitError(f"Unsupported front matter indentation on line {line_number}.")
        key, value = _split_front_matter_pair(raw_line.strip(), line_number)
        current_map[key] = _parse_scalar(value)
    return metadata


def _split_front_matter_pair(line: str, line_number: int) -> tuple[str, str]:
    if ":" not in line:
        raise PromptKitError(f"Expected `key: value` in front matter line {line_number}.")
    key, value = line.split(":", 1)
    key = key.strip()
    if not key:
        raise PromptKitError(f"Empty front matter key on line {line_number}.")
    return key, value.strip()


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def load_vars_file(path: str | Path) -> dict[str, Any]:
    vars_path = Path(path)
    suffix = vars_path.suffix.lower()
    raw_text = vars_path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(raw_text)
    elif suffix == ".toml":
        data = tomllib.loads(raw_text)
    else:
        raise PromptKitError(f"Unsupported vars file type `{suffix}`. Use .json or .toml.")
    if not isinstance(data, dict):
        raise PromptKitError("Vars file must contain an object at the top level.")
    return data


def render_prompt_document(
    document: PromptDocument,
    variables: dict[str, Any] | None = None,
    *,
    strict: bool = True,
    variant: str | None = None,
) -> tuple[str, list[str]]:
    variables = variables or {}
    engine = str(document.metadata.get("engine", "mini-mustache"))
    if engine not in _SUPPORTED_ENGINES:
        raise PromptKitError(f"Unsupported prompt engine `{engine}`.")
    if engine == "text":
        return document.body, []

    nodes = _parse_template(document.body)
    missing: set[str] = set()
    rendered = _render_nodes(
        nodes,
        [variables],
        missing,
        document=document,
        selected_variant=_selected_variant(document, variables, variant),
        partial_stack=[document.path.resolve()],
    )
    if strict and missing:
        names = ", ".join(sorted(missing))
        raise PromptKitError(f"Missing prompt variable(s): {names}")
    warnings = [f"Missing prompt variable: {name}" for name in sorted(missing)]
    return rendered, warnings


def lint_prompt_document(
    document: PromptDocument,
    variables: dict[str, Any] | None = None,
    *,
    render: bool = True,
    variant: str | None = None,
) -> list[LintMessage]:
    variables = variables or {}
    messages: list[LintMessage] = []
    engine = str(document.metadata.get("engine", "mini-mustache"))
    if engine not in _SUPPORTED_ENGINES:
        messages.append(LintMessage("error", f"Unsupported prompt engine `{engine}`."))
        return messages
    if "id" not in document.metadata:
        messages.append(LintMessage("warning", "Prompt front matter has no `id`."))
    inputs = document.metadata.get("inputs", {})
    if inputs and not isinstance(inputs, dict):
        messages.append(LintMessage("error", "`inputs` front matter must be a mapping."))
        inputs = {}
    if engine != "text":
        try:
            nodes = _parse_template(document.body)
        except PromptKitError as exc:
            messages.append(LintMessage("error", str(exc)))
            return messages
        try:
            _collect_partial_documents(document, nodes, {}, [document.path.resolve()])
        except PromptKitError as exc:
            messages.append(LintMessage("error", str(exc)))
            return messages
        declared_inputs = set(inputs)
        available_inputs = set(variables)
        for name in sorted(_required_top_level_inputs(nodes, document=document)):
            if name not in declared_inputs and name not in available_inputs:
                messages.append(
                    LintMessage(
                        "warning",
                        f"`{name}` is used by the template but is not declared in front matter inputs.",
                    )
                )
    for name, type_name in sorted(inputs.items()):
        if name not in variables:
            if variables:
                messages.append(LintMessage("error", f"Input `{name}` is declared but not provided."))
            continue
        type_error = _check_type(name, variables[name], str(type_name))
        if type_error:
            messages.append(LintMessage("error", type_error))
    if render and variables:
        try:
            render_prompt_document(document, variables, strict=True, variant=variant)
        except PromptKitError as exc:
            messages.append(LintMessage("error", str(exc)))
    return messages


def snapshot_prompt_document(
    document: PromptDocument,
    variables: dict[str, Any],
    out_dir: str | Path,
    *,
    strict: bool = True,
    variant: str | None = None,
) -> Path:
    selected_variant = _selected_variant(document, variables, variant)
    rendered, warnings = render_prompt_document(document, variables, strict=strict, variant=selected_variant)
    prompt_id = str(document.metadata.get("id") or document.path.stem)
    timestamp = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = Path(out_dir) / _safe_id(prompt_id) / timestamp
    suffix = 1
    while snapshot_dir.exists():
        snapshot_dir = Path(out_dir) / _safe_id(prompt_id) / f"{timestamp}_{suffix}"
        suffix += 1
    snapshot_dir.mkdir(parents=True)

    rendered_path = snapshot_dir / "rendered.md"
    vars_path = snapshot_dir / "vars.json"
    manifest_path = snapshot_dir / "manifest.json"
    rendered_path.write_text(rendered, encoding="utf-8")
    vars_text = json.dumps(variables, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    vars_path.write_text(vars_text, encoding="utf-8")
    manifest = {
        "prompt_path": str(document.path),
        "prompt_id": prompt_id,
        "engine": document.metadata.get("engine", "mini-mustache"),
        "created_at_utc": timestamp,
        "prompt_sha256": _sha256_text(document.raw_text),
        "rendered_sha256": _sha256_text(rendered),
        "vars_sha256": _sha256_text(vars_text),
        "variant": selected_variant,
        "warnings": warnings,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot_dir


def compile_prompt_document(document: PromptDocument, *, include_partials: bool = True) -> dict[str, Any]:
    engine = str(document.metadata.get("engine", "mini-mustache"))
    if engine not in _SUPPORTED_ENGINES:
        raise PromptKitError(f"Unsupported prompt engine `{engine}`.")
    nodes = [] if engine == "text" else _parse_template(document.body)
    partials: dict[str, Any] = {}
    if include_partials and engine != "text":
        _collect_partial_documents(document, nodes, partials, [document.path.resolve()])
    return {
        "schema": "promptkit.ir.v1",
        "prompt_path": str(document.path),
        "prompt_id": document.metadata.get("id") or document.path.stem,
        "engine": engine,
        "metadata": document.metadata,
        "body_sha256": _sha256_text(document.body),
        "nodes": _serialize_nodes(nodes),
        "partials": partials,
    }


def _parse_template(template: str) -> list[TemplateNode]:
    nodes, position, close_name = _parse_nodes(template, 0, None)
    if close_name is not None:
        raise PromptKitError(f"Unexpected closing section `{{{{/{close_name}}}}}`.")
    if position != len(template):
        raise PromptKitError("Template parser stopped before the end of the document.")
    return nodes


def _parse_nodes(
    template: str,
    position: int,
    stop_name: str | None,
) -> tuple[list[TemplateNode], int, str | None]:
    nodes: list[TemplateNode] = []
    while position < len(template):
        start = template.find("{{", position)
        if start < 0:
            nodes.append(TextNode(template[position:]))
            return nodes, len(template), None
        if start > position:
            nodes.append(TextNode(template[position:start]))

        if template.startswith("{{!--", start):
            end_comment = template.find("--}}", start + 5)
            if end_comment < 0:
                raise PromptKitError("Unclosed mustache block comment.")
            position = end_comment + 4
            continue

        end = template.find("}}", start + 2)
        if end < 0:
            raise PromptKitError("Unclosed mustache tag.")
        token = template[start + 2 : end].strip()
        position = end + 2
        if not token:
            nodes.append(TextNode(template[start:position]))
            continue
        if token.startswith("!"):
            continue

        marker = token[0]
        if marker in {"#", "^"}:
            name = token[1:].strip()
            if not name:
                raise PromptKitError("Section tag is missing a name.")
            variant_name = _parse_variant_name(name) if marker == "#" else None
            if variant_name is not None:
                children, position, close_name = _parse_nodes(template, position, "variant")
                if close_name != "variant":
                    raise PromptKitError(
                        f"Variant `{{{{#variant {variant_name}}}}}` is missing closing tag `{{{{/variant}}}}`."
                    )
                nodes.append(VariantNode(name=variant_name, children=children))
                continue
            children, position, close_name = _parse_nodes(template, position, name)
            if close_name != name:
                raise PromptKitError(f"Section `{{{{#{name}}}}}` is missing closing tag `{{{{/{name}}}}}`.")
            nodes.append(SectionNode(name=name, inverted=marker == "^", children=children))
            continue
        if marker == ">":
            name = token[1:].strip()
            if not name:
                raise PromptKitError("Partial tag is missing a name.")
            nodes.append(PartialNode(name=name))
            continue
        if marker == "/":
            name = token[1:].strip()
            if stop_name is None:
                return nodes, position, name
            if name != stop_name:
                raise PromptKitError(f"Expected closing section `{{{{/{stop_name}}}}}`, got `{{{{/{name}}}}}`.")
            return nodes, position, name
        nodes.append(VarNode(token))
    if stop_name is not None:
        raise PromptKitError(f"Section `{{{{#{stop_name}}}}}` is missing closing tag `{{{{/{stop_name}}}}}`.")
    return nodes, position, None


def _render_nodes(
    nodes: list[TemplateNode],
    contexts: list[Any],
    missing: set[str],
    *,
    document: PromptDocument,
    selected_variant: str | None,
    partial_stack: list[Path],
) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, TextNode):
            parts.append(node.text)
        elif isinstance(node, VarNode):
            found, value = _resolve(contexts, node.name)
            if not found:
                missing.add(node.name)
                continue
            parts.append(_stringify(value))
        elif isinstance(node, SectionNode):
            found, value = _resolve(contexts, node.name)
            truthy = found and _is_truthy(value)
            if node.inverted:
                if not truthy:
                    parts.append(
                        _render_nodes(
                            node.children,
                            contexts,
                            missing,
                            document=document,
                            selected_variant=selected_variant,
                            partial_stack=partial_stack,
                        )
                    )
                continue
            if not truthy:
                continue
            if isinstance(value, list):
                for item in value:
                    parts.append(
                        _render_nodes(
                            node.children,
                            contexts + [item],
                            missing,
                            document=document,
                            selected_variant=selected_variant,
                            partial_stack=partial_stack,
                        )
                    )
            elif isinstance(value, dict):
                parts.append(
                    _render_nodes(
                        node.children,
                        contexts + [value],
                        missing,
                        document=document,
                        selected_variant=selected_variant,
                        partial_stack=partial_stack,
                    )
                )
            else:
                parts.append(
                    _render_nodes(
                        node.children,
                        contexts,
                        missing,
                        document=document,
                        selected_variant=selected_variant,
                        partial_stack=partial_stack,
                    )
                )
        elif isinstance(node, PartialNode):
            partial_document = _load_partial_document(document, node.name, partial_stack)
            partial_nodes = _parse_template(partial_document.body)
            parts.append(
                _render_nodes(
                    partial_nodes,
                    contexts,
                    missing,
                    document=partial_document,
                    selected_variant=selected_variant,
                    partial_stack=partial_stack + [partial_document.path.resolve()],
                )
            )
        elif isinstance(node, VariantNode):
            if node.name == selected_variant:
                parts.append(
                    _render_nodes(
                        node.children,
                        contexts,
                        missing,
                        document=document,
                        selected_variant=selected_variant,
                        partial_stack=partial_stack,
                    )
                )
    return "".join(parts)


def _resolve(contexts: list[Any], name: str) -> tuple[bool, Any]:
    name = name.strip()
    if name == ".":
        return True, contexts[-1] if contexts else None
    for context in reversed(contexts):
        found, value = _resolve_from_context(context, name)
        if found:
            return True, value
    return False, None


def _resolve_from_context(context: Any, name: str) -> tuple[bool, Any]:
    current = context
    for part in name.split("."):
        if part == "":
            return False, None
        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return False, None
            index = int(part)
            if index >= len(current):
                return False, None
            current = current[index]
            continue
        if hasattr(current, part):
            current = getattr(current, part)
            continue
        return False, None
    return True, current


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _is_truthy(value: Any) -> bool:
    return bool(value)


def _selected_variant(document: PromptDocument, variables: dict[str, Any], variant: str | None) -> str | None:
    if variant:
        return variant
    variable_variant = variables.get("variant")
    if isinstance(variable_variant, str) and variable_variant:
        return variable_variant
    default_variant = document.metadata.get("default_variant")
    if isinstance(default_variant, str) and default_variant:
        return default_variant
    return None


def _parse_variant_name(section_name: str) -> str | None:
    parts = section_name.split(None, 1)
    if len(parts) != 2 or parts[0] != "variant":
        return None
    name = parts[1].strip()
    if (name.startswith('"') and name.endswith('"')) or (name.startswith("'") and name.endswith("'")):
        name = name[1:-1]
    if not name:
        raise PromptKitError("Variant tag is missing a variant name.")
    return name


def _load_partial_document(document: PromptDocument, partial_name: str, partial_stack: list[Path]) -> PromptDocument:
    partial_path = _resolve_partial_path(document, partial_name)
    if partial_path in partial_stack:
        chain = " -> ".join(str(path) for path in partial_stack + [partial_path])
        raise PromptKitError(f"Recursive partial include detected: {chain}")
    if not partial_path.is_file():
        raise PromptKitError(f"Partial `{partial_name}` does not exist: {partial_path}")
    raw_text = partial_path.read_text(encoding="utf-8")
    metadata, body = parse_prompt_text(raw_text)
    return PromptDocument(path=partial_path, metadata=metadata, body=body, raw_text=raw_text)


def _resolve_partial_path(document: PromptDocument, partial_name: str) -> Path:
    partials = document.metadata.get("partials", {})
    if partials:
        if not isinstance(partials, dict):
            raise PromptKitError("`partials` front matter must be a mapping.")
        if partial_name in partials:
            return (document.path.parent / str(partials[partial_name])).resolve()
    explicit_path = partial_name.replace("/", "\\")
    if "\\" in explicit_path or Path(explicit_path).suffix:
        return (document.path.parent / explicit_path).resolve()
    candidates = [
        document.path.parent / "partials" / f"{partial_name}.prompt.md",
        document.path.parent / "partials" / f"{partial_name}.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return candidates[0].resolve()


def _collect_partial_documents(
    document: PromptDocument,
    nodes: list[TemplateNode],
    partials: dict[str, Any],
    partial_stack: list[Path],
) -> None:
    for node in nodes:
        if isinstance(node, PartialNode):
            partial_document = _load_partial_document(document, node.name, partial_stack)
            partial_nodes = _parse_template(partial_document.body)
            partials[node.name] = {
                "path": str(partial_document.path),
                "sha256": _sha256_text(partial_document.raw_text),
                "nodes": _serialize_nodes(partial_nodes),
            }
            _collect_partial_documents(
                partial_document,
                partial_nodes,
                partials,
                partial_stack + [partial_document.path.resolve()],
            )
        elif isinstance(node, SectionNode):
            _collect_partial_documents(document, node.children, partials, partial_stack)
        elif isinstance(node, VariantNode):
            _collect_partial_documents(document, node.children, partials, partial_stack)


def _serialize_nodes(nodes: list[TemplateNode]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for node in nodes:
        if isinstance(node, TextNode):
            serialized.append({"type": "text", "text": node.text})
        elif isinstance(node, VarNode):
            serialized.append({"type": "var", "name": node.name})
        elif isinstance(node, SectionNode):
            serialized.append(
                {
                    "type": "section",
                    "name": node.name,
                    "inverted": node.inverted,
                    "children": _serialize_nodes(node.children),
                }
            )
        elif isinstance(node, PartialNode):
            serialized.append({"type": "partial", "name": node.name})
        elif isinstance(node, VariantNode):
            serialized.append({"type": "variant", "name": node.name, "children": _serialize_nodes(node.children)})
    return serialized


def _required_top_level_inputs(
    nodes: list[TemplateNode],
    *,
    document: PromptDocument | None = None,
    inside_section: bool = False,
    partial_stack: list[Path] | None = None,
) -> set[str]:
    names: set[str] = set()
    if document is not None and partial_stack is None:
        partial_stack = [document.path.resolve()]
    for node in nodes:
        if isinstance(node, VarNode):
            if not inside_section and node.name != ".":
                names.add(node.name.split(".", 1)[0])
        elif isinstance(node, SectionNode):
            names.add(node.name.split(".", 1)[0])
            names.update(
                _required_top_level_inputs(
                    node.children,
                    document=document,
                    inside_section=True,
                    partial_stack=partial_stack,
                )
            )
        elif isinstance(node, PartialNode) and document is not None and partial_stack is not None:
            partial_document = _load_partial_document(document, node.name, partial_stack)
            names.update(
                _required_top_level_inputs(
                    _parse_template(partial_document.body),
                    document=partial_document,
                    inside_section=inside_section,
                    partial_stack=partial_stack + [partial_document.path.resolve()],
                )
            )
        elif isinstance(node, VariantNode):
            names.update(
                _required_top_level_inputs(
                    node.children,
                    document=document,
                    inside_section=inside_section,
                    partial_stack=partial_stack,
                )
            )
    return names


def _check_type(name: str, value: Any, type_name: str) -> str | None:
    normalized = type_name.lower()
    if normalized in {"any", "unknown"}:
        return None
    checks = {
        "string": isinstance(value, str),
        "str": isinstance(value, str),
        "int": isinstance(value, int) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "float": isinstance(value, (int, float)) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "bool": isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "list": isinstance(value, list),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
        "dict": isinstance(value, dict),
    }
    if normalized not in checks:
        return f"Input `{name}` declares unsupported type `{type_name}`."
    if not checks[normalized]:
        return f"Input `{name}` expected `{type_name}`, got `{type(value).__name__}`."
    return None


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    safe = _SAFE_ID_RE.sub("_", value).strip("._")
    return safe or "prompt"
