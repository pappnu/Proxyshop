"""
* Helpers: Masks
"""

# Standard Library Imports
from _ctypes import COMError

# Third Party Imports
from photoshop.api import ActionDescriptor, ActionReference, DialogModes
from photoshop.api._artlayer import ArtLayer
from photoshop.api._layerSet import LayerSet

# Local Imports
from src import APP
from src.helpers.selection import select_canvas

# QOL Definitions
NO_DIALOG = DialogModes.DisplayNoDialogs

"""
* Copying Masks
"""


def copy_layer_mask(
    layer_from: ArtLayer | LayerSet, layer_to: ArtLayer | LayerSet
) -> None:
    """Copies mask from one layer to another.

    Args:
        layer_from: Layer to copy from.
        layer_to: Layer to copy to.
    """
    desc1 = ActionDescriptor()
    ref17 = ActionReference()
    ref18 = ActionReference()
    desc1.putClass(APP.instance.sID("new"), APP.instance.sID("channel"))
    ref17.putEnumerated(
        APP.instance.sID("channel"),
        APP.instance.sID("channel"),
        APP.instance.sID("mask"),
    )
    ref17.putIdentifier(APP.instance.sID("layer"), layer_to.id)
    desc1.putReference(APP.instance.sID("at"), ref17)
    ref18.putEnumerated(
        APP.instance.sID("channel"),
        APP.instance.sID("channel"),
        APP.instance.sID("mask"),
    )
    ref18.putIdentifier(APP.instance.sID("layer"), layer_from.id)
    desc1.putReference(APP.instance.sID("using"), ref18)
    APP.instance.executeAction(APP.instance.sID("make"), desc1, NO_DIALOG)


def copy_vector_mask(
    layer_from: ArtLayer | LayerSet, layer_to: ArtLayer | LayerSet
) -> None:
    """Copies vector mask from one layer to another.

    Args:
        layer_from: Layer to copy from.
        layer_to: Layer to copy to.
    """
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref2 = ActionReference()
    ref3 = ActionReference()
    ref1.putClass(APP.instance.sID("path"))
    desc1.putReference(APP.instance.sID("target"), ref1)
    ref2.putEnumerated(
        APP.instance.sID("path"),
        APP.instance.sID("path"),
        APP.instance.sID("vectorMask"),
    )
    ref2.putIdentifier(APP.instance.sID("layer"), layer_to.id)
    desc1.putReference(APP.instance.sID("at"), ref2)
    ref3.putEnumerated(
        APP.instance.sID("path"),
        APP.instance.sID("path"),
        APP.instance.sID("vectorMask"),
    )
    ref3.putIdentifier(APP.instance.sID("layer"), layer_from.id)
    desc1.putReference(APP.instance.sID("using"), ref3)
    APP.instance.executeAction(APP.instance.sID("make"), desc1, NO_DIALOG)


"""
* Applying Masks
"""


def apply_mask_to_layer_fx(layer: ArtLayer | LayerSet | None = None) -> None:
    """Sets the layer mask to apply only to layer effects in blending options.

    Args:
        layer: ArtLayer or LayerSet object.
    """
    if not layer:
        layer = APP.instance.activeDocument.activeLayer
    ref = ActionReference()
    ref.putIdentifier(APP.instance.sID("layer"), layer.id)
    desc = APP.instance.executeActionGet(ref)
    layer_fx = desc.getObjectValue(APP.instance.sID("layerEffects"))
    layer_fx.putBoolean(APP.instance.sID("layerMaskAsGlobalMask"), True)
    desc = ActionDescriptor()
    desc.putReference(APP.instance.sID("target"), ref)
    desc.putObject(APP.instance.sID("to"), APP.instance.sID("layer"), layer_fx)
    APP.instance.executeAction(APP.instance.sID("set"), desc, NO_DIALOG)


def set_layer_mask(
    layer: ArtLayer | LayerSet | None = None, visible: bool = True
) -> None:
    """Set the visibility of a layer's mask.

    Args:
        layer: ArtLayer object.
        visible: Whether to make the layer mask visible.
    """
    if not layer:
        layer = APP.instance.activeDocument.activeLayer
    desc1 = ActionDescriptor()
    desc2 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putIdentifier(APP.instance.cID("Lyr "), layer.id)
    desc1.putReference(APP.instance.sID("target"), ref1)
    desc2.putBoolean(APP.instance.cID("UsrM"), visible)
    desc1.putObject(APP.instance.cID("T   "), APP.instance.cID("Lyr "), desc2)
    APP.instance.executeAction(APP.instance.cID("setd"), desc1, NO_DIALOG)


def enable_mask(layer: ArtLayer | LayerSet | None = None) -> None:
    """Enables a given layer's mask.

    Args:
        layer: ArtLayer object.
    """
    set_layer_mask(layer, True)


def disable_mask(layer: ArtLayer | LayerSet | None = None) -> None:
    """Disables a given layer's mask.

    Args:
        layer: ArtLayer object.
    """
    set_layer_mask(layer, False)


def apply_mask(layer: ArtLayer | LayerSet | None = None) -> None:
    """Applies a given layer's mask.

    Args:
        layer: ArtLayer or LayerSet object, use active layer if not provided.
    """
    if layer:
        APP.instance.activeDocument.activeLayer = layer
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putEnumerated(
        APP.instance.sID("channel"),
        APP.instance.sID("channel"),
        APP.instance.sID("mask"),
    )
    desc1.putReference(APP.instance.sID("target"), ref1)
    desc1.putBoolean(APP.instance.sID("apply"), True)
    APP.instance.executeAction(APP.instance.sID("delete"), desc1, NO_DIALOG)


