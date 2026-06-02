#!/usr/bin/env python3
"""Minimal metadata-aware document indexer for this workspace.

The tool scans Markdown docs, parses lightweight YAML frontmatter, and lets us:

- audit which docs are already indexed
- query docs by workspace, domain, series, type, or status
- inspect one document's metadata and relationships
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = (".md",)
LIST_FIELDS = {"domains", "series", "related", "supersedes", "artifact_paths"}
REQUIRED_FIELDS = ("id", "title", "type", "workspace", "domains", "status", "created")
GENERATED_SOURCE_EXCLUDED_TYPES = {"index", "sample"}
SCOPE_KIND_TO_FOLDER = {
    "workspace": "workspaces",
    "domain": "domains",
    "series": "series",
    "type": "types",
    "status": "statuses",
}
TERM_TABLES = {
    "domains": ("document_domains", "domain_value"),
    "series": ("document_series", "series_value"),
    "related": ("document_related", "related_doc_id"),
    "supersedes": ("document_supersedes", "superseded_doc_id"),
    "artifact_paths": ("document_artifact_paths", "artifact_path"),
}
DEFAULT_DB_PATH = "tools/doc_index.sqlite3"


@dataclass
class DocRecord:
    path: Path
    rel_path: str
    docs_root: str
    inferred_workspace: str
    has_frontmatter: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    title_from_heading: str | None = None
    validation_errors: list[str] = field(default_factory=list)

    @property
    def doc_id(self) -> str | None:
        return _as_string(self.metadata.get("id"))

    @property
    def title(self) -> str | None:
        return _as_string(self.metadata.get("title")) or self.title_from_heading

    @property
    def workspace(self) -> str:
        return _as_string(self.metadata.get("workspace")) or self.inferred_workspace

    @property
    def doc_type(self) -> str | None:
        return _as_string(self.metadata.get("type"))

    @property
    def status(self) -> str | None:
        return _as_string(self.metadata.get("status"))

    @property
    def domains(self) -> list[str]:
        return _as_list(self.metadata.get("domains"))

    @property
    def series(self) -> list[str]:
        return _as_list(self.metadata.get("series"))

    @property
    def related(self) -> list[str]:
        return _as_list(self.metadata.get("related"))

    @property
    def supersedes(self) -> list[str]:
        return _as_list(self.metadata.get("supersedes"))

    @property
    def artifact_paths(self) -> list[str]:
        return _as_list(self.metadata.get("artifact_paths"))

    @property
    def summary(self) -> str | None:
        return _as_string(self.metadata.get("summary"))

    @property
    def created(self) -> str | None:
        return _as_string(self.metadata.get("created"))

    @property
    def updated(self) -> str | None:
        return _as_string(self.metadata.get("updated"))

    @property
    def is_indexed(self) -> bool:
        return self.has_frontmatter and not self.validation_errors and bool(self.doc_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.doc_id,
            "title": self.title,
            "type": self.doc_type,
            "workspace": self.workspace,
            "domains": self.domains,
            "series": self.series,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
            "summary": self.summary,
            "related": self.related,
            "supersedes": self.supersedes,
            "artifact_paths": self.artifact_paths,
            "path": str(self.path),
            "relative_path": self.rel_path,
            "docs_root": self.docs_root,
            "has_frontmatter": self.has_frontmatter,
            "indexed": self.is_indexed,
            "validation_errors": self.validation_errors,
        }


def _as_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = _as_string(value)
    return [text] if text else []


def strip_matching_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def parse_inline_list(text: str) -> list[str]:
    body = text[1:-1].strip()
    if not body:
        return []
    parts = [strip_matching_quotes(part.strip()) for part in body.split(",")]
    return [part for part in parts if part]


def parse_scalar(text: str) -> Any:
    stripped = text.strip()
    if stripped == "[]":
        return []
    if stripped.startswith("[") and stripped.endswith("]"):
        return parse_inline_list(stripped)
    return strip_matching_quotes(stripped)


def metadata_truthy(value: Any) -> bool:
    text = _as_string(value)
    if text is None:
        return False
    return text.lower() in {"1", "true", "yes", "on"}


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise ValueError("frontmatter starts with '---' but has no closing '---'")

    metadata: dict[str, Any] = {}
    index = 1
    while index < closing_index:
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            raise ValueError(f"unsupported frontmatter line: {line}")

        key, raw_value = match.groups()
        key = key.strip()

        if raw_value.strip():
            metadata[key] = parse_scalar(raw_value)
            index += 1
            continue

        nested_items: list[str] = []
        nested_lines: list[str] = []
        look_ahead = index + 1
        while look_ahead < closing_index:
            nested_line = lines[look_ahead]
            if not nested_line.startswith(("  ", "\t")):
                break
            stripped = nested_line.strip()
            if stripped:
                nested_lines.append(stripped)
                if stripped.startswith("- "):
                    nested_items.append(strip_matching_quotes(stripped[2:].strip()))
            look_ahead += 1

        if nested_lines and len(nested_items) == len(nested_lines):
            metadata[key] = nested_items
        elif not nested_lines:
            metadata[key] = []
        else:
            metadata[key] = "\n".join(nested_lines)

        index = look_ahead

    body = "\n".join(lines[closing_index + 1 :])
    return metadata, body


def extract_first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            heading = line[2:].strip()
            return heading or None
    return None


def infer_workspace_from_rel_path(rel_path: Path) -> str:
    parts = rel_path.parts
    if len(parts) >= 2 and parts[0] == "docs":
        return "root"
    if len(parts) >= 3 and parts[1] == "docs":
        return parts[0]
    return "unknown"


def discover_docs_roots(workspace_root: Path) -> list[Path]:
    roots: list[Path] = []
    root_docs = workspace_root / "docs"
    if root_docs.is_dir():
        roots.append(root_docs)

    for child in sorted(workspace_root.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        docs_dir = child / "docs"
        if docs_dir.is_dir():
            roots.append(docs_dir)

    return roots


def normalize_metadata(metadata: dict[str, Any], inferred_workspace: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in LIST_FIELDS:
            normalized[key] = _as_list(value)
        else:
            normalized[key] = _as_string(value)

    if not normalized.get("workspace"):
        normalized["workspace"] = inferred_workspace

    for field_name in LIST_FIELDS:
        normalized.setdefault(field_name, [])

    return normalized


def validate_metadata(metadata: dict[str, Any], heading: str | None) -> list[str]:
    errors: list[str] = []
    for field_name in REQUIRED_FIELDS:
        value = metadata.get(field_name)
        if field_name == "title":
            value = value or heading
        if field_name == "domains":
            if not _as_list(value):
                errors.append(f"missing required field: {field_name}")
            continue
        if not _as_string(value):
            errors.append(f"missing required field: {field_name}")
    return errors


def scan_docs(
    workspace_root: Path,
    docs_roots: list[Path],
    extensions: tuple[str, ...],
) -> list[DocRecord]:
    records: list[DocRecord] = []

    for docs_root in docs_roots:
        root_label = docs_root.relative_to(workspace_root).as_posix()
        for path in sorted(docs_root.rglob("*"), key=lambda item: item.as_posix().lower()):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue

            rel_path = path.relative_to(workspace_root)
            rel_path_str = rel_path.as_posix()
            inferred_workspace = infer_workspace_from_rel_path(rel_path)
            text = path.read_text(encoding="utf-8")
            heading = extract_first_heading(text)

            record = DocRecord(
                path=path,
                rel_path=rel_path_str,
                docs_root=root_label,
                inferred_workspace=inferred_workspace,
                has_frontmatter=False,
                title_from_heading=heading,
            )

            parsed = parse_frontmatter(text)
            if parsed is None:
                records.append(record)
                continue

            frontmatter, _ = parsed
            record.has_frontmatter = True
            record.metadata = normalize_metadata(frontmatter, inferred_workspace)
            record.validation_errors = validate_metadata(record.metadata, heading)
            records.append(record)

    return records


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "unknown"


def markdown_link(from_path: Path, to_path: Path, label: str) -> str:
    relative = os.path.relpath(to_path, start=from_path.parent).replace("\\", "/")
    return f"[{label}]({relative})"


def sort_records(records: list[DocRecord]) -> list[DocRecord]:
    return sorted(
        records,
        key=lambda record: (
            record.title or "",
            record.workspace,
            record.rel_path,
        ),
    )


def record_preference_key(record: DocRecord) -> tuple[int, int, str]:
    return (
        1 if metadata_truthy(record.metadata.get("autogenerated")) else 0,
        len(record.rel_path),
        record.rel_path,
    )


def dedupe_records_by_doc_id(
    records: list[DocRecord],
) -> tuple[list[DocRecord], dict[str, list[str]]]:
    chosen: dict[str, DocRecord] = {}
    duplicates: dict[str, list[str]] = defaultdict(list)

    for record in records:
        if not record.doc_id:
            continue
        existing = chosen.get(record.doc_id)
        if existing is None:
            chosen[record.doc_id] = record
            continue

        if record_preference_key(record) < record_preference_key(existing):
            duplicates[record.doc_id].append(existing.rel_path)
            chosen[record.doc_id] = record
        else:
            duplicates[record.doc_id].append(record.rel_path)

    return sort_records(list(chosen.values())), {
        doc_id: sorted(set(paths))
        for doc_id, paths in duplicates.items()
    }


def source_records_for_scope_generation(records: list[DocRecord]) -> list[DocRecord]:
    filtered_records = [
        record
        for record in records
        if record.is_indexed and record.doc_type not in GENERATED_SOURCE_EXCLUDED_TYPES
    ]
    deduped_records, _duplicates = dedupe_records_by_doc_id(filtered_records)
    return deduped_records


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    initialize_db(connection)
    return connection


def initialize_db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            workspace TEXT NOT NULL,
            status TEXT NOT NULL,
            created TEXT NOT NULL,
            updated TEXT,
            summary TEXT,
            path TEXT NOT NULL,
            relative_path TEXT NOT NULL UNIQUE,
            docs_root TEXT NOT NULL,
            autogenerated INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS document_domains (
            doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
            domain_value TEXT NOT NULL,
            PRIMARY KEY (doc_id, domain_value)
        );

        CREATE TABLE IF NOT EXISTS document_series (
            doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
            series_value TEXT NOT NULL,
            PRIMARY KEY (doc_id, series_value)
        );

        CREATE TABLE IF NOT EXISTS document_related (
            doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
            related_doc_id TEXT NOT NULL,
            PRIMARY KEY (doc_id, related_doc_id)
        );

        CREATE TABLE IF NOT EXISTS document_supersedes (
            doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
            superseded_doc_id TEXT NOT NULL,
            PRIMARY KEY (doc_id, superseded_doc_id)
        );

        CREATE TABLE IF NOT EXISTS document_artifact_paths (
            doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
            artifact_path TEXT NOT NULL,
            PRIMARY KEY (doc_id, artifact_path)
        );

        CREATE TABLE IF NOT EXISTS scope_members (
            scope_kind TEXT NOT NULL,
            scope_value TEXT NOT NULL,
            source_type TEXT NOT NULL,
            doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (scope_kind, scope_value, source_type, doc_id)
        );

        CREATE TABLE IF NOT EXISTS db_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_documents_workspace ON documents(workspace);
        CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
        CREATE INDEX IF NOT EXISTS idx_scope_members_lookup ON scope_members(scope_kind, scope_value, source_type, position);
        """
    )


