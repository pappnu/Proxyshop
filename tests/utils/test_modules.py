import sys
from pathlib import Path
from types import ModuleType

from src.utils.modules import import_module_from_path, unload_module


def test_unload_module_removes_package_and_submodules() -> None:
    package_name = "test_unload_module_package"
    module_names = [
        package_name,
        f"{package_name}.child",
        f"{package_name}.child.grandchild",
        f"{package_name}_sibling",
    ]
    sys.modules.update({name: ModuleType(name) for name in module_names})

    try:
        unload_module(package_name)

        assert package_name not in sys.modules
        assert f"{package_name}.child" not in sys.modules
        assert f"{package_name}.child.grandchild" not in sys.modules
        assert f"{package_name}_sibling" in sys.modules
    finally:
        for name in module_names:
            sys.modules.pop(name, None)


def test_import_module_from_path_hotswap_loads_changed_module(tmp_path: Path) -> None:
    module_name = "test_hotswap_module"
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text('value = "first"\n', encoding="utf-8")

    try:
        module = import_module_from_path(module_name, module_path)
        assert module.value == "first"

        module_path.write_text('value = "changed"\n', encoding="utf-8")

        reloaded_module = import_module_from_path(
            module_name, module_path, hotswap=True
        )

        assert reloaded_module.value == "changed"
    finally:
        unload_module(module_name)
