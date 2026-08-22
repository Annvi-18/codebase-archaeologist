from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from llm import GeminiClient
from models import (
    ArchitectureComponent,
    ArchitectureFlow,
    ArchitectureResult,
    CodebaseStructure,
    GeminiSemanticResult,
)

load_dotenv()


class RelationshipArchitectureAgent:
    """
    Agent 3.

    Uses the README, Tree-sitter structure, and
    normalized semantic relationships to explain
    the repository architecture at a high level.

    One repository-level Gemini call.
    """

    def __init__(self):
        self.llm = GeminiClient(
            api_key=os.getenv(
                "GEMINI_ARCHITECTURE_API_KEY"
            )
        )

    def analyze(
        self,
        readme: str,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
    ) -> ArchitectureResult:

        evidence = self._build_evidence(
            readme,
            structure,
            semantic,
        )

        response = self.llm.generate_json(
            self._build_prompt(evidence)
        )

        return self._parse_result(response)

    # ========================================================
    # EVIDENCE
    # ========================================================

    def _build_evidence(
        self,
        readme: str,
        structure: CodebaseStructure,
        semantic: GeminiSemanticResult,
    ) -> dict[str, Any]:

        return {
            "readme": readme,

            "files": [
                {
                    "file_path": file.file_path,
                    "language": file.language,
                }
                for file in structure.files
            ],

            "entities": [
                {
                    "id": entity.id,
                    "file_path": entity.file_path,
                    "kind": entity.kind,
                    "name": entity.name,
                    "parent_id": entity.parent_id,
                }
                for entity in structure.entities
            ],

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
                    "export_type": item.export_type,
                }
                for item in semantic.exports
            ],

            "relationships": [
                {
                    "file_path": item.file_path,
                    "source_entity_id": item.source_entity_id,
                    "target_name": item.target_name,
                    "relation_type": item.relation_type,
                    "line": item.line,
                }
                for item in semantic.relationships
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

        prompt = """
You are Agent 3 of a code archaeology system.

Understand the repository using:
- README: stated project purpose
- Tree-sitter: actual code structure
- Semantic relationships: connections found in the code

Do not parse source code.
Do not invent files, entities, technologies, relationships, or behavior.

TASK:
1. Explain what the repository is about.
2. Summarize its main purpose and capabilities.
3. Identify technologies/languages supported by the evidence.
4. Group related files/entities into meaningful components.
5. Explain how the major components interact.
6. Identify important end-to-end flows.
7. Identify the architecture style only when supported.
8. Compare the README's stated purpose with the implementation evidence.

RELATIONSHIPS AND INFERENCE:

- Prefer explicit relationships, imports, exports, calls, implementations,
  inheritance, references, file paths, entities, and README evidence.
- If an explicit relationship is missing, infer the most likely relationship
  only when strong structural evidence supports it.
- Do not leave a relationship empty simply because Tree-sitter/normalization
  did not explicitly provide one if the available evidence supports a
  conservative inference.
- Inferred relationships must be marked as inferred.
- Never infer runtime behavior merely because it is common for a framework.
- Never invent database operations, API calls, authentication behavior,
  execution order, or dependencies without supporting evidence.
- If no reasonable relationship can be established, leave it empty.

Use only these relationship types:

uses
calls
imports
exports
implements
extends
depends_on
contains
routes_to
frontend_calls_backend
controller_uses_service
service_uses_repository
component_uses_service
model_used_by_component
persists_to
reads_from

Use the most specific type supported by the evidence. Otherwise use
"uses" or "depends_on".

CONFIDENCE:
- 0.90–1.00: directly supported
- 0.75–0.89: strongly supported inference
- 0.50–0.74: weaker inference
- Below 0.50: do not include

For inferred relationships, include:
"inferred": true
"confidence": <value>
"evidence": "<short reason>"

For directly observed relationships:
"inferred": false

FRAMING:

- Components should explain their role and responsibilities, not just list files.
- Relationships should explain meaningful architectural connections.
- Flows should describe how major components work together.
- Prefer important cross-component flows over trivial imports.
- Keep descriptions concise.
- Do not repeat raw Tree-sitter data unnecessarily.
- Keep all conclusions grounded in the supplied evidence.

Return ONLY valid JSON:

{
  "purpose": "...",
  "summary": "...",
  "technologies": [],
  "major_capabilities": [],
  "architecture_style": null,

  "components": [
    {
      "name": "...",
      "description": "...",
      "files": [],
      "entities": []
    }
  ],

  "flows": [
    {
      "name": "...",
      "description": "...",
      "steps": []
    }
  ]
}

EVIDENCE:
"""

        return prompt + evidence_json

    # ========================================================
    # RESPONSE PARSER
    # ========================================================

    def _parse_result(
        self,
        data: Any,
    ) -> ArchitectureResult:

        if not isinstance(data, dict):
            raise RuntimeError(
                "Agent 3 response must be a JSON object."
            )

        components = []

        for item in data.get("components", []):

            if not isinstance(item, dict):
                continue

            name = item.get("name")

            if not isinstance(name, str):
                continue

            description = item.get(
                "description",
                "",
            )

            if not isinstance(description, str):
                description = ""

            files = item.get("files", [])

            if not isinstance(files, list):
                files = []

            files = [
                value
                for value in files
                if isinstance(value, str)
            ]

            entities = item.get("entities", [])

            if not isinstance(entities, list):
                entities = []

            entities = [
                value
                for value in entities
                if isinstance(value, str)
            ]

            components.append(
                ArchitectureComponent(
                    name=name,
                    description=description,
                    files=files,
                    entities=entities,
                )
            )

        flows = []

        for item in data.get("flows", []):

            if not isinstance(item, dict):
                continue

            name = item.get("name")

            if not isinstance(name, str):
                continue

            description = item.get(
                "description",
                "",
            )

            if not isinstance(description, str):
                description = ""

            steps = item.get("steps", [])

            if not isinstance(steps, list):
                steps = []

            steps = [
                value
                for value in steps
                if isinstance(value, str)
            ]

            flows.append(
                ArchitectureFlow(
                    name=name,
                    description=description,
                    steps=steps,
                )
            )

        purpose = data.get("purpose", "")

        if not isinstance(purpose, str):
            purpose = ""

        summary = data.get("summary", "")

        if not isinstance(summary, str):
            summary = ""

        technologies = data.get(
            "technologies",
            [],
        )

        if not isinstance(technologies, list):
            technologies = []

        technologies = [
            value
            for value in technologies
            if isinstance(value, str)
        ]

        capabilities = data.get(
            "major_capabilities",
            [],
        )

        if not isinstance(capabilities, list):
            capabilities = []

        capabilities = [
            value
            for value in capabilities
            if isinstance(value, str)
        ]

        architecture_style = data.get(
            "architecture_style"
        )

        if not isinstance(
            architecture_style,
            str,
        ):
            architecture_style = None

        return ArchitectureResult(
            purpose=purpose,
            summary=summary,
            technologies=technologies,
            major_capabilities=capabilities,
            architecture_style=architecture_style,
            components=components,
            flows=flows,
        )