import json
import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiClient:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set in the environment."
            )

        self.client = genai.Client(api_key=api_key)

        self.model = "models/gemini-3.5-flash-lite"

    def classify_repository_files(
        self,
        repository_name: str,
        languages: dict,
        files: list[dict],
    ) -> list[dict]:

        prompt = self._build_classification_prompt(
            repository_name,
            languages,
            files,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": 0,
                "response_mime_type": "application/json",
            },
        )

        response_text = response.text

        if not response_text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Gemini returned invalid JSON."
            ) from error

        return result.get("classifications", [])

    def _build_classification_prompt(
        self,
        repository_name: str,
        languages: dict,
        files: list[dict],
    ) -> str:

        return f"""
You are analyzing a software repository.

Your task is to classify repository files based ONLY on
the evidence provided.

IMPORTANT RULES:

1. Do not assume a specific programming language or framework.
2. Do not use hardcoded technology-specific rules.
3. Infer the role of each file from its path, filename,
   extension, size, surrounding repository structure,
   and language information.
4. Do not invent information that is not supported by the
   provided evidence.
5. Return exactly one category for every provided file.
6. Preserve every file path exactly as provided.

Allowed categories:

- source
- test
- documentation
- configuration
- asset
- generated
- build
- other

Category meanings:

source:
Files that appear to contain application/library source code.

test:
Files primarily associated with automated tests.

documentation:
Human-readable documentation or project explanation.

configuration:
Files primarily containing project/tool/application configuration.

asset:
Images, fonts, media, static resources, or other non-code assets.

generated:
Files that appear to be generated automatically from another source.

build:
Build scripts, wrappers, compiled artifacts, packaging output,
or files primarily used to build/package the project.

other:
Anything that does not confidently fit another category.

Repository:

Name:
{repository_name}

Languages:
{json.dumps(languages, indent=2)}

Files:
{json.dumps(files, indent=2)}

Return ONLY valid JSON in this format:

{{
  "classifications": [
    {{
      "path": "exact/path/from/input",
      "category": "one_allowed_category"
    }}
  ]
}}
"""