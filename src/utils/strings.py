import codecs
import html
import string
import unicodedata
from urllib import parse

import yarl


def normalize_str(text: str, no_space: bool = False) -> str:
    normalized = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()
    normalized = normalized.replace(" ", "") if no_space else normalized.strip()
    return normalized.translate(str.maketrans("", "", string.punctuation)).lower()


def normalize_ver(st: str) -> str:
    return "".join(char for char in st if char in ".0123456789")


def decode_url(url: str) -> yarl.URL:
    decoded = codecs.decode(html.unescape(parse.unquote(url)), "unicode_escape")
    return yarl.URL(decoded)


def strip_lines(text: str, num: int, sep: str = "\n") -> str:
    if num == 0:
        return text
    lines = text.split(sep)
    return sep.join(lines[:num] if num < 0 else lines[num:])


def get_line(text: str, i: int, sep: str = "\n") -> str:
    lines = text.split(sep)
    if not -len(lines) <= i < len(lines):
        raise IndexError(
            f"Not enough lines in multiline string. Index of {i} is invalid."
        )
    return lines[i]


def get_lines(text: str, num: int, sep: str = "\n") -> str:
    if num == 0:
        return text
    lines = text.split(sep)
    if abs(num) > len(lines):
        return text
    return sep.join(lines[num:] if num < 0 else lines[:num])
