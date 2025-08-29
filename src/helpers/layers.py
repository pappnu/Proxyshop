"""
* Helpers: Layers and Layer Groups
"""

# Standard Library Imports
from contextlib import suppress
from collections.abc import Sequence, Iterable

# Third Party Imports
from photoshop.api import (
    DialogModes,
    ActionDescriptor,
    ActionReference,
    BlendMode,
    ElementPlacement,
)
from photoshop.api._artlayer import ArtLayer
from photoshop.api._document import Document
from photoshop.api._layerSet import LayerSet

# Local Imports
from src import APP, ENV
from src.utils.adobe import (
    LayerContainer,
    LayerContainerTypes,
    ReferenceLayer,
    PS_EXCEPTIONS,
)

# QOL Definitions
NO_DIALOG = DialogModes.DisplayNoDialogs


"""
* Searching Layers
"""


def getLayer(
    name: str,
    group: str
    | None
    | LayerContainerTypes
    | Iterable[LayerContainerTypes | str | None] = None,
) -> ArtLayer | None:
    """Retrieve ArtLayer object from given name and group/group tree.

    Args:
        name: Name of the layer.
        group: Parent group (name or object), or ordered list of groups (names, or first can be an object).

    Returns:
        Layer object requested
    """
    try:
        # LayerSet provided?
        if not group:
            # LayerSet not provided
            return APP.instance.activeDocument.artLayers[name]
        elif isinstance(group, str):
            # LayerSet name given
            return APP.instance.activeDocument.layerSets[group].artLayers[name]
        elif isinstance(group, LayerContainer):
            # LayerSet object given
            return group.artLayers[name]
        elif isinstance(group, tuple | list):
            # Tuple or list of LayerSets
            layer_set = APP.instance.activeDocument
            for g in group:
                if isinstance(g, str):
                    # LayerSet name given
                    layer_set = layer_set.layerSets[g]
                elif isinstance(g, LayerContainer):
                    # LayerSet object given
                    layer_set = g
            return layer_set.artLayers[name]
        # ArtLayer can't be located
        raise OSError("ArtLayer invalid")
    except PS_EXCEPTIONS:
        # Layer couldn't be found
        if ENV.DEV_MODE:
            print(f'Layer "{name}" could not be found!')
            if group and isinstance(group, LayerSet):
                print(f"LayerSet reference used: {group.name}")
            elif group and isinstance(group, str):
                print(f"LayerSet reference used: {group}")
    return


def getLayerSet(
    name: str,
    group: str
    | None
    | LayerContainerTypes
    | Iterable[LayerContainerTypes | str | None] = None,
) -> LayerSet | None:
    """Retrieve layer group object.

    Args:
        name: Name of the group to look for.
        group: Parent group (name or object), or ordered list of groups (names, or first can be an object).

    Returns:
        Group object requested.
    """
    try:
        # Was LayerSet provided?
        if not group:
            # No LayerSet given
            return APP.instance.activeDocument.layerSets[name]
        elif isinstance(group, str):
            # LayerSet name given
            return APP.instance.activeDocument.layerSets[group].layerSets[name]
        elif isinstance(group, tuple | list):
            # Tuple or list of groups
            layer_set = APP.instance.activeDocument
            for g in group:
                if isinstance(g, str):
                    # LayerSet name given
                    layer_set = layer_set.layerSets[g]
                elif isinstance(g, LayerContainer):
                    # LayerSet object given
                    layer_set = g
            return layer_set.layerSets[name]
        elif isinstance(group, LayerContainer):
            # LayerSet object given
            return group.layerSets[name]
        # LayerSet can't be located
        raise OSError("LayerSet invalid")
    except PS_EXCEPTIONS:
        # LayerSet couldn't be found
        if ENV.DEV_MODE:
            print(f'LayerSet "{name}" could not be found!')
            if group and isinstance(group, LayerSet):
                print(f"LayerSet reference used: {group.name}")
            elif group and isinstance(group, str):
                print(f"LayerSet reference used: {group}")
    return


