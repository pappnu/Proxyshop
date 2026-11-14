import zipfile
from pathlib import Path

from src.utils.archive import unpack_archive


def test_unpack_archive_extracts_and_removes_archive(tmp_path: Path) -> None:
    archive_path = tmp_path / "payload.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("payload.txt", "contents")

    unpack_archive(archive_path)

    assert not archive_path.exists()
    assert (tmp_path / "payload.txt").read_text(encoding="utf-8") == "contents"
