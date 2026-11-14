import bz2
import gzip
import lzma
import shutil
import tarfile
import zipfile
from collections.abc import Callable
from contextlib import ExitStack
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Literal

import py7zr

_ARCHIVE_LOCK = Lock()


class ArchType(StrEnum):
    Zip = ".zip"
    GZip = ".gz"
    XZip = ".xz"
    BZip2 = ".bz2"
    SevenZip = ".7z"
    TarGZip = ".tar.gz"
    TarXZip = ".tar.xz"
    TarBZip2 = ".tar.bz2"
    TarSevenZip = ".tar.7z"


def unpack_zip(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    with zipfile.ZipFile(path) as archive:
        archive.extractall(path=path.parent)


def unpack_gz(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    with gzip.open(path) as source, (path.parent / path.stem).open("wb") as target:
        shutil.copyfileobj(source, target)


def unpack_xz(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    with lzma.open(path) as source, (path.parent / path.stem).open("wb") as target:
        shutil.copyfileobj(source, target)


def unpack_bz2(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    with bz2.open(path) as source, (path.parent / path.stem).open("wb") as target:
        shutil.copyfileobj(source, target)


def unpack_7z(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    with py7zr.SevenZipFile(path, "r") as archive:
        archive.extractall(path=path.parent)


def unpack_tar(path: Path, mode: Literal["gz", "xz", "bz2"] = "gz") -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    with ExitStack() as stack:
        if mode == "gz":
            archive = stack.enter_context(tarfile.open(path, "r:gz"))
        elif mode == "xz":
            archive = stack.enter_context(tarfile.open(path, "r:xz"))
        else:
            archive = stack.enter_context(tarfile.open(path, "r:bz2"))
        archive.extractall(path=path.parent)


def unpack_tar_gz(path: Path) -> None:
    unpack_tar(path, mode="gz")


def unpack_tar_xz(path: Path) -> None:
    unpack_tar(path, mode="xz")


def unpack_tar_bz2(path: Path) -> None:
    unpack_tar(path, mode="bz2")


def unpack_archive(
    path: Path, remove: bool = True, thread_lock: Lock | None = None
) -> None:
    suffix_map: tuple[tuple[str, Callable[[Path], None]], ...] = (
        (ArchType.TarGZip, unpack_tar_gz),
        (ArchType.TarXZip, unpack_tar_xz),
        (ArchType.TarBZip2, unpack_tar_bz2),
        (ArchType.TarSevenZip, unpack_7z),
        (ArchType.Zip, unpack_zip),
        (ArchType.GZip, unpack_gz),
        (ArchType.XZip, unpack_xz),
        (ArchType.BZip2, unpack_bz2),
        (ArchType.SevenZip, unpack_7z),
    )
    action = next(
        (handler for suffix, handler in suffix_map if path.name.endswith(suffix)),
        None,
    )
    if action is None:
        return
    lock = thread_lock or _ARCHIVE_LOCK
    with lock:
        action(path)
    if remove:
        path.unlink()