def get_reference_layer(
    name: str, group: None | str | LayerSet | Document = None
) -> ReferenceLayer | None:
    """Get an ArtLayer that is a static reference layer.

    Args:
        name: Name of the reference layer.
        group: Name of a LayerSet or LayerSet object which contains the reference layer, if provided.

    Notes:
        ReferenceLayer is a subclass of ArtLayer which includes
            supplemental features for caching and improving execution
            time on bounds and dimensions handling.
    """

    # Select the proper group if str or None provided
    if not group:
        group = APP.instance.activeDocument
    if isinstance(group, str):
        try:
            group = APP.instance.activeDocument.layerSets[group]
        except PS_EXCEPTIONS:
            group = APP.instance.activeDocument

    # Select the reference layer
    with suppress(Exception):
        return ReferenceLayer(parent=group.artLayers.app[name], app=APP.instance)
    return None


"""
* Creating Layers
"""


def create_new_layer(layer_name: str | None = None) -> ArtLayer:
    """Creates a new layer below the currently active layer. The layer will be visible.

    Args:
        layer_name: Optional name for the new layer

    Returns:
        Newly created layer object
    """
    # Create new layer at top of layers
    active_layer = APP.instance.activeDocument.activeLayer
    layer = APP.instance.activeDocument.artLayers.add()
    layer.name = layer_name or "Layer"

    # Name it & set blend mode to normal
    layer.blendMode = BlendMode.NormalBlend

    # Move the layer below
    layer.move(active_layer, ElementPlacement.PlaceAfter)
    return layer


def merge_layers(
    layers: list[ArtLayer | LayerSet], name: str | None = None
) -> ArtLayer:
    """Merge a set of layers together.

    Args:
        layers: Layers to be merged, uses active if not provided.
        name: Name of the newly created layer.

    Returns:
        Returns the merged layer.
    """
    # TODO Check if this can merge layer groups with layers.

    # Return layer if only one is present in the list
    if len(layers) == 1 and isinstance((layer := layers[0]), ArtLayer):
        return layer

    # Select none, then select entire list
    if layers:
        select_layers(layers)

    # Merge layers and return result
    APP.instance.executeAction(APP.instance.sID("mergeLayersNew"), None, NO_DIALOG)

    active_layer = APP.instance.activeDocument.activeLayer
    if not isinstance(active_layer, ArtLayer):
        raise ValueError(
            "Failed to merge layers. Active layer is unexpectedly not an ArtLayer."
        )

    if name:
        active_layer.name = name
    return active_layer


"""
* Layer Groups
"""


def group_layers(
    name: str = "New Group",
    layers: list[ArtLayer | LayerSet] | None = None,
) -> LayerSet:
    """Groups the selected layers.

    Args:
        name: Name of the new group.
        layers: Layers to group, will use active if not provided.

    Returns:
        The newly created group.
    """
    # Select layers if given
    if layers:
        select_layers(layers)

    # Group the layers
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref2 = ActionReference()
    ref1.putClass(APP.instance.sID("layerSection"))
    desc1.putReference(APP.instance.sID("null"), ref1)
    ref2.putEnumerated(
        APP.instance.cID("Lyr "), APP.instance.cID("Ordn"), APP.instance.cID("Trgt")
    )
    desc1.putReference(APP.instance.cID("From"), ref2)
    desc2 = ActionDescriptor()
    desc2.putString(APP.instance.cID("Nm  "), name)
    desc1.putObject(APP.instance.cID("Usng"), APP.instance.sID("layerSection"), desc2)
    desc1.putInteger(APP.instance.sID("layerSectionStart"), 0)
    desc1.putInteger(APP.instance.sID("layerSectionEnd"), 1)
    desc1.putString(APP.instance.cID("Nm  "), name)
    APP.instance.executeAction(APP.instance.cID("Mk  "), desc1, NO_DIALOG)

    active_layer = APP.instance.activeDocument.activeLayer
    if not isinstance(active_layer, LayerSet):
        raise ValueError(
            "Failed to group layers. Active layer is unexpectedly not a LayerSet."
        )

    return active_layer


