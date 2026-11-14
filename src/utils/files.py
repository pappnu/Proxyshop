import os
from logging import getLogger
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel

from src.utils.data_structures import parse_model

_logger = getLogger(__name__)


class _ProjectInfo(BaseModel):
    version: str


class _ProjectFile(BaseModel):
    project: _ProjectInfo


def get_temporary_file(
    path: Path, ext: str = ".tmp", allow_existing: bool = False
) -> Path:
    temp = path.with_suffix(ext)
    if allow_existing:
        path_exists = path.is_file()
        for name in os.listdir(path.parent):
            candidate = path.parent / name
            if candidate.is_dir() or (
                path_exists and os.path.samefile(candidate, path)
            ):
                continue
            if temp.name in candidate.name:
                return candidate

    with NamedTemporaryFile(prefix=temp.name, dir=temp.parent, delete=False) as file:
        return Path(file.name)


def get_unique_filename(path: Path, increment_template: str = "({})") -> Path:
    stem, index = path.stem, 1
    while path.is_file():
        path = path.with_stem(f"{stem} {increment_template.format(index)}")
        index += 1
    return path


def get_project_version(path: Path) -> str:
    try:
        return parse_model(path, _ProjectFile).project.version
    except Exception as exc:
        fallback = "0.0.0"
        _logger.warning(
            f"Unable to read project version from {path}, defaulting to {fallback}",
            exc_info=exc,
        )
        return fallback
