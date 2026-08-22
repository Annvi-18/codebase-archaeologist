# from __future__ import annotations

# import json
# import os
# from typing import Any

# from dotenv import load_dotenv

# from llm import GeminiClient
# from models import (
#     RepositoryInfo,
#     CodebaseStructure,
#     GeminiSemanticResult,
#     ArchitectureResult,
#     ArchaeologicalResult,
#     ReportResult,
# )

# load_dotenv()


# class ReportGenerator:
#     """
#     Final report generation layer.

#     Consumes the completed outputs of Agents 1–4
#     and produces a concise, developer-facing report.

#     This class does not perform repository analysis.
#     """

#     def __init__(self):
#         self.llm = GeminiClient(
#             api_key=os.getenv(
#                 "GEMINI_REPORT_API_KEY"
#             )
#         )

#     def generate(
#         self,
#         repository: RepositoryInfo,
#         structure: CodebaseStructure,
#         semantic: GeminiSemanticResult,
#         architecture: ArchitectureResult,
#         archaeology: ArchaeologicalResult,
#     ) -> ReportResult:

#         evidence = self._build_evidence(
#             repository,
#             structure,
#             semantic,
#             architecture,
#             archaeology,
#         )

#         prompt = self._build_prompt(evidence)

#         response = self.llm.generate_json(prompt)

#         return self._parse_result(response)

#     # ========================================================
#     # EVIDENCE
#     # ========================================================

#     def _build_evidence(
#         self,
#         repository: RepositoryInfo,
#         structure: CodebaseStructure,
#         semantic: GeminiSemanticResult,
#         architecture: ArchitectureResult,
#         archaeology: ArchaeologicalResult,
#     ) -> dict[str, Any]:

#         return {
#             "repository": {
#                 "name": repository.name,
#                 "url": repository.url,
#                 "default_branch": repository.default_branch,
#                 "total_files": repository.total_files,
#                 "total_directories": (
#                     repository.total_directories
#                 ),
#                 "languages": repository.languages,
#                 "source_files": repository.source_files,
#                 "test_files": repository.test_files,
#                 "documentation_files": (
#                     repository.documentation_files
#                 ),
#                 "configuration_files": (
#                     repository.configuration_files
#                 ),
#             },

#             "structure": {
#                 "files": [
#                     {
#                         "file_path": file.file_path,
#                         "language": file.language,
#                         "line_count": file.line_count,
#                         "code_lines": file.code_lines,
#                         "comment_lines": (
#                             file.comment_lines
#                         ),
#                         "blank_lines": (
#                             file.blank_lines
#                         ),
#                         "entity_count": len(
#                             file.entities
#                         ),
#                         "import_count": len(
#                             file.imports
#                         ),
#                         "export_count": len(
#                             file.exports
#                         ),
#                         "relationship_count": len(
#                             file.relationships
#                         ),
#                         "error_count": file.error_count,
#                         "max_depth": file.max_depth,
#                     }
#                     for file in structure.files
#                 ],
#             },

#             "semantic": {
#                 "imports": [
#                     {
#                         "file_path": item.file_path,
#                         "source": item.source,
#                         "items": [
#                             {
#                                 "name": imported.name,
#                                 "alias": imported.alias,
#                             }
#                             for imported in item.items
#                         ],
#                     }
#                     for item in semantic.imports
#                 ],

#                 "exports": [
#                     {
#                         "file_path": item.file_path,
#                         "name": item.name,
#                         "source": item.source,
#                         "export_type": (
#                             item.export_type
#                         ),
#                     }
#                     for item in semantic.exports
#                 ],

#                 "relationships": [
#                     {
#                         "file_path": item.file_path,
#                         "source_entity_id": (
#                             item.source_entity_id
#                         ),
#                         "target_name": (
#                             item.target_name
#                         ),
#                         "relation_type": (
#                             item.relation_type
#                         ),
#                         "line": item.line,
#                     }
#                     for item in semantic.relationships
#                 ],
#             },

#             # =================================================
#             # AGENT 3
#             # =================================================

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

#             # =================================================
#             # AGENT 4
#             # =================================================

#             "archaeology": {
#                 "findings": [
#                     {
#                         "title": finding.title,
#                         "category": finding.category,
#                         "severity": finding.severity,
#                         "description": (
#                             finding.description
#                         ),
#                         "affected_files": (
#                             finding.affected_files
#                         ),
#                         "evidence": finding.evidence,
#                         "evidence_refs": (
#                             finding.evidence_refs
#                         ),
#                         "confidence": (
#                             finding.confidence
#                         ),
#                         "confidence_reason": (
#                             finding.confidence_reason
#                         ),
#                         "severity_reason": (
#                             finding.severity_reason
#                         ),
#                     }
#                     for finding
#                     in archaeology.findings
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
# You are the final report generator of a code archaeology system.

# Agents 1–4 have already analyzed the repository.

# Your job is to turn their results into a clear,
# developer-facing repository report.

# You are NOT performing new repository analysis.

# Use ONLY the supplied evidence.

# Do not invent:
# - technologies
# - components
# - files
# - relationships
# - flows
# - dependencies
# - architecture
# - risks
# - repository purpose

# If evidence is insufficient, omit the claim.

# ============================================================
# REPORT
# ============================================================

# 1. OVERVIEW

# Briefly explain what the repository is and what it does.

# Keep it to approximately 2–4 sentences.

# ------------------------------------------------------------

# 2. PURPOSE

# Explain the main purpose and important capabilities
# supported by the evidence.

# ------------------------------------------------------------

# 3. TECHNOLOGIES

# List the actual languages, frameworks, libraries,
# platforms, databases, and other technologies supported
# by the evidence.

# Do not infer technologies from convention.

# ------------------------------------------------------------

# 4. ARCHITECTURE

# Explain:

# - overall architecture style
# - major layers
# - responsibility of the layers
# - important component relationships
# - important frontend/backend/database relationships
#   when supported

# This should explain how the repository is organized,
# not merely name the architecture style.

# ------------------------------------------------------------

# 5. COMPONENTS

# Include only the important architectural components.

# For each component return:

# {
#   "name": "...",
#   "responsibility": "...",
#   "key_entities": [],
#   "connections": []
# }

# Rules:

# - Do NOT include a full file list.
# - Do NOT list every entity.
# - Select only the most important entities.
# - Keep the responsibility concise.
# - Connections must be supported by Agent 3 evidence.

# ------------------------------------------------------------

# 6. FLOWS

# Include only the important application flows.

# For each flow return:

# {
#   "name": "...",
#   "steps": []
# }

# Rules:

# - Do NOT include a separate description.
# - Steps should explain the flow clearly.
# - Preserve the actual order identified by Agent 3.
# - Do not invent runtime behavior.
# - Do not create flows that are not supported by evidence.

# ------------------------------------------------------------

# 7. FINDINGS

# Preserve the meaningful findings from Agent 4.

# For each finding return:

# {
#   "title": "...",
#   "category": "...",
#   "severity": "...",
#   "description": "...",
#   "affected_files": [],
#   "evidence": [],
#   "confidence": 0.0
# }

# Do not create new findings.

# ------------------------------------------------------------

# 8. RISKS

# Explain the practical implications of the findings.

# Focus on:

# - maintainability
# - complexity
# - reliability
# - architectural risk
# - modification risk

# Do not simply repeat the finding description.

# ============================================================
# DETAIL LEVEL
# ============================================================

# Overview, Purpose, and Technologies:
# concise.

# Architecture:
# detailed enough to understand the system structure.

# Components:
# concise and selective.

# Flows:
# clear and step-based.

# Findings:
# detailed and evidence-based.

# Risks:
# practical and concise.

# Do not produce unnecessary text.

# The report should feel like a curated technical
# understanding of the repository, not a dump of
# everything discovered by the previous agents.

# ============================================================
# GROUNDING
# ============================================================

# Every important claim must be supported by supplied evidence.

# Do not turn an inference into a fact.

# Do not invent missing information.

# ============================================================
# OUTPUT
# ============================================================

# Return ONLY valid JSON.

