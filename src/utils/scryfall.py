"""
* Scryfall API Module
"""

# Standard Library Imports
from collections.abc import Callable, Sequence
from pathlib import Path
from shutil import copyfileobj
from typing import (
    Any,
    Literal,
    NotRequired,
    ParamSpec,
    SupportsInt,
    TypedDict,
    TypeVar,
    Unpack,
)

import requests
import yarl

# Third Party Imports
from backoff import expo, on_exception
from hexproof.scryfall.enums import ScryURL
from limits import RateLimitItemPerSecond
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from omnitils.exceptions import ExceptionLogger, log_on_exception, return_on_exception
from requests.exceptions import RequestException

# Local Imports
from src import CONSOLE, PATH
from src.console import get_bullet_points
from src.utils.download import HEADERS
from src.utils.rate_limit import rate_limit

"""
* Types
"""

T = TypeVar("T")
P = ParamSpec("P")


class ScryfallError(TypedDict):
    """Error object outlined in Scryfall's API docs.

    Notes:
        https://scryfall.com/docs/api/errors
    """

    object: Literal["error"]
    code: str
    status: int
    details: str
    type: NotRequired[str]
    warnings: NotRequired[list[str]]


"""
* Scryfall Objects
"""

# Rate limiter to safely limit Scryfall requests
_rate_limit_storage = MemoryStorage()
_scryfall_rate_limit = MovingWindowRateLimiter(_rate_limit_storage)
_rate_limit = RateLimitItemPerSecond(10)

# Scryfall HTTP header
scryfall_http_header = HEADERS.Default.copy()

"""
* Scryfall Error Handling
"""


class ScryfallExceptionKwargs(TypedDict):
    exception: NotRequired[Exception | None]
    card_name: NotRequired[str | None]
    card_set: NotRequired[str | None]
    card_number: NotRequired[str | None]
    lang: NotRequired[str | None]


class ScryfallException(RequestException):
    """Exception representing a failure to retrieve Scryfall data."""

    def __init__(
        self,
        *args: object,
        request: requests.Request | requests.PreparedRequest | None = None,
        response: requests.Response | None = None,
        **kwargs: Unpack[ScryfallExceptionKwargs],
    ) -> None:
        """Allow details relating to the exception to be passed.

        Keyword Args:
            exception (Exception): Caught exception to pull potential request details from.
            card_name (str): Name of a card.
            card_set (str): Set code of a card.
            card_number (str): Collector number of a card.
            lang (str): Language of a card.
        """

        # Check for our kwargs
        exception = kwargs.get("exception", None)
        params = {
            "Name": kwargs.get("card_name", None),
            "Set": kwargs.get("card_set", None),
            "Num": kwargs.get("card_number", None),
            "Lang": kwargs.get("lang", None),
        }

        # Compile error message
        msg = "Scryfall request failed!"
        if any(params.values()):
            # List the params provided
            msg += "\nParams: "
            p = [f"{k}: '{v}'" for k, v in params.items() if v]
            msg += ", ".join(p)
        if exception and isinstance(exception, RequestException) and exception.request:
            # Provide the URL which failed
            msg += f"\nAPI URL: {exception.request.url}"
        if exception:
            # Provide the exception cause
            msg += f"\nReason: {exception}"
        super().__init__(msg)


