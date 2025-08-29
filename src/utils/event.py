from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class SubscriptableEvent(Generic[T]):
    def __init__(self) -> None:
        self._listeners: set[Callable[[T], None]] = set()

    def add_listener(self, listener: Callable[[T], None]) -> None:
        self._listeners.add(listener)

    def listen_once(self, listener: Callable[[T], None]) -> None:
        def one_off(value: T) -> None:
            try:
                self._listeners.remove(one_off)
            except KeyError:
                pass
            listener(value)

        self.add_listener(one_off)

    def remove_listener(self, listener: Callable[[T], None]) -> bool:
        try:
            self._listeners.remove(listener)
            return True
        except KeyError:
            return False

    def trigger(self, value: T) -> None:
        # Copy the set in order to allow listeners to remove themselves during iteration.
        for listener in self._listeners.copy():
            listener(value)
