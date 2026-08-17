from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FileInfo:
    path: str
    size: int
    category: str


@dataclass
class RepositoryInfo:
    name: str
    url: str
    default_branch: str
    total_files: int
    total_directories: int

    languages: Dict[str, int] = field(default_factory=dict)

    source_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    documentation_files: List[str] = field(default_factory=list)
    configuration_files: List[str] = field(default_factory=list)
    asset_files: List[str] = field(default_factory=list)
    generated_files: List[str] = field(default_factory=list)
    build_files: List[str] = field(default_factory=list)
    other_files: List[str] = field(default_factory=list)

    files: List[FileInfo] = field(default_factory=list)