import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv

from models import FileInfo, RepositoryInfo
from llm import GeminiClient


load_dotenv()


class RepositoryAnalyzer:
    """
    Agent 1: Repository Analyzer

    Responsibility:
    - Retrieve repository metadata
    - Clone the repository
    - Build a generic repository inventory
    - Use Gemini to semantically classify files
    - Produce RepositoryInfo

    This agent does NOT contain language-specific or
    framework-specific classification rules.
    """

    IGNORED_DIRECTORIES = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        "target",
        "coverage",
        ".idea",
        ".vscode",
    }

    def __init__(self):
        self.llm = GeminiClient()

    # =========================================================
    # PUBLIC ENTRY POINT
    # =========================================================

    def analyze(self, github_url: str) -> RepositoryInfo:

        owner, repository = self._parse_github_url(
            github_url
        )

        repository = repository.removesuffix(".git")

        metadata = self._get_repository_metadata(
            owner,
            repository,
        )

        languages = self._get_repository_languages(
            owner,
            repository,
        )

        temp_directory = tempfile.mkdtemp(
            prefix="archaeologist_"
        )

        try:

            repo_path = self._clone_repository(
                github_url,
                temp_directory,
            )

            inventory = self._build_inventory(
                repo_path
            )

            classifications = self.llm.classify_repository_files(
                repository_name=metadata["name"],
                languages=languages,
                files=inventory,
            )

            return self._build_repository_info(
                github_url=github_url,
                metadata=metadata,
                languages=languages,
                inventory=inventory,
                classifications=classifications,
            )

        finally:

            shutil.rmtree(
                temp_directory,
                ignore_errors=True,
            )

    # =========================================================
    # GITHUB
    # =========================================================

    def _github_headers(self):

        token = os.getenv("GITHUB_TOKEN")

        headers = {
            "Accept": "application/vnd.github+json"
        }

        if token:
            headers["Authorization"] = (
                f"Bearer {token}"
            )

        return headers

    def _parse_github_url(self, github_url: str):

        cleaned_url = github_url.rstrip("/")

        if cleaned_url.endswith(".git"):
            cleaned_url = cleaned_url[:-4]

        parts = cleaned_url.split("/")

        if len(parts) < 2:
            raise ValueError(
                "Invalid GitHub repository URL."
            )

        owner = parts[-2]
        repository = parts[-1]

        return owner, repository

    def _get_repository_metadata(
        self,
        owner: str,
        repository: str,
    ):

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repository}"
        )

        response = requests.get(
            url,
            headers=self._github_headers(),
            timeout=20,
        )

        if response.status_code == 404:
            raise ValueError(
                "Repository not found or is not public."
            )

        response.raise_for_status()

        return response.json()

    def _get_repository_languages(
        self,
        owner: str,
        repository: str,
    ):

        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repository}/languages"
        )

        response = requests.get(
            url,
            headers=self._github_headers(),
            timeout=20,
        )

        response.raise_for_status()

        return response.json()

    # =========================================================
    # GIT
    # =========================================================

    def _clone_repository(
        self,
        github_url: str,
        destination: str,
    ):

        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                github_url,
                destination,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:

            raise RuntimeError(
                f"Failed to clone repository:\n"
                f"{result.stderr}"
            )

        return destination

    # =========================================================
    # GENERIC FILESYSTEM INVENTORY
    # =========================================================

    def _build_inventory(
        self,
        repo_path: str,
    ) -> list[dict]:

        inventory = []

        for root, directories, filenames in os.walk(
            repo_path
        ):

            directories[:] = [
                directory
                for directory in directories
                if directory not in self.IGNORED_DIRECTORIES
            ]

            for filename in filenames:

                absolute_path = Path(root) / filename

                try:

                    relative_path = (
                        absolute_path
                        .relative_to(repo_path)
                    )

                except ValueError:

                    continue

                try:

                    size = absolute_path.stat().st_size

                except OSError:

                    size = 0

                inventory.append(
                    {
                        "path": str(relative_path),
                        "size": size,
                        "extension": (
                            absolute_path.suffix.lower()
                        ),
                        "parent_directory": (
                            relative_path.parent.as_posix()
                        ),
                    }
                )

        return inventory

    # =========================================================
    # BUILD FINAL MODEL
    # =========================================================

    def _build_repository_info(
        self,
        github_url: str,
        metadata: dict,
        languages: dict,
        inventory: list[dict],
        classifications: list[dict],
    ) -> RepositoryInfo:

        classification_map = {
            item["path"]: item["category"]
            for item in classifications
            if "path" in item and "category" in item
        }

        files = []

        source_files = []
        test_files = []
        documentation_files = []
        configuration_files = []
        asset_files = []
        generated_files = []
        build_files = []
        other_files = []

        directories = set()

        for item in inventory:

            path = item["path"]

            category = classification_map.get(
                path,
                "other",
            )

            file_info = FileInfo(
                path=path,
                size=item["size"],
                category=category,
            )

            files.append(file_info)

            self._add_to_category(
                path=path,
                category=category,
                source_files=source_files,
                test_files=test_files,
                documentation_files=documentation_files,
                configuration_files=configuration_files,
                asset_files=asset_files,
                generated_files=generated_files,
                build_files=build_files,
                other_files=other_files,
            )

            parent = Path(path).parent

            while str(parent) != ".":

                directories.add(
                    parent.as_posix()
                )

                parent = parent.parent

        return RepositoryInfo(
            name=metadata["name"],
            url=github_url,
            default_branch=metadata[
                "default_branch"
            ],
            total_files=len(files),
            total_directories=len(directories),
            languages=languages,
            source_files=source_files,
            test_files=test_files,
            documentation_files=documentation_files,
            configuration_files=configuration_files,
            asset_files=asset_files,
            generated_files=generated_files,
            build_files=build_files,
            other_files=other_files,
            files=files,
        )

    # =========================================================
    # CATEGORY ROUTING
    # =========================================================

    def _add_to_category(
        self,
        path: str,
        category: str,
        source_files: list,
        test_files: list,
        documentation_files: list,
        configuration_files: list,
        asset_files: list,
        generated_files: list,
        build_files: list,
        other_files: list,
    ):

        category_lists = {
            "source": source_files,
            "test": test_files,
            "documentation": documentation_files,
            "configuration": configuration_files,
            "asset": asset_files,
            "generated": generated_files,
            "build": build_files,
            "other": other_files,
        }

        target = category_lists.get(
            category,
            other_files,
        )

        target.append(path)