def set_db_metadata(connection: sqlite3.Connection, metadata: dict[str, str]) -> None:
    connection.executemany(
        """
        INSERT INTO db_metadata(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        list(metadata.items()),
    )


def upsert_documents(connection: sqlite3.Connection, records: list[DocRecord]) -> None:
    indexed_records, _duplicates = dedupe_records_by_doc_id(
        [record for record in records if record.is_indexed and record.doc_id]
    )
    current_doc_ids = [record.doc_id for record in indexed_records if record.doc_id]

    if not indexed_records:
        connection.execute("DELETE FROM scope_members WHERE source_type = 'generated'")
        connection.execute("DELETE FROM document_domains")
        connection.execute("DELETE FROM document_series")
        connection.execute("DELETE FROM document_related")
        connection.execute("DELETE FROM document_supersedes")
        connection.execute("DELETE FROM document_artifact_paths")
        connection.execute("DELETE FROM documents")
        return

    connection.executemany(
        """
        INSERT INTO documents(
            doc_id,
            title,
            doc_type,
            workspace,
            status,
            created,
            updated,
            summary,
            path,
            relative_path,
            docs_root,
            autogenerated
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(doc_id) DO UPDATE SET
            title=excluded.title,
            doc_type=excluded.doc_type,
            workspace=excluded.workspace,
            status=excluded.status,
            created=excluded.created,
            updated=excluded.updated,
            summary=excluded.summary,
            path=excluded.path,
            relative_path=excluded.relative_path,
            docs_root=excluded.docs_root,
            autogenerated=excluded.autogenerated
        """,
        [
            (
                record.doc_id,
                record.title or record.doc_id,
                record.doc_type or "",
                record.workspace,
                record.status or "",
                record.created or "",
                record.updated,
                record.summary,
                str(record.path),
                record.rel_path,
                record.docs_root,
                1 if metadata_truthy(record.metadata.get("autogenerated")) else 0,
            )
            for record in indexed_records
        ],
    )

    placeholders = ", ".join("?" for _ in current_doc_ids)
    connection.execute(
        f"DELETE FROM documents WHERE doc_id NOT IN ({placeholders})",
        current_doc_ids,
    )

    for table_name, _column_name in TERM_TABLES.values():
        connection.execute(f"DELETE FROM {table_name}")

    for field_name, (table_name, column_name) in TERM_TABLES.items():
        rows: list[tuple[str, str]] = []
        for record in indexed_records:
            values = getattr(record, field_name)
            rows.extend((record.doc_id, value) for value in values)
        if rows:
            connection.executemany(
                f"INSERT INTO {table_name}(doc_id, {column_name}) VALUES(?, ?)",
                rows,
            )


def rebuild_generated_scope_rows(connection: sqlite3.Connection, records: list[DocRecord]) -> int:
    source_records = source_records_for_scope_generation(records)
    groups = build_scope_groups(source_records, list(SCOPE_KIND_TO_FOLDER.keys()))
    connection.execute("DELETE FROM scope_members WHERE source_type = 'generated'")

    rows: list[tuple[str, str, str, str, int]] = []
    for scope_kind, grouped in groups.items():
        for scope_value, docs in grouped.items():
            for position, record in enumerate(docs, start=1):
                if not record.doc_id:
                    continue
                rows.append(
                    (
                        scope_kind,
                        scope_value,
                        "generated",
                        record.doc_id,
                        position,
                    )
                )

    if rows:
        connection.executemany(
            """
            INSERT INTO scope_members(scope_kind, scope_value, source_type, doc_id, position)
            VALUES(?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def document_exists(connection: sqlite3.Connection, doc_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM documents WHERE doc_id = ?",
        (doc_id,),
    ).fetchone()
    return row is not None


def get_scope_member_doc_ids(
    connection: sqlite3.Connection,
    scope_kind: str,
    scope_value: str,
    source_type: str,
) -> list[str]:
    rows = connection.execute(
        """
        SELECT doc_id
        FROM scope_members
        WHERE scope_kind = ?
          AND scope_value = ?
          AND source_type = ?
        ORDER BY position, doc_id
        """,
        (scope_kind, scope_value, source_type),
    ).fetchall()
    return [row["doc_id"] for row in rows]


def replace_scope_members(
    connection: sqlite3.Connection,
    scope_kind: str,
    scope_value: str,
    source_type: str,
    ordered_doc_ids: list[str],
) -> None:
    connection.execute(
        """
        DELETE FROM scope_members
        WHERE scope_kind = ?
          AND scope_value = ?
          AND source_type = ?
        """,
        (scope_kind, scope_value, source_type),
    )
    if ordered_doc_ids:
        connection.executemany(
            """
            INSERT INTO scope_members(scope_kind, scope_value, source_type, doc_id, position)
            VALUES(?, ?, ?, ?, ?)
            """,
            [
                (scope_kind, scope_value, source_type, doc_id, index)
                for index, doc_id in enumerate(ordered_doc_ids, start=1)
            ],
        )


def insert_at_position(items: list[str], value: str, position: int | None) -> tuple[list[str], int]:
    updated = [item for item in items if item != value]
    if position is None:
        updated.append(value)
        return updated, len(updated)

    target_index = max(0, min(position - 1, len(updated)))
    updated.insert(target_index, value)
    return updated, target_index + 1


def rebuild_db(
    connection: sqlite3.Connection,
    workspace_root: Path,
    docs_roots: list[Path],
    records: list[DocRecord],
) -> dict[str, Any]:
    indexed_records, duplicate_doc_ids = dedupe_records_by_doc_id(
        [record for record in records if record.is_indexed and record.doc_id]
    )
    source_records = source_records_for_scope_generation(records)
    missing_records = [record for record in records if not record.has_frontmatter]
    invalid_records = [
        record for record in records if record.has_frontmatter and record.validation_errors
    ]

    with connection:
        upsert_documents(connection, records)
        generated_member_count = rebuild_generated_scope_rows(connection, records)
        set_db_metadata(
            connection,
            {
                "workspace_root": str(workspace_root),
                "docs_roots_json": json.dumps([str(path) for path in docs_roots]),
                "last_rebuild": date.today().isoformat(),
            },
        )

    return {
        "workspace_root": str(workspace_root),
        "docs_roots": [str(path) for path in docs_roots],
        "total_docs_scanned": len(records),
        "indexed_docs": len(indexed_records),
        "scope_source_docs": len(source_records),
        "duplicate_doc_ids": sorted(duplicate_doc_ids.keys()),
        "missing_frontmatter": len(missing_records),
        "invalid_frontmatter": len(invalid_records),
        "generated_scope_members": generated_member_count,
    }


def load_term_map(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    doc_ids: list[str],
) -> dict[str, list[str]]:
    if not doc_ids:
        return {}

    placeholders = ", ".join("?" for _ in doc_ids)
    rows = connection.execute(
        f"""
        SELECT doc_id, {column_name} AS value
        FROM {table_name}
        WHERE doc_id IN ({placeholders})
        ORDER BY doc_id, value
        """,
        doc_ids,
    ).fetchall()

    result: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        result[row["doc_id"]].append(row["value"])
    return result


def load_documents_by_ids(
    connection: sqlite3.Connection,
    doc_ids: list[str],
) -> dict[str, DocRecord]:
    unique_doc_ids = list(dict.fromkeys(doc_ids))
    if not unique_doc_ids:
        return {}

    placeholders = ", ".join("?" for _ in unique_doc_ids)
    rows = connection.execute(
        f"""
        SELECT doc_id, title, doc_type, workspace, status, created, updated, summary,
               path, relative_path, docs_root, autogenerated
        FROM documents
        WHERE doc_id IN ({placeholders})
        """,
        unique_doc_ids,
    ).fetchall()

    domains = load_term_map(connection, "document_domains", "domain_value", unique_doc_ids)
    series = load_term_map(connection, "document_series", "series_value", unique_doc_ids)
    related = load_term_map(connection, "document_related", "related_doc_id", unique_doc_ids)
    supersedes = load_term_map(
        connection,
        "document_supersedes",
        "superseded_doc_id",
        unique_doc_ids,
    )
    artifact_paths = load_term_map(
        connection,
        "document_artifact_paths",
        "artifact_path",
        unique_doc_ids,
    )

    records: dict[str, DocRecord] = {}
    for row in rows:
        metadata: dict[str, Any] = {
            "id": row["doc_id"],
            "title": row["title"],
            "type": row["doc_type"],
            "workspace": row["workspace"],
            "status": row["status"],
            "created": row["created"],
            "updated": row["updated"],
            "summary": row["summary"],
            "domains": domains.get(row["doc_id"], []),
            "series": series.get(row["doc_id"], []),
            "related": related.get(row["doc_id"], []),
            "supersedes": supersedes.get(row["doc_id"], []),
            "artifact_paths": artifact_paths.get(row["doc_id"], []),
            "autogenerated": "true" if row["autogenerated"] else "false",
        }
        records[row["doc_id"]] = DocRecord(
            path=Path(row["path"]),
            rel_path=row["relative_path"],
            docs_root=row["docs_root"],
            inferred_workspace=row["workspace"],
            has_frontmatter=True,
            metadata=metadata,
        )
    return records


def fetch_scope_groups_from_db(
    connection: sqlite3.Connection,
    selected_scopes: list[str],
    source_type: str,
) -> dict[str, dict[str, list[DocRecord]]]:
    groups: dict[str, dict[str, list[DocRecord]]] = {}

    for scope_kind in selected_scopes:
        parameters: list[Any] = [scope_kind]
        source_clause = ""
        if source_type != "all":
            source_clause = "AND source_type = ?"
            parameters.append(source_type)

        rows = connection.execute(
            f"""
            SELECT scope_value, doc_id, position, source_type
            FROM scope_members
            WHERE scope_kind = ?
              {source_clause}
            ORDER BY scope_value, position, doc_id
            """,
            parameters,
        ).fetchall()

        grouped_doc_ids: dict[str, list[str]] = defaultdict(list)
        all_doc_ids: list[str] = []
        for row in rows:
            if row["doc_id"] not in grouped_doc_ids[row["scope_value"]]:
                grouped_doc_ids[row["scope_value"]].append(row["doc_id"])
                all_doc_ids.append(row["doc_id"])

        docs_by_id = load_documents_by_ids(connection, all_doc_ids)
        groups[scope_kind] = {
            scope_value: [
                docs_by_id[doc_id]
                for doc_id in doc_ids
                if doc_id in docs_by_id
            ]
            for scope_value, doc_ids in grouped_doc_ids.items()
        }

    return groups


def build_scope_groups(
    records: list[DocRecord],
    selected_scopes: list[str],
) -> dict[str, dict[str, list[DocRecord]]]:
    groups: dict[str, dict[str, list[DocRecord]]] = {
        scope_kind: defaultdict(list) for scope_kind in selected_scopes
    }

    for record in records:
        if "workspace" in groups:
            groups["workspace"][record.workspace].append(record)
        if "domain" in groups:
            for domain in record.domains:
                groups["domain"][domain].append(record)
        if "series" in groups:
            for series_value in record.series:
                groups["series"][series_value].append(record)
        if "type" in groups and record.doc_type:
            groups["type"][record.doc_type].append(record)
        if "status" in groups and record.status:
            groups["status"][record.status].append(record)

    return {
        scope_kind: {
            value: sort_records(group_records)
            for value, group_records in grouped_records.items()
        }
        for scope_kind, grouped_records in groups.items()
    }


def autogenerated_frontmatter(
    doc_id: str,
    title: str,
    summary: str,
    today: str,
    extra_fields: dict[str, str],
) -> list[str]:
    lines = [
        "---",
        f"id: {doc_id}",
        f"title: {title}",
        "type: index",
        "workspace: root",
        "domains:",
        "  - docs-process",
        "status: reference",
        f"created: {today}",
        f"updated: {today}",
        f"summary: {summary}",
        "related: []",
        "supersedes: []",
        "artifact_paths: []",
    ]
    for key, value in extra_fields.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return lines


def render_scope_page(
    scope_kind: str,
    scope_value: str,
    docs: list[DocRecord],
    output_path: Path,
    workspace_root: Path,
    generator_command: str,
    source_description: str,
) -> str:
    today = date.today().isoformat()
    title = f"{scope_kind.title()} Scope: {scope_value}"
    summary = f"Auto-generated index for docs in the {scope_kind} scope `{scope_value}`."
    doc_count = len(docs)
    workspaces = sorted({record.workspace for record in docs})
    doc_types = sorted({record.doc_type for record in docs if record.doc_type})
    statuses = sorted({record.status for record in docs if record.status})

    lines = autogenerated_frontmatter(
        doc_id=f"scope-{scope_kind}-{slugify(scope_value)}",
        title=title,
        summary=summary,
        today=today,
        extra_fields={
            "scope_kind": scope_kind,
            "scope_value": scope_value,
            "autogenerated": "true",
        },
    )
    lines.extend(
        [
            "",
            f"# {title}",
            "",
            summary,
            "",
            "## Index",
            "",
            "- [Summary](#summary)",
            "- [Docs](#docs)",
            "- [Generation](#generation)",
            "",
            "## Summary",
            "",
            f"- Scope kind: `{scope_kind}`",
            f"- Scope value: `{scope_value}`",
            f"- Indexed docs: {doc_count}",
            f"- Workspaces represented: {', '.join(f'`{value}`' for value in workspaces) if workspaces else '-'}",
            f"- Document types represented: {', '.join(f'`{value}`' for value in doc_types) if doc_types else '-'}",
            f"- Statuses represented: {', '.join(f'`{value}`' for value in statuses) if statuses else '-'}",
            "",
            "## Docs",
            "",
        ]
    )

    for record in docs:
        target_path = workspace_root / record.rel_path
        link = markdown_link(output_path, target_path, record.title or record.rel_path)
        lines.append(
            f"- {link} (`{record.doc_type or '-'}`, `{record.workspace}`, `{record.status or '-'}`)"
        )
        if record.summary:
            lines.append(f"  Summary: {record.summary}")

    lines.extend(
        [
            "",
            "## Generation",
            "",
            f"- Generated by `{generator_command}`.",
            f"- Source set: {source_description}.",
            "",
        ]
    )
    return "\n".join(lines)


def render_scopes_landing_page(
    groups: dict[str, dict[str, list[DocRecord]]],
    output_root: Path,
    generator_command: str,
    source_description: str,
) -> str:
    today = date.today().isoformat()
    total_scope_pages = sum(len(entries) for entries in groups.values())
    source_docs = {
        record.doc_id: record
        for grouped_entries in groups.values()
        for docs in grouped_entries.values()
        for record in docs
        if record.doc_id
    }

    lines = autogenerated_frontmatter(
        doc_id="generated-scope-index",
        title="Generated Scope Indexes",
        summary="Auto-generated landing page for workspace, domain, series, type, and status indexes.",
        today=today,
        extra_fields={
            "autogenerated": "true",
        },
    )
    lines.extend(
        [
            "",
            "# Generated Scope Indexes",
            "",
            "Auto-generated landing page for scope-based navigation pages derived from document frontmatter.",
            "",
            "## Index",
            "",
            "- [Summary](#summary)",
            "- [Workspaces](#workspaces)",
            "- [Domains](#domains)",
            "- [Series](#series)",
            "- [Types](#types)",
            "- [Statuses](#statuses)",
            "- [Generation](#generation)",
            "",
            "## Summary",
            "",
            f"- Source content docs: {len(source_docs)}",
            f"- Scope pages generated: {total_scope_pages}",
            "",
        ]
    )

    section_map = {
        "workspace": "Workspaces",
        "domain": "Domains",
        "series": "Series",
        "type": "Types",
        "status": "Statuses",
    }

    for scope_kind, section_title in section_map.items():
        lines.extend(["## " + section_title, ""])
        entries = groups.get(scope_kind, {})
        if not entries:
            lines.extend(["- None yet.", ""])
            continue
        folder = SCOPE_KIND_TO_FOLDER[scope_kind]
        for scope_value, docs in sorted(entries.items()):
            page_path = output_root / folder / f"{slugify(scope_value)}.md"
            link = markdown_link(output_root / "index.md", page_path, scope_value)
            lines.append(f"- {link} ({len(docs)} docs)")
        lines.append("")

    lines.extend(
        [
            "## Generation",
            "",
            f"- Generated by `{generator_command}`.",
            f"- Source set: {source_description}.",
            "",
        ]
    )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan and query document metadata across workspace docs roots.",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root to scan. Defaults to the current directory.",
    )
    parser.add_argument(
        "--docs-root",
        action="append",
        default=[],
        help="Explicit docs root relative to workspace root. Repeat to add multiple roots.",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(SUPPORTED_EXTENSIONS),
        help="File extensions to scan. Defaults to .md only.",
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path relative to workspace root. Defaults to {DEFAULT_DB_PATH}.",
    )
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Summarize indexed docs and gaps.")
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    scan_parser.add_argument(
        "--show-missing",
        action="store_true",
        help="List docs that do not currently have frontmatter.",
    )
    scan_parser.add_argument(
        "--show-invalid",
        action="store_true",
        help="List docs that have frontmatter but still miss required fields.",
    )

    list_parser = subparsers.add_parser("list", help="List docs filtered by metadata.")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    list_parser.add_argument("--workspace", help="Filter by workspace value.")
    list_parser.add_argument("--domain", help="Filter by one domain.")
    list_parser.add_argument("--series", help="Filter by one series.")
    list_parser.add_argument("--type", dest="doc_type", help="Filter by document type.")
    list_parser.add_argument("--status", help="Filter by status.")
    list_parser.add_argument(
        "--include-unindexed",
        action="store_true",
        help="Include docs without valid frontmatter in the listing.",
    )
    list_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include domains and series columns in text output.",
    )

    show_parser = subparsers.add_parser("show", help="Show one doc by id or relative path.")
    show_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    show_parser.add_argument("target", help="Document id or relative path.")

    generate_parser = subparsers.add_parser(
        "generate-scopes",
        help="Generate scope index pages from indexed docs.",
    )
    generate_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    generate_parser.add_argument(
        "--output-root",
        default="docs/scopes",
        help="Output directory relative to workspace root. Defaults to docs/scopes.",
    )
    generate_parser.add_argument(
        "--scope",
        action="append",
        choices=list(SCOPE_KIND_TO_FOLDER.keys()),
        help="Limit generation to one or more scope kinds. Defaults to all supported kinds.",
    )

    rebuild_parser = subparsers.add_parser(
        "rebuild-db",
        help="Rebuild the SQLite document index from frontmatter.",
    )
    rebuild_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )

    query_scope_parser = subparsers.add_parser(
        "query-scope",
        help="Query scope memberships from the SQLite index.",
    )
    query_scope_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    query_scope_parser.add_argument(
        "--scope-kind",
        required=True,
        choices=list(SCOPE_KIND_TO_FOLDER.keys()),
        help="Scope kind to query.",
    )
    query_scope_parser.add_argument(
        "--scope-value",
        help="Specific scope value to inspect. If omitted, list available scope values for the kind.",
    )
    query_scope_parser.add_argument(
        "--source-type",
        default="all",
        choices=["generated", "curated", "all"],
        help="Filter by source type. Defaults to all.",
    )
    query_scope_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include domains and series columns when listing docs in a scope.",
    )

    add_curated_parser = subparsers.add_parser(
        "add-curated-scope-member",
        help="Add or reposition one curated scope member in the SQLite index.",
    )
    add_curated_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    add_curated_parser.add_argument(
        "--scope-kind",
        required=True,
        choices=list(SCOPE_KIND_TO_FOLDER.keys()),
        help="Scope kind to update.",
    )
    add_curated_parser.add_argument(
        "--scope-value",
        required=True,
        help="Scope value to update.",
    )
    add_curated_parser.add_argument(
        "--doc-id",
        required=True,
        help="Indexed document id to add or reposition.",
    )
    add_curated_parser.add_argument(
        "--position",
        type=int,
        help="1-based target position. Defaults to appending at the end.",
    )

    remove_curated_parser = subparsers.add_parser(
        "remove-curated-scope-member",
        help="Remove one curated scope member from the SQLite index.",
    )
    remove_curated_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    remove_curated_parser.add_argument(
        "--scope-kind",
        required=True,
        choices=list(SCOPE_KIND_TO_FOLDER.keys()),
        help="Scope kind to update.",
    )
    remove_curated_parser.add_argument(
        "--scope-value",
        required=True,
        help="Scope value to update.",
    )
    remove_curated_parser.add_argument(
        "--doc-id",
        required=True,
        help="Indexed document id to remove.",
    )

    generate_db_parser = subparsers.add_parser(
        "generate-scopes-from-db",
        help="Generate scope index pages from the SQLite index.",
    )
    generate_db_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    generate_db_parser.add_argument(
        "--output-root",
        default="docs/scopes",
        help="Output directory relative to workspace root. Defaults to docs/scopes.",
    )
    generate_db_parser.add_argument(
        "--scope",
        action="append",
        choices=list(SCOPE_KIND_TO_FOLDER.keys()),
        help="Limit generation to one or more scope kinds. Defaults to all supported kinds.",
    )
    generate_db_parser.add_argument(
        "--source-type",
        default="generated",
        choices=["generated", "curated", "all"],
        help="Scope member source type to render. Defaults to generated.",
    )

    return parser


