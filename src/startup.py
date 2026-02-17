from logging import getLogger
from threading import Thread

from packaging.version import InvalidVersion, parse
from pydantic import ValidationError
from requests import RequestException

from src import CON, ENV
from src._state import PATH
from src.utils.adobe import PhotoshopHandler
from src.utils.fonts import check_app_fonts
from src.utils.github import get_github_releases
from src.utils.hexapi import get_api_key, update_hexproof_cache
from src.utils.threading import ThreadInitializedInstance

_logger = getLogger(__name__)


def photoshop_checks(app: PhotoshopHandler) -> None:
    # Check Photoshop connection
    result = app.refresh_app()
    if isinstance(result, OSError):
        # Photoshop test failed
        _logger.exception(
            "Photoshop connection failed. Can't test fonts without Photoshop.",
            exc_info=result,
        )
        return

    # Photoshop test passed
    _logger.info("Connected to Photoshop.")

    # Check for missing or outdated fonts
    missing, outdated = check_app_fonts(app, [PATH.FONTS])

    # Font test passed
    if not missing and not outdated:
        _logger.info("All essential fonts are installed.")
        return

    # Missing fonts
    if missing:
        _logger.warning(
            f"The following fonts aren't installed:<br>{
                '<br>'.join(
                    [details['name'] for details in missing.values() if details['name']]
                )
            }"
        )
    if outdated:
        _logger.warning(
            f"The following fonts are outdated and have to be reinstalled:<br>{
                '<br>'.join(
                    [
                        details['name']
                        for details in outdated.values()
                        if details['name']
                    ]
                )
            }"
        )


def check_app_version() -> None:
    """Check if app is the latest version.

    Returns:
        Return True if up to date, otherwise False.
    """
    if ENV.APP_UPDATES_REPO:
        try:
            releases = get_github_releases(ENV.APP_UPDATES_REPO, per_page=1)
            if len(releases) > 0:
                latest = releases[0].tag_name
                try:
                    update_available = parse(ENV.VERSION.lstrip("v")) < parse(
                        latest.lstrip("v")
                    )
                except InvalidVersion:
                    update_available = ENV.VERSION < latest
                if update_available:
                    _logger.info(
                        f'A newer version of Proxyshop is available: {
                            latest
                        }. <a href="https://github.com/{
                            ENV.APP_UPDATES_REPO
                        }/releases">Download</a>'
                    )
        except RequestException, ValidationError:
            _logger.exception("Failed to check app version.")


def update_set_data() -> None:
    # Update set data if needed
    updated, error = update_hexproof_cache()
    if updated:
        CON.reload()
        _logger.info("Hexproof API data update was applied.")
    if error:
        _logger.error(f"Failed to update Hexproof API data: {error}")


def check_api_keys() -> None:
    # Check if API keys are valid
    if not ENV.API_GOOGLE:
        ENV.API_GOOGLE = get_api_key("proxyshop.google.drive")
    if not ENV.API_AMAZON:
        ENV.API_AMAZON = get_api_key("proxyshop.amazon.s3")
    keys = {
        "Google Drive": ENV.API_GOOGLE,
        "Amazon S3": ENV.API_AMAZON,
    }
    if keys_missing := [k for k, v in keys.items() if not v]:
        _logger.warning(f"Failed to retrieve API keys for: {', '.join(keys_missing)}")
    else:
        _logger.info(f"Retrieved keys for: {', '.join(keys)}")


def run_startup_checks(
    photoshop_initializer: ThreadInitializedInstance[PhotoshopHandler],
) -> None:
    photoshop_initializer.initialize()
    if photoshop_initializer.ready:
        photoshop_checks(photoshop_initializer.instance)
    else:
        photoshop_initializer.add_listener(photoshop_checks)

    for check in (check_app_version, update_set_data, check_api_keys):
        Thread(target=check).start()
