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


class ArchaeologistChat:
    """
    Agent 5 — Repository Chat Agent.

    Uses the completed outputs of Agents 1–4 and the
    final report to answer developer questions about
    the analyzed repository.

    It does not re-analyze the repository.
    """

    def __init__(self):
        self.llm = GeminiClient(
            api_key=os.getenv(
                "GEMINI_CHAT_API_KEY"
            )
        )

    def chat(
        self,
        question: str,
        repository: RepositoryInfo,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
        architecture: ArchitectureResult,
        archaeology: ArchaeologicalResult,
        report: ReportResult,
    ) -> str:

        context = self._build_context(
            repository,
            structure,
            semantic,
            architecture,
            archaeology,
            report,
        )

        prompt = self._build_prompt(
            question,
            context,
        )

        response = self.llm.generate_json(prompt)

        return self._parse_response(response)

    # ========================================================
    # CONTEXT
    # ========================================================

    def _build_context(
        self,
        repository: RepositoryInfo,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
        architecture: ArchitectureResult,
        archaeology: ArchaeologicalResult,
        report: ReportResult,
    ) -> dict[str, Any]:

        return {
            # =================================================
            # AGENT 1
            # =================================================

            "repository": {
                "name": repository.name,
                "url": repository.url,
                "default_branch": (
                    repository.default_branch
                ),
                "total_files": (
                    repository.total_files
                ),
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

            # =================================================
            # AGENT 2
            # =================================================

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
                        "confidence": (
                            finding.confidence
                        ),
                    }
                    for finding
                    in archaeology.findings
                ],
            },

            # =================================================
            # FINAL REPORT
            # =================================================

            "report": {
                "overview": report.overview,
                "purpose": report.purpose,
                "technologies": report.technologies,
                "architecture": report.architecture,
                "components": report.components,
                "flows": report.flows,
                "findings": report.findings,
                "risks": report.risks,
                "solutions": report.solutions,
            },
        }

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        question: str,
        context: dict[str, Any],
    ) -> str:

        context_json = json.dumps(
            context,
            indent=2,
            ensure_ascii=False,
        )

        prompt = f"""
You are the Chat Agent of Codebase Archaeologist.

Answer the developer's question using ONLY the supplied
repository analysis.

The analysis was produced by multiple agents:

Agent 1:
repository inventory and technologies

Agent 2:
structural metrics and normalized relationships

Agent 3:
architecture, components and flows

Agent 4:
archaeological findings, evidence and confidence

Final Report:
human-readable synthesis of the analysis

Rules:

- Do not invent repository facts.
- Do not invent relationships or files.
- Use the agents' outputs together.
- Prefer specific repository evidence over generic explanations.
- If the question asks "why", explain using the available evidence.
- If the question asks "how", use discovered relationships and flows.
- Preserve finding severity and confidence when discussing findings.
- Do not claim to have inspected source code that was not provided.
- Distinguish facts from reasonable inference.
- If the supplied analysis does not contain enough information,
  clearly say that the available repository analysis is insufficient.
- Do not answer using general programming knowledge when the
  question is specifically about this repository.

Give enough detail to fully answer the question.

For architecture, relationships, flows, findings, risks,
and "why/how" questions, explain the relevant evidence,
reasoning, and practical implication instead of giving
a one-line answer.

For simple factual questions, stay concise.

Do not add irrelevant detail or repeat the same information.

Return ONLY valid JSON:

{{
  "answer": "..."
}}

USER QUESTION:
{question}

REPOSITORY ANALYSIS:
{context_json}
"""

        return prompt

    # ========================================================
    # PARSER
    # ========================================================

    def _parse_response(
        self,
        data: Any,
    ) -> str:

        if not isinstance(data, dict):
            raise RuntimeError(
                "Chat response must be a JSON object."
            )

        answer = data.get(
            "answer",
            "",
        )

        if not isinstance(
            answer,
            str,
        ):
            raise RuntimeError(
                "Chat response contains an invalid answer."
            )

        return answer.strip()