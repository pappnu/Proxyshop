"""
* Handles Requests to the hexproof.io API
"""
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from functools import cache
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import requests
from backoff import expo, on_exception
from hexproof.hexapi.enums import HexURL
from hexproof.hexapi.schema.meta import Meta
from limits import RateLimitItemPerSecond
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from omnitils.exceptions import ExceptionLogger, log_on_exception, return_on_exception
from omnitils.files import dump_data_file
from omnitils.rate_limit import rate_limit
from requests import RequestException, get

from src import CON, CONSOLE, ENV, PATH
from src._loader import SymbolsManifest, get_symbols_manifest
from src._state import HexproofSet, HexproofSets
from src.utils.download import HEADERS
from src.utils.github import GitHubReleaseAsset, get_github_releases

"""
* Hexproof.io Objects
"""

# Rate limiter to safely limit Hexproof.io requests
_rate_limit_storage = MemoryStorage()
_hexproof_rate_limit = MovingWindowRateLimiter(_rate_limit_storage)
_rate_limit = RateLimitItemPerSecond(20)

# Hexproof.io HTTP header
hexproof_http_header = HEADERS.Default.copy()

"""
* Scryfall Error Handling
"""


def hexproof_request_wrapper[T, **P](fallback: T, logr: ExceptionLogger | None = None) -> Callable[[Callable[P,T]], Callable[P, T]]:
    """Wrapper for a Hexproof.io request function to handle retries, rate limits, and a final exception catch.

    Args:
        logr: Logger object to output any exception messages.

    Returns:
        Wrapped function.
    """
    logr = logr or CONSOLE

    def decorator(func: Callable[P,T]):
        @return_on_exception(fallback)
        @log_on_exception(logr)
        @rate_limit(limiter=_hexproof_rate_limit, limit=_rate_limit)
        @on_exception(expo, requests.exceptions.RequestException, max_tries=2, max_time=1)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


"""
* Hexproof Requests
"""


@hexproof_request_wrapper('')
def get_api_key(key: str) -> str:
    """Get an API key from https://api.hexproof.io.

    Args:
        key: Name of the API key.

    Returns:
        API key string.

    Raises:
        RequestException if request was unsuccessful.
    """
    url = HexURL.API.Keys.All / key
    res = requests.get(str(url), headers=hexproof_http_header, timeout=(3, 3))
    if res.status_code == 200:
        return res.json().get('key', '')
    raise RequestException(
        res.json().get('details', f"Failed to get key: '{key}'"),
        response=res)


@hexproof_request_wrapper({})
def get_metadata() -> dict[str, Meta]:
    """Return a manifest of all resource metadata.

    Returns:
        dict[str, Hexproof.Meta]: A dictionary containing every resource metadata, with resource name as key.

    Raises:
        RequestException if request was unsuccessful.
    """
    res = requests.get(str(HexURL.API.Meta.All), headers=hexproof_http_header, timeout=(3, 3))
    if res.status_code == 200:
        return {k: Meta(**v) for k, v in res.json().items()}
    raise RequestException(
        res.json().get('details', "Failed to get metadata!"),
        response=res)


@hexproof_request_wrapper({})
def get_sets() -> dict[str,HexproofSet]:
    """Retrieve the current 'Set' data manifest from https://api.hexproof.io.

    Returns:
        Data loaded from the 'Set' data manifest.

    Raises:
        RequestException if request was unsuccessful.
    """
    res = requests.get(str(HexURL.API.Sets.All), headers=hexproof_http_header, timeout=(5, 5))
    if res.status_code == 200:
        return HexproofSets.model_validate_json(res.content).root
    raise RequestException(
        res.json().get('details', 'Failed to get set data!'),
        response=res)


"""
* Data Caching
"""

def _download_symbols(url: str) -> SymbolsManifest | None:
    response = get(url)
    if response.status_code == 200:
        with ZipFile(BytesIO(response.content), "r") as zf:
            zf.extractall(PATH.SRC_IMG_SYMBOLS)
        return get_symbols_manifest()
    return None