def duplicate_group(group: LayerSet, name: str) -> LayerSet:
    """Duplicates current active layer set without renaming contents.

    Args:
        name: Name to give the newly created layer set.

    Returns:
        The newly created layer set object.
    """
    select_layer(group)

    desc241 = ActionDescriptor()
    ref4 = ActionReference()
    ref4.putEnumerated(
        APP.instance.sID("layer"),
        APP.instance.sID("ordinal"),
        APP.instance.sID("targetEnum"),
    )
    desc241.putReference(APP.instance.sID("target"), ref4)
    desc241.putString(APP.instance.sID("name"), name)
    desc241.putInteger(APP.instance.sID("version"), 5)
    APP.instance.executeAction(APP.instance.sID("duplicate"), desc241, NO_DIALOG)

    active_layer = APP.instance.activeDocument.activeLayer
    if not isinstance(active_layer, LayerSet):
        raise ValueError(
            "Failed to duplicate group. Active layer is unexpectedly not a LayerSet."
        )

    return active_layer


def merge_group(group: LayerSet | None = None) -> None:
    """Merges a layer set into a single layer.

    Args:
        group: Layer set to merge. Merges active if not provided.
    """
    if group:
        APP.instance.activeDocument.activeLayer = group
    APP.instance.executeAction(APP.instance.sID("mergeLayersNew"), None, NO_DIALOG)


"""
* Smart Layers
"""


def smart_layer(
    layer: ArtLayer | LayerSet | None = None, docref: Document | None = None
) -> ArtLayer:
    """Makes a given layer, or the currently selected layer(s) into a smart layer.

    Args:
        layer: Layer to turn into smart layer, use active layer(s) if not provided.
        docref: Document reference, use active if not provided.
    """
    docref = docref or APP.instance.activeDocument
    if layer:
        docref.activeLayer = layer
    APP.instance.executeAction(APP.instance.sID("newPlacedLayer"), None, NO_DIALOG)

    active_layer = APP.instance.activeDocument.activeLayer
    if not isinstance(active_layer, ArtLayer):
        raise ValueError(
            "Failed to convert layer to smart layer. Active layer is unexpectedly not an ArtLayer."
        )

    return active_layer


def edit_smart_layer(
    layer: ArtLayer | None = None, docref: Document | None = None
) -> None:
    """Opens the contents of a given smart layer (as a separate document) for editing.

    Args:
        layer: Smart layer to open for editing, use active if not provided.
        docref: Document reference, use active if not provided.
    """
    if layer:
        docref = docref or APP.instance.activeDocument
        docref.activeLayer = layer
    APP.instance.executeAction(
        APP.instance.sID("placedLayerEditContents"), None, NO_DIALOG
    )


def unpack_smart_layer(
    layer: ArtLayer | None = None, docref: Document | None = None
) -> None:
    """Converts a smart layer back into its separate components.

    Args:
        layer: Smart layer to unpack into regular layers, use active if not provided.
        docref: Document reference, use active if not provided.
    """
    if layer:
        docref = docref or APP.instance.activeDocument
        docref.activeLayer = layer
    APP.instance.executeAction(
        APP.instance.sID("placedLayerConvertToLayers"), None, NO_DIALOG
    )


"""
* Layer Locking
"""


