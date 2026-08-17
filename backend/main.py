from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.repository_analyzer import RepositoryAnalyzer


app = FastAPI(
    title="Codebase Archaeologist",
    version="0.1.0",
)


analyzer = RepositoryAnalyzer()


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

        result = analyzer.analyze(
            request.github_url
        )

        return {
            "repository": {
                "name": result.name,
                "url": result.url,
                "default_branch": result.default_branch,
                "total_files": result.total_files,
                "total_directories": (
                    result.total_directories
                ),
            },

            "languages": result.languages,

            "files": [
                {
                    "path": file.path,
                    "size": file.size,
                    "category": file.category,
                }
                for file in result.files
            ],

            "categories": {
                "source": result.source_files,
                "test": result.test_files,
                "documentation": (
                    result.documentation_files
                ),
                "configuration": (
                    result.configuration_files
                ),
                "asset": result.asset_files,
                "generated": result.generated_files,
                "build": result.build_files,
                "other": result.other_files,
            },
        }

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )