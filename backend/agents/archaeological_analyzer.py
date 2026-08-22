# from __future__ import annotations

# import json
# import os
# from typing import Any

# from dotenv import load_dotenv

# from llm import GeminiClient
# from models import (
#     ArchaeologicalFinding,
#     ArchaeologicalResult,
#     CodebaseStructure,
#     GeminiSemanticResult,
#     ArchitectureResult,
# )

# load_dotenv()


# class ArchaeologicalAnalyzer:
#     """
#     Agent 4 — Archaeological Analysis.

#     Uses the completed outputs from:
#     - Tree-sitter
#     - Semantic Normalizer
#     - Agent 3 Architecture Analysis

#     Makes one repository-level Gemini call.
#     """

#     def __init__(self):
#         self.llm = GeminiClient(
#             api_key=os.getenv(
#                 "GEMINI_ARCHAEOLOGY_API_KEY"
#             )
#         )

#     def analyze(
#         self,
#         structure: CodebaseStructure,
#         semantic: GeminiSemanticResult,
#         architecture: ArchitectureResult,
#     ) -> ArchaeologicalResult:

#         evidence = self._build_evidence(
#             structure,
#             semantic,
#             architecture,
#         )

#         prompt = self._build_prompt(evidence)

#         response = self.llm.generate_json(prompt)

#         return self._parse_result(response)

#     # ========================================================
#     # EVIDENCE
#     # ========================================================

#     def _build_evidence(
#         self,
#         structure: CodebaseStructure,
#         semantic: GeminiSemanticResult,
#         architecture: ArchitectureResult,
#     ) -> dict[str, Any]:

#         return {
#             "files": [
#                 {
#                     "file_path": file.file_path,
#                     "language": file.language,
#                     "line_count": file.line_count,
#                     "code_lines": file.code_lines,
#                     "comment_lines": file.comment_lines,
#                     "blank_lines": file.blank_lines,
#                     "error_count": file.error_count,
#                     "max_depth": file.max_depth,
#                     "entity_count": len(file.entities),
#                     "import_count": len(file.imports),
#                     "export_count": len(file.exports),
#                     "relationship_count": len(
#                         file.relationships
#                     ),
#                 }
#                 for file in structure.files
#             ],

#             "relationships": [
#                 {
#                     "file_path": relationship.file_path,
#                     "source_entity_id": (
#                         relationship.source_entity_id
#                     ),
#                     "target_name": (
#                         relationship.target_name
#                     ),
#                     "relation_type": (
#                         relationship.relation_type
#                     ),
#                     "line": relationship.line,
#                 }
#                 for relationship in semantic.relationships
#             ],

#             "architecture": {
#                 "style": (
#                     architecture.architecture_style
#                 ),

#                 "components": [
#                     {
#                         "name": component.name,
#                         "description": (
#                             component.description
#                         ),
#                         "files": component.files,
#                         "entities": component.entities,
#                     }
#                     for component
#                     in architecture.components
#                 ],

#                 "flows": [
#                     {
#                         "name": flow.name,
#                         "description": (
#                             flow.description
#                         ),
#                         "steps": flow.steps,
#                     }
#                     for flow
#                     in architecture.flows
#                 ],
#             },
#         }

#     # ========================================================
#     # PROMPT
#     # ========================================================

#     def _build_prompt(
#         self,
#         evidence: dict[str, Any],
#     ) -> str:

#         evidence_json = json.dumps(
#             evidence,
#             indent=2,
#             ensure_ascii=False,
#         )

#         prompt = """
# You are Agent 4 of a code archaeology system.

# Identify meaningful areas of the repository that may be
# difficult to maintain, understand, or safely modify.

# Use:
# - Tree-sitter structural metrics
# - normalized semantic relationships
# - Agent 3 architecture analysis

# Do not parse source code.
# Do not invent problems.

# Look for:
# - complexity hotspots
# - highly coupled components
# - isolated or potentially unused areas
# - overlapping responsibilities
# - architectural inconsistencies
# - legacy or outdated signals when supported by evidence
# - maintenance risks
# - areas worth investigating

# RULES:

# 1. Every finding must be supported by the supplied evidence.
# 2. Separate observed facts from inference.
# 3. Do not call something dead code unless evidence supports it.
# 4. Do not call something legacy merely because it looks old.
# 5. Do not assume framework conventions prove behavior.
# 6. Prefer a few strong findings over many weak findings.
# 7. Do not report normal architecture as a problem.
# 8. If evidence is insufficient, omit the finding.
# 9. Confidence must reflect the evidence strength.

