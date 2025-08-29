"""
* Helpers: Actions
"""

# Third Party Imports
from photoshop.api import DialogModes, ActionDescriptor, ActionReference

# Local Imports
from src import APP

# QOL Definitions
NO_DIALOG = DialogModes.DisplayNoDialogs

"""
* Working With Actions
"""


def run_action(action_set: str, action: str) -> None:
    """Runs a Photoshop action.

    Args:
        action_set: Name of the group the action is in.
        action: Name of the action.
    """
    desc310 = ActionDescriptor()
    ref7 = ActionReference()
    desc310.putBoolean(APP.instance.sID("dontRecord"), False)
    desc310.putBoolean(APP.instance.sID("forceNotify"), True)
    ref7.putName(APP.instance.sID("action"), action)
    ref7.putName(APP.instance.sID("actionSet"), action_set)
    desc310.putReference(APP.instance.sID("target"), ref7)
    APP.instance.executeAction(APP.instance.sID("play"), desc310, NO_DIALOG)
