"""
* Tests: Card Text Logic
"""
from logging import getLogger
from pathlib import Path
from typing import TypedDict

from omnitils.files import load_data_file

from src._state import PATH
from src.cards import generate_italics

_logger = getLogger(__name__)

"""
* Types
"""


class TestCaseTextItalic (TypedDict):
    """Test cases for validating the generate italics function."""
    result: list[str]
    scenario: str
    text: str


"""
* Test Funcs
"""


def test_all_cases() -> bool:
    """Test all Text Logic cases."""

    # Load our test cases
    success = True
    test_file: Path = Path(PATH.SRC_DATA_TESTS, 'text_italic.toml')
    test_cases: dict[str, TestCaseTextItalic] = load_data_file(test_file)
    _logger.info(f"Testing > Card Text Logic (<b>{test_file.name}</b>)")

    # Check each test case for success
    for name, case in test_cases.items():

        # Compare actual test results VS expected test results
        result_actual, result_expected = generate_italics(case.get('text', '')), case.get('result', [])
        if not sorted(result_actual) == sorted(result_expected):
            success = False
            msg_actual = ''.join(f'\n {i}. <i>{n}</i>' for i, n in enumerate(result_actual, start=1))
            msg_expected = ''.join(f'\n {i}. <i>{n}</i>' for i, n in enumerate(result_expected, start=1))
            _logger.error(f"Case: {name} ({case.get('scenario', '')})")

            # Log what we expect
            if not result_expected:
                _logger.warning("This card doesn't have italic text!")
            else:
                _logger.warning(f"Italic strings expected: {msg_expected}")

            # Log what we found
            if not result_actual:
                _logger.warning("No italic strings were found!")
            else:
                _logger.warning(f"Italic strings found: {msg_actual}")

    # Did any tests fail?
    if success:
        _logger.info('All tests successful!')
    return success
