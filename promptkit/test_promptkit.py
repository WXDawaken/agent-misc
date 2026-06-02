from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from .core import (
    PromptDocument,
    compile_prompt_document,
    lint_prompt_document,
    load_prompt_document,
    parse_prompt_text,
    render_prompt_document,
    snapshot_prompt_document,
)


class PromptKitTests(unittest.TestCase):
    def test_render_variables_sections_and_inverted_sections(self) -> None:
        document = _document(
            """---
id: test.prompt
engine: mini-mustache
inputs:
  title: string
  items: list
---
# {{title}}
{{#items}}
- {{name}}: {{value}}
{{/items}}
{{^missing}}
fallback
{{/missing}}
"""
        )

        rendered, warnings = render_prompt_document(
            document,
            {
                "title": "Report",
                "items": [
                    {"name": "a", "value": 1},
                    {"name": "b", "value": 2},
                ],
            },
        )

        self.assertEqual(warnings, [])
        self.assertIn("# Report", rendered)
        self.assertIn("- a: 1", rendered)
        self.assertIn("- b: 2", rendered)
        self.assertIn("fallback", rendered)

    def test_lint_reports_missing_declared_input_when_vars_are_supplied(self) -> None:
        document = _document(
            """---
id: test.prompt
engine: mini-mustache
inputs:
  name: string
---
Hello {{name}}
"""
        )

        messages = lint_prompt_document(document, {}, render=True)

        self.assertFalse(any(message.level == "error" for message in messages))

        messages = lint_prompt_document(document, {"name": 1}, render=True)

        self.assertTrue(any("expected `string`" in message.message for message in messages))

    def test_snapshot_writes_manifest_and_rendered_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            document = _document(
                """---
id: test.snapshot
engine: mini-mustache
inputs:
  name: string
---
Hello {{name}}
""",
                Path(tmp) / "prompt.md",
            )

            snapshot_dir = snapshot_prompt_document(document, {"name": "Ada"}, Path(tmp) / "snapshots")

            rendered = (snapshot_dir / "rendered.md").read_text(encoding="utf-8")
            manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(rendered, "Hello Ada\n")
            self.assertEqual(manifest["prompt_id"], "test.snapshot")
            self.assertIn("rendered_sha256", manifest)

    def test_render_partials_and_named_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            partial_path = root / "partials" / "header.prompt.md"
            partial_path.parent.mkdir(parents=True)
            partial_path.write_text("Header for {{name}}\n", encoding="utf-8")
            document = _document(
                """---
id: test.variant
engine: mini-mustache
default_variant: short
inputs:
  name: string
partials:
  header: partials/header.prompt.md
---
{{> header}}
{{#variant "short"}}
Short body.
{{/variant}}
{{#variant "long"}}
Long body for {{name}}.
{{/variant}}
""",
                root / "prompt.md",
            )

            rendered, _ = render_prompt_document(document, {"name": "Ada"})
            self.assertIn("Header for Ada", rendered)
            self.assertIn("Short body.", rendered)
            self.assertNotIn("Long body", rendered)

            rendered, _ = render_prompt_document(document, {"name": "Ada"}, variant="long")
            self.assertIn("Long body for Ada.", rendered)
            self.assertNotIn("Short body.", rendered)

    def test_compile_includes_partial_ir_and_variant_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            partial_path = root / "partials" / "header.prompt.md"
            partial_path.parent.mkdir(parents=True)
            partial_path.write_text("Header for {{name}}\n", encoding="utf-8")
            document = _document(
                """---
id: test.compile
engine: mini-mustache
partials:
  header: partials/header.prompt.md
---
{{> header}}
{{#variant "strict"}}
Strict body.
{{/variant}}
""",
                root / "prompt.md",
            )

            ir = compile_prompt_document(document)

            self.assertEqual(ir["schema"], "promptkit.ir.v1")
            self.assertEqual(ir["nodes"][0], {"type": "partial", "name": "header"})
            self.assertEqual(ir["nodes"][1]["type"], "text")
            self.assertEqual(ir["nodes"][2]["type"], "variant")
            self.assertEqual(ir["nodes"][2]["name"], "strict")
            self.assertIn("header", ir["partials"])
            self.assertEqual(ir["partials"]["header"]["nodes"][0]["type"], "text")


def _document(text: str, path: Path | None = None):
    if path is None:
        metadata, body = parse_prompt_text(text)
        return PromptDocument(path=Path("memory.prompt.md"), metadata=metadata, body=body, raw_text=text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return load_prompt_document(path)


if __name__ == "__main__":
    unittest.main()
