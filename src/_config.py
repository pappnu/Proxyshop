"""
* Global Settings Module
"""

from enum import StrEnum
from typing import Literal, overload

from src._loader import ConfigHandler, CustomConfigParser
from src._state import PATH
from src.enums.settings import (
    BorderColor,
    CollectorMode,
    CollectorPromo,
    FillMode,
    HasDefault,
    OutputFileType,
    ScryfallSorting,
    ScryfallUnique,
    WatermarkMode,
)


class AppConfig:
    """Stores the current state of app and template settings. Can be changed within a template
    class to affect rendering behavior."""

    def __init__(
        self,
        app_config: ConfigHandler | None = None,
        base_config: ConfigHandler | None = None,
        user_config: ConfigHandler | None = None,
    ):
        """Load initial settings values."""
        self.app_config = app_config or ConfigHandler(
            base_schema_path=PATH.SRC_DATA_CONFIG_APP,
            schema_path=None,
            ini_path=PATH.SRC_DATA_CONFIG_INI_APP,
        )
        self.base_config = base_config or ConfigHandler(
            base_schema_path=PATH.SRC_DATA_CONFIG_BASE,
            schema_path=None,
            ini_path=PATH.SRC_DATA_CONFIG_INI_BASE,
        )
        self.load(user_config)

    # region Pre-rendering properties

    @property
    def lang(self) -> str:
        return self.app_config.get_str_setting(
            "APP.DATA", "Scryfall.Language", default="en"
        )

    @property
    def scry_sorting(self) -> ScryfallSorting:
        return self.app_config.get_enum_setting(
            "APP.DATA",
            "Scryfall.Sorting",
            ScryfallSorting,
            default=ScryfallSorting.Released,
        )

    @property
    def scry_ascending(self) -> bool:
        return self.app_config.get_bool_setting(
            "APP.DATA", "Scryfall.Ascending", default=False
        )

    @property
    def scry_extras(self) -> bool:
        return self.app_config.get_bool_setting(
            "APP.DATA", "Scryfall.Extras", default=False
        )

    @property
    def scry_unique(self) -> ScryfallUnique:
        return self.app_config.get_enum_setting(
            "APP.DATA", "Scryfall.Unique", ScryfallUnique, default=ScryfallUnique.Arts
        )

    @property
    def manually_edit_card_data(self) -> bool:
        return self.app_config.get_bool_setting(
            "APP.DATA", "Manually.Edit.Card.Data", default=False
        )

    @property
    def manual_text_editor(self) -> str:
        return self.app_config.get_str_setting(
            "APP.DATA", "Manual.Text.Editor", default='notepad "{}"'
        )

    # endregion Pre-rendering properties

    def update_definitions(self):
        """Updates the defined settings values using the currently loaded ConfigParser object."""

        # APP - FILES
        self.overwrite_duplicate = self.file.getboolean(
            "APP.FILES", "Overwrite.Duplicate", fallback=True
        )
        self.output_file_type = self.get_option(
            "APP.FILES", "Output.File.Type", OutputFileType
        )
        self.output_file_name = self.file.get(
            section="APP.FILES",
            option="Output.File.Name",
            fallback="#name (#frame<, #suffix>) [#set] {#num}",
        )
        self.png_compression_level = self.file.getint(
            "APP.FILES", "PNG.Compression.Level", fallback=3
        )

        # APP - DATA
        self.use_printed_texts = self.file.getboolean(
            "APP.DATA", "Scryfall.Use.Printed.Texts", fallback=False
        )

        # APP - TEXT
        self.force_english_formatting = self.file.getboolean(
            "APP.TEXT", "Force.English.Formatting", fallback=False
        )

        # APP - RENDER
        self.select_variation = self.file.getboolean(
            "APP.RENDER", "Select.Variation", fallback=False
        )
        self.vertical_fullart = self.file.getboolean(
            "APP.RENDER", "Vertical.Fullart", fallback=False
        )

        # BASE - TEXT
        self.flavor_divider = self.file.getboolean(
            "BASE.TEXT", "Flavor.Divider", fallback=True
        )
        self.remove_flavor = self.file.getboolean(
            "BASE.TEXT", "No.Flavor.Text", fallback=False
        )
        self.remove_reminder = self.file.getboolean(
            "BASE.TEXT", "No.Reminder.Text", fallback=False
        )
        self.collector_mode = self.get_option(
            "BASE.TEXT", "Collector.Mode", CollectorMode
        )
        self.collector_promo = self.get_option(
            "BASE.TEXT", "Collector.Promo", CollectorPromo
        )

        # BASE - SYMBOLS
        self.symbol_enabled = self.file.getboolean(
            "BASE.SYMBOLS", "Enable.Expansion.Symbol", fallback=True
        )
        self.symbol_default = self.file.get(
            "BASE.SYMBOLS", "Default.Symbol", fallback="MTG"
        )
        self.symbol_force_default = self.file.getboolean(
            "BASE.SYMBOLS", "Force.Default.Symbol", fallback=False
        )
        self.symbol_force_rarity = self.file.get(
            "BASE.SYMBOLS", "Force.Rarity", fallback=""
        )

        # BASE - WATERMARKS
        self.watermark_mode = self.get_option(
            "BASE.WATERMARKS", "Watermark.Mode", WatermarkMode
        )
        self.watermark_default = self.file.get(
            "BASE.WATERMARKS", "Default.Watermark", fallback="WOTC"
        )
        self.watermark_opacity = self.file.getfloat(
            "BASE.WATERMARKS", "Watermark.Opacity", fallback=30
        )
        self.enable_basic_watermark = self.file.getboolean(
            "BASE.WATERMARKS", "Enable.Basic.Watermark", fallback=True
        )

        # BASE - TEMPLATES
        self.fill_mode: FillMode = FillMode(
            self.file.get(
                "BASE.TEMPLATES",
                "Border.Fill.Mode",
                fallback=FillMode.CONTENT_AWARE_FILL.value,
            )
        )
        self.fill_contract = self.file.getint(
            "BASE.TEMPLATES", "Border.Fill.Contract", fallback=10
        )
        self.fill_smooth = self.file.getint(
            "BASE.TEMPLATES", "Border.Fill.Smooth", fallback=0
        )
        self.fill_feather = self.file.getint(
            "BASE.TEMPLATES", "Border.Fill.Feather", fallback=5
        )
        self.exit_early = self.file.getboolean(
            "BASE.TEMPLATES", "Manual.Edit", fallback=False
        )
        self.pause_for_manual_art_alignment = self.file.getboolean(
            "BASE.TEMPLATES", "Manual.Art.Alignment.Pause", fallback=False
        )
        self.minimize_photoshop = self.file.getboolean(
            "BASE.TEMPLATES", "Minimize.Photoshop", fallback=False
        )
        self.import_scryfall_scan = self.file.getboolean(
            "BASE.TEMPLATES", "Import.Scryfall.Scan", fallback=False
        )
        self.border_color = self.get_option(
            "BASE.TEMPLATES", "Border.Color", BorderColor
        )

    """
    * Setting Utils
    """

    def get_option(
        self,
        section: str,
        key: str,
        enum_class: type[StrEnum],
        default: str | None = None,
    ) -> str:
        """Returns the current value of an "options" setting if that option exists in its StrEnum class.
        Otherwise, returns the default value of that StrEnum class.

        Args:
            section: Group (section) to access within the config file.
            key: Key to access within the setting group (section).
            enum_class: StrEnum class representing the options of this setting.
            default: Default value to return if current value is invalid.

        Returns:
            Validated current value, or default value.
        """
        defa: str = (
            default or str(enum_class.Default)
            if isinstance(enum_class, HasDefault)
            else ""
        )
        if self.file.has_section(section):
            option = self.file[section].get(key, fallback=defa)
            if option in enum_class:
                return option
        return defa

    @overload
    def get_setting(
        self, section: str, key: str, default: bool, is_bool: Literal[True]
    ) -> bool: ...

    @overload
    def get_setting(
        self, section: str, key: str, default: bool | None, is_bool: Literal[True]
    ) -> bool | None: ...

    @overload
    def get_setting(
        self, section: str, key: str, default: str, is_bool: Literal[False] = False
    ) -> str: ...

    @overload
    def get_setting(
        self,
        section: str,
        key: str,
        default: str | None = None,
        is_bool: Literal[False] = False,
    ) -> str | None: ...

    def get_setting(
        self,
        section: str,
        key: str,
        default: str | bool | None = None,
        is_bool: bool = False,
    ) -> str | bool | None:
        """Check if the setting exists and return it. Default will be returned if missing.

        Args:
            section: Section to look for.
            key: Key to look for within section.
            default: Default value to return if section/key missing.
            is_bool: Whether this value is a boolean.

        Returns:
            Value or default
        """
        if self.file.has_section(section):
            if self.file.has_option(section, key):
                if is_bool:
                    return self.file.getboolean(section, key, fallback=default)
                return self.file[section].get(key, fallback=default)
        return default

    @overload
    def get_bool_setting(self, section: str, key: str, default: bool) -> bool: ...

    @overload
    def get_bool_setting(
        self, section: str, key: str, default: bool | None = None
    ) -> bool | None: ...

    def get_bool_setting(
        self, section: str, key: str, default: bool | None = None
    ) -> bool | None:
        return self.get_setting(section, key, default, is_bool=True)

    @overload
    def get_int_setting(self, section: str, key: str, default: int) -> int: ...

    @overload
    def get_int_setting(
        self, section: str, key: str, default: int | None = None
    ) -> int | None: ...

    def get_int_setting(
        self, section: str, key: str, default: int | None = None
    ) -> int | None:
        setting = self.get_setting(section, key, None)
        if setting is not None:
            return int(setting)
        return default

    @overload
    def get_float_setting(self, section: str, key: str, default: float) -> float: ...

    @overload
    def get_float_setting(
        self, section: str, key: str, default: float | None = None
    ) -> float | None: ...

    def get_float_setting(
        self, section: str, key: str, default: float | None = None
    ) -> float | None:
        setting = self.get_setting(section, key, None)
        if setting is not None:
            return float(setting)
        return default

    """
    * Load ConfigParser Object
    """

    def load(self, config: ConfigHandler | None = None) -> None:
        """Reload the config file and define new values

        Args:
            config: to load from if provided, otherwise use app-wide configuration.
        """
        self.file = CustomConfigParser(default_section="", allow_no_value=True)
        # Combine app and base/template configs
        self.file.read_dict(self.app_config.setting_values)
        self.file.read_dict(
            (
                config if config and config.has_config else self.base_config
            ).setting_values
        )
        self.update_definitions()

    def copy(self, config: ConfigHandler | None = None) -> AppConfig:
        """Copy the config.

        Args:
            config: to load from if provided, otherwise use app-wide configuration.
        """
        return AppConfig(self.app_config, self.base_config, config)