# SEVERITY:
# Use only:
# - low
# - medium
# - high

# CONFIDENCE:
# 0.90–1.00 = directly supported
# 0.75–0.89 = strongly supported inference
# 0.50–0.74 = weaker inference

# Do not include findings below 0.50 confidence.

# Return ONLY valid JSON.

# Expected format:

# {
#   "findings": [
#     {
#       "title": "...",
#       "category": "...",
#       "severity": "low",
#       "description": "...",
#       "affected_files": [],
#       "evidence": [],
#       "confidence": 0.0
#     }
#   ]
# }

# Repository evidence:
# """

#         return prompt + evidence_json

#     # ========================================================
#     # PARSER
#     # ========================================================

#     def _parse_result(
#         self,
#         data: Any,
#     ) -> ArchaeologicalResult:

#         if not isinstance(data, dict):
#             raise RuntimeError(
#                 "Agent 4 response must be a JSON object."
#             )

#         raw_findings = data.get(
#             "findings",
#             [],
#         )

#         if not isinstance(
#             raw_findings,
#             list,
#         ):
#             raw_findings = []

#         findings = []

#         for item in raw_findings:

#             if not isinstance(
#                 item,
#                 dict,
#             ):
#                 continue

#             title = item.get("title")
#             category = item.get("category")
#             severity = item.get("severity")
#             description = item.get(
#                 "description",
#                 "",
#             )

#             if not isinstance(title, str):
#                 continue

#             if not isinstance(category, str):
#                 continue

#             if not isinstance(severity, str):
#                 continue

#             if not isinstance(
#                 description,
#                 str,
#             ):
#                 description = ""

#             affected_files = item.get(
#                 "affected_files",
#                 [],
#             )

#             if not isinstance(
#                 affected_files,
#                 list,
#             ):
#                 affected_files = []

#             affected_files = [
#                 value
#                 for value in affected_files
#                 if isinstance(value, str)
#             ]

#             evidence = item.get(
#                 "evidence",
#                 [],
#             )

#             if not isinstance(
#                 evidence,
#                 list,
#             ):
#                 evidence = []

#             evidence = [
#                 value
#                 for value in evidence
#                 if isinstance(value, str)
#             ]

#             confidence = item.get(
#                 "confidence",
#                 0.0,
#             )

#             if not isinstance(
#                 confidence,
#                 (int, float),
#             ):
#                 confidence = 0.0

#             confidence = max(
#                 0.0,
#                 min(
#                     1.0,
#                     float(confidence),
#                 ),
#             )

#             if confidence < 0.50:
#                 continue

#             findings.append(
#                 ArchaeologicalFinding(
#                     title=title,
#                     category=category,
#                     severity=severity,
#                     description=description,
#                     affected_files=affected_files,
#                     evidence=evidence,
#                     confidence=confidence,
#                 )
#             )

#         return ArchaeologicalResult(
#             findings=findings
#         )

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from llm import GeminiClient
from models import (
    ArchaeologicalFinding,
    ArchaeologicalResult,
    CodebaseStructure,
    GeminiSemanticResult,
    ArchitectureResult,
)

load_dotenv()


