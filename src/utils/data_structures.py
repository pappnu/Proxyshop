import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path

import yaml
from pydantic import BaseModel


def first[T](iterable: Iterable[T]) -> T:
    return next(iter(iterable))


def find_index[T](iterable: Iterable[T], condition: Callable[[T], bool]) -> int:
    for idx, item in enumerate(iterable):
        if condition(item):
            return idx
    return -1


def parse_model[T: BaseModel](path: Path, model: type[T]) -> T:
    if path.suffix == ".json":
        return model.model_validate_json(path.read_bytes())
    else:
        if path.suffix == ".toml":
            with open(path, "rb") as f:
                data = tomllib.load(f)
            return model.model_validate(data)
        if path.suffix in (".yaml", ".yml"):
            with open(path, "rb") as f:
                data = yaml.safe_load(f)
            return model.model_validate(data)
    raise NotImplementedError(
        f"{
            model
        } can be parsed only from .json, .toml, .yaml and .yml files. Got file: {path}"
    )


def dump_model(path: Path, model: BaseModel) -> None:
    with open(path, "w", encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            yaml.dump(model.model_dump(), stream=f)
