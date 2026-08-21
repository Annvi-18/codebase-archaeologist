from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from tree_sitter_language_pack import (
    ProcessConfig,
    detect_language_from_path,
    process,
)
from tree_sitter_language_pack._native import (
    Diagnostic,
    ExportInfo,
    ImportInfo,
    Span,
    StructureItem,
    SymbolInfo,
)

from models import (
    CodebaseStructure,
    CodeEntity,
    CodeExport,
    CodeImport,
    CodeImportItem,
    FileStructure,
    ParseDiagnostic,
)


class CodeStructureAnalyzer:
    """
    Agent 2 — Deterministic Tree-sitter structure analyzer.

    This agent uses only `tree_sitter_language_pack.process()`.

    It does not:
        - call Gemini or any LLM
        - perform semantic reasoning
        - parse source with regex
        - hardcode language or framework rules

    Flow:

        source file
          → language detection
          → Tree-sitter process()
          → FileStructure
          → aggregate
          → CodebaseStructure
    """

    # Pack-level structural categories, not grammar node names.
    STRUCTURAL_KINDS = frozenset({
        "function",
        "method",
        "class",
        "struct",
        "interface",
        "enum",
        "module",
        "trait",
        "impl",
        "namespace",
        "type",
    })

    EXPORT_KINDS = frozenset({
        "named",
        "default",
        "re_export",
        "reexport",
    })

    SYMBOL_KINDS = frozenset({
        "function",
        "class",
        "type",
        "interface",
        "enum",
        "module",
        "struct",
    })

    NON_IDENTIFIER_CHARS = frozenset("{}()[];,=<>'\"`")

    def analyze(
        self,
        repository_path: str,
        source_files: list[str],
    ) -> CodebaseStructure:
        result = CodebaseStructure()
        repository = Path(repository_path)

        for relative_path in source_files:
            file_path = repository / relative_path

            if not file_path.is_file():
                continue

            file_structure = self._analyze_file(
                repository_path=repository,
                file_path=file_path,
            )

            if file_structure is None:
                continue

            result.files.append(file_structure)
            result.entities.extend(file_structure.entities)
            result.imports.extend(file_structure.imports)
            result.exports.extend(file_structure.exports)
            result.diagnostics.extend(file_structure.diagnostics)

        self._validate_structure(result)
        return result

    def _analyze_file(
        self,
        repository_path: Path,
        file_path: Path,
    ) -> FileStructure | None:
        relative_path = file_path.relative_to(repository_path).as_posix()

        language = detect_language_from_path(str(file_path))
        if not language:
            return None

        try:
            source = file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError as error:
            return FileStructure(
                file_path=relative_path,
                language=str(language),
                line_count=0,
                code_lines=0,
                comment_lines=0,
                blank_lines=0,
                error_count=1,
                max_depth=0,
                diagnostics=[
                    ParseDiagnostic(
                        file_path=relative_path,
                        message=str(error),
                        severity="read_error",
                        start_line=1,
                        end_line=1,
                    )
                ],
            )

        config = ProcessConfig(
            language=language,
            structure=True,
            imports=True,
            exports=True,
            comments=False,
            docstrings=False,
            symbols=True,
            diagnostics=True,
        )

        try:
            parsed = process(source, config)
        except Exception as error:
            line_count = source.count("\n") + 1 if source else 0
            return FileStructure(
                file_path=relative_path,
                language=str(language),
                line_count=line_count,
                code_lines=0,
                comment_lines=0,
                blank_lines=0,
                error_count=1,
                max_depth=0,
                diagnostics=[
                    ParseDiagnostic(
                        file_path=relative_path,
                        message=str(error),
                        severity="parser_error",
                        start_line=1,
                        end_line=max(1, line_count),
                    )
                ],
            )

        metrics = parsed.metrics
        structure = FileStructure(
            file_path=relative_path,
            language=parsed.language,
            line_count=metrics.total_lines,
            code_lines=metrics.code_lines,
            comment_lines=metrics.comment_lines,
            blank_lines=metrics.blank_lines,
            error_count=metrics.error_count,
            max_depth=metrics.max_depth,
        )

        decorator_names: set[str] = set()
        for item in parsed.structure:
            self._collect_structure_item(
                item=item,
                file_path=relative_path,
                parent_id=None,
                output=structure.entities,
                decorator_names=decorator_names,
            )

        self._collect_symbols(
            parsed.symbols,
            relative_path,
            structure.entities,
        )
        self._repair_parent_ids(structure.entities)

        self._collect_imports(
            parsed.imports,
            relative_path,
            structure,
        )
        self._collect_exports(
            parsed.exports,
            relative_path,
            structure,
            decorator_names,
        )
        self._collect_diagnostics(
            parsed.diagnostics,
            relative_path,
            structure,
        )

        structure.relationships = []
        return structure

    def _collect_structure_item(
        self,
        item: StructureItem,
        file_path: str,
        parent_id: str | None,
        output: list[CodeEntity],
        decorator_names: set[str],
    ) -> None:
        for decorator in item.decorators or []:
            normalized = self._normalize_decorator_name(decorator)
            if normalized:
                decorator_names.add(normalized)

        kind_label = self._kind_label(item.kind)
        span = item.span
        next_parent_id = parent_id

        if (
            span is not None
            and kind_label.lower() in self.STRUCTURAL_KINDS
        ):
            entity_id = self._create_entity_id(
                file_path=file_path,
                start_byte=span.start_byte,
                end_byte=span.end_byte,
                kind=kind_label,
                name=item.name,
            )
            output.append(
                CodeEntity(
                    id=entity_id,
                    file_path=file_path,
                    kind=kind_label,
                    name=item.name,
                    start_line=span.start_line + 1,
                    end_line=span.end_line + 1,
                    start_column=span.start_column,
                    end_column=span.end_column,
                    parent_id=parent_id,
                    visibility=item.visibility,
                    signature=item.signature,
                    decorators=list(item.decorators or []),
                    doc_comment=item.doc_comment,
                )
            )
            next_parent_id = entity_id

        for child in item.children or []:
            self._collect_structure_item(
                item=child,
                file_path=file_path,
                parent_id=next_parent_id,
                output=output,
                decorator_names=decorator_names,
            )

    def _collect_symbols(
        self,
        raw_symbols: Sequence[SymbolInfo],
        file_path: str,
        output: list[CodeEntity],
    ) -> None:
        """
        Fill structural gaps the outline missed (for example
        Go type/struct declarations) without adding variables.
        """

        existing = {
            (
                entity.name,
                entity.start_line,
                entity.kind.lower(),
            )
            for entity in output
        }

        for symbol in raw_symbols:
            kind_label = self._kind_label(symbol.kind)
            if kind_label.lower() not in self.SYMBOL_KINDS:
                continue

            span = symbol.span
            if span is None or not symbol.name:
                continue

            key = (
                symbol.name,
                span.start_line + 1,
                kind_label.lower(),
            )
            if key in existing:
                continue

            # Type and Struct often describe the same declaration.
            if kind_label.lower() == "type":
                alt = (symbol.name, span.start_line + 1, "struct")
                if alt in existing:
                    continue

            entity_id = self._create_entity_id(
                file_path=file_path,
                start_byte=span.start_byte,
                end_byte=span.end_byte,
                kind=kind_label,
                name=symbol.name,
            )
            output.append(
                CodeEntity(
                    id=entity_id,
                    file_path=file_path,
                    kind=kind_label,
                    name=symbol.name,
                    start_line=span.start_line + 1,
                    end_line=span.end_line + 1,
                    start_column=span.start_column,
                    end_column=span.end_column,
                    parent_id=None,
                    visibility=None,
                    signature=None,
                    decorators=[],
                    doc_comment=symbol.doc,
                )
            )
            existing.add(key)

    def _collect_imports(
        self,
        raw_imports: Sequence[ImportInfo],
        file_path: str,
        structure: FileStructure,
    ) -> None:
        for item in raw_imports:
            source_name = item.source if isinstance(item.source, str) else ""
            raw_items = item.items if isinstance(item.items, list) else []
            alias = item.alias if isinstance(item.alias, str) else None

            import_items: list[CodeImportItem] = []
            for imported in raw_items:
                if isinstance(imported, str) and imported:
                    import_items.append(
                        CodeImportItem(name=imported, alias=None)
                    )

            if alias and len(import_items) == 1:
                import_items[0] = CodeImportItem(
                    name=import_items[0].name,
                    alias=alias,
                )

            structure.imports.append(
                CodeImport(
                    file_path=file_path,
                    source=source_name,
                    items=import_items,
                    is_wildcard=bool(item.is_wildcard),
                    line=self._line_from_span(item.span),
                )
            )
            structure.parser_imports.append(
                {
                    "source": source_name,
                    "items": [
                        imported
                        for imported in raw_items
                        if isinstance(imported, str)
                    ],
                    "alias": alias,
                    "is_wildcard": bool(item.is_wildcard),
                    "line": self._line_from_span(item.span),
                }
            )

    def _collect_exports(
        self,
        raw_exports: Sequence[ExportInfo],
        file_path: str,
        structure: FileStructure,
        decorator_names: set[str],
    ) -> None:
        seen: set[str] = set()

        for item in raw_exports:
            raw_name = item.name if isinstance(item.name, str) else None
            kind_label = self._kind_label(item.kind)
            line = self._line_from_span(item.span)

            structure.parser_exports.append(
                {
                    "name": raw_name,
                    "kind": kind_label,
                    "line": line,
                }
            )

            export_names = self._resolve_export_names(
                raw_name=raw_name,
                span=item.span,
                entities=structure.entities,
                decorator_names=decorator_names,
            )

            export_type = kind_label or "named"
            kind_key = kind_label.lower().replace("-", "_")
            if kind_key and kind_key not in self.EXPORT_KINDS:
                export_type = "named"

            for name in export_names:
                if name in seen:
                    continue
                seen.add(name)
                structure.exports.append(
                    CodeExport(
                        file_path=file_path,
                        name=name,
                        source=None,
                        export_type=export_type,
                        line=line,
                    )
                )

    def _resolve_export_names(
        self,
        raw_name: str | None,
        span: Span | None,
        entities: list[CodeEntity],
        decorator_names: set[str],
    ) -> list[str]:
        """
        Tree-sitter sometimes puts a whole statement or a
        decorator in ExportInfo.name. Do not treat those as
        identifiers. Recover names only from entities already
        extracted from the same file.
        """

        if self._is_export_identifier(raw_name):
            assert raw_name is not None
            stripped = raw_name.lstrip("@").strip()
            if stripped in decorator_names:
                return []
            return [raw_name.strip()]

        overlapping = self._overlapping_export_entities(span, entities)
        if overlapping:
            return overlapping

        if not raw_name or raw_name.lstrip().startswith("@"):
            return []

        names: list[str] = []
        entity_names = {
            entity.name
            for entity in entities
            if entity.name
        }
        for token in self._identifier_tokens(raw_name):
            if token in entity_names and token not in decorator_names:
                names.append(token)
        return names

    def _overlapping_export_entities(
        self,
        span: Span | None,
        entities: list[CodeEntity],
    ) -> list[str]:
        if span is None:
            return []

        export_start = span.start_line + 1
        export_end = span.end_line + 1
        overlapping = [
            entity
            for entity in entities
            if entity.name
            and not (
                entity.end_line < export_start
                or entity.start_line > export_end
            )
        ]
        if not overlapping:
            return []

        overlapping_ids = {entity.id for entity in overlapping}
        names: list[str] = []
        for entity in overlapping:
            if entity.parent_id in overlapping_ids:
                continue
            if entity.name and entity.name not in names:
                names.append(entity.name)
        return names

    def _collect_diagnostics(
        self,
        raw_diagnostics: Sequence[Diagnostic],
        file_path: str,
        structure: FileStructure,
    ) -> None:
        for diagnostic in raw_diagnostics:
            span = diagnostic.span
            start_line = 1
            end_line = 1
            if span is not None:
                start_line = span.start_line + 1
                end_line = span.end_line + 1

            structure.diagnostics.append(
                ParseDiagnostic(
                    file_path=file_path,
                    message=str(diagnostic.message),
                    severity=str(diagnostic.severity),
                    start_line=start_line,
                    end_line=end_line,
                )
            )

    def _validate_structure(self, structure: CodebaseStructure) -> None:
        self._repair_parent_ids(structure.entities)
        for file_structure in structure.files:
            self._repair_parent_ids(file_structure.entities)
            file_structure.relationships = []
        structure.relationships = []

    @staticmethod
    def _repair_parent_ids(entities: list[CodeEntity]) -> None:
        entity_ids = {entity.id for entity in entities}
        for entity in entities:
            if (
                entity.parent_id is not None
                and entity.parent_id not in entity_ids
            ):
                entity.parent_id = None

    @staticmethod
    def _kind_label(kind: object) -> str:
        if kind is None:
            return ""

        label = str(kind).strip()
        if "." in label:
            label = label.rsplit(".", 1)[-1]
        if "(" in label:
            label = label.split("(", 1)[0]
        return label.strip()

    @classmethod
    def _is_export_identifier(cls, name: str | None) -> bool:
        if not isinstance(name, str):
            return False

        text = name.strip()
        if not text:
            return False
        if text[0] in {"@", "#"}:
            return False

        for character in text:
            if character.isspace() or character in cls.NON_IDENTIFIER_CHARS:
                return False
        return True

    @classmethod
    def _identifier_tokens(cls, text: str) -> list[str]:
        tokens: list[str] = []
        current: list[str] = []
        for character in text:
            if character.isspace() or character in cls.NON_IDENTIFIER_CHARS:
                if current:
                    tokens.append("".join(current))
                    current = []
            else:
                current.append(character)
        if current:
            tokens.append("".join(current))
        return tokens

    @staticmethod
    def _normalize_decorator_name(decorator: str) -> str:
        if not isinstance(decorator, str):
            return ""

        text = decorator.strip()
        if text.startswith("@"):
            text = text[1:].strip()

        for character in ("(", "[", "{", " "):
            index = text.find(character)
            if index >= 0:
                text = text[:index]
        return text.strip()

    @staticmethod
    def _line_from_span(span: Span | None) -> int:
        if span is None:
            return 0
        return span.start_line + 1

    @staticmethod
    def _create_entity_id(
        file_path: str,
        start_byte: int,
        end_byte: int,
        kind: str,
        name: str | None,
    ) -> str:
        raw = (
            f"{file_path}:"
            f"{start_byte}:"
            f"{end_byte}:"
            f"{kind}:"
            f"{name or ''}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