# Use exactly this structure:

# {
#   "overview": "...",
#   "purpose": "...",
#   "technologies": [],

#   "architecture": "...",

#   "components": [
#     {
#       "name": "...",
#       "responsibility": "...",
#       "key_entities": [],
#       "connections": []
#     }
#   ],

#   "flows": [
#     {
#       "name": "...",
#       "steps": []
#     }
#   ],

#   "findings": [
#     {
#       "title": "...",
#       "category": "...",
#       "severity": "...",
#       "description": "...",
#       "affected_files": [],
#       "evidence": [],
#       "confidence": 0.0
#     }
#   ],

#   "risks": []
# }

# Do not return components, flows, or findings as strings.

# Repository evidence:
# """

#         return prompt + evidence_json

#     # ========================================================
#     # RESPONSE PARSER
#     # ========================================================

#     def _parse_result(
#         self,
#         data: Any,
#     ) -> ReportResult:

#         if not isinstance(data, dict):
#             raise RuntimeError(
#                 "Report response must be a JSON object."
#             )

#         overview = data.get(
#             "overview",
#             "",
#         )

#         purpose = data.get(
#             "purpose",
#             "",
#         )

#         architecture = data.get(
#             "architecture",
#             "",
#         )

#         technologies = data.get(
#             "technologies",
#             [],
#         )

#         components = data.get(
#             "components",
#             [],
#         )

#         flows = data.get(
#             "flows",
#             [],
#         )

#         findings = data.get(
#             "findings",
#             [],
#         )

#         risks = data.get(
#             "risks",
#             [],
#         )

#         if not isinstance(
#             overview,
#             str,
#         ):
#             overview = ""

#         if not isinstance(
#             purpose,
#             str,
#         ):
#             purpose = ""

#         if not isinstance(
#             architecture,
#             str,
#         ):
#             architecture = ""

#         def clean_strings(
#             value: Any,
#         ) -> list[str]:

#             if not isinstance(
#                 value,
#                 list,
#             ):
#                 return []

#             return [
#                 item
#                 for item in value
#                 if isinstance(
#                     item,
#                     str,
#                 )
#             ]

#         def clean_objects(
#             value: Any,
#         ) -> list[dict]:

#             if not isinstance(
#                 value,
#                 list,
#             ):
#                 return []

#             return [
#                 item
#                 for item in value
#                 if isinstance(
#                     item,
#                     dict,
#                 )
#             ]

#         return ReportResult(
#             overview=overview,

#             purpose=purpose,

#             technologies=clean_strings(
#                 technologies
#             ),

#             architecture=architecture,

#             components=clean_objects(
#                 components
#             ),

#             flows=clean_objects(
#                 flows
#             ),

#             findings=clean_objects(
#                 findings
#             ),

#             risks=clean_strings(
#                 risks
#             ),
#         )



from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from llm import GeminiClient
from models import (
    RepositoryInfo,
    CodebaseStructure,
    GeminiSemanticResult,
    ArchitectureResult,
    ArchaeologicalResult,
    ReportResult,
)

load_dotenv()


class ReportGenerator:
    """
    Final report generation layer.

    Consumes the completed outputs of Agents 1–4
    and produces a developer-facing report.

    This class does not perform repository analysis.
    """

    def __init__(self):
        self.llm = GeminiClient(
            api_key=os.getenv(
                "GEMINI_REPORT_API_KEY"
            )
        )

    def generate(
        self,
        repository: RepositoryInfo,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
        architecture: ArchitectureResult,
        archaeology: ArchaeologicalResult,
    ) -> ReportResult:

        evidence = self._build_evidence(
            repository,
            structure,
            semantic,
            architecture,
            archaeology,
        )

        prompt = self._build_prompt(evidence)

        response = self.llm.generate_json(prompt)

        return self._parse_result(response)

    # ========================================================
    # EVIDENCE
    # ========================================================

    def _build_evidence(
        self,
        repository: RepositoryInfo,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
        architecture: ArchitectureResult,
        archaeology: ArchaeologicalResult,
    ) -> dict[str, Any]:

        return {
            "repository": {
                "name": repository.name,
                "url": repository.url,
                "default_branch": repository.default_branch,
                "total_files": repository.total_files,
                "total_directories": (
                    repository.total_directories
                ),
                "languages": repository.languages,
                "source_files": repository.source_files,
                "test_files": repository.test_files,
                "documentation_files": (
                    repository.documentation_files
                ),
                "configuration_files": (
                    repository.configuration_files
                ),
            },

            "structure": {
                "files": [
                    {
                        "file_path": file.file_path,
                        "language": file.language,
                        "line_count": file.line_count,
                        "code_lines": file.code_lines,
                        "comment_lines": (
                            file.comment_lines
                        ),
                        "blank_lines": (
                            file.blank_lines
                        ),
                        "entity_count": len(
                            file.entities
                        ),
                        "import_count": len(
                            file.imports
                        ),
                        "export_count": len(
                            file.exports
                        ),
                        "relationship_count": len(
                            file.relationships
                        ),
                        "error_count": file.error_count,
                        "max_depth": file.max_depth,
                    }
                    for file in structure.files
                ],
            },

            "semantic": {
                "imports": [
                    {
                        "file_path": item.file_path,
                        "source": item.source,
                        "items": [
                            {
                                "name": imported.name,
                                "alias": imported.alias,
                            }
                            for imported in item.items
                        ],
                    }
                    for item in semantic.imports
                ],

                "exports": [
                    {
                        "file_path": item.file_path,
                        "name": item.name,
                        "source": item.source,
                        "export_type": (
                            item.export_type
                        ),
                    }
                    for item in semantic.exports
                ],

                "relationships": [
                    {
                        "file_path": item.file_path,
                        "source_entity_id": (
                            item.source_entity_id
                        ),
                        "target_name": (
                            item.target_name
                        ),
                        "relation_type": (
                            item.relation_type
                        ),
                        "line": item.line,
                    }
                    for item in semantic.relationships
                ],
            },

            # =================================================
            # AGENT 3
            # =================================================

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

            # =================================================
            # AGENT 4
            # =================================================

            "archaeology": {
                "findings": [
                    {
                        "title": finding.title,
                        "category": finding.category,
                        "severity": finding.severity,
                        "description": (
                            finding.description
                        ),
                        "affected_files": (
                            finding.affected_files
                        ),
                        "evidence": finding.evidence,
                        "evidence_refs": (
                            finding.evidence_refs
                        ),
                        "confidence": (
                            finding.confidence
                        ),
                        "confidence_reason": (
                            finding.confidence_reason
                        ),
                        "severity_reason": (
                            finding.severity_reason
                        ),
                    }
                    for finding
                    in archaeology.findings
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
You are the final report generator of a code archaeology system.

Agents 1–4 have already analyzed this repository.
Synthesize their outputs into one detailed,
developer-facing report.

Use ONLY the supplied evidence.
Do not invent facts, relationships, components,
flows, technologies, risks, or solutions.

Use all agents together:
- Agent 1: repository inventory and technologies
- Agent 2: structure, metrics, and normalized relationships
- Agent 3: architecture, components, and flows
- Agent 4: archaeological findings and evidence

============================================================
REPORT
============================================================

1. OVERVIEW

Give a detailed 3–5 sentence explanation of:
- what the repository is
- what it does
- its major capabilities
- its major system boundaries
- how the main parts work together

2. PURPOSE

Explain the repository's purpose and important capabilities
in enough detail for a developer unfamiliar with the project
to understand what the system is built to accomplish.

3. TECHNOLOGIES

List technologies supported by the supplied evidence.
Do not infer technologies from convention.

4. ARCHITECTURE

Give a detailed explanation of:
- architecture style
- major layers/components
- responsibility of each layer
- how major components interact
- important frontend/backend/database boundaries
- important relationships supporting the architecture

Do not merely name the architecture pattern.

5. COMPONENTS

Return only meaningful architectural components.

For each:

{
  "name": "...",
  "responsibility": "...",
  "key_entities": [],
  "connections": []
}

Responsibility should be 2–4 meaningful sentences explaining
what the component does and its role in the system.

Do NOT include a full file list.

Connections are IMPORTANT.

Build connections using:
- Agent 3 component entities
- Agent 3 component information
- Agent 2 normalized relationships
- Agent 2 source/target entities

Match relationships to the appropriate components.

Example:
"Controller → Service"
"Service → Repository"
"LoginComponent → AuthenticationService"

If supported relationships exist for a component,
connections should NOT be empty.

Never invent a connection.

6. FLOWS

For each important flow:

{
  "name": "...",
  "explanation": "...",
  "steps": []
}

Give a short explanation of what the flow accomplishes,
then provide the important ordered steps.

Use Agent 3 flows and Agent 2 relationships together.
Do not invent runtime behavior.

7. FINDINGS

Use Agent 4 findings.

Make each description detailed enough to explain:
- what was observed
- why it matters
- what area it affects

Preserve the supplied evidence, severity and confidence.

Do not create new findings.

8. RISKS

Explain the practical impact of the important findings,
especially maintainability, complexity, reliability,
architectural and modification risks.

9. SOLUTIONS

For significant findings, provide a grounded solution.

Each solution:

{
  "finding": "...",
  "solution": "...",
  "reason": "..."
}

Solutions must be based on the finding and available evidence.
Do not invent exact code changes when the evidence is insufficient.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use exactly:

{
  "overview": "...",
  "purpose": "...",
  "technologies": [],
  "architecture": "...",

  "components": [
    {
      "name": "...",
      "responsibility": "...",
      "key_entities": [],
      "connections": []
    }
  ],

  "flows": [
    {
      "name": "...",
      "explanation": "...",
      "steps": []
    }
  ],

  "findings": [
    {
      "title": "...",
      "category": "...",
      "severity": "...",
      "description": "...",
      "affected_files": [],
      "evidence": [],
      "confidence": 0.0
    }
  ],

  "risks": [],

  "solutions": [
    {
      "finding": "...",
      "solution": "...",
      "reason": "..."
    }
  ]
}

All fields must use the correct JSON types.
Do not return markdown.
Do not return explanations outside the JSON.

Repository evidence:
"""

        return prompt + evidence_json

    # ========================================================
    # RESPONSE PARSER
    # ========================================================

    def _parse_result(
        self,
        data: Any,
    ) -> ReportResult:

        if not isinstance(data, dict):
            raise RuntimeError(
                "Report response must be a JSON object."
            )

        overview = data.get(
            "overview",
            "",
        )

        purpose = data.get(
            "purpose",
            "",
        )

        architecture = data.get(
            "architecture",
            "",
        )

        technologies = data.get(
            "technologies",
            [],
        )

        components = data.get(
            "components",
            [],
        )

        flows = data.get(
            "flows",
            [],
        )

        findings = data.get(
            "findings",
            [],
        )

        risks = data.get(
            "risks",
            [],
        )

        solutions = data.get(
            "solutions",
            [],
        )

        if not isinstance(
            overview,
            str,
        ):
            overview = ""

        if not isinstance(
            purpose,
            str,
        ):
            purpose = ""

        if not isinstance(
            architecture,
            str,
        ):
            architecture = ""

        def clean_strings(
            value: Any,
        ) -> list[str]:

            if not isinstance(
                value,
                list,
            ):
                return []

            return [
                item
                for item in value
                if isinstance(
                    item,
                    str,
                )
            ]

        def clean_objects(
            value: Any,
        ) -> list[dict]:

            if not isinstance(
                value,
                list,
            ):
                return []

            return [
                item
                for item in value
                if isinstance(
                    item,
                    dict,
                )
            ]

        return ReportResult(
            overview=overview,

            purpose=purpose,

            technologies=clean_strings(
                technologies
            ),

            architecture=architecture,

            components=clean_objects(
                components
            ),

            flows=clean_objects(
                flows
            ),

            findings=clean_objects(
                findings
            ),

            risks=clean_strings(
                risks
            ),

            solutions=clean_objects(
                solutions
            ),
        )