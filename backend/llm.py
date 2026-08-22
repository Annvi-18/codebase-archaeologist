from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


class GeminiClient:
    """
    Shared Gemini client.

    All model calls go through generate_json() so they
    share one rate limiter. Nothing in this client is
    invoked once per source file.

    Agent 1:
        classify_repository_files() — batched inventory.

    Agent 2 semantic work lives in CodeStructureNormalizer
    and consumes already-built Tree-sitter output.
    """

    CLASSIFY_BATCH_SIZE = 80
    MIN_INTERVAL_SECONDS = 4.5

    # Shared across every GeminiClient instance so Agent 1–4
    # cannot burst past the per-minute quota.
    _lock = threading.Lock()
    _last_call_at = 0.0

    def __init__(self, api_key: str | None = None):

        api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set."
            )

        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=3,
                    initial_delay=8.0,
                    max_delay=45.0,
                    http_status_codes=[
                        408,
                        429,
                        500,
                        502,
                        503,
                        504,
                    ],
                )
            ),
        )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite",
        )

    # ========================================================
    # RATE-LIMITED JSON CALL
    # ========================================================

    def generate_json(
        self,
        prompt: str,
    ) -> Any:
        """
        Single Gemini entry point.

        Waits between requests so we stay under the
        model's per-minute request quota.
        """

        with GeminiClient._lock:
            self._wait_for_slot()

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )

            GeminiClient._last_call_at = time.monotonic()

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Gemini returned invalid JSON."
            ) from error

    def _wait_for_slot(self) -> None:

        if GeminiClient._last_call_at <= 0:
            return

        elapsed = time.monotonic() - GeminiClient._last_call_at
        remaining = self.MIN_INTERVAL_SECONDS - elapsed

        if remaining > 0:
            time.sleep(remaining)

    # ========================================================
    # AGENT 1
    # REPOSITORY FILE CLASSIFICATION
    # ========================================================

    def classify_repository_files(
        self,
        repository_name: str,
        languages: dict[str, int],
        files: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """
        Classify the inventory in batches.

        One Gemini call covers many files. A large
        repository is split by inventory size, never
        one request per file.
        """

        if not files:
            return []

        results: list[dict[str, str]] = []
        batch_size = self.CLASSIFY_BATCH_SIZE

        for start in range(0, len(files), batch_size):

            batch = files[start:start + batch_size]

            data = self.generate_json(
                self._build_classification_prompt(
                    repository_name=repository_name,
                    languages=languages,
                    files=batch,
                )
            )

            results.extend(
                self._parse_classifications(data)
            )

        return results

    def _parse_classifications(
        self,
        data: Any,
    ) -> list[dict[str, str]]:

        if not isinstance(data, dict):
            raise RuntimeError(
                "Gemini classification response must be a JSON object."
            )

        classifications = data.get("classifications", [])

        if not isinstance(classifications, list):
            raise RuntimeError(
                "Gemini classification response does not "
                "contain a valid classifications list."
            )

        result = []

        for item in classifications:

            if not isinstance(item, dict):
                continue

            path = item.get("path")
            category = item.get("category")

            if not isinstance(path, str):
                continue

            if not isinstance(category, str):
                continue

            result.append(
                {
                    "path": path,
                    "category": category,
                }
            )

        return result

    def _build_classification_prompt(
        self,
        repository_name: str,
        languages: dict[str, int],
        files: list[dict[str, Any]],
    ) -> str:

        evidence = {
            "repository_name": repository_name,
            "languages": languages,
            "files": files,
        }

        evidence_json = json.dumps(
            evidence,
            indent=2,
            ensure_ascii=False,
        )

        return """
You are the repository file-classification component of
a language-agnostic code archaeology system.

The Python system has collected generic repository facts.
You must semantically classify the files.

============================================================
IMPORTANT
============================================================

Do NOT assume a specific:

- programming language
- framework
- library
- ecosystem
- build system
- architecture

Do not rely on hardcoded language-specific rules.

Do not rely on hardcoded framework-specific rules.

Use the supplied evidence:

- repository context
- path
- filename
- extension
- file size
- parent directory
- language information
- surrounding repository information

Do not invent information.

Every supplied file must receive exactly one category.

Preserve the file path exactly.

============================================================
ALLOWED CATEGORIES
============================================================

source

test

documentation

configuration

asset

generated

build

other

============================================================
CATEGORY MEANING
============================================================

source:
A file that appears to contain application or library
source code.

test:
A file whose primary purpose is automated testing or
test support.

documentation:
A human-readable project document or explanatory file.

configuration:
A file primarily used to configure a tool, application,
environment, project, or development process.

asset:
A non-source resource such as an image, font, media,
static resource, or other resource file.

generated:
A file that appears to have been automatically generated
from another source or process.

build:
A file primarily used for building, compiling, packaging,
wrapping, or producing distributable output.

other:
A file that does not confidently fit another category.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use exactly:

{
  "classifications": [
    {
      "path": "exact input path",
      "category": "one allowed category"
    }
  ]
}

Do not return markdown.

Do not return explanations.

Do not omit files.

Do not modify paths.

============================================================
REPOSITORY EVIDENCE
============================================================
""" + "\n" + evidence_json
