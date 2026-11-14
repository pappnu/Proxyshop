from collections.abc import Callable
from contextlib import suppress
from typing import overload


@overload
def return_on_exception[T, V, **P](
    response: T,
) -> Callable[[Callable[P, V]], Callable[P, V | T]]: ...


@overload
def return_on_exception[T, V, **P](
    response: T | None = None,
) -> Callable[[Callable[P, V]], Callable[P, V | T | None]]: ...


def return_on_exception[T, V, **P](
    response: T | None = None,
) -> Callable[[Callable[P, V]], Callable[P, V | T | None]]:
    def decorator(func: Callable[P, V]) -> Callable[P, V | T | None]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> V | T | None:
            with suppress(Exception):
                return func(*args, **kwargs)
            return response

        return wrapper

    return decorator
