# from dataclasses import asdict

# import requests

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel

# from agents.repository_analyzer import RepositoryAnalyzer
# from agents.code_structure_normalizer import (
#     CodeStructureNormalizer,
# )
# from agents.relationship_architecture import (
#     RelationshipArchitectureAgent,
# )
# from agents.archaeological_analyzer import (
#     ArchaeologicalAnalyzer,
# )
# # from backend.agents import report_generator
# from agents.report_generator import ReportGenerator
# from agents.archaeologist_chat import ArchaeologistChat

# app = FastAPI(
#     title="Codebase Archaeologist",
#     version="0.1.0",
# )


# analyzer = RepositoryAnalyzer()
# normalizer = CodeStructureNormalizer()
# architecture_agent = RelationshipArchitectureAgent()
# archaeology_agent = ArchaeologicalAnalyzer()
# report_generator_agent = ReportGenerator()
# chat_agent = ArchaeologistChat()

# class RepositoryRequest(BaseModel):
#     github_url: str

# class ChatRequest(BaseModel):
#     question: str

# @app.get("/")
# def root():
#     return {
#         "message": "Codebase Archaeologist is running"
#     }


# @app.post("/analyze")
# def analyze_repository(

#     request: RepositoryRequest,
# ):
#     try:

#         # ====================================================
#         # AGENT 1
#         # ====================================================

#         result = analyzer.analyze(
#             request.github_url
#         )

#         # ====================================================
#         # AGENT 2 — TREE-SITTER
#         # ====================================================

#         if result.structure is None:
#             raise HTTPException(
#                 status_code=500,
#                 detail=(
#                     "Tree-sitter did not produce "
#                     "a CodebaseStructure."
#                 ),
#             )

#         # ====================================================
#         # AGENT 2 — NORMALIZER
#         # One Gemini pass over Tree-sitter output, never
#         # per file. Skip if Agent 1 already attached it.
#         # ====================================================

#         if result.semantic is None:
#             result.semantic = normalizer.normalize(
#                 result.structure
#             )

#         semantic_result = result.semantic

#         if semantic_result is None:
#             raise HTTPException(
#                 status_code=500,
#                 detail=(
#                     "Semantic normalizer did not produce "
#                     "a GeminiSemanticResult."
#                 ),
#             )

#         # ====================================================
#         # README
#         # ====================================================

#         readme = ""

#         readme_file = next(
#             (
#                 file
#                 for file in result.files
#                 if file.path.lower().replace("\\", "/")
#                 .split("/")[-1]
#                 == "readme.md"
#             ),
#             None,
#         )

#         if readme_file:

#             github_url = request.github_url.rstrip("/")

#             if github_url.endswith(".git"):
#                 github_url = github_url[:-4]

#             readme_url = (
#                 f"{github_url}/raw/refs/heads/"
#                 f"{result.default_branch}/"
#                 f"{readme_file.path.replace(chr(92), '/')}"
#             )

#             response = requests.get(
#                 readme_url,
#                 timeout=20,
#             )

#             if response.ok:
#                 readme = response.text

#         # ====================================================
#         # AGENT 3
#         # ====================================================

#         architecture_result = (
#             architecture_agent.analyze(
#                 readme=readme,
#                 structure=result.structure,
#                 semantic=semantic_result,
#             )
#         )

#         # ====================================================
#         # AGENT 4 — ARCHAEOLOGICAL ANALYSIS
#         # ====================================================

#         archaeology_result = archaeology_agent.analyze(
#             structure=result.structure,
#             semantic=semantic_result,
#             architecture=architecture_result,
#         )

#         report = report_generator_agent.generate(
#             repository=result,
#             structure=result.structure,
#             semantic=semantic_result,
#             architecture=architecture_result,
#             archaeology=archaeology_result,
#         )
#         # ====================================================
#         # RETURN
#         # ====================================================

#         return {
            
#             "report": asdict(report),
#         }

#     except HTTPException:
#         raise

#     except Exception as error:
#         raise HTTPException(
#             status_code=400,
#             detail=str(error),
#         )


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
from agents.report_generator import ReportGenerator
from agents.archaeologist_chat import ArchaeologistChat


app = FastAPI(
    title="Codebase Archaeologist",
    version="0.1.0",
)


analyzer = RepositoryAnalyzer()
normalizer = CodeStructureNormalizer()
architecture_agent = RelationshipArchitectureAgent()
archaeology_agent = ArchaeologicalAnalyzer()
report_generator_agent = ReportGenerator()
chat_agent = ArchaeologistChat()


# ============================================================
# CURRENT ANALYSIS
# ============================================================

current_analysis = None


class RepositoryRequest(BaseModel):
    github_url: str


class ChatRequest(BaseModel):
    question: str


@app.get("/")
def root():
    return {
        "message": "Codebase Archaeologist is running"
    }


@app.post("/analyze")
def analyze_repository(
    request: RepositoryRequest,
):
    global current_analysis

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

        if result.semantic is None:
            result.semantic = normalizer.normalize(
                result.structure
            )

        semantic_result = result.semantic

        if semantic_result is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Semantic normalizer did not produce "
                    "a GeminiSemanticResult."
                ),
            )

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

        archaeology_result = (
            archaeology_agent.analyze(
                structure=result.structure,
                semantic=semantic_result,
                architecture=architecture_result,
            )
        )

        # ====================================================
        # REPORT GENERATOR
        # ====================================================

        report = report_generator_agent.generate(
            repository=result,
            structure=result.structure,
            semantic=semantic_result,
            architecture=architecture_result,
            archaeology=archaeology_result,
        )

        # ====================================================
        # STORE COMPLETE ANALYSIS FOR CHAT
        # ====================================================

        current_analysis = {
            "repository": result,
            "structure": result.structure,
            "semantic": semantic_result,
            "architecture": architecture_result,
            "archaeology": archaeology_result,
            "report": report,
        }

        # ====================================================
        # RETURN REPORT
        # ====================================================

        return {
            "report": asdict(report),
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ============================================================
# CHAT
# ============================================================

@app.post("/chat")
def chat_repository(
    request: ChatRequest,
):
    global current_analysis

    try:

        # ----------------------------------------------------
        # Make sure a repository has been analyzed first
        # ----------------------------------------------------

        if current_analysis is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Analyze a repository before "
                    "using the chat."
                ),
            )

        # ----------------------------------------------------
        # Ask Agent 5
        # ----------------------------------------------------

        answer = chat_agent.chat(
            question=request.question,
            repository=current_analysis[
                "repository"
            ],
            structure=current_analysis[
                "structure"
            ],
            semantic=current_analysis[
                "semantic"
            ],
            architecture=current_analysis[
                "architecture"
            ],
            archaeology=current_analysis[
                "archaeology"
            ],
            report=current_analysis[
                "report"
            ],
        )

        return {
            "answer": answer,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )