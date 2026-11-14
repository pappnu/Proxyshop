from pathlib import Path

from src.utils.files import get_project_version


def test_get_project_version_reads_project_version(tmp_path: Path) -> None:
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")

    assert get_project_version(project_file) == "1.2.3"


def test_get_project_version_defaults_when_project_version_is_missing(
    tmp_path: Path,
) -> None:
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text('[project]\nname = "Name"\n', encoding="utf-8")

    assert get_project_version(project_file) == "0.0.0"
