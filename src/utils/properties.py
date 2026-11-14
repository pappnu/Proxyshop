from collections.abc import Callable
from typing import Protocol, overload


class SupportsChangeTracking(Protocol):
    _changes: set[str]


class tracked_prop[T, C: SupportsChangeTracking]:
    """A cached property that records assignments in the instance's _changes set."""

    def __init__(self, getter: Callable[[C], T]):
        self.getter = getter
        self._name: str | None = None
        self._cache_name: str | None = None

    @overload
    def __get__(self, instance: None, _owner: type[C]) -> tracked_prop[T, C]: ...

    @overload
    def __get__(self, instance: C, _owner: type[C]) -> T: ...

    def __get__(
        self, instance: C | None, _owner: type[C]
    ) -> T | tracked_prop[T, C]:
        if instance is None:
            return self
        if self._cache_name is None:
            return self.getter(instance)
        try:
            return getattr(instance, self._cache_name)
        except AttributeError:
            value = self.getter(instance)
            setattr(instance, self._cache_name, value)
            return value

    def __set__(self, instance: C, value: T) -> None:
        if self._cache_name is not None:
            setattr(instance, self._cache_name, value)
        if self._name is not None:
            instance._changes.add(self._name)  # pyright: ignore[reportPrivateUsage]

    def __set_name__(self, _owner: type[C], name: str) -> None:
        self._name = name
        self._cache_name = f"_{name}_tracked_value"

    def __delete__(self, instance: C) -> None:
        if self._cache_name is not None and hasattr(instance, self._cache_name):
            delattr(instance, self._cache_name)
