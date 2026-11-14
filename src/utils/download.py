"""
* Utils: Downloads and Updates
"""

import json
import os
import shutil
from collections.abc import Callable, Mapping, MutableMapping
from contextlib import suppress
from pathlib import Path

import requests
import yarl

from src import DEFAULT_HEADERS
from src.utils.archive import unpack_archive
from src.utils.files import get_temporary_file

DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024


def get_new_session(
    headers: MutableMapping[str, str | bytes],
    stream: bool = False,
    path_cookies: Path | None = None,
) -> requests.Session:
    session = requests.session()
    session.headers = headers
    if stream:
        session.stream = True
    if path_cookies and path_cookies.is_file():
        with path_cookies.open(encoding="utf-8") as file:
            for key, value in json.load(file):
                session.cookies[key] = value
    return session


def check_resume_file(
    path: str | os.PathLike[str],
    headers: Mapping[str, str | bytes],
) -> bool:
    range_header = headers.get("Range")
    if (
        not isinstance(range_header, str)
        or not os.path.exists(path)
        or "bytes=" not in range_header
    ):
        return False
    try:
        start = int(range_header[6:].split("-")[0])
        return start == os.path.getsize(path)
    except IndexError, TypeError, ValueError:
        return False


def estimate_content_length(response: requests.Response, default: int = 0) -> int:
    total = response.headers.get("Content-Length", default)
    with suppress(TypeError, ValueError):
        if isinstance(total, str):
            total = int("".join(char for char in total if char.isdigit()) or default)
        return int(total)
    return default


def download_file(
    url: str | yarl.URL,
    path: str | os.PathLike[str],
    headers: MutableMapping[str, str | bytes],
    callback: Callable[[int, int], None] | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str | os.PathLike[str]:
    write_mode = "ab" if check_resume_file(path, headers) else "wb"
    with requests.get(str(url), headers=headers, stream=True) as response:
        response.raise_for_status()
        total = estimate_content_length(response) if callback else 0
        with open(path, write_mode) as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    raise OSError("Bad chunk detected, likely a truncated stream!")
                file.write(chunk)
                if callback:
                    current = file.tell()
                    callback(current, max(current, total))
    return path


def download_file_from_response(
    response: requests.Response,
    path: str | os.PathLike[str],
    callback: Callable[[int, int], None] | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str | os.PathLike[str]:
    response.raise_for_status()
    total = estimate_content_length(response) if callback else 0
    write_mode = "ab" if check_resume_file(path, response.headers) else "wb"
    with open(path, write_mode) as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if not chunk:
                raise OSError("Bad chunk detected, likely a truncated stream!")
            file.write(chunk)
            if callback:
                current = file.tell()
                callback(current, max(current, total))
    return path


def download_cloudfront(
    url: yarl.URL, path: Path, callback: Callable[[int, int], None] | None = None
) -> bool:
    """Download a template from cloudfront cached Amazon S3 bucket.

    Args:
        url: URL to S3/cloudfront hosted file.
        path: Path to save the archive.
        callback: Callback function to update progress.

    Returns:
        True if download is successful, otherwise False.
    """
    # Get a temp file
    temp_path = get_temporary_file(path=path, ext=".amzn")

    # Start the download
    try:
        download_file(
            url=url, path=temp_path, callback=callback, headers=DEFAULT_HEADERS
        )
        shutil.move(temp_path, path)
        unpack_archive(path)
    except requests.RequestException, FileExistsError, FileNotFoundError:
        return False
    return True
