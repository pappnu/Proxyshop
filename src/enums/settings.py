"""
* Enums: Settings
"""

from enum import StrEnum, nonmember
from typing import Protocol, runtime_checkable


@runtime_checkable
class HasDefault(Protocol):
    Default: nonmember[str]


"""
* App Settings
"""


class OutputFileType(StrEnum):
    JPG = "jpg"
    PNG = "png"
    PSD = "psd"

    Default = nonmember(JPG)


class ScryfallSorting(StrEnum):
    Released = "released"
    Set = "set"
    Rarity = "rarity"
    USD = "usd"
    EUR = "eur"
    EDHRec = "edhrec"
    Artist = "artist"

    Default = nonmember(Released)


class ScryfallUnique(StrEnum):
    Prints = "prints"
    Arts = "arts"

    Default = nonmember(Arts)


"""
* Base Settings
"""


class CollectorMode(StrEnum):
    Normal = "default"
    Modern = "modern"
    Minimal = "minimal"
    ArtistOnly = "artist"

    Default = nonmember(Normal)


class BorderColor(StrEnum):
    Black = "black"
    White = "white"
    Silver = "silver"
    Gold = "gold"

    Default = nonmember(Black)


class CollectorPromo(StrEnum):
    Automatic = "automatic"
    Always = "always"
    Never = "never"

    Default = nonmember(Automatic)


class WatermarkMode(StrEnum):
    Disabled = "Disabled"
    Automatic = "Automatic"
    Fallback = "Fallback"
    Forced = "Forced"

    Default = nonmember(Disabled)


class FillMode(StrEnum):
    NO_FILL = "No Fill"
    CONTENT_AWARE_FILL = "Content-Aware Fill"
    GENERATIVE_FILL = "Generative Fill"
    REMOVE_CONTENT_FILL = "Remove Content Fill"


"""
* Template: Borderless
"""


class BorderlessColorMode(StrEnum):
    All = "All"
    Twins_And_PT = "Twins and PT"
    Textbox = "Textbox"
    Twins = "Twins"
    PT = "PT Box"
    Disabled = "None"

    Default = nonmember(Twins_And_PT)


class BorderlessTextbox(StrEnum):
    Automatic = "Automatic"
    Textless = "Textless"
    Normal = "Normal"
    Medium = "Medium"
    Short = "Short"
    Tall = "Tall"

    Default = nonmember(Automatic)


"""
* Template: Modern Classic
"""


class ModernClassicCrown(StrEnum):
    Pinlines = "Pinlines"
    TexturePinlines = "Texture Pinlines"
    TextureBackground = "Texture Background"

    Default = nonmember(Pinlines)
