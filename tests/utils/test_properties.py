from src.utils.properties import tracked_prop


def test_tracked_prop_is_cached_per_instance_and_tracks_updates() -> None:
    class State:
        def __init__(self) -> None:
            self._changes: set[str] = set()

        @tracked_prop
        def values(self) -> list[int]:
            return []

    first, second = State(), State()
    first.values.append(1)
    assert second.values == []
    first.values = [2]
    assert first._changes == {"values"}  # pyright: ignore[reportPrivateUsage]
    del first.values
    assert first.values == []
