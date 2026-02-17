"""
* Tests: Frame Logic
* Credit to Chilli: https://tinyurl.com/chilli-frame-logic-tests
"""
from concurrent.futures import Future, as_completed
from concurrent.futures import ThreadPoolExecutor as Pool
from logging import getLogger
from multiprocessing import cpu_count
from pathlib import Path

from colorama import Fore, Style
from omnitils.files import load_data_file
from tqdm import tqdm

from src import CFG
from src._state import PATH
from src.cards import CardDetails, get_card_data, process_card_data
from src.console import LogColors
from src.enums.mtg import CardTextPatterns
from src.layouts import CardLayout, layout_map

_logger = getLogger(__name__)

"""
* TYPES
"""

FrameData = list[str]

"""
* UTIL FUNCS
"""


def get_frame_logic_cases() -> dict[str, dict[str, FrameData]]:
    """Return frame logic test cases from TOML data file."""
    return load_data_file(Path(PATH.SRC_DATA_TESTS, 'frame_data.toml'))


def format_result(layout: CardLayout) -> FrameData:
    """Format frame logic test result for comparison.

    Args:
        layout: Test result card layout data.

    Returns:
        Formatted frame logic test result data.
    """
    return [
        str(layout.__class__.__name__),
        str(layout.background),
        str(layout.pinlines),
        str(layout.twins),
        str(layout.is_nyx),
        str(layout.is_colorless)
    ]


"""
* TEST FUNCS
"""


def test_case(card_name: str, card_data: FrameData) -> tuple[str, FrameData, FrameData] | None:
    """Test frame logic for a target test case.

    Args:
        card_name: Card name for test case.
        card_data: Card data for test case.

    Returns:
        Tuple containing (card name, actual data, correct data) if the test failed, otherwise None.
    """
    try:
        # Check if a set code was provided
        set_code = None
        if all([n in card_name for n in ['[', ']']]):
             if set_match := CardTextPatterns.PATH_SET.search(card_name):
                set_code = set_match.group(1)
                card_name = card_name.replace(f'[{set_code}]', '').strip()

        # Create a fake card details object
        details: CardDetails = {
            'name': card_name,
            'set': set_code or "",
            'number': '',
            'creator': '',
            'file': Path(),
            'artist': ''
        }

        # Pull Scryfall data
        scryfall = get_card_data(
            card=details,
            cfg=CFG)
        if not scryfall:
            raise OSError('Did not return valid data from Scryfall.')
        # Process the Scryfall data
        scryfall = process_card_data(scryfall, details)
    except Exception as e:
        # Exception occurred during Scryfall lookup
        return _logger.error(f"Scryfall error occurred at card: '{card_name}'", exc_info=e)

    # Pull layout data for the card
    try:
        result_data: FrameData = format_result(
            layout_map[scryfall['layout']](
                scryfall=scryfall,
                file={
                    'name': card_name,
                    'artist': scryfall['artist'],
                    'set_code': scryfall['set'],
                    'creator': '', 'filename': ''}))
    except Exception as e:
        # Exception occurred during layout generation
        return _logger.error(f"Layout error occurred at card: '{card_name}'", exc_info=e)

    # Compare the results
    if not result_data == card_data:
        return card_name, result_data, card_data
    return


def test_target_case(cards: dict[str, FrameData]) -> None:
    """Test a known Frame Logic test case.

    Args:
        cards: Individual card frame cases to test.

    Returns:
        True if tests succeeded, otherwise False.
    """
    # Submit tests to a pool
    with Pool(max_workers=cpu_count()) as executor:
        tests_submitted: list[Future[tuple[str, FrameData, FrameData] | None]] = []
        tests_failed: list[tuple[str, FrameData, FrameData]] = []

        # Submit tasks to executor
        for card_name, data in cards.items():
            tests_submitted.append(
                executor.submit(test_case, card_name, data))

        # Create a progress bar
        pbar = tqdm(
            total=len(tests_submitted),
            bar_format=f'{LogColors.BLUE}'
                       '{l_bar}{bar}{r_bar}'
                       f'{LogColors.RESET}')

        # Iterate over completed tasks, update progress bar, add failed tasks
        for task in as_completed(tests_submitted):
            pbar.update(1)
            if result := task.result():
                tests_failed.append(result)

    # Set the progress bar result
    if tests_failed:
        pbar.set_postfix({
            "Status": (
                Fore.RED + "FAILED" + Style.RESET_ALL
            ) if tests_failed else (
                Fore.GREEN + "SUCCESS" + Style.RESET_ALL
            )
        })

    # Close progress bar and return failures
    pbar.close()

    # Log failed results
    if tests_failed:
        _logger.error("=" * 40)
        for name, actual, correct in tests_failed:
            _logger.warning(f'NAME: {name}')
            _logger.warning(f'RESULT [Actual / Expected]:\n'
                         f'{LogColors.RESET}{LogColors.WHITE}{actual}\n{correct}')
            _logger.error("=" * 40)
        _logger.error("SOME TESTS FAILED!")
        return

    # All tests successful
    _logger.info("ALL TESTS SUCCESSFUL!")


def test_all_cases() -> None:
    """Test all Frame Logic cases."""
    cases = get_frame_logic_cases()

    # Submit tests to a pool
    for case, cards in cases.items():
        _logger.info(f"CASE: {case}")
        test_target_case(cards)
