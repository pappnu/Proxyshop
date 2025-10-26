"""
* Load Global Application State
"""

from src.utils.adobe import PhotoshopHandler
from src.utils.threading import ThreadInitializedInstance

from ._config import AppConfig
from ._loader import (
    get_all_plugins,
    get_all_templates,
    get_template_map,
    get_template_map_defaults,
)
from ._state import PATH, AppConstants, AppEnvironment

"""
* Globally Loaded Objects
"""


# Global environment object
ENV = AppEnvironment()

# Global constants object
CON = AppConstants()

# Global settings object
CFG = AppConfig(env=ENV)

# Global Photoshop handler
APP = ThreadInitializedInstance(lambda: PhotoshopHandler(env=ENV))

# Conditionally import the GUI console
if not ENV.HEADLESS:
    from src.gui.console import GUIConsole as Console
else:
    from .console import TerminalConsole as Console
CONSOLE = Console(cfg=CFG, env=ENV, app=APP)

# Global plugins and templates
PLUGINS = get_all_plugins(con=CON, env=ENV)
TEMPLATES = get_all_templates(con=CON, env=ENV, plugins=PLUGINS)
TEMPLATE_MAP = get_template_map(templates=TEMPLATES)
TEMPLATE_DEFAULTS = get_template_map_defaults(TEMPLATE_MAP)

# Export objects
__all__ = ["APP", "CFG", "CON", "CONSOLE", "ENV", "PATH"]