def set_layer_vector_mask(
    layer: ArtLayer | LayerSet | None = None, visible: bool = False
) -> None:
    """Set the visibility of a layer's vector mask.

    Args:
        layer: ArtLayer object.
        visible: Whether to make the vector mask visible.
    """
    if not layer:
        layer = APP.instance.activeDocument.activeLayer
    desc1 = ActionDescriptor()
    desc2 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putIdentifier(APP.instance.sID("layer"), layer.id)
    desc1.putReference(APP.instance.sID("target"), ref1)
    desc2.putBoolean(APP.instance.sID("vectorMaskEnabled"), visible)
    desc1.putObject(APP.instance.sID("to"), APP.instance.sID("layer"), desc2)
    APP.instance.executeAction(APP.instance.sID("set"), desc1, NO_DIALOG)


def enable_vector_mask(layer: ArtLayer | LayerSet | None = None) -> None:
    """Enables a given layer's vector mask.

    Args:
        layer: ArtLayer object.
    """
    set_layer_vector_mask(layer, True)


def disable_vector_mask(layer: ArtLayer | LayerSet | None = None) -> None:
    """Disables a given layer's vector mask.

    Args:
        layer: ArtLayer object.
    """
    set_layer_vector_mask(layer, False)


"""
* Editing Masks
"""


def enter_mask_channel(layer: ArtLayer | LayerSet | None = None):
    """Enters mask channel to allow working with current layer's mask.

    Args:
        layer: Layer to make active, if provided.
    """
    if layer:
        APP.instance.activeDocument.activeLayer = layer
    d1 = ActionDescriptor()
    r1 = ActionReference()
    r1.putEnumerated(
        APP.instance.sID("channel"),
        APP.instance.sID("channel"),
        APP.instance.sID("mask"),
    )
    d1.putReference(APP.instance.sID("target"), r1)
    d1.putBoolean(APP.instance.sID("makeVisible"), True)
    APP.instance.executeAction(APP.instance.sID("select"), d1, NO_DIALOG)


def enter_rgb_channel(layer: ArtLayer | LayerSet | None = None):
    """Enters the RGB channel (default channel).

    Args:
        layer: Layer to make active, if provided.
    """
    if layer:
        APP.instance.activeDocument.activeLayer = layer
    d1 = ActionDescriptor()
    r1 = ActionReference()
    r1.putEnumerated(
        APP.instance.sID("channel"),
        APP.instance.sID("channel"),
        APP.instance.sID("RGB"),
    )
    d1.putReference(APP.instance.sID("target"), r1)
    d1.putBoolean(APP.instance.sID("makeVisible"), True)
    APP.instance.executeAction(APP.instance.sID("select"), d1, NO_DIALOG)


def create_mask(layer: ArtLayer | LayerSet | None = None):
    """Add a mask to provided or active layer.

    Args:
        layer: Layer to make active, if provided.
    """
    if layer:
        APP.instance.activeDocument.activeLayer = layer
    d1 = ActionDescriptor()
    r1 = ActionReference()
    d1.putClass(APP.instance.sID("new"), APP.instance.sID("channel"))
    r1.putEnumerated(
        APP.instance.sID("channel"),
        APP.instance.sID("channel"),
        APP.instance.sID("mask"),
    )
    d1.putReference(APP.instance.sID("at"), r1)
    d1.putEnumerated(
        APP.instance.sID("using"),
        APP.instance.sID("userMaskEnabled"),
        APP.instance.sID("revealAll"),
    )
    APP.instance.executeAction(APP.instance.sID("make"), d1, NO_DIALOG)


def copy_to_mask(
    target: ArtLayer | LayerSet,
    source: ArtLayer | LayerSet | None = None,
):
    """Copies the pixels of the current layer, creates a mask on target layer,
    enters that layer's mask, and pastes to the mask before exiting the mask.

    Args:
        target: Layer to create a mask on and paste the copied pixels.
        source: Layer to copy pixels from, use active if not provided.
    """

    # Select canvas and copy
    docref = APP.instance.activeDocument
    if source:
        docref.activeLayer = source
    docsel = docref.selection
    select_canvas(docref)
    docsel.copy()
    docsel.deselect()

    # Create a mask, enter, paste, and exit
    docref.activeLayer = target
    create_mask()
    enter_mask_channel()
    try:
        docref.paste()
    except COMError:
        # The operation likely succeeded, but an error was thrown anyways
        pass
    enter_rgb_channel()


"""
* Removing Masks
"""


def delete_mask(layer: ArtLayer | LayerSet | None = None) -> None:
    """Removes a given layer's mask.

    Args:
        layer: ArtLayer ore LayerSet object, use active layer if not provided.
    """
    if layer:
        APP.instance.activeDocument.activeLayer = layer
    desc1 = ActionDescriptor()
    ref1 = ActionReference()
    ref1.putEnumerated(
        APP.instance.sID("channel"),
        APP.instance.sID("ordinal"),
        APP.instance.sID("targetEnum"),
    )
    desc1.putReference(APP.instance.sID("target"), ref1)
    APP.instance.executeAction(APP.instance.sID("delete"), desc1, NO_DIALOG)
