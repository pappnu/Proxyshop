from collections.abc import Callable, Iterable
from functools import wraps
from time import sleep, time

from limits import RateLimitItem
from limits.strategies import RateLimiter


class RateLimitError(Exception):
    pass


def rate_limit[T, **P](
    limiter: RateLimiter,
    limit: RateLimitItem,
    reschedule: bool = True,
    identifiers: Iterable[str] = (),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Limit calls, sleeping until the next window when reschedule is enabled."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if reschedule:
                while not limiter.hit(limit, *identifiers):
                    window = limiter.get_window_stats(limit, *identifiers)
                    sleep(max(0, window.reset_time - time()))
            elif not limiter.hit(limit, *identifiers):
                raise RateLimitError(f"Limit exceeded for '{identifiers}' '{limit}'")
            return func(*args, **kwargs)

        return wrapper

    return decorator
