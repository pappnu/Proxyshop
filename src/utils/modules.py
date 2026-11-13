import sys
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from os import PathLike
from pathlib import Path
from types import ModuleType


def _add_python_path(path: str | PathLike[str]) -> None:
    path_string = str(path)
    if path_string not in sys.path:
        sys.path.append(path_string)


def _remove_python_path(path: str | PathLike[str]) -> None:
    path_string = str(path)
    if path_string in sys.path:
        sys.path.remove(path_string)


def unload_module(name: str) -> None:
    """Removes a module and its submodules from `sys.modules`."""
    for module_name in list(sys.modules):
        if module_name == name or module_name.startswith(f"{name}."):
            del sys.modules[module_name]


def import_modules_recursively(
    name: str, path: Path, hotswap: bool = False
) -> ModuleType | None:
    """Imports modules from a directory and its subdirectories recursivley,
    optionally reloading the imported modules."""
    if name in sys.modules:
        if not hotswap:
            return sys.modules[name]
        unload_module(name)

    _add_python_path(path)
    try:
        _import_nested_modules(
            name=name,
            path=path,
            recursive=True,
            hotswap=hotswap,
            ignored=["__init__.py", "__pycache__"],
        )

        init_module = path / "__init__.py"
        if not init_module.is_file():
            return None

        return import_module_from_path(name=name, path=init_module, hotswap=hotswap)
    finally:
        _remove_python_path(path)


def _import_nested_modules(
    name: str,
    path: Path,
    recursive: bool = True,
    hotswap: bool = False,
    ignored: list[str] | None = None,
) -> None:
    if ignored is None:
        ignored = []

    for item in path.iterdir():
        if item.name in ignored:
            continue

        module_name = f"{name}.{item.stem}"
        if item.is_dir() and recursive:
            _add_python_path(item)
            try:
                _import_nested_modules(
                    name=module_name,
                    path=item,
                    hotswap=hotswap,
                    ignored=ignored,
                )
            finally:
                _remove_python_path(item)
        elif item.is_file() and item.suffix == ".py":
            import_module_from_path(name=module_name, path=item, hotswap=hotswap)


def import_module_from_path(name: str, path: Path, hotswap: bool = False) -> ModuleType:
    """Loads a Python module from a file path, optionally reloading it."""
    if name in sys.modules:
        if not hotswap:
            return sys.modules[name]
        unload_module(name)

    spec = spec_from_file_location(name=name, location=path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module {name!r} from {path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


def get_local_module(module_path: str, hotswap: bool = False) -> ModuleType:
    """Imports a local module by dotted name, optionally reloading it."""
    if module_path in sys.modules:
        if not hotswap:
            return sys.modules[module_path]
        unload_module(module_path)

    module = import_module(module_path)
    sys.modules[module_path] = module
    return module
