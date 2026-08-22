from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# AGENT 1
# ============================================================

@dataclass
class FileInfo:
    path: str
    extension: str
    size: int
    category: str


@dataclass
class RepositoryInfo:
    name: str
    url: str
    default_branch: str

    total_files: int
    total_directories: int

    languages: dict[str, int] = field(
        default_factory=dict
    )

    source_files: list[str] = field(
        default_factory=list
    )

    test_files: list[str] = field(
        default_factory=list
    )

    documentation_files: list[str] = field(
        default_factory=list
    )

    configuration_files: list[str] = field(
        default_factory=list
    )

    asset_files: list[str] = field(
        default_factory=list
    )

    generated_files: list[str] = field(
        default_factory=list
    )

    build_files: list[str] = field(
        default_factory=list
    )

    other_files: list[str] = field(
        default_factory=list
    )

    files: list[FileInfo] = field(
        default_factory=list
    )

    structure: Optional[CodebaseStructure] = None

    semantic: Optional[GeminiSemanticResult] = None


# ============================================================
# AGENT 2 — UNIVERSAL CODE STRUCTURE
# ============================================================

@dataclass
class CodeEntity:
    """
    Universal structural entity.

    No language-specific or framework-specific fields.
    """

    id: str
    file_path: str

    kind: str
    name: Optional[str]

    start_line: int
    end_line: int

    start_column: int
    end_column: int

    parent_id: Optional[str] = None

    visibility: Optional[str] = None

    signature: Optional[str] = None

    decorators: list[str] = field(
        default_factory=list
    )

    doc_comment: Optional[str] = None


@dataclass
class CodeImportItem:

    name: str

    alias: Optional[str] = None


@dataclass
class CodeImport:

    file_path: str

    source: str

    items: list[CodeImportItem] = field(
        default_factory=list
    )

    is_wildcard: bool = False

    line: int = 0


@dataclass
class CodeExport:

    file_path: str

    name: Optional[str]

    source: Optional[str]

    export_type: str

    line: int = 0


@dataclass
class CodeRelationship:
    """
    Generic relationship between structural entities.

    relation_type is intentionally free-form.

    We do not define language/framework-specific
    relationship types.
    """

    file_path: str

    source_entity_id: str

    target_name: str

    relation_type: str

    line: int = 0


@dataclass
class ParseDiagnostic:

    file_path: str

    message: str

    severity: str

    start_line: int

    end_line: int


@dataclass
class FileStructure:

    file_path: str

    language: str

    line_count: int

    code_lines: int

    comment_lines: int

    blank_lines: int

    error_count: int

    max_depth: int

    entities: list[CodeEntity] = field(
        default_factory=list
    )

    imports: list[CodeImport] = field(
        default_factory=list
    )

    exports: list[CodeExport] = field(
        default_factory=list
    )

    relationships: list[CodeRelationship] = field(
        default_factory=list
    )

    diagnostics: list[ParseDiagnostic] = field(
        default_factory=list
    )

    parser_imports: list[dict] = field(
        default_factory=list
    )

    parser_exports: list[dict] = field(
        default_factory=list
    )


@dataclass
class CodebaseStructure:

    files: list[FileStructure] = field(
        default_factory=list
    )

    entities: list[CodeEntity] = field(
        default_factory=list
    )

    imports: list[CodeImport] = field(
        default_factory=list
    )

    exports: list[CodeExport] = field(
        default_factory=list
    )

    relationships: list[CodeRelationship] = field(
        default_factory=list
    )

    diagnostics: list[ParseDiagnostic] = field(
        default_factory=list
    )


# ============================================================
# GEMINI — AGENT 2 SEMANTIC RESULT
# ============================================================

@dataclass
class GeminiImportItem:

    name: str

    alias: Optional[str] = None


@dataclass
class GeminiImport:

    source: str

    file_path: Optional[str] = None

    items: list[GeminiImportItem] = field(
        default_factory=list
    )

    is_wildcard: bool = False

    line: int = 0


@dataclass
class GeminiExport:

    name: Optional[str]

    source: Optional[str]

    export_type: str

    file_path: Optional[str] = None

    line: int = 0


@dataclass
class GeminiRelationship:

    source_entity_id: str

    target_name: str

    relation_type: str

    file_path: Optional[str] = None

    line: int = 0


@dataclass
class GeminiSemanticResult:

    imports: list[GeminiImport] = field(
        default_factory=list
    )

    exports: list[GeminiExport] = field(
        default_factory=list
    )

    relationships: list[GeminiRelationship] = field(
        default_factory=list
    )

@dataclass
class ArchitectureComponent:
    name: str
    description: str

    files: list[str] = field(
        default_factory=list
    )

    entities: list[str] = field(
        default_factory=list
    )


@dataclass
class ArchitectureFlow:
    name: str
    description: str

    steps: list[str] = field(
        default_factory=list
    )


@dataclass
class ArchitectureResult:
    purpose: str
    summary: str

    technologies: list[str] = field(
        default_factory=list
    )

    major_capabilities: list[str] = field(
        default_factory=list
    )

    architecture_style: Optional[str] = None

    components: list[ArchitectureComponent] = field(
        default_factory=list
    )

    flows: list[ArchitectureFlow] = field(
        default_factory=list
    )


@dataclass
class ArchaeologicalResult:
    findings: list[ArchaeologicalFinding] = field(
        default_factory=list
    )

@dataclass
class ArchaeologicalFinding:
    title: str
    category: str
    severity: str
    description: str

    affected_files: list[str] = field(
        default_factory=list
    )

    evidence: list[str] = field(
        default_factory=list
    )

    confidence: float = 0.0

    evidence_refs: list[dict] = field(
        default_factory=list
    )

    confidence_reason: str = ""

    severity_reason: str = ""


@dataclass
class ReportResult:
    overview: str = ""

    purpose: str = ""

    technologies: list[str] = field(
        default_factory=list
    )

    architecture: str = ""

    components: list[dict] = field(
        default_factory=list
    )

    flows: list[dict] = field(
        default_factory=list
    )

    findings: list[dict] = field(
        default_factory=list
    )

    risks: list[str] = field(
        default_factory=list
    )

    solutions: list[dict] = field(
        default_factory=list
    )