from pathlib import Path
from typing import ClassVar

from pytest import MonkeyPatch

from src.utils.download import download_file


def test_download_file_streams_chunks_and_reports_progress(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    class FakeResponse:
        headers: ClassVar[dict[str, str]] = {"Content-Length": "5"}

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def raise_for_status(self) -> None:
            pass

        def iter_content(self, chunk_size: int):
            assert chunk_size == 8 * 1024 * 1024
            yield b"he"
            yield b"llo"

    def fake(*args: object, **kwargs: object) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setattr("src.utils.download.requests.get", fake)
    destination = tmp_path / "download.bin"
    progress: list[tuple[int, int]] = []

    assert (
        download_file(
            "https://localhost:8000/file",
            destination,
            headers={},
            callback=lambda current, total: progress.append((current, total)),
        )
        == destination
    )
    assert destination.read_bytes() == b"hello"
    assert progress == [(2, 5), (5, 5)]