def update_hexproof_cache() -> tuple[bool, str | None]:
    """Check for a hexproof.io data update.

    Returns:
        tuple: A tuple containing the boolean success state of the update, and a string message
            explaining the error if one occurred.
    """
    meta, updated = {}, False
    with suppress(Exception):
        meta: dict[str, Meta] = get_metadata()

    # Check against current metadata
    new_set_data: dict[str,HexproofSet] | None = None
    _current, _next = CON.metadata.get('sets'), meta.get('sets')
    if not _current or not _next or _current.version != _next.version:
        try:
            # Download updated 'Set' data
            new_set_data = get_sets()
            updated = True
        except (RequestException, ValueError, OSError):
            return False, "Unable to update 'Set' data from hexproof.io!"

    # Check against current symbol data
    new_symbols: SymbolsManifest | None = None
    symbols_dl_url: str | None = None
    if ENV.SYMBOL_UPDATES_REPO:
        symbols_releases = get_github_releases(ENV.SYMBOL_UPDATES_REPO, per_page=1)
        if len(symbols_releases) > 0:
            latest_release = symbols_releases[0]
            if len(latest_release.assets) > 0:
                chosen_asset: GitHubReleaseAsset | None = None
                for asset in latest_release.assets:
                    if "optimized" in asset.name:
                        chosen_asset = asset
                        break
                if not chosen_asset:
                    chosen_asset = latest_release.assets[0]
                asset_timestamp: datetime
                try:
                    asset_timestamp = datetime.fromisoformat(latest_release.tag_name)
                except ValueError:
                    asset_timestamp = datetime.fromisoformat(chosen_asset.updated_at)
                if not (
                    current_symbols_manifest := get_symbols_manifest()
                ) or asset_timestamp > datetime.fromisoformat(
                    current_symbols_manifest.meta.date
                ):
                    symbols_dl_url = chosen_asset.browser_download_url
    else:
        _current, _next = CON.metadata.get("symbols"), meta.get("symbols")
        if not _current or not _next or _current.version != _next.version:
            symbols_dl_url = str(HexURL.API.Symbols.All / "package")

    if symbols_dl_url:
        try:
            # Download and unpack updated 'Symbols' assets
            new_symbols = _download_symbols(symbols_dl_url)
            updated = updated or bool(new_symbols)
        except (RequestException, FileNotFoundError):
            return False, "Unable to download symbols package!"

    # Update metadata
    try:
        if not updated:
            return updated, None
        
        # Ensure that all symbols are present in set data
        if new_symbols:
            symbs = new_symbols.set.symbols
            set_data = new_set_data or CON.set_data
            for card_set, data in set_data.items():
                if data.code_symbol == "default":
                    if card_set.upper() in symbs:
                        data.code_symbol = card_set
                    # elif card_set in symbs:
                    #    data.code_symbol = card_set
                    else:
                        curr_key = card_set
                        curr_data = data
                        while curr_data.code_parent:
                            curr_key = curr_data.code_parent
                            curr_data = set_data.get(curr_key, None)
                            if not curr_data:
                                break
                            if curr_key.upper() in symbs:
                                data.code_symbol = curr_key
                                break
                            # elif curr_key in symbs:
                            #    data.code_symbol = curr_key
                            #    break
            for card_set in symbs:
                if (card_set_low := card_set.lower()) not in set_data:
                    set_data[card_set_low] = HexproofSet(
                        code_symbol=card_set_low, count_cards=0, count_tokens=0
                    )
            with open(PATH.SRC_DATA_HEXPROOF_SET, "w") as f:
                f.write(HexproofSets(set_data).model_dump_json(indent=2))

        dump_data_file(
            obj={k: v.model_dump() for k, v in meta.items()},
            path=PATH.SRC_DATA_HEXPROOF_META)
        return updated, None
    except (FileNotFoundError, OSError, ValueError):
        return False, 'Unable to update metadata from hexproof.io!'


"""
* Accessing Local Data
"""


@cache
def get_set_data(code: str) -> HexproofSet | None:
    """Returns a specific 'Set' object by set code.

    Args:
        code: Code a 'Set' is identified by.

    Returns:
        A 'Set' object if located, otherwise None.
    """
    return CON.set_data.get(code.lower(), None)


def get_watermark_svg_from_set(code: str) -> Path | None:
    """Look for a watermark SVG in the 'Set' symbol catalog.

    Args:
        code: Set code to look for.

    Returns:
        Path to a watermark SVG file if found, otherwise None.
    """

    # Look for a recognized set
    set_obj = get_set_data(code)
    if not set_obj:
        return

    # Check if this set has a provided symbol code
    if not set_obj.code_symbol:
        return

    # Check if this symbol code matches a supported watermark
    p = PATH.SRC_IMG_SYMBOLS / 'set' / set_obj.code_symbol.upper() / 'WM.svg'
    return p if p.is_file() else None


def get_watermark_svg(wm: str) -> Path | None:
    """Look for a watermark SVG in the watermark symbol catalog. If not found, look for a 'set' watermark.

    Args:
        wm: Watermark name to look for.

    Returns:
        Path to a watermark SVG file if found, otherwise None.
    """
    p = (PATH.SRC_IMG_SYMBOLS / 'watermark' / wm.lower()).with_suffix('.svg')
    return p if p.is_file() else get_watermark_svg_from_set(wm)