class ArchaeologicalAnalyzer:
    """
    Agent 4 — Archaeological Analysis.

    Uses the completed outputs from:
    - Tree-sitter
    - Semantic Normalizer
    - Agent 3 Architecture Analysis

    Makes one repository-level Gemini call.
    """

    def __init__(self):
        self.llm = GeminiClient(
            api_key=os.getenv(
                "GEMINI_ARCHAEOLOGY_API_KEY"
            )
        )

    def analyze(
        self,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
        architecture: ArchitectureResult,
    ) -> ArchaeologicalResult:

        evidence = self._build_evidence(
            structure,
            semantic,
            architecture,
        )

        prompt = self._build_prompt(evidence)

        response = self.llm.generate_json(prompt)

        result = self._parse_result(response)

        self._validate_result(
            result,
            structure,
            semantic,
            architecture,
        )

        return result

    # ========================================================
    # EVIDENCE
    # ========================================================

    def _build_evidence(
        self,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
        architecture: ArchitectureResult,
    ) -> dict[str, Any]:

        return {
            "files": [
                {
                    "file_path": file.file_path,
                    "language": file.language,
                    "line_count": file.line_count,
                    "code_lines": file.code_lines,
                    "comment_lines": file.comment_lines,
                    "blank_lines": file.blank_lines,
                    "error_count": file.error_count,
                    "max_depth": file.max_depth,
                    "entity_count": len(file.entities),
                    "import_count": len(file.imports),
                    "export_count": len(file.exports),
                    "relationship_count": len(
                        file.relationships
                    ),
                }
                for file in structure.files
            ],

            "relationships": [
                {
                    "file_path": relationship.file_path,
                    "source_entity_id": (
                        relationship.source_entity_id
                    ),
                    "target_name": (
                        relationship.target_name
                    ),
                    "relation_type": (
                        relationship.relation_type
                    ),
                    "line": relationship.line,
                }
                for relationship in semantic.relationships
            ],

            "architecture": {
                "style": (
                    architecture.architecture_style
                ),

                "components": [
                    {
                        "name": component.name,
                        "description": (
                            component.description
                        ),
                        "files": component.files,
                        "entities": component.entities,
                    }
                    for component
                    in architecture.components
                ],

                "flows": [
                    {
                        "name": flow.name,
                        "description": (
                            flow.description
                        ),
                        "steps": flow.steps,
                    }
                    for flow
                    in architecture.flows
                ],
            },
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

        prompt = """
You are Agent 4 of a code archaeology system.

Identify meaningful areas of the repository that may be
difficult to maintain, understand, or safely modify.

Use:
- Tree-sitter structural metrics
- normalized semantic relationships
- Agent 3 architecture analysis

Do not parse source code.
Do not invent problems.

Look for:
- complexity hotspots
- highly coupled components
- isolated or potentially unused areas
- overlapping responsibilities
- architectural inconsistencies
- legacy or outdated signals when supported by evidence
- maintenance risks
- areas worth investigating

============================================================
EVIDENCE POLICY
============================================================

Every finding MUST be supported by supplied evidence.

Separate:
- observed facts
- strong inferences
- weaker inferences

Do not call something dead code unless the evidence supports it.

Do not call something legacy merely because it looks old.

Do not assume framework conventions prove behavior.

Prefer a few strong findings over many weak findings.

Do not report normal architecture as a problem.

If evidence is insufficient, omit the finding.

============================================================
RELATIONSHIP POLICY
============================================================

Only use relationships supported by the supplied relationships,
entities, architecture components, architecture flows, or file
structure.

Do not invent target entities.

If a target cannot be matched to supplied evidence, do not treat
it as an observed relationship.

When a relationship is inferred rather than explicit, clearly
identify it as an inference.

Do not invent:
- API calls
- database operations
- authentication behavior
- execution order
- framework behavior
- dependencies

unless supported by the supplied evidence.

============================================================
FLOW POLICY
============================================================

Do not reconstruct a flow merely because it is conventional.

Every flow step must be supported by supplied evidence.

For each flow, distinguish:

"explicit"
= directly supported by supplied relationships or architecture.

"strong_inference"
= not directly stated but strongly supported by multiple pieces
  of supplied evidence.

Do not include weak or speculative flows.

============================================================
FINDING POLICY
============================================================

A finding should contain:

- the problem/observation
- affected files
- evidence
- confidence
- why the confidence is appropriate
- why the severity is appropriate

Do not create a finding only because a metric is unusual.

A metric becomes a finding only when it represents a meaningful
maintenance, architectural, reliability, or archaeological concern.

============================================================
SEVERITY
============================================================

Use only:

- low
- medium
- high

High:
Potentially blocks execution/build/deployment or represents a
major architectural/reliability/security concern.

Medium:
Meaningful maintainability, complexity, coupling, or reliability
concern.

Low:
Minor maintainability or archaeological observation.

============================================================
CONFIDENCE
============================================================

0.90–1.00 = directly supported
0.75–0.89 = strongly supported inference
0.50–0.74 = weaker inference

Do not include findings below 0.50 confidence.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Expected format:

{
  "findings": [
    {
      "title": "...",
      "category": "...",
      "severity": "low",
      "description": "...",
      "affected_files": [],
      "evidence": [],
      "evidence_refs": [],
      "confidence": 0.0,
      "confidence_reason": "...",
      "severity_reason": "..."
    }
  ]
}

For evidence_refs use only evidence that exists in the supplied
repository evidence.

Example:

"evidence_refs": [
  {
    "type": "file_metric",
    "file": "...",
    "metric": "max_depth",
    "value": 28
  }
]

For a relationship:

"evidence_refs": [
  {
    "type": "relationship",
    "source_entity_id": "...",
    "target_name": "...",
    "relation_type": "uses"
  }
]

Do not create evidence references for facts that are not present
in the supplied evidence.

============================================================
REPOSITORY EVIDENCE
============================================================
"""

        return prompt + evidence_json

    # ========================================================
    # PARSER
    # ========================================================

    def _parse_result(
        self,
        data: Any,
    ) -> ArchaeologicalResult:

        if not isinstance(data, dict):
            raise RuntimeError(
                "Agent 4 response must be a JSON object."
            )

        raw_findings = data.get(
            "findings",
            [],
        )

        if not isinstance(
            raw_findings,
            list,
        ):
            raw_findings = []

        findings = []

        for item in raw_findings:

            if not isinstance(
                item,
                dict,
            ):
                continue

            title = item.get("title")
            category = item.get("category")
            severity = item.get("severity")
            description = item.get(
                "description",
                "",
            )

            if not isinstance(title, str):
                continue

            if not isinstance(category, str):
                continue

            if not isinstance(severity, str):
                continue

            if severity not in {
                "low",
                "medium",
                "high",
            }:
                continue

            if not isinstance(
                description,
                str,
            ):
                description = ""

            affected_files = item.get(
                "affected_files",
                [],
            )

            if not isinstance(
                affected_files,
                list,
            ):
                affected_files = []

            affected_files = [
                value
                for value in affected_files
                if isinstance(value, str)
            ]

            evidence = item.get(
                "evidence",
                [],
            )

            if not isinstance(
                evidence,
                list,
            ):
                evidence = []

            evidence = [
                value
                for value in evidence
                if isinstance(value, str)
            ]

            evidence_refs = item.get(
                "evidence_refs",
                [],
            )

            if not isinstance(
                evidence_refs,
                list,
            ):
                evidence_refs = []

            evidence_refs = [
                value
                for value in evidence_refs
                if isinstance(value, dict)
            ]

            confidence = item.get(
                "confidence",
                0.0,
            )

            if not isinstance(
                confidence,
                (int, float),
            ):
                confidence = 0.0

            confidence = max(
                0.0,
                min(
                    1.0,
                    float(confidence),
                ),
            )

            if confidence < 0.50:
                continue

            confidence_reason = item.get(
                "confidence_reason",
                "",
            )

            if not isinstance(
                confidence_reason,
                str,
            ):
                confidence_reason = ""

            severity_reason = item.get(
                "severity_reason",
                "",
            )

            if not isinstance(
                severity_reason,
                str,
            ):
                severity_reason = ""

            if not evidence_refs:
                continue

            findings.append(
                ArchaeologicalFinding(
                    title=title,
                    category=category,
                    severity=severity,
                    description=description,
                    affected_files=affected_files,
                    evidence=evidence,
                    confidence=confidence,
                    evidence_refs=evidence_refs,
                    confidence_reason=confidence_reason,
                    severity_reason=severity_reason,
                )
            )

        return ArchaeologicalResult(
            findings=findings
        )

    # ========================================================
    # DETERMINISTIC VALIDATION
    # ========================================================

    def _validate_result(
        self,
        result: ArchaeologicalResult,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
        architecture: ArchitectureResult,
    ) -> None:

        known_files = {
            file.file_path
            for file in structure.files
        }

        known_entity_ids = {
            entity.id
            for entity in structure.entities
        }

        known_relationships = {
            (
                relationship.source_entity_id,
                relationship.target_name,
                relationship.relation_type,
            )
            for relationship in semantic.relationships
        }

        known_component_files = {
            file_path
            for component in architecture.components
            for file_path in component.files
        }

        for finding in result.findings:

            finding.affected_files = [
                file_path
                for file_path in finding.affected_files
                if file_path in known_files
                or file_path in known_component_files
            ]

            validated_refs = []

            for ref in finding.evidence_refs:

                if not isinstance(
                    ref,
                    dict,
                ):
                    continue

                ref_type = ref.get("type")

                if ref_type == "file_metric":

                    file_path = ref.get("file")

                    if file_path not in known_files:
                        continue

                    validated_refs.append(ref)

                elif ref_type == "relationship":

                    source_entity_id = ref.get(
                        "source_entity_id"
                    )

                    target_name = ref.get(
                        "target_name"
                    )

                    relation_type = ref.get(
                        "relation_type"
                    )

                    if (
                        source_entity_id
                        not in known_entity_ids
                    ):
                        continue

                    if (
                        source_entity_id,
                        target_name,
                        relation_type,
                    ) not in known_relationships:
                        continue

                    validated_refs.append(ref)

            finding.evidence_refs = validated_refs

        result.findings = [
            finding
            for finding in result.findings
            if finding.evidence_refs
        ]