def lock_layer(layer: ArtLayer | LayerSet, protection: str = "protectAll") -> None:
    """Locks the given layer.

    Args:
        layer: The layer to lock.
        protection: protectAll to lock, protectNone to unlock
    """
    d1 = ActionDescriptor()
    d2 = ActionDescriptor()
    r1 = ActionReference()
    r1.putIdentifier(APP.instance.sID("layer"), layer.id)
    d1.putReference(APP.instance.sID("target"), r1)
    d2.putBoolean(APP.instance.sID(protection), True)
    idlayerLocking = APP.instance.sID("layerLocking")
    d1.putObject(idlayerLocking, idlayerLocking, d2)
    APP.instance.executeAction(APP.instance.sID("applyLocking"), d1, NO_DIALOG)


def unlock_layer(layer: ArtLayer | LayerSet) -> None:
    """Unlocks the given layer.

    Args:
        layer: The layer to unlock.
    """
    lock_layer(layer, "protectNone")


"""
* Selecting Layers
"""


def select_layer(layer: ArtLayer | LayerSet, make_visible: bool = False) -> None:
    """Select a layer and optionally make it visible.

    Args:
        layer: Layer to select.
        make_visible: Whether to force the layer to be visible.
    """
    d1 = ActionDescriptor()
    r1 = ActionReference()
    r1.putIdentifier(APP.instance.sID("layer"), layer.id)
    d1.putReference(APP.instance.sID("target"), r1)
    d1.putBoolean(APP.instance.sID("makeVisible"), make_visible)
    APP.instance.executeAction(APP.instance.sID("select"), d1, NO_DIALOG)


def select_layer_add(layer: ArtLayer | LayerSet, make_visible: bool = False) -> None:
    """Add layer to currently selected and optionally force it to be visible.

    Args:
        layer: Layer to select.
        make_visible: Make the layer visible if not currently visible.
    """
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putIdentifier(APP.instance.sID("layer"), layer.id)
    desc1.putReference(APP.instance.sID("target"), ref1)
    desc1.putEnumerated(
        APP.instance.sID("selectionModifier"),
        APP.instance.sID("selectionModifierType"),
        APP.instance.sID("addToSelection"),
    )
    desc1.putBoolean(APP.instance.sID("makeVisible"), make_visible)
    APP.instance.executeAction(APP.instance.sID("select"), desc1, NO_DIALOG)


def select_layers(layers: Sequence[ArtLayer | LayerSet]) -> None:
    """Makes a list of layers active (selected) in the layer panel.

    Args:
        layers: List of layers or layer sets.
    """
    # Select no layers
    if not layers:
        return
    if len(layers) == 1:
        APP.instance.activeDocument.activeLayer = layers[0]
    select_no_layers()

    # ID's and descriptors
    idLayer = APP.instance.sID("layer")
    idSelect = APP.instance.sID("select")
    idTarget = APP.instance.sID("target")
    idAddToSel = APP.instance.sID("addToSelection")
    idSelMod = APP.instance.sID("selectionModifier")
    idSelModType = APP.instance.sID("selectionModifierType")
    d1, r1 = ActionDescriptor(), ActionReference()

    # Select initial layer
    r1.putIdentifier(idLayer, layers[0].id)
    d1.putReference(idTarget, r1)
    d1.putEnumerated(idSelMod, idSelModType, idAddToSel)
    d1.putBoolean(APP.instance.sID("makeVisible"), False)
    APP.instance.executeAction(idSelect, d1, NO_DIALOG)

    # Select each additional layer
    for lay in layers[1:]:
        r1.putIdentifier(idLayer, lay.id)
        d1.putReference(idTarget, r1)
        APP.instance.executeAction(idSelect, d1, NO_DIALOG)


def select_no_layers() -> None:
    """Deselect all layers."""
    d1, r1 = ActionDescriptor(), ActionReference()
    r1.putEnumerated(
        APP.instance.sID("layer"),
        APP.instance.sID("ordinal"),
        APP.instance.sID("targetEnum"),
    )
    d1.putReference(APP.instance.sID("target"), r1)
    APP.instance.executeAction(APP.instance.sID("selectNoLayers"), d1, NO_DIALOG)
