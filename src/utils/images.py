from dataclasses import dataclass
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import IO

from PIL import Image
from pydantic import ValidationError

from src.cards import CardDetails, parse_card_info
from src.render_spec import parse_render_spec
from src.utils.data_structures import find_index
from src.utils.scryfall import ScryfallCard

_logger = getLogger(__name__)

IMAGE_ENCODING_TO_SUFFIX_MAPPING: dict[str, str] = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WebP": ".webp",
}


def save_scaled_card_image(
    input_path: str | PathLike[str] | IO[bytes],
    output_path: Path,
    image_format: str,
    downscale_width: int | None = None,
    quality: int = 95,
):
    with Image.open(input_path) as f:
        if downscale_width is not None:
            img_width, img_height = f.size
            ratio = downscale_width / img_width
            if ratio < 1:
                f.thumbnail(
                    (downscale_width, round(ratio * img_height)),
                    resample=Image.Resampling.LANCZOS,
                )
        image_format = image_format.lower()
        if image_format == "png":
            save_kwargs = {"optimize": True}
        elif image_format == "jpeg":
            if f.mode == "RGBA":
                f = f.convert("RGB")
            save_kwargs = {"optimize": True, "quality": quality}
        elif image_format == "webp":
            save_kwargs = {"quality": quality, "method": 6}
        else:
            save_kwargs = {}
        f.save(output_path, format=image_format, **save_kwargs)


def match_images_with_data_files(
    paths: list[Path],
) -> list[CardDetails | tuple[CardDetails, ScryfallCard]]:
    """
    Pairs data files (.json) with image files that share the same name.

    Raises:
        Pydantic.ValidationError: if some of the data files don't conform to the data model
    """
    data_files = [pth for pth in paths if pth.suffix == ".json"]
    render_specs = [pth for pth in paths if pth.suffix in (".yaml", ".yml")]
    image_files = [pth for pth in paths if pth.suffix not in (".json", ".yaml", ".yml")]

    results: list[CardDetails | tuple[CardDetails, ScryfallCard]] = []

    @dataclass
    class _ValidationError(ValidationError):
        file: Path

    def add_card(card: CardDetails) -> None:
        card_name = card["name"]

        idx = find_index(data_files, lambda item: item.stem == card_name)
        if idx > -1:
            data_file = data_files.pop(idx)
            try:
                results.append(
                    (
                        card,
                        ScryfallCard.model_validate_json(data_file.read_bytes()),
                    )
                )
            except ValidationError as e:
                raise _ValidationError(data_file) from e
        else:
            results.append(card)

    try:
        for path in render_specs:
            try:
                cards = parse_render_spec(path).cards
            except ValidationError as e:
                raise _ValidationError(path) from e

            for card in cards:
                add_card(card)

        for path in image_files:
            card = parse_card_info(path)
            add_card(card)
    except _ValidationError as e:
        _logger.exception(
            f"Data file <i>{e.file}</i> failed to validate. Please correct the reported errors in the data and then try again. Since the file selection was invalid nothing will be added to the render queue."
        )
        return []

    if data_files:
        _logger.warning(
            f"Couldn't find a matching image file for files:<br>{
                '<br>'.join([str(pth) for pth in data_files])
            }When selecting JSON files for rendering make sure to also select an image whose card name part matches the JSON file's name, e.g. <i>my_custom_card (artist).png</i> and <i>my_custom_card.json</i>. Since the file selection was invalid nothing will be added to the render queue."
        )
        return []

    return results