def filter_records(records: list[DocRecord], args: argparse.Namespace) -> list[DocRecord]:
    filtered = []
    for record in records:
        if not args.include_unindexed and not record.is_indexed:
            continue
        if args.workspace and record.workspace != args.workspace:
            continue
        if args.domain and args.domain not in record.domains:
            continue
        if args.series and args.series not in record.series:
            continue
        if args.doc_type and record.doc_type != args.doc_type:
            continue
        if args.status and record.status != args.status:
            continue
        filtered.append(record)
    return filtered


def print_table(rows: list[dict[str, str]], columns: list[str]) -> None:
    widths = {column: len(column) for column in columns}
    for row in rows:
        for column in columns:
            widths[column] = max(widths[column], len(row.get(column, "")))

    header = "  ".join(column.ljust(widths[column]) for column in columns)
    separator = "  ".join("-" * widths[column] for column in columns)
    print(header)
    print(separator)
    for row in rows:
        print("  ".join(row.get(column, "").ljust(widths[column]) for column in columns))


def emit_scan(records: list[DocRecord], docs_roots: list[Path], args: argparse.Namespace) -> int:
    missing = [record for record in records if not record.has_frontmatter]
    invalid = [record for record in records if record.has_frontmatter and record.validation_errors]
    indexed = [record for record in records if record.is_indexed]

    if args.json:
        payload = {
            "docs_roots": [str(root) for root in docs_roots],
            "summary": {
                "total_docs": len(records),
                "indexed_docs": len(indexed),
                "missing_frontmatter": len(missing),
                "invalid_frontmatter": len(invalid),
            },
            "indexed_docs": [record.to_dict() for record in indexed],
            "missing_frontmatter_docs": [record.to_dict() for record in missing],
            "invalid_frontmatter_docs": [record.to_dict() for record in invalid],
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("Docs roots:")
    for root in docs_roots:
        print(f"- {root}")
    print(f"Total docs scanned: {len(records)}")
    print(f"Indexed docs: {len(indexed)}")
    print(f"Missing frontmatter: {len(missing)}")
    print(f"Invalid frontmatter: {len(invalid)}")

    if args.show_missing and missing:
        print("\nMissing frontmatter:")
        for record in missing:
            print(f"- {record.rel_path}")

    if args.show_invalid and invalid:
        print("\nInvalid frontmatter:")
        for record in invalid:
            joined_errors = "; ".join(record.validation_errors)
            print(f"- {record.rel_path}: {joined_errors}")

    return 0


def emit_list(records: list[DocRecord], args: argparse.Namespace) -> int:
    filtered = filter_records(records, args)
    filtered.sort(key=lambda record: (record.workspace, record.rel_path))

    if args.json:
        print(json.dumps([record.to_dict() for record in filtered], indent=2))
        return 0

    if not filtered:
        print("No matching docs.")
        return 0

    rows: list[dict[str, str]] = []
    for record in filtered:
        row = {
            "id": record.doc_id or "-",
            "workspace": record.workspace,
            "type": record.doc_type or "-",
            "status": record.status or "-",
            "path": record.rel_path,
        }
        if args.verbose:
            row["domains"] = ", ".join(record.domains)
            row["series"] = ", ".join(record.series)
        rows.append(row)

    columns = ["id", "workspace", "type", "status", "path"]
    if args.verbose:
        columns.extend(["domains", "series"])
    print_table(rows, columns)
    return 0


def find_record(records: list[DocRecord], target: str) -> DocRecord | None:
    by_id = [record for record in records if record.doc_id == target]
    if len(by_id) == 1:
        return by_id[0]

    normalized_target = target.replace("\\", "/")
    by_path = [record for record in records if record.rel_path == normalized_target]
    if len(by_path) == 1:
        return by_path[0]

    return None


def emit_show(records: list[DocRecord], args: argparse.Namespace) -> int:
    record = find_record(records, args.target)
    if record is None:
        print(f"No document found for target: {args.target}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(record.to_dict(), indent=2))
        return 0

    print(f"Path: {record.rel_path}")
    print(f"Title: {record.title or '-'}")
    print(f"ID: {record.doc_id or '-'}")
    print(f"Workspace: {record.workspace}")
    print(f"Type: {record.doc_type or '-'}")
    print(f"Status: {record.status or '-'}")
    print(f"Created: {record.created or '-'}")
    print(f"Updated: {record.updated or '-'}")
    print(f"Domains: {', '.join(record.domains) or '-'}")
    print(f"Series: {', '.join(record.series) or '-'}")
    print(f"Related: {', '.join(record.related) or '-'}")
    print(f"Supersedes: {', '.join(record.supersedes) or '-'}")
    print(f"Artifact paths: {', '.join(record.artifact_paths) or '-'}")
    print(f"Summary: {record.summary or '-'}")
    print(f"Has frontmatter: {'yes' if record.has_frontmatter else 'no'}")
    print(f"Indexed: {'yes' if record.is_indexed else 'no'}")
    if record.validation_errors:
        print(f"Validation errors: {'; '.join(record.validation_errors)}")
    return 0


def emit_generate_scopes(
    records: list[DocRecord],
    workspace_root: Path,
    args: argparse.Namespace,
) -> int:
    selected_scopes = args.scope or list(SCOPE_KIND_TO_FOLDER.keys())
    source_records = source_records_for_scope_generation(records)
    groups = build_scope_groups(source_records, selected_scopes)
    output_root = (workspace_root / args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    generator_command = "python E:\\agent_misc\\tools\\doc_index.py generate-scopes"
    source_description = (
        "indexed Markdown docs with valid frontmatter, excluding docs whose `type` is `index` or `sample`"
    )

    written_pages: list[dict[str, Any]] = []
    for scope_kind in selected_scopes:
        folder_name = SCOPE_KIND_TO_FOLDER[scope_kind]
        scope_dir = output_root / folder_name
        scope_dir.mkdir(parents=True, exist_ok=True)
        for scope_value, grouped_docs in sorted(groups.get(scope_kind, {}).items()):
            output_path = scope_dir / f"{slugify(scope_value)}.md"
            content = render_scope_page(
                scope_kind=scope_kind,
                scope_value=scope_value,
                docs=grouped_docs,
                output_path=output_path,
                workspace_root=workspace_root,
                generator_command=generator_command,
                source_description=source_description,
            )
            output_path.write_text(content, encoding="utf-8")
            written_pages.append(
                {
                    "scope_kind": scope_kind,
                    "scope_value": scope_value,
                    "doc_count": len(grouped_docs),
                    "path": str(output_path),
                }
            )

    landing_page_path = output_root / "index.md"
    landing_page_path.write_text(
        render_scopes_landing_page(
            groups,
            output_root,
            generator_command=generator_command,
            source_description=source_description,
        ),
        encoding="utf-8",
    )

    if args.json:
        payload = {
            "output_root": str(output_root),
            "landing_page": str(landing_page_path),
            "source_docs": len(source_records),
            "scope_pages_written": len(written_pages),
            "pages": written_pages,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Output root: {output_root}")
    print(f"Source docs: {len(source_records)}")
    print(f"Scope pages written: {len(written_pages)}")
    print(f"Landing page: {landing_page_path}")
    for scope_kind in selected_scopes:
        print(
            f"- {scope_kind}: {len(groups.get(scope_kind, {}))} pages"
        )
    return 0


def emit_rebuild_db(
    connection: sqlite3.Connection,
    workspace_root: Path,
    docs_roots: list[Path],
    records: list[DocRecord],
    args: argparse.Namespace,
) -> int:
    summary = rebuild_db(connection, workspace_root, docs_roots, records)
    summary["db_path"] = str((workspace_root / args.db_path).resolve())

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Database: {summary['db_path']}")
    print(f"Docs roots: {len(summary['docs_roots'])}")
    print(f"Total docs scanned: {summary['total_docs_scanned']}")
    print(f"Indexed docs: {summary['indexed_docs']}")
    print(f"Scope source docs: {summary['scope_source_docs']}")
    print(f"Duplicate doc ids skipped: {len(summary['duplicate_doc_ids'])}")
    print(f"Missing frontmatter: {summary['missing_frontmatter']}")
    print(f"Invalid frontmatter: {summary['invalid_frontmatter']}")
    print(f"Generated scope members: {summary['generated_scope_members']}")
    return 0


def emit_query_scope(connection: sqlite3.Connection, args: argparse.Namespace) -> int:
    if args.scope_value:
        parameters: list[Any] = [args.scope_kind, args.scope_value]
        source_clause = ""
        if args.source_type != "all":
            source_clause = "AND sm.source_type = ?"
            parameters.append(args.source_type)

        rows = connection.execute(
            f"""
            SELECT sm.doc_id, sm.source_type, sm.position
            FROM scope_members sm
            WHERE sm.scope_kind = ?
              AND sm.scope_value = ?
              {source_clause}
            ORDER BY sm.position, sm.doc_id
            """,
            parameters,
        ).fetchall()

        ordered_doc_ids: list[str] = []
        seen_doc_ids: set[str] = set()
        for row in rows:
            if row["doc_id"] not in seen_doc_ids:
                ordered_doc_ids.append(row["doc_id"])
                seen_doc_ids.add(row["doc_id"])

        docs_by_id = load_documents_by_ids(connection, ordered_doc_ids)
        docs = [docs_by_id[doc_id] for doc_id in ordered_doc_ids if doc_id in docs_by_id]

        if args.json:
            payload = {
                "scope_kind": args.scope_kind,
                "scope_value": args.scope_value,
                "source_type": args.source_type,
                "doc_count": len(docs),
                "docs": [record.to_dict() for record in docs],
            }
            print(json.dumps(payload, indent=2))
            return 0

        if not docs:
            print("No matching docs.")
            return 0

        rows_for_table: list[dict[str, str]] = []
        for record in docs:
            row = {
                "id": record.doc_id or "-",
                "workspace": record.workspace,
                "type": record.doc_type or "-",
                "status": record.status or "-",
                "path": record.rel_path,
            }
            if args.verbose:
                row["domains"] = ", ".join(record.domains)
                row["series"] = ", ".join(record.series)
            rows_for_table.append(row)

        columns = ["id", "workspace", "type", "status", "path"]
        if args.verbose:
            columns.extend(["domains", "series"])
        print_table(rows_for_table, columns)
        return 0

    parameters = [args.scope_kind]
    source_clause = ""
    if args.source_type != "all":
        source_clause = "AND source_type = ?"
        parameters.append(args.source_type)

    rows = connection.execute(
        f"""
        SELECT scope_value,
               GROUP_CONCAT(DISTINCT source_type) AS source_types,
               COUNT(DISTINCT doc_id) AS doc_count
        FROM scope_members
        WHERE scope_kind = ?
          {source_clause}
        GROUP BY scope_value
        ORDER BY scope_value
        """,
        parameters,
    ).fetchall()

    if args.json:
        payload = [
            {
                "scope_kind": args.scope_kind,
                "scope_value": row["scope_value"],
                "source_types": sorted((row["source_types"] or "").split(",")) if row["source_types"] else [],
                "doc_count": row["doc_count"],
            }
            for row in rows
        ]
        print(json.dumps(payload, indent=2))
        return 0

    if not rows:
        print("No matching scopes.")
        return 0

    print_table(
        [
            {
                "scope_value": row["scope_value"],
                "source_types": row["source_types"] or "-",
                "doc_count": str(row["doc_count"]),
            }
            for row in rows
        ],
        ["scope_value", "source_types", "doc_count"],
    )
    return 0


def emit_add_curated_scope_member(
    connection: sqlite3.Connection,
    args: argparse.Namespace,
) -> int:
    if args.position is not None and args.position < 1:
        print("Position must be 1 or greater.", file=sys.stderr)
        return 1

    if not document_exists(connection, args.doc_id):
        print(
            f"Document id `{args.doc_id}` is not in the SQLite index. Run `rebuild-db` first.",
            file=sys.stderr,
        )
        return 1

    existing_doc_ids = get_scope_member_doc_ids(
        connection,
        args.scope_kind,
        args.scope_value,
        "curated",
    )
    updated_doc_ids, final_position = insert_at_position(
        existing_doc_ids,
        args.doc_id,
        args.position,
    )

    with connection:
        replace_scope_members(
            connection,
            args.scope_kind,
            args.scope_value,
            "curated",
            updated_doc_ids,
        )

    payload = {
        "scope_kind": args.scope_kind,
        "scope_value": args.scope_value,
        "doc_id": args.doc_id,
        "position": final_position,
        "member_count": len(updated_doc_ids),
        "source_type": "curated",
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(
        f"Added `{args.doc_id}` to curated {args.scope_kind} scope `{args.scope_value}` at position {final_position}."
    )
    print(f"Curated member count: {len(updated_doc_ids)}")
    return 0


def emit_remove_curated_scope_member(
    connection: sqlite3.Connection,
    args: argparse.Namespace,
) -> int:
    existing_doc_ids = get_scope_member_doc_ids(
        connection,
        args.scope_kind,
        args.scope_value,
        "curated",
    )
    updated_doc_ids = [doc_id for doc_id in existing_doc_ids if doc_id != args.doc_id]
    removed = len(updated_doc_ids) != len(existing_doc_ids)

    if removed:
        with connection:
            replace_scope_members(
                connection,
                args.scope_kind,
                args.scope_value,
                "curated",
                updated_doc_ids,
            )

    payload = {
        "scope_kind": args.scope_kind,
        "scope_value": args.scope_value,
        "doc_id": args.doc_id,
        "removed": removed,
        "member_count": len(updated_doc_ids),
        "source_type": "curated",
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    if removed:
        print(
            f"Removed `{args.doc_id}` from curated {args.scope_kind} scope `{args.scope_value}`."
        )
    else:
        print(
            f"`{args.doc_id}` was not present in curated {args.scope_kind} scope `{args.scope_value}`."
        )
    print(f"Curated member count: {len(updated_doc_ids)}")
    return 0


def emit_generate_scopes_from_db(
    connection: sqlite3.Connection,
    workspace_root: Path,
    args: argparse.Namespace,
) -> int:
    selected_scopes = args.scope or list(SCOPE_KIND_TO_FOLDER.keys())
    output_root = (workspace_root / args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    groups = fetch_scope_groups_from_db(connection, selected_scopes, args.source_type)
    generator_command = "python E:\\agent_misc\\tools\\doc_index.py generate-scopes-from-db"
    source_description = f"SQLite scope_members rows with source_type `{args.source_type}`"

    written_pages: list[dict[str, Any]] = []
    for scope_kind in selected_scopes:
        folder_name = SCOPE_KIND_TO_FOLDER[scope_kind]
        scope_dir = output_root / folder_name
        scope_dir.mkdir(parents=True, exist_ok=True)
        for scope_value, grouped_docs in sorted(groups.get(scope_kind, {}).items()):
            output_path = scope_dir / f"{slugify(scope_value)}.md"
            output_path.write_text(
                render_scope_page(
                    scope_kind=scope_kind,
                    scope_value=scope_value,
                    docs=grouped_docs,
                    output_path=output_path,
                    workspace_root=workspace_root,
                    generator_command=generator_command,
                    source_description=source_description,
                ),
                encoding="utf-8",
            )
            written_pages.append(
                {
                    "scope_kind": scope_kind,
                    "scope_value": scope_value,
                    "doc_count": len(grouped_docs),
                    "path": str(output_path),
                }
            )

    landing_page_path = output_root / "index.md"
    landing_page_path.write_text(
        render_scopes_landing_page(
            groups,
            output_root,
            generator_command=generator_command,
            source_description=source_description,
        ),
        encoding="utf-8",
    )

    if args.json:
        payload = {
            "output_root": str(output_root),
            "landing_page": str(landing_page_path),
            "scope_pages_written": len(written_pages),
            "pages": written_pages,
            "source_type": args.source_type,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Output root: {output_root}")
    print(f"Scope pages written: {len(written_pages)}")
    print(f"Landing page: {landing_page_path}")
    print(f"Source type: {args.source_type}")
    for scope_kind in selected_scopes:
        print(f"- {scope_kind}: {len(groups.get(scope_kind, {}))} pages")
    return 0


def resolve_docs_roots(workspace_root: Path, requested_roots: list[str]) -> list[Path]:
    if requested_roots:
        roots = [workspace_root / root for root in requested_roots]
    else:
        roots = discover_docs_roots(workspace_root)

    resolved = [root.resolve() for root in roots if root.is_dir()]
    if not resolved:
        raise FileNotFoundError("no docs roots found to scan")
    return resolved


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    command = args.command or "scan"
    workspace_root = Path(args.workspace_root).resolve()
    db_path = (workspace_root / args.db_path).resolve()
    extensions = tuple(
        extension if extension.startswith(".") else f".{extension}"
        for extension in args.extensions
    )

    scan_required_commands = {"scan", "list", "show", "generate-scopes", "rebuild-db"}
    if command in scan_required_commands:
        try:
            docs_roots = resolve_docs_roots(workspace_root, args.docs_root)
            records = scan_docs(workspace_root, docs_roots, extensions)
        except (FileNotFoundError, OSError, ValueError) as exc:
            print(f"doc-index error: {exc}", file=sys.stderr)
            return 1

    if command == "scan":
        return emit_scan(records, docs_roots, args)
    if command == "list":
        return emit_list(records, args)
    if command == "show":
        return emit_show(records, args)
    if command == "generate-scopes":
        return emit_generate_scopes(records, workspace_root, args)
    if command == "rebuild-db":
        try:
            with connect_db(db_path) as connection:
                return emit_rebuild_db(connection, workspace_root, docs_roots, records, args)
        except (sqlite3.DatabaseError, OSError, ValueError) as exc:
            print(f"doc-index error: {exc}", file=sys.stderr)
            return 1
    if command == "query-scope":
        try:
            with connect_db(db_path) as connection:
                return emit_query_scope(connection, args)
        except (sqlite3.DatabaseError, OSError, ValueError) as exc:
            print(f"doc-index error: {exc}", file=sys.stderr)
            return 1
    if command == "add-curated-scope-member":
        try:
            with connect_db(db_path) as connection:
                return emit_add_curated_scope_member(connection, args)
        except (sqlite3.DatabaseError, OSError, ValueError) as exc:
            print(f"doc-index error: {exc}", file=sys.stderr)
            return 1
    if command == "remove-curated-scope-member":
        try:
            with connect_db(db_path) as connection:
                return emit_remove_curated_scope_member(connection, args)
        except (sqlite3.DatabaseError, OSError, ValueError) as exc:
            print(f"doc-index error: {exc}", file=sys.stderr)
            return 1
    if command == "generate-scopes-from-db":
        try:
            with connect_db(db_path) as connection:
                return emit_generate_scopes_from_db(connection, workspace_root, args)
        except (sqlite3.DatabaseError, OSError, ValueError) as exc:
            print(f"doc-index error: {exc}", file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