def scryfall_request_wrapper(
    logger: ExceptionLogger | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Wrapper for a Scryfall request function to handle retries, rate limits, and a final exception catch.

    Args:
        logr: Logger object to output any exception messages.

    Returns:
        Wrapped function.
    """
    logr = logger or CONSOLE

    def decorator(func: Callable[P, T]):
        @log_on_exception(logr)
        @on_exception(
            expo, requests.exceptions.RequestException, max_tries=2, max_time=1
        )
        @rate_limit(strategy=_scryfall_rate_limit, limit=_rate_limit, reschedule=0.1)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_error(
    error: ScryfallError,
    response: requests.Response | None = None,
    **kwargs: Unpack[ScryfallExceptionKwargs],
) -> ScryfallException:
    """Returns a ScryfallException object created using data from a ScryfallError object.

    Args:
        error: ScryfallError object returned from a failed Scryfall API request.
        response: A requests Response object containing details of the failed Scryfall request, if not provided
            defaults to a None value.

    Returns:
        A ScryfallException object.
    """
    msg = error["details"]
    if warns := error.get("warnings"):
        msg += get_bullet_points(warns, "  -")
    kwargs["exception"] = RequestException(msg, response=response)
    return ScryfallException(**kwargs)


"""
* Scryfall Requests: Cards
"""


@scryfall_request_wrapper()
def get_card_unique(
    card_set: str, card_number: str, lang: str = "en"
) -> dict[str, Any]:
    """Get card using /cards/:code/:number(/:lang) Scryfall API endpoint.

    Notes:
        https://scryfall.com/docs/api/cards/collector

    Args:
        card_set: Set code of the card, ex: MH2
        card_number: Collector number of the card
        lang: Lang code to look for, ex: en

    Returns:
        Card dict or ScryfallException
    """
    # Establish API pathing
    url = ScryURL.API.Cards.Main / card_set.lower() / card_number
    url = url / lang if lang != "en" else url

    # Track the params
    params: ScryfallExceptionKwargs = {
        "card_set": card_set,
        "card_number": card_number,
        "lang": lang,
    }

    # Request the data
    res = requests.get(url=str(url), headers=scryfall_http_header)
    card = res.json()

    # Ensure playable card was returned
    if card.get("object") == "error":
        raise get_error(error=card, response=res, **params)
    if card.get("object") == "card" and is_playable_card(card):
        return card
    params["exception"] = RequestException(
        "No card found with the provided set and number.", response=res
    )
    raise ScryfallException(**params)


@scryfall_request_wrapper()
def get_card_search(
    card_name: str,
    card_set: str | None = None,
    lang: str = "en",
    **kwargs: str | SupportsInt | float | Sequence[str | SupportsInt | float],
) -> dict[str, Any]:
    """Get card using /cards/search Scryfall API endpoint.

    Notes:
        https://scryfall.com/docs/api/cards/search

    Args:
        card_name: Name of the card, ex: Damnation
        card_set: Set code to look for, ex: MH2
        lang: Lang code to look for, ex: en

    Keyword Args:
        include_extras (str): A boolean string indicating whether to return card
            objects marked as 'extras'.
        dir (str): Direction to sort the results, asc: ascending, desc: descending.
        unique (str): Strategy for deciding what Card objects are considered unique for
            returning results. Options are: card, arts, prints
        order (str): Strategy for sorting the returned  results. Options are:
            name, set, released, rarity, color, usd, tix, eur, cmc, power, toughness,
            edhrec, penny, artist, review

    Returns:
        Card dict or ScryfallException
    """
    # Query Scryfall
    res = requests.get(
        url=str(
            ScryURL.API.Cards.Search.with_query(
                {
                    "q": f'!"{card_name}"'
                    f" lang:{lang}"
                    f"{f' set:{card_set.lower()}' if card_set else ''}",
                    **kwargs,
                }
            )
        ),
        headers=scryfall_http_header,
    )
    data = res.json()

    # Check for a playable card
    if data.get("object") == "error":
        raise get_error(
            error=data, response=res, card_name=card_name, card_set=card_set, lang=lang
        )
    for c in data.get("data", []):
        if is_playable_card(c):
            return c

    # No playable results
    raise ScryfallException(
        exception=RequestException(
            "No card found with the provided search terms.", response=res
        ),
        card_name=card_name,
        card_set=card_set,
        lang=lang,
    )


@scryfall_request_wrapper()
@return_on_exception([])
def get_cards_paged(
    url: yarl.URL | None = None,
    all_pages: bool = True,
    **kwargs: str | SupportsInt | float | Sequence[str | SupportsInt | float],
) -> list[dict[str, Any]]:
    """Grab paginated card list from a Scryfall API endpoint.

    Args:
        url: Scryfall API URL endpoint to access, uses Scryfall Search API if not provided.
        all_pages: Whether to return all additional pages, or just the first. Returns all by default.
        **kwargs: Optional parameters to pass to API endpoint.
    """
    # Configure URL object
    url = url or ScryURL.API.Cards.Search

    # Query Scryfall
    req = requests.get(url=str(url.with_query(kwargs)), headers=scryfall_http_header)
    res = req.json()
    cards = res.get("data", [])

    # Check for an error object
    if res.get("object") == "error":
        raise get_error(error=res, response=req)

    # Add additional pages if any exist
    if all_pages and res.get("has_more") and res.get("next_page"):
        cards.extend(get_cards_paged(url=res.get["next_page"], all_pages=all_pages))
    return cards


@scryfall_request_wrapper()
@return_on_exception([])
def get_cards_oracle(
    oracle_id: str,
    all_pages: bool = False,
    **kwargs: str | SupportsInt | float | Sequence[str | SupportsInt | float],
) -> list[dict[str, Any]]:
    """Grab paginated card list from a Scryfall API endpoint using the Oracle ID of the card.

    Args:
        oracle_id: Scryfall Oracle ID of the card.
        all_pages: Whether to return all additional pages, or just the first.
        **kwargs: Optional parameters to pass to API endpoint.

    Returns:
        A list of card objects.
    """
    return get_cards_paged(
        url=ScryURL.API.Cards.Search,
        all_pages=all_pages,
        q=f"oracleid:{oracle_id}",
        dir=kwargs.pop("dir", "asc"),
        order=kwargs.pop("order", "released"),
        unique=kwargs.pop("unique", "prints"),
        **kwargs,
    )


"""
* Scryfall Requests: Sets
"""


@scryfall_request_wrapper()
@return_on_exception({})
def get_set(card_set: str) -> dict[str, Any]:
    """Grab Set data from Scryfall.

    Args:
        card_set: The set to look for, ex: MH2

    Returns:
        Scryfall set dict or empty dict.
    """
    # Make the request
    res = requests.get(
        str(ScryURL.API.Sets.All / card_set.upper()),
        headers=scryfall_http_header,
    )
    data = res.json()

    # Check for an error object
    if data.get("object") == "error":
        raise get_error(error=data, response=res, **{"card_set": card_set})
    return data or {}


"""
* Scryfall Requests: Generics
"""


@scryfall_request_wrapper()
@return_on_exception({})
def get_uri_object(
    url: yarl.URL,
    **kwargs: str | SupportsInt | float | Sequence[str | SupportsInt | float],
) -> dict[str, Any]:
    """Pull a single object from Scryfall using a URI from a previous Scryfall data set.

    Args:
        url: Formatted URL to pull object from.

    Returns:
        A Scryfall object, e.g. Card, Set, etc.
    """
    res = requests.get(str(url.with_query(kwargs)), headers=scryfall_http_header)
    data = res.json()

    # Check for error object
    if data.get("object") == "error":
        raise get_error(error=data, response=res)
    return data


@scryfall_request_wrapper()
@return_on_exception(None)
def get_card_scan(img_url: str) -> Path:
    """Downloads scryfall art from URL

    Args:
        img_url: Scryfall URI for image.

    Returns:
        Filename of the saved image, None if unsuccessful.

    Raises:
        RequestException: If image couldn't be retrieved.
    """
    res = requests.get(img_url, stream=True)
    if res.status_code != 200:
        raise RequestException("Couldn't retrieve image from scryfall.", response=res)
    with open(PATH.LOGS_SCAN, "wb") as f:
        copyfileobj(res.raw, f)
    return PATH.LOGS_SCAN


"""
* Scryfall Data Utils
"""


def is_playable_card(card_json: dict[str, Any]) -> bool:
    """Checks if this card object is a playable game piece.

    Args:
        card_json: Scryfall data for this card.

    Returns:
        Valid scryfall data if check passed, else None.
    """
    if card_json.get("set_type") in ["minigame"]:
        # Ignore minigame insert cards
        return False
    if card_json.get("layout") in ["art_series", "reversible_card"]:
        # Ignore art series and reversible cards
        # TODO: Implement support for reversible
        return False
    if card_json.get("set_type") in ["memorabilia"] and "(Theme)" in card_json.get(
        "name", ""
    ):
        # Ignore theme insert cards (Jumpstart)
        return False
    return True
