from __future__ import annotations

import json
from typing import Any

from llm import GeminiClient
from models import (
    CodebaseStructure,
    CodeRelationship,
    FileStructure,
    GeminiExport,
    GeminiImport,
    GeminiImportItem,
    GeminiRelationship,
    GeminiSemanticResult,
)


class CodeStructureNormalizer:
    """
    Semantic layer over Tree-sitter output.

    Tree-sitter runs first and produces the full
    CodebaseStructure. This class then sends that
    structure to Gemini:

        - one call when the payload is small
        - a few file-group batches when it is large

    Never one Gemini call per source file.
    Never sends source code. Only structural facts.
    """

    # Keep each request well under typical Flash-Lite
    # token limits. A batch is a group of files, not
    # a single file, unless one file itself is huge.
    MAX_EVIDENCE_CHARS = 80_000

    def __init__(
        self,
        llm: GeminiClient | None = None,
    ):
        self.llm = llm or GeminiClient()

    def normalize(
        self,
        structure: CodebaseStructure,
    ) -> GeminiSemanticResult:
        """
        Interpret the completed Tree-sitter structure.
        """

        if not structure.files:
            return GeminiSemanticResult()

        batches = self._partition_files(structure.files)

        merged = GeminiSemanticResult()

        for batch in batches:

            data = self.llm.generate_json(
                self._build_prompt(
                    self._serialize_files(batch)
                )
            )

            part = self._parse_result(data)

            merged.imports.extend(part.imports)
            merged.exports.extend(part.exports)
            merged.relationships.extend(part.relationships)

        self._apply_relationships(structure, merged)

        return merged

    # ========================================================
    # BATCHING
    # ========================================================

    def _partition_files(
        self,
        files: list[FileStructure],
    ) -> list[list[FileStructure]]:
        """
        Pack files into payload-sized groups.

        Small repositories become one Gemini call.
        Large ones become a handful of parts.
        """

        batches: list[list[FileStructure]] = []
        current: list[FileStructure] = []
        current_size = 0

        for file in files:

            encoded = json.dumps(
                self._serialize_file(file),
                ensure_ascii=False,
            )
            size = len(encoded)

            if current and current_size + size > self.MAX_EVIDENCE_CHARS:
                batches.append(current)
                current = []
                current_size = 0

            current.append(file)
            current_size += size

        if current:
            batches.append(current)

        return batches

    # ========================================================
    # COMPACT TREE-SITTER EVIDENCE
    # ========================================================

    def _serialize_files(
        self,
        files: list[FileStructure],
    ) -> dict[str, Any]:

        return {
            "files": [
                self._serialize_file(file)
                for file in files
            ]
        }

    def _serialize_file(
        self,
        file: FileStructure,
    ) -> dict[str, Any]:

        return {
            "file_path": file.file_path,
            "language": file.language,
            "entities": [
                {
                    "id": entity.id,
                    "kind": entity.kind,
                    "name": entity.name,
                    "start_line": entity.start_line,
                    "end_line": entity.end_line,
                    "parent_id": entity.parent_id,
                    "visibility": entity.visibility,
                    "signature": entity.signature,
                }
                for entity in file.entities
            ],
            "imports": [
                {
                    "source": item.source,
                    "items": [
                        {
                            "name": imported.name,
                            "alias": imported.alias,
                        }
                        for imported in item.items
                    ],
                    "is_wildcard": item.is_wildcard,
                    "line": item.line,
                }
                for item in file.imports
            ],
            "exports": [
                {
                    "name": item.name,
                    "source": item.source,
                    "export_type": item.export_type,
                    "line": item.line,
                }
                for item in file.exports
            ],
        }

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        evidence: dict[str, Any],
    ) -> str:

        evidence_json = json.dumps(
            evidence,
            indent=2,
            ensure_ascii=False,
        )

        return f"""
You are the semantic normalization component of a
language-agnostic code archaeology system.

Tree-sitter has ALREADY analyzed the source files.
You are receiving compact structural facts only.

This payload may be the entire repository or one
part of a larger repository. Use only the evidence
in this payload.

You are NOT responsible for parsing source code.
You are NOT receiving source code.

============================================================
STRICT RULES
============================================================

1. Do not assume a programming language or framework.
2. Do not invent entities, imports, or exports.
3. Do not change entity IDs.
4. Every source_entity_id MUST exist in the supplied entities.
5. Do not invent source locations.
6. Preserve supplied line numbers when possible.
7. If a relationship is not supported by the evidence, omit it.
8. Return ONLY valid JSON. No markdown.

============================================================
RELATIONSHIPS
============================================================

Identify explicit structural relationships.

Use generic labels such as:
calls, imports, inherits, implements, instantiates,
references, contains, overrides, uses, depends_on.

============================================================
OUTPUT
============================================================

Return exactly:

{{
  "imports": [],
  "exports": [],
  "relationships": []
}}

Import:
{{
  "file_path": "...",
  "source": "...",
  "items": [{{ "name": "...", "alias": null }}],
  "is_wildcard": false,
  "line": 0
}}

Export:
{{
  "file_path": "...",
  "name": null,
  "source": null,
  "export_type": "...",
  "line": 0
}}

Relationship:
{{
  "file_path": "...",
  "source_entity_id": "...",
  "target_name": "...",
  "relation_type": "...",
  "line": 0
}}

============================================================
TREE-SITTER STRUCTURAL EVIDENCE
============================================================

{evidence_json}
"""

    # ========================================================
    # APPLY GEMINI RELATIONSHIPS ONTO TREE-SITTER STRUCTURE
    # ========================================================

    def _apply_relationships(
        self,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
    ) -> None:

        entities = {
            entity.id: entity
            for entity in structure.entities
        }

        relationships: list[CodeRelationship] = []

        for rel in semantic.relationships:

            entity = entities.get(rel.source_entity_id)

            if entity is None:
                continue

            file_path = rel.file_path or entity.file_path

            relationships.append(
                CodeRelationship(
                    file_path=file_path,
                    source_entity_id=rel.source_entity_id,
                    target_name=rel.target_name,
                    relation_type=rel.relation_type,
                    line=rel.line,
                )
            )

        structure.relationships = relationships

        by_file: dict[str, list[CodeRelationship]] = {}

        for rel in relationships:
            by_file.setdefault(rel.file_path, []).append(rel)

        for file in structure.files:
            file.relationships = by_file.get(file.file_path, [])

    # ========================================================
    # RESPONSE PARSER
    # ========================================================

    def _parse_result(
        self,
        data: Any,
    ) -> GeminiSemanticResult:

        if not isinstance(data, dict):
            raise RuntimeError(
                "Gemini response must be a JSON object."
            )

        return GeminiSemanticResult(
            imports=self._parse_imports(data.get("imports", [])),
            exports=self._parse_exports(data.get("exports", [])),
            relationships=self._parse_relationships(
                data.get("relationships", [])
            ),
        )

    def _parse_imports(
        self,
        raw_imports: Any,
    ) -> list[GeminiImport]:

        if not isinstance(raw_imports, list):
            return []

        result = []

        for item in raw_imports:

            if not isinstance(item, dict):
                continue

            source = item.get("source")

            if not isinstance(source, str):
                continue

            parsed_items = []
            raw_items = item.get("items", [])

            if isinstance(raw_items, list):

                for imported in raw_items:

                    if not isinstance(imported, dict):
                        continue

                    name = imported.get("name")

                    if not isinstance(name, str):
                        continue

                    alias = imported.get("alias")

                    if alias is not None and not isinstance(alias, str):
                        alias = None

                    parsed_items.append(
                        GeminiImportItem(
                            name=name,
                            alias=alias,
                        )
                    )

            wildcard = item.get("is_wildcard", False)

            if not isinstance(wildcard, bool):
                wildcard = False

            line = item.get("line", 0)

            if not isinstance(line, int):
                line = 0

            file_path = item.get("file_path")

            if file_path is not None and not isinstance(file_path, str):
                file_path = None

            result.append(
                GeminiImport(
                    source=source,
                    file_path=file_path,
                    items=parsed_items,
                    is_wildcard=wildcard,
                    line=line,
                )
            )

        return result

    def _parse_exports(
        self,
        raw_exports: Any,
    ) -> list[GeminiExport]:

        if not isinstance(raw_exports, list):
            return []

        result = []

        for item in raw_exports:

            if not isinstance(item, dict):
                continue

            name = item.get("name")

            if name is not None and not isinstance(name, str):
                name = None

            source = item.get("source")

            if source is not None and not isinstance(source, str):
                source = None

            export_type = item.get("export_type", "unknown")

            if not isinstance(export_type, str):
                export_type = "unknown"

            line = item.get("line", 0)

            if not isinstance(line, int):
                line = 0

            file_path = item.get("file_path")

            if file_path is not None and not isinstance(file_path, str):
                file_path = None

            result.append(
                GeminiExport(
                    name=name,
                    source=source,
                    export_type=export_type,
                    file_path=file_path,
                    line=line,
                )
            )

        return result

    def _parse_relationships(
        self,
        raw_relationships: Any,
    ) -> list[GeminiRelationship]:

        if not isinstance(raw_relationships, list):
            return []

        result = []

        for item in raw_relationships:

            if not isinstance(item, dict):
                continue

            source_entity_id = item.get("source_entity_id")
            target_name = item.get("target_name")
            relation_type = item.get("relation_type")

            if not isinstance(source_entity_id, str):
                continue

            if not isinstance(target_name, str):
                continue

            if not isinstance(relation_type, str):
                continue

            line = item.get("line", 0)

            if not isinstance(line, int):
                line = 0

            file_path = item.get("file_path")

            if file_path is not None and not isinstance(file_path, str):
                file_path = None

            result.append(
                GeminiRelationship(
                    source_entity_id=source_entity_id,
                    target_name=target_name,
                    relation_type=relation_type,
                    file_path=file_path,
                    line=line,
                )
            )

        return result
