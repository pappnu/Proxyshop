import os
import re
import shutil
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import NotRequired, TypedDict

import requests
import yarl
from pydantic import RootModel
from requests import Response, Session

from src.utils.data_structures import dump_model
from src.utils.download import (
    DEFAULT_CHUNK_SIZE,
    download_file_from_response,
    get_new_session,
)
from src.utils.files import get_temporary_file
from src.utils.strings import decode_url

_logger = getLogger(__name__)


@dataclass
class GoogleReg:
    URL: re.Pattern[str] = re.compile(r'"downloadUrl":"([^"]+)')
    FORM: re.Pattern[str] = re.compile(r'id="download-form" action="(.+?)"')
    EXPORT: re.Pattern[str] = re.compile(r'href="(/uc\?export=download[^"]+)')
    ERROR: re.Pattern[str] = re.compile(r'<p class="uc-error-subcaption">(.*)</p>')


class GoogleDriveMetadata(TypedDict):
    description: NotRequired[str]
    name: str
    size: int


def gdrive_get_confirmation_url(contents: str) -> yarl.URL:
    for line in contents.splitlines():
        if match := GoogleReg.EXPORT.search(line):
            return decode_url(f"https://docs.google.com{match.group(1)}")
        if match := GoogleReg.FORM.search(line):
            return decode_url(match.group(1))
        if match := GoogleReg.URL.search(line):
            return decode_url(match.group(1))
        if match := GoogleReg.ERROR.search(line):
            raise OSError(match.group(1))
    raise OSError(
        "Google Drive file has been made private or has reached its daily request limit."
    )


def gdrive_process_url(
    url: str | yarl.URL,
    headers: MutableMapping[str, str | bytes],
    sess: Session | None = None,
    path_cookies: Path | None = None,
) -> tuple[Session, Response] | None:
    if sess is None:
        sess = get_new_session(headers=headers, stream=True, path_cookies=path_cookies)
    response = sess.get(str(url))
    if path_cookies:
        gdrive_update_cookies(sess, path_cookies)

    if "Content-Disposition" in response.headers:
        return sess, response

    try:
        return gdrive_process_url(
            url=gdrive_get_confirmation_url(response.text),
            sess=sess,
            headers=headers,
            path_cookies=path_cookies,
        )
    except Exception:
        _logger.exception("Google Drive denied access to the file at URL: %s", url)
        response.close()
        sess.close()
        return None


def gdrive_update_cookies(sess: Session, path_cookies: Path) -> None:
    dump_model(
        path_cookies,
        RootModel(
            [
                (key, value)
                for key, value in sess.cookies.items()
                if not key.startswith("download_warning_")
            ]
        ),
    )


def gdrive_get_metadata(
    file_id: str,
    api_key: str,
    headers: MutableMapping[str, str | bytes],
) -> GoogleDriveMetadata | None:
    try:
        with requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={
                "alt": "json",
                "fields": "description,name,size",
                "key": api_key,
            },
        ) as response:
            if response.status_code != 200:
                return None
            result = response.json()
            if "name" in result and "size" in result:
                return result
    except requests.RequestException, ValueError:
        _logger.exception(f"Failed to retrieve Google Drive metadata for {file_id}")
    return None


def gdrive_download_file(
    url: yarl.URL | str,
    path: Path,
    headers: MutableMapping[str, str | bytes],
    callback: Callable[[int, int], None] | None = None,
    path_cookies: Path | None = None,
    allow_resume: bool = True,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = get_temporary_file(path=path, ext=".drive", allow_existing=allow_resume)
    size = temp_file.stat().st_size
    request_headers = headers
    if size > 0:
        request_headers = {**headers, "Range": f"bytes={size}-"}

    check = gdrive_process_url(
        url=url, headers=request_headers, path_cookies=path_cookies
    )
    if check is None:
        return None
    session, response = check
    try:
        download_file_from_response(
            response=response,
            path=temp_file,
            callback=callback,
            chunk_size=chunk_size,
        )
    except requests.RequestException, OSError:
        _logger.exception(f"Google Drive download failed: {path.name} | {url}")
        return None
    finally:
        response.close()
        session.close()

    if not (path.is_file() and os.path.samefile(temp_file, path)):
        shutil.move(temp_file, path)
    return path
