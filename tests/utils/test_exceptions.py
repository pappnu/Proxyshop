from src.utils.exceptions import return_on_exception


def test_return_on_exception_uses_fallback() -> None:
    @return_on_exception([])
    def failing_call() -> list[str]:
        raise ValueError("expected")

    assert failing_call() == []
