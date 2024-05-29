"""
Utility functions leveraged by CLI tool.
"""

import click


def debug_msg(debug: bool, message: str) -> None:
    """
    Helper function to print out debug messages if the debug flag is set.

    Args:
        debug (bool): Debug flag ( default is False )
        message (str): Debug message
    """
    if debug:
        click.secho(f"DEBUG: {message}", fg="yellow")


def debug_result(debug: bool, result: tuple[bool, str]) -> None:
    """
    Helper function to print debug messages from device actions.

    Args:
        debug (bool): Debug flag ( default is False )
        result (tuple): A tuple object with first item a bool on status and second a reason message
    """
    if debug:
        debug_msg(debug, f"Action Successful: {result[0]}")
        debug_msg(debug, f"Message: '{result[1]}'")


def check_result(
    device: str, action: str, result: tuple[bool, str], debug: bool = False
) -> None:
    """
    Helper function to verify the results of a device action.

    If the action was unsuccessful, a message will be printed
    to std_error

    Args:
        device (str): The name of the device
        action (str): A string descirption of action
        result (tuple): A tuple object with first item a bool on status and second a reason message
        debug (bool): Debug flag ( default is False )
    """
    if debug:
        debug_result(debug, result)

    # Unpack the result
    success, reason = result

    if not success:
        click.secho(
            f"ERROR: Action {action} on Device {device} failed with reason '{reason}'",
            fg="red",
            err=True,
        )
