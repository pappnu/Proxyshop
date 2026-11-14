from src.utils.strings import get_line, normalize_str


def test_normalize_str() -> None:
    assert normalize_str("Café!") == "cafe"


def test_get_line() -> None:
    assert get_line("first|second", 1, sep="|") == "second"
