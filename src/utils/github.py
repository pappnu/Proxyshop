from collections.abc import Callable
from logging import getLogger
from typing import Literal

from backoff import expo, on_exception
from limits import RateLimitItemPerHour
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from omnitils.exceptions import return_on_exception
from omnitils.rate_limit import rate_limit
from pydantic import BaseModel, RootModel
from requests import RequestException, get

from src.utils.logging import log_on_exception

_logger = getLogger(__name__)

# Rate limiter to safely limit GitHub requests
_rate_limit_storage = MemoryStorage()
_rate_limiter = MovingWindowRateLimiter(_rate_limit_storage)
_rate_limit = RateLimitItemPerHour(60)

_headers = {"accept": "application/vnd.github+json"}

GITHUB_API_BASE_URL = "https://api.github.com/"
GITHUB_API_RELEASES_URL = (
    GITHUB_API_BASE_URL + "repos/{repo}/releases?per_page={per_page}&page={page}"
)


# These definitions are incomplete since we don't need most of the fields.
class GitHubReleaseAsset(BaseModel):
    id: int
    name: str
    content_type: str
    state: Literal["uploaded", "open"]
    size: int
    """Bytes"""
    created_at: str
    updated_at: str
    browser_download_url: str


class GitHubRelease(BaseModel):
    id: int
    tag_name: str
    name: str
    draft: bool
    prerelease: bool
    created_at: str
    updated_at: str
    published_at: str
    assets: list[GitHubReleaseAsset]


GitHubReleases = RootModel[list[GitHubRelease]]


def github_request_wrapper[T, **P](
    fallback: T,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]):
        @return_on_exception(fallback)
        @log_on_exception(logger=_logger)
        @rate_limit(limiter=_rate_limiter, limit=_rate_limit)
        @on_exception(expo, RequestException, logger=None, max_tries=1, max_time=1)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


_default_releases: list[GitHubRelease] = []


@github_request_wrapper(_default_releases)
def get_github_releases(
    repository: str, per_page: int = 5, page: int = 1
) -> list[GitHubRelease]:
    response = get(
        GITHUB_API_RELEASES_URL.format(repo=repository, per_page=per_page, page=page),
        headers=_headers,
        timeout=(10, 10),
    )
    if response.status_code == 200:
        return GitHubReleases.model_validate_json(response.content).root
    raise RequestException(response=response)
