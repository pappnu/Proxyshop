"""
* Scryfall API Module
"""

from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from shutil import copyfileobj
from typing import (
    Generic,
    Literal,
    NotRequired,
    ParamSpec,
    SupportsInt,
    TypedDict,
    TypeVar,
    Unpack,
)
from uuid import UUID

import requests
import yarl
from backoff import expo, on_exception
from hexproof.scryfall.enums import ScryURL
from limits import RateLimitItemPerSecond
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from omnitils.exceptions import ExceptionLogger, log_on_exception, return_on_exception
from pydantic import BaseModel, HttpUrl, ValidationError
from requests.exceptions import RequestException

from src import CONSOLE, PATH
from src.console import get_bullet_points
from src.utils.download import HEADERS
from src.utils.rate_limit import rate_limit

"""
* Types
"""

T = TypeVar("T")
P = ParamSpec("P")

type LayoutType = Literal[
    "normal",
    "split",
    "flip",
    "transform",
    "modal_dfc",
    "meld",
    "leveler",
    "class",
    "case",
    "saga",
    "adventure",
    "mutate",
    "prototype",
    "battle",
    "planar",
    "scheme",
    "vanguard",
    "token",
    "double_faced_token",
    "emblem",
    "augment",
    "host",
    "art_series",
    "reversible_card",
    # Non-official extensions
    "planeswalker",
    "planeswalker_tf",
    "planeswalker_mdfc",
    "station",
]

type MagicColor = Literal["W", "U", "B", "R", "G"]

type Legality = Literal["legal", "not_legal", "restricted", "banned"]

type BorderColor = Literal["black", "white", "borderless", "yellow", "silver", "gold"]

type Finish = Literal["foil", "nonfoil", "etched"]

type FrameEffect = Literal[
    "legendary",
    "miracle",
    "enchantment",
    "draft",
    "devoid",
    "tombstone",
    "colorshifted",
    "inverted",
    "sunmoondfc",
    "compasslanddfc",
    "originpwdfc",
    "mooneldrazidfc",
    "waxingandwaningmoondfc",
    "showcase",
    "extendedart",
    "companion",
    "etched",
    "snow",
    "lesson",
    "shatteredglass",
    "convertdfc",
    "fandfc",
    "upsidedowndfc",
    "spree",
    # Non-official
    "meld",
]

type ScryfallGame = Literal["paper", "arena", "mtgo"]

type ScryfallImageStatus = Literal["missing", "placeholder", "lowres", "highres_scan"]

type Rarity = Literal["common", "uncommon", "rare", "special", "mythic", "bonus"]

type SetType = Literal[
    "core",
    "expansion",
    "masters",
    "eternal",
    "alchemy",
    "masterpiece",
    "arsenal",
    "from_the_vault",
    "spellbook",
    "premium_deck",
    "duel_deck",
    "draft_innovation",
    "treasure_chest",
    "commander",
    "planechase",
    "archenemy",
    "vanguard",
    "funny",
    "starter",
    "box",
    "promo",
    "token",
    "memorabilia",
    "minigame",
]


class ScryfallImageUris(BaseModel):
    png: HttpUrl
    border_crop: HttpUrl
    art_crop: HttpUrl
    large: HttpUrl
    normal: HttpUrl
    small: HttpUrl


class ScryfallPrices(BaseModel):
    usd: str | None = None
    usd_foil: str | None = None
    usd_etched: str | None = None
    eur: str | None = None
    eur_foil: str | None = None
    eur_etched: str | None = None
    tix: str | None = None


class ScryfallPurchaseUris(BaseModel):
    tcgplayer: HttpUrl
    cardmarket: HttpUrl
    cardhoarder: HttpUrl


class ScryfallRelatedCard(BaseModel):
    id: UUID
    object: Literal["related_card"]
    component: Literal["token", "meld_part", "meld_result", "combo_piece"]
    name: str
    type_line: str
    uri: HttpUrl


class ScryfallPreview(BaseModel):
    previewed_at: date | None = None
    source_uri: HttpUrl | Literal[""] | None = None
    source: str | None = None


class ScryfallCardFace(BaseModel):
    artist: str | None = None
    artist_id: UUID | None = None
    cmc: float | None = None
    color_indicator: list[MagicColor] | None = None
    colors: list[MagicColor] | None = None
    defense: str | None = None
    flavor_text: str | None = None
    illustration_id: UUID | None = None
    image_uris: ScryfallImageUris | None = None
    layout: LayoutType | None = None
    loyalty: str | None = None
    mana_cost: str | None = None
    name: str
    object: Literal["card_face"]
    oracle_id: UUID | None = None
    oracle_text: str | None = None
    power: str | None = None
    printed_name: str | None = None
    printed_text: str | None = None
    printed_type_line: str | None = None
    toughness: str | None = None
    type_line: str | None = None
    watermark: str | None = None


class ScryfallCard(BaseModel):
    class Config:
        fields = {"front": {"exclude": True}}

    # Core Card Fields
    arena_id: int | None = None
    id: UUID
    lang: str
    mtgo_id: int | None = None
    mtgo_foil_id: int | None = None
    multiverse_ids: list[int] | None = None
    tcgplayer_id: int | None = None
    tcgplayer_etched_id: int | None = None
    cardmarket_id: int | None = None
    object: Literal["card"]
    layout: LayoutType
    oracle_id: UUID | None = None
    prints_search_uri: HttpUrl
    rulings_uri: HttpUrl
    scryfall_uri: HttpUrl
    uri: HttpUrl

    # Gameplay Fields
    all_parts: list[ScryfallRelatedCard] | None = None
    card_faces: list[ScryfallCardFace] | None = None
    cmc: float
    color_identity: list[MagicColor]
    color_indicator: list[MagicColor] | None = None
    colors: list[MagicColor] | None = None
    defense: str | None = None
    edhrec_rank: int | None = None
    game_changer: bool | None = None
    hand_modifier: str | None = None
    keywords: list[str]
    legalities: dict[str, Legality]
    life_modifier: str | None = None
    loyalty: str | None = None
    mana_cost: str | None = None
    name: str
    oracle_text: str | None = None
    penny_rank: int | None = None
    power: str | None = None
    produced_mana: list[str] | None = None
    reserved: bool
    toughness: str | None = None
    type_line: str

    # Print Fields
    artist: str | None = None
    artist_ids: list[UUID] | None = None
    attraction_lights: list[int] | None = None
    booster: bool
    border_color: BorderColor
    card_back_id: UUID | None = None
    collector_number: str
    content_warning: bool | None = None
    digital: bool
    finishes: list[Finish]
    flavor_name: str | None = None
    flavor_text: str | None = None
    frame_effects: list[FrameEffect] | None = None
    frame: str
    full_art: bool
    games: list[ScryfallGame]
    highres_image: bool
    illustration_id: UUID | None = None
    image_status: ScryfallImageStatus
    image_uris: ScryfallImageUris | None = None
    oversized: bool
    prices: ScryfallPrices
    printed_name: str | None = None
    printed_text: str | None = None
    printed_type_line: str | None = None
    promo: bool
    promo_types: list[str] | None = None
    purchase_uris: ScryfallPurchaseUris | None = None
    rarity: Rarity
    related_uris: dict[str, HttpUrl]
    released_at: date
    reprint: bool
    scryfall_set_uri: HttpUrl
    set_name: str
    set_search_uri: HttpUrl
    set_type: SetType
    set_uri: HttpUrl
    set: str
    set_id: UUID
    story_spotlight: bool
    textless: bool
    variation: bool
    variation_of: UUID | None = None
    security_stamp: str | None = None
    watermark: str | None = None
    preview: ScryfallPreview | None = None

    # Non-official extensions
    front: bool = True


class ScryfallList(BaseModel, Generic[T]):
    object: Literal["list"]
    data: list[T]
    has_more: bool
    next_page: HttpUrl | None = None
    total_cards: int | None = None
    warnings: list[str] | None = None


class ScryfallCardList(ScryfallList[ScryfallCard]):
    pass


class ScryfallSet(BaseModel):
    object: Literal["set"]
    id: UUID
    code: str
    mtgo_code: str | None = None
    arena_code: str | None = None
    tcgplayer_id: int | None = None
    name: str
    set_type: SetType
    released_at: date | None = None
    block_code: str | None = None
    block: str | None = None
    parent_set_code: str | None = None
    card_count: int
    printed_size: int | None = None
    digital: bool
    foil_only: bool
    nonfoil_only: bool
    scryfall_uri: HttpUrl
    uri: HttpUrl
    icon_svg_uri: HttpUrl
    search_uri: HttpUrl


class ScryfallError(BaseModel):
    """Error object outlined in Scryfall's API docs.

    Notes:
        https://scryfall.com/docs/api/errors
    """

    object: Literal["error"]
    code: str
    status: int
    details: str
    type: str | None = None
    warnings: list[str] | None = None


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
        @rate_limit(strategy=_scryfall_rate_limit, limit=_rate_limit)
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
    msg = error.details
    if warns := error.warnings:
        msg += get_bullet_points(warns, "  -")
    kwargs["exception"] = RequestException(msg, response=response)
    return ScryfallException(**kwargs)


"""
* Scryfall Requests: Cards
"""


@scryfall_request_wrapper()
def get_card_via_url(url: str) -> ScryfallCard:
    res = requests.get(url=str(url), headers=scryfall_http_header)

    try:
        card = ScryfallCard.model_validate_json(res.content)
        if is_playable_card(card):
            return card
    except ValidationError as exc:
        # Handle Scryfall error
        try:
            err = ScryfallError.model_validate_json(res.content)
            raise get_error(error=err, response=res)
        except ValidationError:
            raise ScryfallException(exception=exc)

    # No playable result
    raise ScryfallException(
        exception=RequestException(
            "No playable card found with the provided set and number.", response=res
        )
    )


@scryfall_request_wrapper()
def get_card_unique(card_set: str, card_number: str, lang: str = "en") -> ScryfallCard:
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

    # Request the data
    res = requests.get(url=str(url), headers=scryfall_http_header)

    try:
        card = ScryfallCard.model_validate_json(res.content)
        if is_playable_card(card):
            return card
    except ValidationError as exc:
        # Handle Scryfall error
        try:
            err = ScryfallError.model_validate_json(res.content)
            raise get_error(
                error=err,
                response=res,
                card_set=card_set,
                card_number=card_number,
                lang=lang,
            )
        except ValidationError:
            raise ScryfallException(
                exception=exc,
                card_set=card_set,
                card_number=card_number,
                lang=lang,
            )

    # No playable result
    raise ScryfallException(
        exception=RequestException(
            "No playable card found with the provided set and number.", response=res
        ),
        card_set=card_set,
        card_number=card_number,
        lang=lang,
    )


@scryfall_request_wrapper()
def get_card_search(
    card_name: str,
    card_set: str | None = None,
    lang: str = "en",
    **kwargs: str | SupportsInt | float | Sequence[str | SupportsInt | float],
) -> ScryfallCard:
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

    try:
        list_data = ScryfallCardList.model_validate_json(res.content)
        for card in list_data.data:
            if is_playable_card(card):
                return card
    except ValidationError as exc:
        # Handle Scryfall error
        try:
            err = ScryfallError.model_validate_json(res.content)
            raise get_error(
                error=err,
                response=res,
                card_name=card_name,
                card_set=card_set,
                lang=lang,
            )
        except ValidationError:
            raise ScryfallException(
                exception=exc, card_name=card_name, card_set=card_set, lang=lang
            )

    # No playable results
    raise ScryfallException(
        exception=RequestException(
            "No playable card found with the provided search terms.", response=res
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
    **kwargs: yarl.QueryVariable,
) -> list[ScryfallCard]:
    """Grab paginated card list from a Scryfall API endpoint.

    Args:
        url: Scryfall API URL endpoint to access, uses Scryfall Search API if not provided.
        all_pages: Whether to return all additional pages, or just the first. Returns all by default.
        **kwargs: Optional parameters to pass to API endpoint.
    """
    # Configure URL object
    url = url or ScryURL.API.Cards.Search

    # Query Scryfall
    res = requests.get(url=str(url.with_query(kwargs)), headers=scryfall_http_header)

    try:
        list_data = ScryfallCardList.model_validate_json(res.content)
        cards = list_data.data
        if all_pages and list_data.has_more and list_data.next_page:
            cards.extend(
                get_cards_paged(
                    url=yarl.URL(str(list_data.next_page)), all_pages=all_pages
                )
            )
        return cards
    except ValidationError as exc:
        # Handle Scryfall error
        try:
            err = ScryfallError.model_validate_json(res.content)
            raise get_error(error=err, response=res)
        except ValidationError:
            raise ScryfallException(exception=exc)


@scryfall_request_wrapper()
@return_on_exception(None)
def get_cards_oracle(
    oracle_id: str,
    all_pages: bool = False,
    **kwargs: yarl.QueryVariable,
) -> list[ScryfallCard]:
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
def get_set(card_set: str) -> ScryfallSet:
    """Grab Set data from Scryfall.

    Args:
        card_set: The set to look for, ex: MH2

    Returns:
        Scryfall set dict or empty dict.
    """
    # Make the request
    res = requests.get(
        str(ScryURL.API.Sets.All / card_set.upper()), headers=scryfall_http_header
    )

    try:
        return ScryfallSet.model_validate_json(res.content)
    except ValidationError as exc:
        # Handle Scryfall error
        try:
            err = ScryfallError.model_validate_json(res.content)
            raise get_error(
                error=err,
                response=res,
                card_set=card_set,
            )
        except ValidationError:
            raise ScryfallException(exception=exc, card_set=card_set)


"""
* Scryfall Requests: Generics
"""


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


def is_playable_card(card: ScryfallCard) -> bool:
    """Checks if this card object is a playable game piece.

    Args:
        card_json: Scryfall data for this card.

    Returns:
        Valid scryfall data if check passed, else None.
    """
    if card.set_type == "minigame":
        # Ignore minigame insert cards
        return False
    if card.layout in ["art_series", "reversible_card"]:
        # Ignore art series and reversible cards
        # TODO: Implement support for reversible
        return False
    if card.set_type == "memorabilia" and "(Theme)" in card.name:
        # Ignore theme insert cards (Jumpstart)
        return False
    return True
