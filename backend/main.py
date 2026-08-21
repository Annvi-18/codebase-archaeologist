from dataclasses import asdict

import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.repository_analyzer import RepositoryAnalyzer
from agents.code_structure_normalizer import (
    CodeStructureNormalizer,
)
from agents.relationship_architecture import (
    RelationshipArchitectureAgent,
)
from agents.archaeological_analyzer import (
    ArchaeologicalAnalyzer,
)

app = FastAPI(
    title="Codebase Archaeologist",
    version="0.1.0",
)


analyzer = RepositoryAnalyzer()
normalizer = CodeStructureNormalizer()
architecture_agent = RelationshipArchitectureAgent()
archaeology_agent = ArchaeologicalAnalyzer()

class RepositoryRequest(BaseModel):
    github_url: str


@app.get("/")
def root():
    return {
        "message": "Codebase Archaeologist is running"
    }


@app.post("/analyze")
def analyze_repository(
    request: RepositoryRequest,
):
    try:

        # ====================================================
        # AGENT 1
        # ====================================================

        result = analyzer.analyze(
            request.github_url
        )

        # ====================================================
        # AGENT 2 — TREE-SITTER
        # ====================================================

        if result.structure is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Tree-sitter did not produce "
                    "a CodebaseStructure."
                ),
            )

        # ====================================================
        # AGENT 2 — NORMALIZER
        # ====================================================

        semantic_result = normalizer.normalize(
            result.structure
        )

        result.semantic = semantic_result

        # ====================================================
        # README
        # ====================================================

        readme = ""

        readme_file = next(
            (
                file
                for file in result.files
                if file.path.lower().replace("\\", "/")
                .split("/")[-1]
                == "readme.md"
            ),
            None,
        )

        if readme_file:

            github_url = request.github_url.rstrip("/")

            if github_url.endswith(".git"):
                github_url = github_url[:-4]

            readme_url = (
                f"{github_url}/raw/refs/heads/"
                f"{result.default_branch}/"
                f"{readme_file.path.replace(chr(92), '/')}"
            )

            response = requests.get(
                readme_url,
                timeout=20,
            )

            if response.ok:
                readme = response.text

        # ====================================================
        # AGENT 3
        # ====================================================

        architecture_result = (
            architecture_agent.analyze(
                readme=readme,
                structure=result.structure,
                semantic=semantic_result,
            )
        )

        # ====================================================
        # AGENT 4 — ARCHAEOLOGICAL ANALYSIS
        # ====================================================

        # ====================================================
        # AGENT 4 — ARCHAEOLOGICAL ANALYSIS
        # ====================================================

        archaeology_result = archaeology_agent.analyze(
            structure=result.structure,
            semantic=semantic_result,
            architecture=architecture_result,
        )
        # ====================================================
        # RETURN
        # ====================================================

        return {
            "repository": asdict(result),
            "architecture": asdict(
                architecture_result
            ),
            "archaeology": asdict(
                archaeology_result
            ),
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )